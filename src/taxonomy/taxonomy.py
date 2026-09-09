"""Intent taxonomy management, validation, and schema definitions."""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.common.config import CONFIGS_DIR


class IntentTaxonomy:
    """Manager for the AppleSupport 10-intent taxonomy."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else (CONFIGS_DIR / "intents.yaml")
        self._intents_data = self._load_taxonomy()
        self.intent_names = list(self._intents_data.keys())

    def _load_taxonomy(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Taxonomy config not found at: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("intents", {})

    def get_intent_names(self) -> List[str]:
        """Return list of valid intent labels."""
        return self.intent_names.copy()

    def is_valid_intent(self, intent: str) -> bool:
        """Check if an intent label exists in taxonomy."""
        return intent in self._intents_data

    def get_intent_info(self, intent: str) -> Dict[str, Any]:
        """Get metadata, description, and examples for an intent."""
        if not self.is_valid_intent(intent):
            raise KeyError(f"Unknown intent: {intent}. Valid intents: {self.intent_names}")
        return self._intents_data[intent]

    def get_intent_description(self, intent: str) -> str:
        """Get concise description of an intent."""
        return self.get_intent_info(intent).get("description", "")

    def get_prompt_taxonomy_summary(self) -> str:
        """Format a clean, structured summary of the taxonomy for LLM prompt injection."""
        lines = []
        for name, data in self._intents_data.items():
            lines.append(f"- {name}: {data.get('description')}")
        return "\n".join(lines)


# Singleton instance for convenience
default_taxonomy = IntentTaxonomy()
