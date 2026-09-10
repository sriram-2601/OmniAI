"""Automated test suite validating 22+ American and Mexican languages, dialects, and indigenous varieties."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.multilingual.normalizer import MultilingualProcessor
from src.routing.risk import default_risk_classifier
from src.routing.router import default_router
from src.generation.generator import default_generator
from src.agent import default_agent
from src.common.config import PROJECT_ROOT


CORPUS_PATH = PROJECT_ROOT / "data" / "multilingual" / "american_languages_corpus.json"


def test_multilingual_corpus_exists_and_contains_22_languages():
    """Verify that the American & Mexican multilingual corpus contains all 22 languages."""
    assert CORPUS_PATH.exists(), f"Missing {CORPUS_PATH}"
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_languages"] >= 20
    assert len(data["languages"]) >= 20

    # Verify key Mexican & American languages are present
    expected_keys = [
        "es_mx", "spanglish", "nahuatl", "maya", "zapotec", "mixtec",
        "otomi", "totonac", "tarahumara", "huasteco", "en_us", "fr_ca",
        "ht_creole", "navajo", "cherokee", "inuktitut", "pt_br", "quechua",
        "guarani", "aymara", "es_co", "es_ar"
    ]
    for key in expected_keys:
        assert key in data["languages"], f"Expected {key} in corpus"


def test_supported_languages_registry_count():
    """Verify that MultilingualProcessor registers 22+ American and regional languages."""
    registry = MultilingualProcessor.get_supported_languages()
    assert len(registry) >= 22


def test_mexican_spanish_detection_and_normalization():
    """Verify Mexican Spanish slang detection and technical diagnostic normalization."""
    query = "Mi iPhone se calienta un chingo y la pila no dura nada, se baja de volada."
    lang_code, lang_label = MultilingualProcessor.detect_language(query)
    assert lang_code == "es-MX"
    assert "Mexican Spanish" in lang_label

    normalized, _ = MultilingualProcessor.normalize_to_semantic_inquiry(query)
    assert "battery" in normalized.lower() or "drains" in normalized.lower()


def test_spanglish_border_detection():
    """Verify US-Mexico border Spanglish / Pocho detection and normalization."""
    query = "Mi phone se freezeó después del update y la battery está dying rápido."
    lang_code, lang_label = MultilingualProcessor.detect_language(query)
    assert lang_code == "spanglish"
    assert "Spanglish" in lang_label


def test_indigenous_mexican_languages():
    """Verify detection of Mexican indigenous languages: Nahuatl, Maya, Zapotec, Mixtec."""
    # Nahuatl
    code, label = MultilingualProcessor.detect_language("Notepoz amo tequiti, chicahualiztli cenca totonqui.")
    assert code == "nahuatl"

    # Maya
    code, label = MultilingualProcessor.detect_language("Le u nu'ukulil ma' táan u meyaj, jach choko'.")
    assert code == "maya"

    # Zapotec
    code, label = MultilingualProcessor.detect_language("Guendanabani sti' celular cadi cayaca chaahui, rilaa naxhi.")
    assert code == "zapotec"

    # Mixtec
    code, label = MultilingualProcessor.detect_language("Kóo kánuu teléfono yu'u, xíña nǐ'no batería.")
    assert code == "mixtec"


def test_north_american_varieties():
    """Verify Canadian French, Haitian Creole, Navajo, Cherokee, and Inuktitut."""
    # Canadian French
    code, label = MultilingualProcessor.detect_language("Mon cellulaire est pogné sur la pomme pis la batterie se vide d'une shot.")
    assert code == "fr-CA"

    # Haitian Creole
    code, label = MultilingualProcessor.detect_language("Telefòn mwen an pa vle mache, batri a ap desann twò vit.")
    assert code == "ht"

    # Navajo
    code, label = MultilingualProcessor.detect_language("Béésh bee haneʼé doo naalnish da, atsʼíís deesdoi.")
    assert code == "navajo"

    # Cherokee
    code, label = MultilingualProcessor.detect_language("ᏗᏟᏃᎮᏗ Ꮭ ᏱᏚᎸᏫᏍᏓᏁ, ᎠᏰᎸ ᎤᏗᎴᎩ ᏂᎦᎵᏍᏗᎭ.")
    assert code == "cherokee"

    # Inuktitut
    code, label = MultilingualProcessor.detect_language("Uqaalautiga aullaqattangittuq, kiatsartualuk battery nungulertuq.")
    assert code == "inuktitut"


def test_south_american_varieties():
    """Verify Brazilian Portuguese, Quechua, Guarani, Aymara, and Argentine Spanish."""
    # Brazilian Portuguese
    code, label = MultilingualProcessor.detect_language("Meu iPhone tá travando direto e a bateria tá viciada, descarrega voando.")
    assert code == "pt-BR"

    # Quechua
    code, label = MultilingualProcessor.detect_language("Celulary mana allintachu llamk'an, baterian q'uñipakun.")
    assert code == "quechua"

    # Guarani
    code, label = MultilingualProcessor.detect_language("Che celular ndomomba'apói porã, batería hakueterei.")
    assert code == "guarani"

    # Aymara
    code, label = MultilingualProcessor.detect_language("Celularaxa janiw walikiti, batería junt'utapuniwa.")
    assert code == "aymara"

    # Argentine Spanish
    code, label = MultilingualProcessor.detect_language("Che @AppleSupport, el celu se me tildó y no dura un carajo.")
    assert code == "es-AR"


def test_multilingual_risk_safety_overrides():
    """Verify that high-risk financial, security, and safety queries trigger HIGH risk in American languages."""
    # Mexican Spanish: credit card fraud
    risk_mx = default_risk_classifier.evaluate_risk(
        "Me cobraron doble lana en mi tarjeta de crédito por una suscripción",
        "APP_STORE_BILLING",
        0.90,
    )
    assert risk_mx.level == "HIGH"
    assert risk_mx.requires_human_verification is True

    # Brazilian Portuguese: hacked iCloud
    risk_pt = default_risk_classifier.evaluate_risk(
        "Hackearam minha conta do iCloud e trocaram minha senha",
        "ACCOUNT_ACCESS",
        0.90,
    )
    assert risk_pt.level == "HIGH"

    # Canadian French: credit card double charge
    risk_fr = default_risk_classifier.evaluate_risk(
        "J'ai été facturé deux fois sur ma carte de crédit",
        "APP_STORE_BILLING",
        0.90,
    )
    assert risk_fr.level == "HIGH"

    # Haitian Creole: duplicate card charge
    risk_ht = default_risk_classifier.evaluate_risk(
        "Yo chaje kat mwen an de fwa nan Apple Store",
        "APP_STORE_BILLING",
        0.90,
    )
    assert risk_ht.level == "HIGH"

    # Physical safety hazard in Spanish: swollen battery
    risk_safe = default_risk_classifier.evaluate_risk(
        "La batería de mi cel está inflada y sale humo",
        "BATTERY_POWER",
        0.90,
    )
    assert risk_safe.level == "HIGH"


def test_end_to_end_agent_multilingual_pipeline():
    """Verify that the end-to-end agent processes multilingual queries and enforces <=280 characters."""
    test_queries = [
        "Mi iPhone se calienta un chingo y la pila no dura nada, se baja de volada.",
        "Meu iPhone tá travando direto depois da atualização e a bateria tá viciada.",
        "Mon cellulaire est pogné sur la pomme pis la batterie se vide d'une shot.",
        "Notepoz amo tequiti, chicahualiztli cenca totonqui.",
    ]

    for q in test_queries:
        out = default_agent.process_message(q)
        assert out.language is not None
        assert out.draft_reply is not None
        assert len(out.draft_reply) <= 280, f"Reply exceeded 280 chars: {len(out.draft_reply)}"
        assert out.decision is not None
