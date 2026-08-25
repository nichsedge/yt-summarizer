"""End-to-end tests of the video processing pipeline (all I/O mocked)."""

from unittest.mock import MagicMock, patch

from yt_summarizer.config import Settings
from yt_summarizer.core.summarizer import YouTubeSubtitleSummarizer

VIDEO_URL = "https://www.youtube.com/watch?v=AAAAAAAAAAA"


def make_summarizer(tmp_path, force=False) -> YouTubeSubtitleSummarizer:
    settings = Settings()
    settings.output.output_dir = str(tmp_path)
    summarizer = YouTubeSubtitleSummarizer(
        provider="openai", api_key="test-key", force=force, settings=settings
    )
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "- summarized point\n"
    fake_client.chat.completions.create.return_value = fake_response
    summarizer.summary_generator.client = fake_client
    return summarizer


def run_pipeline(summarizer):
    with (
        patch(
            "yt_summarizer.core.summarizer.get_video_title_from_html",
            return_value="Test Video",
        ),
        patch.object(
            summarizer.transcript_processor,
            "get_subtitles",
            return_value="Sentence one. Sentence two. Sentence three.",
        ),
    ):
        return summarizer.process_video(VIDEO_URL)


class TestProcessVideo:
    def test_generates_named_file(self, tmp_path):
        summarizer = make_summarizer(tmp_path)
        output_file = run_pipeline(summarizer)

        assert output_file == str(tmp_path / "Test_Video_AAAAAAAAAAA.md")
        content = (tmp_path / "Test_Video_AAAAAAAAAAA.md").read_text()
        assert "# Test Video" in content
        assert "- summarized point" in content

    def test_skips_existing_summary(self, tmp_path):
        summarizer = make_summarizer(tmp_path)
        first = run_pipeline(summarizer)

        # Second run must not call the AI again.
        summarizer.summary_generator.client.chat.completions.create.reset_mock()
        second = run_pipeline(summarizer)

        assert first == second
        summarizer.summary_generator.client.chat.completions.create.assert_not_called()

    def test_force_regenerates(self, tmp_path):
        summarizer = make_summarizer(tmp_path)
        run_pipeline(summarizer)

        forced = make_summarizer(tmp_path, force=True)
        output_file = run_pipeline(forced)

        forced.summary_generator.client.chat.completions.create.assert_called()
        content = (tmp_path / "Test_Video_AAAAAAAAAAA.md").read_text()
        assert "- summarized point" in content
        assert output_file == str(tmp_path / "Test_Video_AAAAAAAAAAA.md")

    def test_model_passed_to_token_counter(self, tmp_path):
        summarizer = make_summarizer(tmp_path)
        assert summarizer.token_counter.model_name == "gpt-3.5-turbo"
