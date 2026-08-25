"""Tests for summary generation helpers."""

from yt_summarizer.config import Settings
from yt_summarizer.core.summary import SummaryGenerator


class StubProviderConfig:
    """Avoids constructing a real OpenAI client."""

    provider = "stub"
    model = "stub-model"

    def create_client(self):
        return None


class StubTokenCounter:
    pass


def make_generator(tmp_path) -> SummaryGenerator:
    settings = Settings()
    settings.output.output_dir = str(tmp_path)
    return SummaryGenerator(StubProviderConfig(), StubTokenCounter(), settings)


class TestOutputPathFor:
    def test_includes_video_id(self, tmp_path):
        gen = make_generator(tmp_path)
        path = gen.output_path_for("My Video Title", "Zcwo9yoN_l4")
        assert path.endswith("My_Video_Title_Zcwo9yoN_l4.md")

    def test_sanitizes_title(self, tmp_path):
        gen = make_generator(tmp_path)
        path = gen.output_path_for("What: Happens? Next", "AAAAAAAAAAA")
        assert ":" not in path
        assert "?" not in path
        assert path.endswith("_AAAAAAAAAAA.md")

    def test_without_video_id(self, tmp_path):
        gen = make_generator(tmp_path)
        path = gen.output_path_for("My Video")
        assert path.endswith("My_Video.md")


class TestSaveSummary:
    def test_writes_file_and_returns_path(self, tmp_path):
        gen = make_generator(tmp_path)
        target = str(tmp_path / "video_AAAAAAAAAAA.md")
        result = gen.save_summary("# Doc\n", target)
        assert result == target
        assert (tmp_path / "video_AAAAAAAAAAA.md").read_text() == "# Doc\n"


class TestMergeSummaries:
    def test_single_summary(self, tmp_path):
        gen = make_generator(tmp_path)
        doc = gen.merge_summaries(["- point one"], "Cool Video")
        assert doc.startswith("# Cool Video\n")
        assert "- point one" in doc
        assert "Table of Contents" not in doc

    def test_multi_summary_has_toc(self, tmp_path):
        gen = make_generator(tmp_path)
        doc = gen.merge_summaries(["- a", "- b", "- c"], "Long Video")
        assert "## Table of Contents" in doc
        for i in (1, 2, 3):
            assert f"[Part {i}](#part-{i})" in doc
            assert f"## Part {i}" in doc

    def test_fallback_title(self, tmp_path):
        gen = make_generator(tmp_path)
        doc = gen.merge_summaries(["- x"], "")
        assert doc.startswith("# YouTube Video Summary")
