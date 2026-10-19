"""
Tokenizer & Prefix Fingerprinting Service for ContextPulse.
Handles token estimation, SHA-256 prefix hashing, and Longest Common Prefix (LCP) matching.
"""

import hashlib
from typing import Tuple, Optional, List

try:
    import tiktoken
    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENCODER = None


class TokenizerService:
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Count tokens in text using tiktoken cl100k_base if available,
        falling back to a calibrated 3.8 chars/token heuristic.
        """
        if not text:
            return 0
        if _TIKTOKEN_ENCODER is not None:
            try:
                return len(_TIKTOKEN_ENCODER.encode(text))
            except Exception:
                pass
        # Calibrated heuristic: 1 token ~= 3.8 characters for English/code
        words = len(text.split())
        chars = len(text)
        return max(1, int(chars / 3.8) if chars > 0 else words)

    @staticmethod
    def compute_sha256(text: str) -> str:
        """
        Generate a deterministic SHA-256 hex digest for normalized prefix text.
        """
        normalized = text.strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_prefix(text: str, token_threshold: int) -> Tuple[str, str, int]:
        """
        Splits text into (prefix, suffix, prefix_token_count).
        If total tokens < token_threshold, prefix is text and suffix is empty.
        Otherwise extracts prefix containing approximately token_threshold tokens.
        """
        total_tokens = TokenizerService.count_tokens(text)
        if total_tokens <= token_threshold:
            return text, "", total_tokens

        if _TIKTOKEN_ENCODER is not None:
            try:
                tokens = _TIKTOKEN_ENCODER.encode(text)
                prefix_tokens = tokens[:token_threshold]
                suffix_tokens = tokens[token_threshold:]
                prefix_str = _TIKTOKEN_ENCODER.decode(prefix_tokens)
                suffix_str = _TIKTOKEN_ENCODER.decode(suffix_tokens)
                return prefix_str, suffix_str, len(prefix_tokens)
            except Exception:
                pass

        # Heuristic character-based boundary split
        split_index = int(len(text) * (token_threshold / total_tokens))
        prefix_str = text[:split_index]
        suffix_str = text[split_index:]
        prefix_tokens = TokenizerService.count_tokens(prefix_str)
        return prefix_str, suffix_str, prefix_tokens

    @staticmethod
    def longest_common_prefix(s1: str, s2: str) -> str:
        """
        Calculates the longest common prefix string between two texts.
        """
        limit = min(len(s1), len(s2))
        i = 0
        while i < limit and s1[i] == s2[i]:
            i += 1
        return s1[:i]
