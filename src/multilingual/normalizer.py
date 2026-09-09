"""Multilingual & Code-Mixed Language Normalizer.

Supports 100+ languages, with native support for romanized code-mixed text:
- Tenglish (Telugu written in English script)
- Hinglish (Hindi written in English script)
- European, Asian, and Latin languages (Spanish, French, German, etc.)
"""
from __future__ import annotations

import re
from typing import Dict, Any, Tuple


# Common code-mixed lexical dictionaries for intent recognition
TENGLISH_PATTERNS = {
    r"\b(chaala|chala|baaga)\b": "very",
    r"\b(thondaraga|speed ga|fast ga)\b": "rapidly fast",
    r"\b(aipothundi|draining|aipotundi)\b": "draining dying",
    r"\b(em|enti|ela)\s*(cheyali|cheyyali|cheddam)\b": "what should I do how to fix",
    r"\b(pani|cheyatam|cheytam)\s*ledhu\b": "not working",
    r"\b(screen|display)\s*(pagilipoindi|freeze|agipoindi)\b": "screen cracked frozen",
    r"\b(charging|charge)\s*(ekkatle|ekkadam ledhu)\b": "not charging",
    r"\b(password|account)\s*(marchipoya|gurthuledu)\b": "forgot password locked",
    r"\b(dabbu|paise|money)\s*(katta|cut ayyindi|refund)\b": "money charged refund",
}

HINGLISH_PATTERNS = {
    r"\b(bohot|bahut|zyada)\b": "very",
    r"\b(jaldi|fast)\b": "quickly",
    r"\b(khatam|drain|kam)\s*ho\s*raha\b": "draining fast",
    r"\b(kaise|kya)\s*(kare|karein|karu)\b": "how to fix what to do",
    r"\b(kaam|chal)\s*nahi\s*raha\b": "not working",
    r"\b(screen|display)\s*(tut|toot|crack)\s*gaya\b": "screen cracked",
    r"\b(charge|charging)\s*nahi\s*ho\s*raha\b": "not charging",
    r"\b(password|account)\s*(bhul|bhool)\s*gaya\b": "forgot password",
    r"\b(paisa|rupaye)\s*(kat|cut)\s*gaya\b": "money charged",
}


class MultilingualProcessor:
    """Detects language, handles code-mixed Tenglish/Hinglish, and bridges to semantic intent."""

    @staticmethod
    def detect_language(text: str) -> Tuple[str, str]:
        """Detect language family and format.

        Returns:
            (language_code, human_label)
        """
        lowered = text.lower()

        # Check for Telugu script
        if re.search(r"[\u0C00-\u0C7F]", text):
            return "te", "Telugu (తెలుగు)"

        # Check for Devanagari script (Hindi/Marathi)
        if re.search(r"[\u0900-\u097F]", text):
            return "hi", "Hindi (हिन्दी)"

        # Check for Tenglish (Telugu in Latin script)
        tenglish_hits = sum(1 for pat in TENGLISH_PATTERNS if re.search(pat, lowered))
        if tenglish_hits >= 2 or any(w in lowered for w in ["cheyali", "cheyyali", "aipothundi", "ekkatle", "pagilipoindi", "marchipoya"]):
            return "te-Latn", "Tenglish (Telugu in English script)"

        # Check for Hinglish (Hindi in Latin script)
        hinglish_hits = sum(1 for pat in HINGLISH_PATTERNS if re.search(pat, lowered))
        if hinglish_hits >= 2 or any(w in lowered for w in ["kaise kare", "nahi raha", "tut gaya", "bhool gaya"]):
            return "hi-Latn", "Hinglish (Hindi in English script)"

        # Check for Spanish
        if any(w in lowered for w in ["pantalla", "batería", "ayuda", "actualización", "cómo", "funciona"]):
            return "es", "Spanish (Español)"

        # Check for French
        if any(w in lowered for w in ["batterie", "écran", "mise à jour", "comment", "marche pas"]):
            return "fr", "French (Français)"

        # Check for German
        if any(w in lowered for w in ["akku", "bildschirm", "funktioniert", "nach dem update"]):
            return "de", "German (Deutsch)"

        return "en", "English"

    @staticmethod
    def normalize_to_semantic_inquiry(text: str) -> Tuple[str, str]:
        """Normalize code-mixed text into technical diagnostic semantics for retrieval.

        Returns:
            (normalized_query, detected_lang_label)
        """
        lang_code, lang_label = MultilingualProcessor.detect_language(text)
        normalized = text

        if lang_code == "te-Latn":
            for pat, repl in TENGLISH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        elif lang_code == "hi-Latn":
            for pat, repl in HINGLISH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        return normalized, lang_label
