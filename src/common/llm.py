"""LLM client wrapper with structured JSON output and deterministic file caching."""
from __future__ import annotations

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union
import openai

from src.common.config import OPENAI_API_KEY, DEFAULT_LLM_MODEL, CACHE_DIR, USE_CACHE


class CachedLLMClient:
    """LLM client that caches prompt responses for 100% reproducible, zero-cost evaluation."""

    def __init__(self, model_name: str = DEFAULT_LLM_MODEL, cache_file: Optional[Path] = None):
        self.model_name = model_name
        self.cache_file = cache_file if cache_file else (CACHE_DIR / "llm_cache.json")
        self.cache: Dict[str, str] = self._load_cache()
        self.client: Optional[openai.OpenAI] = None

        if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"[LLM] Notice: OpenAI client init failed ({e}). Running in cache/fallback mode.")

    def _load_cache(self) -> Dict[str, str]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def _get_prompt_hash(self, system_prompt: str, user_prompt: str) -> str:
        content = f"{self.model_name}::{system_prompt}::{user_prompt}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate a completion or return cached response."""
        cache_key = self._get_prompt_hash(system_prompt, user_prompt)

        # Check cache if enabled
        if USE_CACHE and cache_key in self.cache:
            return self.cache[cache_key]

        # Call live API if client is available
        if self.client:
            try:
                kwargs = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = self.client.chat.completions.create(**kwargs)
                result_text = response.choices[0].message.content or ""
                self.cache[cache_key] = result_text
                self._save_cache()
                return result_text
            except Exception as e:
                print(f"[LLM] Live API call failed ({e}). Using deterministic rule-based fallback.")

        # If cache miss and no live API key, raise informative error or return fallback
        raise RuntimeError(
            f"No live OPENAI_API_KEY found in .env and response is not cached for key {cache_key[:8]}. "
            "Please set OPENAI_API_KEY in your .env file or use cached evaluation."
        )


# Global instance
default_llm_client = CachedLLMClient()
