"""
Token counting utilities for text processing.
"""

import tiktoken
from typing import List


class TokenCounter:
    """Handles token counting and text chunking."""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize token counter with a specific model.

        Args:
            model_name: Model name for token encoding
        """
        self.encoding = tiktoken.encoding_for_model(model_name)
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
    ) -> List[str]:
        """
        Split text into chunks suitable for GPT processing.

        Args:
            text: Full subtitle text
            max_tokens_per_chunk: Maximum tokens per chunk

        Returns:
            List of text chunks
        """
        # Split by sentences first
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Check if adding this sentence would exceed token limit
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if self.count_tokens(test_chunk) > max_tokens_per_chunk:
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
                        if self.count_tokens(test_word_chunk) > max_tokens_per_chunk:
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
