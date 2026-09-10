"""Risk classification layer evaluating financial, security, legal, and safety risks."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Tuple
from src.common.schemas import RiskAssessment


# Precompiled risk keyword patterns (Multilingual: EN, ES-MX/ES, PT-BR, FR-CA, HT, Indigenous)
HIGH_RISK_FINANCIAL = re.compile(
    r"\b(?:unauthorized charge|double charge|charged twice|stolen card|credit card fraud|"
    r"dispute charge|refund money|bank account|compromised card|fraudulent|"
    r"cobro no autorizado|me cobraron doble|cobran[çc]a indevida|doble lana|tarjeta de cr[eé]dito|"
    r"factur[eé] deux fois|yo chaje m|chaje kat mwen|reembolso|debitaron|nechtominqui|guti bidxichi)\b",
    re.IGNORECASE,
)
HIGH_RISK_SECURITY = re.compile(
    r"\b(?:hacked|compromised|stolen phone|someone logged in|locked out of apple id|"
    r"security lock|2fa code not received|two-factor bypass|unrecognized device|"
    r"hackearon|hackearam|cuenta bloqueada|conta invadida|perd[ií] mi contrase[ñn]a|"
    r"esqueci minha senha|mot de passe oubli[eé]|modpas mwen bliye|olvid[eé] mi clave)\b",
    re.IGNORECASE,
)
HIGH_RISK_LEGAL_SAFETY = re.compile(
    r"\b(?:lawyer|lawsuit|sue apple|attorney|legal action|court|swollen battery|"
    r"battery expanded|caught fire|smoke|exploded|sparking|"
    r"bater[ií]a inflada|bater[ií]a hinchada|bateria estufou|sale humo|fum[eé]e|fuma[çc]a|pegando fogo)\b",
    re.IGNORECASE,
)
HIGH_RISK_CYBER_ATTACK = re.compile(
    r"(?:"
    r"'\s*or\s*['\"\d]\s*=\s*['\"\d]|union\s+select|drop\s+table|sleep\s*\(|information_schema|"
    r"<script[\s>]|javascript:|onerror\s*=|onload\s*=|<iframe>|<svg[\s>]|"
    r";\s*(?:cat|rm|whoami|id|ls|dir|netstat|curl|wget)\b|(?:\.\.[/\\]){1,}|"
    r"\{\{.*?\}\}|\$\{.*?\}|"
    r"\b(?:ignore\s+(?:all\s+)?previous\s+instructions|disregard\s+previous|system\s+prompt|"
    r"jailbreak|dan\s+mode|developer\s+mode|bypass\s+safety|you\s+are\s+now\s+unrestricted|"
    r"override\s+rules|exfiltrate|prompt\s+injection)\b"
    r")",
    re.IGNORECASE,
)

MEDIUM_RISK_FRUSTRATION = re.compile(
    r"\b(?:third time|still not working|tried everything|useless|ruined my phone|"
    r"worst update|horrible support|unacceptable|cancel subscription|repair status|"
    r"una porquer[ií]a|p[eé]ssimo|horrible servicio|inaceptable|inadmissible|pa bon menm)\b",
    re.IGNORECASE,
)


class RiskClassifier:
    """Evaluates the risk level of an incoming customer support inquiry."""

    def evaluate_risk(
        self,
        customer_message: str,
        predicted_intent: str,
        intent_confidence: float = 1.0,
    ) -> RiskAssessment:
        """Classify message risk into LOW, MEDIUM, or HIGH with explanatory factors."""
        factors: List[str] = []
        score = 0.1  # baseline low risk

        # 1. Critical Policy Overrides by Intent
        if predicted_intent == "ACCOUNT_ACCESS":
            factors.append("Account authentication and credential management requires human verification.")
            score = max(score, 0.85)

        if predicted_intent == "APP_STORE_BILLING":
            factors.append("Financial transactions and billing disputes require human authorization.")
            score = max(score, 0.85)

        # 2. High Risk Keyword Detections
        if HIGH_RISK_CYBER_ATTACK.search(customer_message):
            factors.append("Detected cyber security exploit payload or adversarial prompt attack (VAPT Gate). Immediate High Risk escalation.")
            score = 0.99

        if HIGH_RISK_FINANCIAL.search(customer_message):
            factors.append("Detected financial dispute or unauthorized payment keyword.")
            score = max(score, 0.90)

        if HIGH_RISK_SECURITY.search(customer_message):
            factors.append("Detected account compromise or credential lockout indicator.")
            score = max(score, 0.92)

        if HIGH_RISK_LEGAL_SAFETY.search(customer_message):
            factors.append("Detected legal threat or physical battery safety hazard.")
            score = 0.98

        # 3. Medium Risk Indicators
        if MEDIUM_RISK_FRUSTRATION.search(customer_message):
            factors.append("Customer expresses elevated frustration or repeated troubleshooting failure.")
            score = max(score, 0.55)

        if predicted_intent in ("HARDWARE_DISPLAY", "STORE_REPAIR_SERVICE") and score < 0.50:
            if not any(w in customer_message.lower() for w in ["appointment", "book", "hours", "status"]):
                factors.append("Physical hardware damage or repair intake typically requires human inspection.")
                score = max(score, 0.50)

        # 4. Low Confidence Escalator
        if intent_confidence < 0.40:
            factors.append("Low intent classification confidence introduces risk of misguidance.")
            score = max(score, 0.60)

        # Assign Risk Tier
        if score >= 0.75:
            level = "HIGH"
            requires_human = True
        elif score >= 0.45:
            level = "MEDIUM"
            requires_human = True
        else:
            level = "LOW"
            requires_human = False

        if not factors:
            factors.append("Standard informational or self-service troubleshooting query.")

        return RiskAssessment(
            level=level,
            score=round(score, 2),
            risk_factors=factors,
            requires_human_verification=requires_human,
        )


# Global instance
default_risk_classifier = RiskClassifier()
