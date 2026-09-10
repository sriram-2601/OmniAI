"""Evidence-grounded reply generation module with LLM integration and deterministic synthesis."""
from __future__ import annotations

import json
import re
from typing import List, Tuple, Dict, Any, Optional

from src.common.schemas import EvidenceItem, RiskAssessment, IntentPrediction, RoutingDecision
from src.generation.prompts import SYSTEM_PROMPT_TEMPLATE, USER_PROMPT_TEMPLATE, format_evidence_context
from src.common.llm import default_llm_client
from src.multilingual.normalizer import MultilingualProcessor


class ReplyGenerator:
    """Generates concise, evidence-grounded Twitter support replies with multilingual support."""

    def __init__(self, llm_client=default_llm_client):
        self.llm_client = llm_client

    def generate_reply(
        self,
        customer_message: str,
        intent: IntentPrediction,
        risk: RiskAssessment,
        decision: RoutingDecision,
        evidence: List[EvidenceItem],
    ) -> Tuple[str, List[str]]:
        """Generate a grounded reply and return (reply_text, used_evidence_ids)."""
        evidence_context = format_evidence_context(evidence)
        used_case_ids = [e.case_id for e in evidence[:2]]
        lang_code, lang_label = MultilingualProcessor.detect_language(customer_message)

        # If decision is ESCALATE due to high risk / authentication / billing, synthesize safe handoff
        if decision.decision == "ESCALATE":
            if risk.level == "HIGH":
                # Spanish (Mexican, Colombian, Argentine, Spanglish)
                if lang_code in ("es", "es-MX", "es-CO", "es-AR", "spanglish"):
                    if intent.intent == "ACCOUNT_ACCESS":
                        reply = (
                            "Queremos ayudarte con la seguridad de tu Apple ID. Por favor ingresa a "
                            "https://iforgot.apple.com o contáctanos por DM para asistirte de forma segura."
                        )
                    elif intent.intent == "APP_STORE_BILLING":
                        reply = (
                            "Estamos para ayudarte con tu facturación. Para revisar cobros de forma segura "
                            "sin compartir datos privados, envíanos un DM o visita reportaproblem.apple.com."
                        )
                    else:
                        reply = (
                            "Entendemos la importancia de tu caso. Por favor envíanos un DM para que "
                            "nuestro equipo especializado pueda apoyarte de forma segura."
                        )
                # Brazilian Portuguese
                elif lang_code == "pt-BR":
                    if intent.intent == "ACCOUNT_ACCESS":
                        reply = (
                            "A segurança da sua conta é prioridade. Acesse https://iforgot.apple.com "
                            "imediatamente ou nos envie uma DM para suporte seguro."
                        )
                    elif intent.intent == "APP_STORE_BILLING":
                        reply = (
                            "Queremos te ajudar com essa cobrança com segurança. Acesse reportaproblem.apple.com "
                            "ou nos mande uma DM."
                        )
                    else:
                        reply = (
                            "Entendemos a urgência da situação. Por favor nos envie uma DM para que "
                            "nossa equipe especializada possa te atender com segurança."
                        )
                # Canadian French / French
                elif lang_code in ("fr", "fr-CA"):
                    if intent.intent == "ACCOUNT_ACCESS":
                        reply = (
                            "La sécurité de votre compte Apple est primordiale. Rendez-vous sur "
                            "https://iforgot.apple.com ou écrivez-nous en DM."
                        )
                    elif intent.intent == "APP_STORE_BILLING":
                        reply = (
                            "Nous sommes là pour vous aider avec votre facturation. Visitez "
                            "reportaproblem.apple.com ou écrivez-nous en DM en toute sécurité."
                        )
                    else:
                        reply = (
                            "Nous comprenons l'importance de la situation. Veuillez nous envoyer un "
                            "message direct pour une assistance sécurisée."
                        )
                # Haitian Creole
                elif lang_code == "ht":
                    if intent.intent == "ACCOUNT_ACCESS":
                        reply = (
                            "Sekirite Apple ID ou se priyorite nou. Tanpri vizite https://iforgot.apple.com "
                            "oswa voye yon DM ba nou pou èd an sekirite."
                        )
                    elif intent.intent == "APP_STORE_BILLING":
                        reply = (
                            "Nou la pou ede w ak fakti ou a san danje. Tanpri vizite reportaproblem.apple.com "
                            "oswa voye yon DM pou nou."
                        )
                    else:
                        reply = (
                            "Nou konprann sitiyasyon sa a enpòtan. Tanpri voye yon DM ba nou pou ekip nou an ka ede w."
                        )
                # Default English & Indigenous fallback
                else:
                    if intent.intent == "ACCOUNT_ACCESS":
                        reply = (
                            "We'd love to help with your Apple ID security. Because this involves sensitive "
                            "account verification, please reach out to us via DM or visit https://iforgot.apple.com to begin."
                        )
                    elif intent.intent == "APP_STORE_BILLING":
                        reply = (
                            "We're here to help with your billing inquiry. To securely review transactions and "
                            "subscriptions without sharing private details, please send us a DM or check https://reportaproblem.apple.com."
                        )
                    else:
                        reply = (
                            "We understand this is critical. Please send us a DM so we can securely look into this "
                            "and connect you with our specialized support team."
                        )
                return reply, used_case_ids

        # Attempt LLM generation if client is available
        user_prompt = USER_PROMPT_TEMPLATE.format(
            customer_message=customer_message,
            intent_name=intent.intent,
            intent_confidence=intent.confidence,
            risk_level=risk.level,
            decision=decision.decision,
            decision_reason=decision.reason,
            evidence_context=evidence_context,
        )

        try:
            raw_response = self.llm_client.generate(
                system_prompt=SYSTEM_PROMPT_TEMPLATE,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            # Parse JSON
            cleaned_json = raw_response.strip()
            if "```json" in cleaned_json:
                cleaned_json = cleaned_json.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_json:
                cleaned_json = cleaned_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned_json)
            reply_text = parsed.get("reply", "")
            case_ids = parsed.get("grounded_in_case_ids", used_case_ids)

            # Enforce 280 character length limit
            if len(reply_text) > 280:
                reply_text = reply_text[:277] + "..."

            if reply_text:
                return reply_text, case_ids
        except Exception:
            # Fallback to high-fidelity historical template synthesis
            pass

        # Deterministic Grounded Fallback: Synthesize from top historical precedent
        if evidence:
            top_precedent = evidence[0].brand_response.strip()
            # Clean handle tags if any
            top_precedent = re.sub(r"^@\w+\s*", "", top_precedent)
            # Ensure friendly Apple style opening
            if not any(top_precedent.lower().startswith(g) for g in ["we're here", "thanks", "hello", "hi"]):
                reply = f"We're here to help. {top_precedent}"
            else:
                reply = top_precedent

            if len(reply) > 280:
                reply = reply[:277] + "..."
            return reply, used_case_ids

        # Out-of-scope / zero evidence fallback
        default_reply = "Thanks for reaching out to Apple Support. Could you share your device model and current iOS version so we can assist?"
        return default_reply, []


# Global instance
default_generator = ReplyGenerator()
