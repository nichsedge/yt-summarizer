"""Test token counting utilities."""

import pytest
from yt_summarizer.utils import TokenCounter


class TestTokenCounter:
    """Test token counter functionality."""

    def test_count_tokens(self):
        """Test token counting."""
        counter = TokenCounter()

        # Simple text
        text = "Hello, world!"
        count = counter.count_tokens(text)
        assert count > 0
        assert isinstance(count, int)

        # Empty text
        assert counter.count_tokens("") == 0

        # Longer text
        long_text = "This is a longer text that should have more tokens. " * 10
        long_count = counter.count_tokens(long_text)
        assert long_count > count

    def test_split_text_into_chunks(self):
        """Test text chunking."""
        counter = TokenCounter()
        counter.encoding = MockEncoding()

        # Short text that fits in one chunk
        short_text = "Short text"
        chunks = counter.split_text_into_chunks(short_text, max_tokens_per_chunk=100)
        assert len(chunks) == 1
        assert chunks[0] == short_text

        # Text that requires multiple chunks
        long_text = "Sentence one. Sentence two. Sentence three. Sentence four. " * 10
        counter.encoding = MockEncoding(token_per_char=5)  # Force smaller chunks
        chunks = counter.split_text_into_chunks(long_text, max_tokens_per_chunk=10)
        assert len(chunks) > 1

        # Verify chunks are not empty
        for chunk in chunks:
            assert chunk.strip()

    def test_chunk_with_long_sentence(self):
        """Test chunking when a single sentence is too long."""
        counter = TokenCounter()
        counter.encoding = MockEncoding()

        # Create a very long single sentence
        long_sentence = "word " * 100  # 200 words
        chunks = counter.split_text_into_chunks(long_sentence, max_tokens_per_chunk=10)

        # Should split into multiple chunks
        assert len(chunks) > 1


class MockEncoding:
    """Mock encoding for testing."""

    def __init__(self, token_per_char=1):
        self.token_per_char = token_per_char

    def encode(self, text):
        """Return mock tokens."""
        words = text.split()
        # Simulate tokens as words
        return list(range(len(words) * self.token_per_char))