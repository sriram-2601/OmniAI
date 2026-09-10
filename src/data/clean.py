"""Text cleaning, normalization, and PII protection for customer support tweets."""
from __future__ import annotations

import re
import html
from typing import Optional


# Precompiled regex patterns
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
MENTION_PATTERN = re.compile(r"@[\w_]+")
LEADING_MENTIONS_PATTERN = re.compile(r"^(?:@[\w_]+\s*)+")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
MULTI_SPACE_PATTERN = re.compile(r"\s+")


def clean_tweet_text(
    text: str,
    strip_leading_mentions: bool = True,
    anonymize_pii: bool = True,
    preserve_urls: bool = False,
) -> str:
    """Clean and normalize tweet text.

    Args:
        text: Raw tweet text string.
        strip_leading_mentions: If True, remove leading @handles (e.g. '@AppleSupport @115854 Hello' -> 'Hello').
        anonymize_pii: If True, replace emails and phone numbers with placeholders.
        preserve_urls: If False, replace URLs with [URL] or clean domain.

    Returns:
        Cleaned, normalized string.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    # 1. Unescape HTML entities (&amp; -> &, &gt; -> >, &#39; -> ', etc.)
    cleaned = html.unescape(text)

    # 2. Anonymize sensitive PII if present
    if anonymize_pii:
        cleaned = EMAIL_PATTERN.sub("[EMAIL]", cleaned)
        cleaned = PHONE_PATTERN.sub("[PHONE]", cleaned)
        cleaned = CREDIT_CARD_PATTERN.sub("[CREDIT_CARD]", cleaned)

    # 3. Handle leading mentions
    if strip_leading_mentions:
        cleaned = LEADING_MENTIONS_PATTERN.sub("", cleaned)

    # 4. URL normalization
    if not preserve_urls:
        cleaned = URL_PATTERN.sub("[URL]", cleaned)

    # 5. Remove remaining inline numerical customer handle IDs (e.g. '@115854')
    cleaned = re.sub(r"@\d+", "[USER]", cleaned)

    # 6. Normalize whitespace
    cleaned = MULTI_SPACE_PATTERN.sub(" ", cleaned).strip()

    return cleaned


def is_valid_customer_query(text: str, min_words: int = 3) -> bool:
    """Check if customer query has sufficient substantive content for classification."""
    cleaned = clean_tweet_text(text, strip_leading_mentions=True)
    words = cleaned.split()
    if len(words) < min_words:
        return False
    # Check if text is just noise or URLs
    non_url_words = [w for w in words if w not in ("[URL]", "[USER]", "[EMAIL]", "[PHONE]")]
    return len(non_url_words) >= min_words
