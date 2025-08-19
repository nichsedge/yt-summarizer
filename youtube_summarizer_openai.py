import os
import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs
import requests
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import tiktoken

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to remove invalid characters

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove invalid characters and replace spaces with underscores
        return re.sub(r'[<>:"/\\|?*]', '', filename).replace(' ', '_')

class YouTubeSubtitleSummarizer:
    def __init__(self, openai_api_key: str):
        """
        Initialize the YouTube Subtitle Summarizer

        Args:
            openai_api_key: OpenAI API key for GPT access
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.max_tokens_per_chunk = 3000  # Leave room for system prompt and response

    def is_playlist_url(self, url: str) -> bool:
        """
        Detect if the provided URL is a YouTube playlist URL.
        """
        parsed = urlparse(url)
        if parsed.hostname not in ("www.youtube.com", "youtube.com"):
            return False
        if parsed.path == "/playlist":
            return True
        # watch URL can embed playlist via list= param
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            return "list" in qs
        return False

    def extract_video_id(self, url: str) -> str:
        """
        Extract YouTube video ID from URL

        Args:
            url: YouTube video URL

        Returns:
            Video ID string
        """
        parsed_url = urlparse(url)

        # Guard: don't allow playlist URL here
        if self.is_playlist_url(url):
            raise ValueError("Provided URL is a playlist. Use process_playlist() for playlists.")

        if parsed_url.hostname == "youtu.be":
            return parsed_url.path[1:]
        elif parsed_url.hostname in ("www.youtube.com", "youtube.com"):
            if parsed_url.path == "/watch":
                return parse_qs(parsed_url.query)["v"][0]
            elif parsed_url.path[:7] == "/embed/":
                return parsed_url.path.split("/")[2]
            elif parsed_url.path[:3] == "/v/":
                return parsed_url.path.split("/")[2]

        raise ValueError(f"Invalid YouTube URL: {url}")

    def get_subtitles(self, video_id: str) -> str:
        """
        Get English subtitles with priority order

        Args:
            video_id: YouTube video ID

        Returns:
            Subtitle text as string
        """
        try:
            # Instantiate API per latest docs and list available transcripts
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)

            # Priority 1: Official English subtitles (manually created if available)
            try:
                transcript = transcript_list.find_transcript(["en"])
                if not transcript.is_generated:
                    logging.info("Found official English subtitles")
                    fetched = transcript.fetch()
                    # Ensure formatter receives a list of dicts
                    fetched_list = list(fetched) if not isinstance(fetched, list) else fetched
                    return self._format_transcript(fetched_list)
            except Exception:
                logging.debug("Official English subtitles not found or error occurred.")

            # Priority 2: Auto-generated English
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
                logging.info("Found auto-generated English subtitles")
                fetched = transcript.fetch()
                fetched_list = list(fetched) if not isinstance(fetched, list) else fetched
                return self._format_transcript(fetched_list)
            except Exception:
                logging.debug("Auto-generated English subtitles not found or error occurred.")

            # Priority 3: Auto-translated English
            try:
                for transcript in transcript_list:
                    try:
                        translated = transcript.translate("en")
                        logging.info(
                            f"Found subtitles in {transcript.language_code}, translated to English"
                        )
                        fetched = translated.fetch()
                        fetched_list = list(fetched) if not isinstance(fetched, list) else fetched
                        return self._format_transcript(fetched_list)
                    except Exception:
                        logging.debug(f"Could not translate {transcript.language_code} to English.")
                        continue
            except Exception:
                logging.debug("No translatable subtitles found or error occurred during translation.")

            raise Exception("No suitable English subtitles found")

        except Exception as e:
            logging.error(f"Error getting subtitles: {str(e)}")
            raise Exception(f"Error getting subtitles: {str(e)}")

    def extract_playlist_video_ids(self, playlist_url: str) -> List[str]:
        """
        Extract unique video IDs from a YouTube playlist HTML without API keys.

        Strategy:
        - Download playlist page HTML.
        - Regex-scan for watch?v=VIDEO_ID (11-char ID).
        - Deduplicate while preserving order.
        """
        if not self.is_playlist_url(playlist_url):
            raise ValueError("URL is not a playlist URL")

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        resp = requests.get(playlist_url, headers=headers, timeout=30)
        resp.raise_for_status()
        html = resp.text

        pattern = re.compile(r"watch\?v=([A-Za-z0-9_-]{11})")
        seen: Set[str] = set()
        ordered: List[str] = []
        for m in pattern.finditer(html):
            vid = m.group(1)
            if vid not in seen:
                seen.add(vid)
                ordered.append(vid)

        if not ordered:
            logging.warning("No video IDs found in playlist HTML. The page might require JS to render items.")
        return ordered

    def process_playlist(self, playlist_url: str) -> List[str]:
        """
        Process a playlist URL by extracting each video's subtitles, summarizing,
        and saving individual markdown files per video.

        Returns a list of paths to generated files.
        """
        logging.info("Detected playlist URL. Extracting video IDs...")
        video_ids = self.extract_playlist_video_ids(playlist_url)
        logging.info(f"Found {len(video_ids)} video IDs in playlist")

        output_files: List[str] = []
        for idx, vid in enumerate(video_ids, 1):
            try:
                logging.info(f"Processing video {idx}/{len(video_ids)}: {vid}")
                video_url = f"https://www.youtube.com/watch?v={vid}"
                out_path = self.process_video(video_url)
                output_files.append(out_path)
            except Exception as e:
                logging.error(f"Failed to process video {vid}: {e}")
                continue

        return output_files

    def _format_transcript(self, transcript_data: List[Dict]) -> str:
        """
        Format transcript data into clean text

        Args:
            transcript_data: Raw transcript data from YouTube API

        Returns:
            Formatted transcript text
        """
        formatter = TextFormatter()
        formatted_text = formatter.format_transcript(transcript_data)

        # Clean up the text
        formatted_text = re.sub(r"\n+", " ", formatted_text)
        formatted_text = re.sub(r"\s+", " ", formatted_text)
        formatted_text = formatted_text.strip()

        return formatted_text

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks suitable for GPT processing

        Args:
            text: Full subtitle text

        Returns:
            List of text chunks
        """
        # Split by sentences first
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Check if adding this sentence would exceed token limit
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if self.count_tokens(test_chunk) > self.max_tokens_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too long, split it further
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        test_word_chunk = (
                            temp_chunk + " " + word if temp_chunk else word
                        )
                        if (
                            self.count_tokens(test_word_chunk)
                            > self.max_tokens_per_chunk
                        ):
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                chunks.append(word)
                        else:
                            temp_chunk = test_word_chunk
                    if temp_chunk:
                        current_chunk = temp_chunk
            else:
                current_chunk = test_chunk

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def summarize_chunk(self, chunk: str, chunk_number: int, total_chunks: int) -> str:
        """
        Summarize a text chunk using OpenAI API

        Args:
            chunk: Text chunk to summarize
            chunk_number: Current chunk number
            total_chunks: Total number of chunks

        Returns:
            Summarized text in bullet points
        """
        system_prompt = """You are an expert at creating educational summaries. Your task is to:

1. Extract the most important concepts, ideas, and information from the provided text
2. Format the summary as clear, well-structured bullet points
3. Optimize for learning and retention
4. Use proper markdown formatting
5. Group related concepts together
6. Include specific details, examples, and key insights
7. Make it suitable for students and learners

Format your response with:
- Main topic headers using ## 
- Key points as bullet points with -
- Sub-points indented with proper spacing
- Important terms or concepts in **bold**
- Examples or specific details in clear, concise language

Focus on clarity, accuracy, and educational value."""

        user_prompt = f"""Please summarize the following text from a YouTube video transcript (Part {chunk_number} of {total_chunks}):

{chunk}

Create a well-structured summary optimized for learning, using bullet points and proper markdown formatting."""

        try:
            # response = self.client.chat.completions.create(
            #     model="gpt-3.5-turbo",
            #     messages=[
            #         {"role": "system", "content": system_prompt},
            #         {"role": "user", "content": user_prompt}
            #     ],
            #     max_tokens=1000,
            #     temperature=0.3
            # )

            # from openai import OpenAI

            # client = OpenAI(
            #     base_url="http://localhost:11434/v1",
            #     api_key="ollama",
            # )

            # response = client.chat.completions.create(
            #     model="llama3.2:3b",
            #     messages=[
            #         {"role": "system", "content": system_prompt},
            #         {"role": "user", "content": user_prompt},
            #     ],
            # )

            from openai import OpenAI

            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
            )

            response = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://nichsedge.github.io/digital-garden",
                    "X-Title": "Youtube Summarizer",
                },
                extra_body={},
                model="openai/gpt-oss-20b:free",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error summarizing chunk {chunk_number}: {str(e)}"

    def merge_summaries(self, summaries: List[str], video_title: str = "") -> str:
        """
        Merge all summaries into a single Markdown document

        Args:
            summaries: List of summary strings
            video_title: Optional video title for the document

        Returns:
            Complete Markdown document
        """
        # Create header
        title = video_title if video_title else "YouTube Video Summary"
        markdown_doc = f"# {title}\n\n"

        # Add metadata
        markdown_doc += f"*Generated on: {self._get_current_date()}*\n"
        markdown_doc += f"*Total sections: {len(summaries)}*\n\n"

        # Add table of contents if multiple sections
        if len(summaries) > 1:
            markdown_doc += "## Table of Contents\n\n"
            for i in range(len(summaries)):
                markdown_doc += f"- [Part {i + 1}](#part-{i + 1})\n"
            markdown_doc += "\n---\n\n"

        # Add each summary
        for i, summary in enumerate(summaries, 1):
            if len(summaries) > 1:
                markdown_doc += f"## Part {i}\n\n"
            markdown_doc += summary + "\n\n"

            if i < len(summaries):
                markdown_doc += "---\n\n"

        return markdown_doc

    def _get_current_date(self) -> str:
        """Get current date as string"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_video_title(self, video_id: str) -> str:
        """
        Get video title from YouTube (simple method)

        Args:
            video_id: YouTube video ID

        Returns:
            Video title or default string
        """
        try:
            # This is a simple method - for production, consider using YouTube Data API
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = requests.get(url, timeout=20)

            # Extract title from HTML (basic regex)
            title_match = re.search(r"<title>([^<]+)</title>", response.text)
            if title_match:
                title = title_match.group(1)
                # Remove " - YouTube" suffix
                title = re.sub(r" - YouTube$", "", title)
                return title
        except Exception:
            pass

        return "YouTube Video Summary"
    
    

    def process_video(
        self, video_url: str
    ) -> str:
        """
        Complete process: extract subtitles, split, summarize, and merge

        Args:
            video_url: YouTube video URL

        Returns:
            Path to generated markdown file
        """
        try:
            # Extract video ID
            logging.info(f"Extracting video ID from URL...")
            video_id = self.extract_video_id(video_url)
            logging.info(f"Video ID: {video_id}")

            # Get video title
            logging.info(f"Getting video title...")
            video_title = self.get_video_title(video_id)
            logging.info(f"✓ Title: {video_title}")

            # Get subtitles
            logging.info(f"Extracting subtitles...")
            subtitles = self.get_subtitles(video_id)
            logging.info(f"Subtitles extracted: {len(subtitles)} characters")

            # Split into chunks
            logging.info(f"Splitting into chunks...")
            chunks = self.split_text_into_chunks(subtitles)
            logging.info(f"Split into {len(chunks)} chunks")

            # Summarize each chunk
            logging.info(f"Generating summaries...")
            summaries = []
            for i, chunk in enumerate(chunks, 1):
                logging.info(f"  Processing chunk {i}/{len(chunks)}...")
                summary = self.summarize_chunk(chunk, i, len(chunks))
                summaries.append(summary)

            # Merge summaries
            logging.info(f"Merging summaries...")
            final_document = self.merge_summaries(summaries, video_title)

            # Save to file
            output_file = './output/' + sanitize_filename(video_title) + ".md"
            logging.info(f"Saving to file...")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_document)

            logging.info(f"Complete! Summary saved to: {output_file}")
            return output_file

        except Exception as e:
            logging.error(f"Error: {str(e)}")
            raise


def main():
    """
    Example usage of the YouTube Subtitle Summarizer
    """
    # Initialize with your OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")

    summarizer = YouTubeSubtitleSummarizer(api_key)

    # Input can be a video or playlist URL
    # url = "https://www.youtube.com/watch?v=xUdCSq4W1Kk&t=33s"
    url = input("Enter YouTube video or playlist URL: ").strip()

    try:
        if summarizer.is_playlist_url(url):
            outputs = summarizer.process_playlist(url)
            logging.info(f"🎉 Success! Generated {len(outputs)} files")
        else:
            result_file = summarizer.process_video(url)
            logging.info(f"🎉 Success! Your summary is ready: {result_file}")
            # Optionally display the first few lines
            with open(result_file, "r", encoding="utf-8") as f:
                preview = f.read()[:500]
                logging.info(f"\nPreview:\n{preview}...")
    except Exception as e:
        logging.error(f"Failed to process input: {str(e)}")


if __name__ == "__main__":
    main()
