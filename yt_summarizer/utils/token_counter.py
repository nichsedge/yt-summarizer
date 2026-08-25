"""
Token counting utilities for text processing.
"""

import logging
import re

import tiktoken


class TokenCounter:
    """Handles token counting and text chunking."""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize token counter for a model.

        Falls back to cl100k_base when the model is unknown to tiktoken
        (e.g. Claude or Llama served through OpenRouter); counts are then
        a close approximation.

        Args:
            model_name: Model name used to pick the token encoding
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            logging.debug(f"No tiktoken encoding for {model_name!r}; using cl100k_base")
            self.encoding = tiktoken.get_encoding("cl100k_base")
        self.model_name = model_name

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def split_text_into_chunks(
        self, text: str, max_tokens_per_chunk: int = 3000
    ) -> list[str]:
        """
        Split text into chunks of at most max_tokens_per_chunk tokens.

        Packs whole sentences; sentences longer than the limit are packed
        word by word. Each sentence/word is encoded exactly once, so the
        cost is linear in text length. Space characters between units are
        approximated as one token.

        Args:
            text: Full subtitle text
            max_tokens_per_chunk: Maximum tokens per chunk

        Returns:
            List of text chunks (empty if the input has no content)
        """
        if not text or not text.strip():
            return []

        chunks: list[str] = []
        parts: list[str] = []
        parts_tokens = 0

        def flush() -> None:
            nonlocal parts, parts_tokens
            if parts:
                chunks.append(" ".join(parts))
                parts = []
                parts_tokens = 0

        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = sentence.strip()
            if not sentence:
                continue

            n_tokens = len(self.encoding.encode(sentence))
            if n_tokens > max_tokens_per_chunk:
                flush()
                chunks.extend(self._pack_words(sentence, max_tokens_per_chunk))
            elif parts and parts_tokens + n_tokens + 1 > max_tokens_per_chunk:
                flush()
                parts.append(sentence)
                parts_tokens = n_tokens
            else:
                parts.append(sentence)
                parts_tokens += n_tokens + 1

        flush()
        return chunks

    def _pack_words(self, sentence: str, max_tokens_per_chunk: int) -> list[str]:
        """Pack an oversized sentence into chunks word by word."""
        chunks: list[str] = []
        words: list[str] = []
        words_tokens = 0

        for word in sentence.split():
            n_tokens = len(self.encoding.encode(word))
            if words and words_tokens + n_tokens + 1 > max_tokens_per_chunk:
                chunks.append(" ".join(words))
                words = []
                words_tokens = 0
            words.append(word)
            words_tokens += n_tokens + 1

        if words:
            chunks.append(" ".join(words))
        return chunks
