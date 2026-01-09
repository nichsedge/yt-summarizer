"""
Summary generation using AI providers.
"""

import logging
from datetime import datetime
from typing import List

from ..config import settings
from ..exceptions import ProviderError


class SummaryGenerator:
    """Generates summaries using configured AI provider."""

    def __init__(self, provider_config, token_counter):
        """
        Initialize the summary generator.

        Args:
            provider_config: Configured provider instance
            token_counter: Token counter instance
        """
        self.provider_config = provider_config
        self.client = provider_config.create_client()
        self.token_counter = token_counter
        self.settings = settings

    def summarize_chunk(self, chunk: str, chunk_number: int, total_chunks: int) -> str:
        """
        Summarize a text chunk using configured AI provider.

        Args:
            chunk: Text chunk to summarize
            chunk_number: Current chunk number
            total_chunks: Total number of chunks

        Returns:
            Summarized text in bullet points

        Raises:
            ProviderError: If summarization fails
        """
        system_prompt = self.settings.system_prompt
        user_prompt = self.settings.user_prompt_template.format(
            chunk_number=chunk_number, total_chunks=total_chunks, text=chunk
        )

        try:
            # Get provider-specific request kwargs
            request_kwargs = self.provider_config.get_request_kwargs()

            # Create the API request
            response = self.client.chat.completions.create(
                model=self.provider_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **request_kwargs,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            error_msg = f"Error summarizing chunk {chunk_number} with {self.provider_config.provider}: {str(e)}"
            logging.error(error_msg)
            raise ProviderError(error_msg)

    def merge_summaries(self, summaries: List[str], video_title: str = "") -> str:
        """
        Merge all summaries into a single Markdown document.

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

    def save_summary(self, markdown_doc: str, video_title: str) -> str:
        """
        Save summary to a markdown file.

        Args:
            markdown_doc: Complete markdown document
            video_title: Video title for filename

        Returns:
            Path to saved file
        """
        from ..utils import sanitize_filename, ensure_output_dir

        # Ensure output directory exists
        ensure_output_dir(self.settings.output.output_dir)

        # Generate output filename
        output_file = (
            f"{self.settings.output.output_dir}/{sanitize_filename(video_title)}.md"
        )

        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_doc)

        return output_file

    def _get_current_date(self) -> str:
        """Get current date as string."""
        return datetime.now().strftime(self.settings.output.date_format)
