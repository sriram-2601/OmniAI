"""Multilingual & Code-Mixed Language Normalizer with Americas & Mexican Support.

Supports 22+ American, Mexican, and Indigenous languages/dialects:
- Mexican Spanish (Español Mexicano / Modismos)
- Spanglish / Pocho (US-Mexico Border)
- Indigenous Mexican (Nahuatl, Maya, Zapotec, Mixtec, Otomi, Totonac, Tarahumara, Huasteco)
- North American Regional & Indigenous (American English, Canadian French, Haitian Creole, Navajo, Cherokee, Inuktitut)
- South & Central American (Brazilian Portuguese, Quechua, Guarani, Aymara, Colombian, Argentine)
- Plus Indic code-mixed (Tenglish, Hinglish) and global languages.
"""
from __future__ import annotations

import re
from typing import Dict, Any, Tuple, Optional, List


# ---------------------------------------------------------------------------
# Lexical normalizer dictionaries for intent recognition & semantic mapping
# ---------------------------------------------------------------------------

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

MEXICAN_SPANISH_PATTERNS = {
    r"\b(no\s+jala|no\s+est[aá]\s+jalando)\b": "not working malfunctioning",
    r"\b(se\s+trab[oó]|se\s+congel[oó])\b": "froze frozen unresponsive",
    r"\b(un\s+chingo|un\s+buen|bien\s+harto)\b": "very severely extremely",
    r"\b(la\s+pila)\b": "battery",
    r"\b(se\s+baja\s+de\s+volada|se\s+acaba\s+en\s+fa)\b": "drains rapidly quickly",
    r"\b(el\s+cel|el\s+celu|la\s+compu)\b": "phone iPhone device",
    r"\b(se\s+estrell[oó]|se\s+quebr[oó])\s*(la\s+pantalla)?\b": "screen cracked shattered",
    r"\b(doble\s+lana|lana|cobro\s+de\s+m[aá]s|me\s+clavaron)\b": "unauthorized money charge billing dispute",
    r"\b(no\s+me\s+deja\s+entrar|olvid[eé]\s+mi\s+clave|olvid[eé]\s+mi\s+contrase[ñn]a)\b": "forgot password locked account access",
}

SPANGLISH_PATTERNS = {
    r"\b(se\s+freeze[oó]|est[aá]\s+freezado)\b": "frozen freezing",
    r"\b(est[aá]\s+crasheando|se\s+crashe[oó])\b": "crashing unexpected crash",
    r"\b(hacer\s+update|hice\s+update)\b": "software update iOS update",
    r"\b(battery\s+est[aá]\s+dying)\b": "battery draining dying fast",
    r"\b(resetear|restartear)\b": "restart reset device",
    r"\b(loguear|loguearme)\b": "login sign in account",
}

BRAZILIAN_PORTUGUESE_PATTERNS = {
    r"\b(t[aá]\s+travando|travou\s+direto)\b": "freezing frozen stuck",
    r"\b(bateria\s+t[aá]\s+viciada|descarrega\s+voando|acaba\s+muito\s+r[aá]pido)\b": "battery degraded draining rapidly fast",
    r"\b(cobran[çc]a\s+indevida|cobraram\s+duas\s+vezes)\b": "unauthorized charge double charge refund",
    r"\b(esqueci\s+minha\s+senha|conta\s+bloqueada|n[aã]o\s+recebo\s+c[oó]digo)\b": "forgot password locked account 2FA",
    r"\b(tela\s+trincada|tela\s+quebrou|n[aã]o\s+d[aá]\s+toque)\b": "touch screen cracked unresponsive",
}

CANADIAN_FRENCH_PATTERNS = {
    r"\b(cellulaire\s+est\s+pogn[eé]|mon\s+cell)\b": "cell phone iPhone stuck frozen",
    r"\b(se\s+vide\s+d'une\s+shot|batterie\s+vide\s+vite)\b": "battery draining instantly fast",
    r"\b(bogue\s+solide|a\s+plant[eé])\b": "crashing bug glitching",
    r"\b([eé]cran\s+p[eé]t[eé]|[eé]cran\s+cass[eé])\b": "screen cracked broken",
    r"\b(factur[eé]\s+deux\s+fois|remboursement)\b": "charged twice unauthorized billing refund",
}

HAITIAN_CREOLE_PATTERNS = {
    r"\b(pa\s+vle\s+mache|pa\s+mache)\b": "not working malfunctioning",
    r"\b(batri\s+a\s+ap\s+desann\s+tw[oò]\s+vit)\b": "battery draining too fast",
    r"\b(ekran\s+an\s+kase)\b": "screen broken cracked",
    r"\b(chaje\s+kat\s+mwen|chaje\s+m\s+de\s+fwa)\b": "charged my card twice unauthorized billing",
    r"\b(modpas\s+mwen\s+bliye|kont\s+mwen\s+bloke)\b": "forgot password account locked",
}

# Indigenous American Normalization lexicons (mapped to technical diagnostics)
INDIGENOUS_AMERICAN_PATTERNS = {
    # Nahuatl
    r"\b(amo\s+tequiti)\b": "not working malfunctioning",
    r"\b(totonqui|cenca\s+totonqui)\b": "overheating very hot",
    r"\b(tlachiyalistli\s+tlapantoc)\b": "screen display cracked broken",
    r"\b(tomin|nechtominqui)\b": "unauthorized money charge billing",
    r"\b(chicahualiztli)\b": "battery power energy",
    # Maya
    r"\b(ma'\s+t[aá]an\s+u\s+meyaj)\b": "not working malfunctioning",
    r"\b(jach\s+choko')\b": "overheating very hot",
    r"\b(pa'ax\s+u\s+yich)\b": "screen cracked broken",
    r"\b(taak'in|ch'a'aj\s+taak'in)\b": "money charge billing transaction",
    # Zapotec
    r"\b(cadi\s+cayaca)\b": "not working malfunctioning",
    r"\b(guendanabani|rilaa\s+naxhi)\b": "battery life draining quickly",
    r"\b(bidxichi|guti\s+bidxichi)\b": "money deducted charge billing",
    # Mixtec
    r"\b(k[oó]o\s+k[aá]nuu)\b": "not working malfunctioning",
    r"\b(x[ií][ñn]a\s+n[iǐ]'no)\b": "battery very hot overheating",
    # Otomi
    r"\b(hin\s+gi\s+pe̱fi|hin\s+gi\s+pefi)\b": "not working malfunctioning",
    r"\b(pa\s+ntsaya)\b": "battery very hot overheating",
    # Totonac
    r"\b(tux[aá]\s+la)\b": "not working malfunctioning",
    r"\b(lhuwa\s+chichi)\b": "battery very hot overheating",
    # Tarahumara
    r"\b(t[aá]si\s+gayena)\b": "cannot function not working",
    r"\b(rata\s+bater[ií]a)\b": "battery hot overheating",
    # Huasteco
    r"\b(yab\s+in\s+t'ojnal)\b": "not working malfunctioning",
    r"\b(k'ak'al\s+an\s+bater[ií]a)\b": "battery hot overheating",
    # Quechua
    r"\b(mana\s+allintachu\s+llamk'an|mana\s+llamk'anchu)\b": "not working malfunctioning",
    r"\b(q'u[ñn]ipakun|q'u[ñn]i)\b": "overheating hot",
    r"\b(qullqi|qullqiyta)\b": "money charge billing refund",
    # Guarani
    r"\b(ndomomba'ap[oó]i)\b": "not working malfunctioning",
    r"\b(hakueterei|pya'e\s+opave)\b": "overheating hot battery draining fast",
    r"\b(pirapire|ojeipe'a.*pirapire)\b": "money taken unauthorized charge",
    # Aymara
    r"\b(janiw\s+walikiti|janiw\s+irnaqkiti)\b": "not working malfunctioning",
    r"\b(junt'utapuniwa|junt'u)\b": "overheating hot battery",
    # Navajo
    r"\b(doo\s+naalnish\s+da)\b": "not working malfunctioning",
    r"\b(deesdoi)\b": "overheating very hot",
    r"\b(b[eé]eso)\b": "money charge billing transaction",
    # Inuktitut
    r"\b(aullaqattangittuq)\b": "not working malfunctioning",
    r"\b(kiatsartuq|kiatsartualuk)\b": "overheating very hot",
    r"\b(kiinaujaq)\b": "money charge billing transaction",
}


# ---------------------------------------------------------------------------
# Multilingual Processor
# ---------------------------------------------------------------------------

class MultilingualProcessor:
    """Detects language, handles code-mixed American/Mexican dialects, and bridges to semantic intent."""

    SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
        "es-MX": {"name": "Mexican Spanish", "flag": "🇲🇽", "region": "Mexico", "family": "Romance"},
        "spanglish": {"name": "Spanglish / Pocho", "flag": "🇲🇽🇺🇸", "region": "US-Mexico Border", "family": "Code-Mixed"},
        "nahuatl": {"name": "Nahuatl", "flag": "🇲🇽", "region": "Central Mexico", "family": "Uto-Aztecan"},
        "maya": {"name": "Yucatec Maya", "flag": "🇲🇽", "region": "Yucatan, Mexico", "family": "Mayan"},
        "zapotec": {"name": "Zapotec", "flag": "🇲🇽", "region": "Oaxaca, Mexico", "family": "Oto-Manguean"},
        "mixtec": {"name": "Mixtec", "flag": "🇲🇽", "region": "Oaxaca/Guerrero, Mexico", "family": "Oto-Manguean"},
        "otomi": {"name": "Otomi", "flag": "🇲🇽", "region": "Central Mexico", "family": "Oto-Manguean"},
        "totonac": {"name": "Totonac", "flag": "🇲🇽", "region": "Veracruz, Mexico", "family": "Totonacan"},
        "tarahumara": {"name": "Tarahumara", "flag": "🇲🇽", "region": "Chihuahua, Mexico", "family": "Uto-Aztecan"},
        "huasteco": {"name": "Huasteco", "flag": "🇲🇽", "region": "La Huasteca, Mexico", "family": "Mayan"},
        "en-US": {"name": "American English", "flag": "🇺🇸", "region": "United States", "family": "Germanic"},
        "fr-CA": {"name": "Canadian French", "flag": "🇨🇦", "region": "Quebec, Canada", "family": "Romance"},
        "ht": {"name": "Haitian Creole", "flag": "🇭🇹", "region": "Caribbean / US Diaspora", "family": "Creole"},
        "navajo": {"name": "Navajo", "flag": "🇺🇸", "region": "Navajo Nation, USA", "family": "Na-Dene"},
        "cherokee": {"name": "Cherokee", "flag": "🇺🇸", "region": "Cherokee Nation, USA", "family": "Iroquoian"},
        "inuktitut": {"name": "Inuktitut", "flag": "🇨🇦", "region": "Arctic Canada", "family": "Eskimo-Aleut"},
        "pt-BR": {"name": "Brazilian Portuguese", "flag": "🇧🇷", "region": "Brazil", "family": "Romance"},
        "quechua": {"name": "Quechua", "flag": "🇵🇪🇧🇴", "region": "Andes", "family": "Quechuan"},
        "guarani": {"name": "Guarani", "flag": "🇵🇾", "region": "Paraguay / Mercosur", "family": "Tupian"},
        "aymara": {"name": "Aymara", "flag": "🇧🇴🇵🇪", "region": "Andean Altiplano", "family": "Aymaran"},
        "es-CO": {"name": "Colombian Spanish", "flag": "🇨🇴", "region": "Colombia", "family": "Romance"},
        "es-AR": {"name": "Argentine Spanish", "flag": "🇦🇷", "region": "Argentina / Uruguay", "family": "Romance"},
        # Indic & Global Extensions
        "te-Latn": {"name": "Tenglish", "flag": "🇮🇳", "region": "South India", "family": "Dravidian Code-Mixed"},
        "hi-Latn": {"name": "Hinglish", "flag": "🇮🇳", "region": "North India", "family": "Indo-Aryan Code-Mixed"},
        "te": {"name": "Telugu", "flag": "🇮🇳", "region": "India (Script)", "family": "Dravidian"},
        "hi": {"name": "Hindi", "flag": "🇮🇳", "region": "India (Script)", "family": "Indo-Aryan"},
        "es": {"name": "Spanish", "flag": "🌐", "region": "Global Spanish", "family": "Romance"},
        "fr": {"name": "French", "flag": "🇫🇷", "region": "Global French", "family": "Romance"},
        "de": {"name": "German", "flag": "🇩🇪", "region": "Germany / Europe", "family": "Germanic"},
        "en": {"name": "English", "flag": "🌐", "region": "International", "family": "Germanic"},
    }

    @classmethod
    def get_supported_languages(cls) -> Dict[str, Dict[str, str]]:
        """Return registry of all supported languages and metadata."""
        return cls.SUPPORTED_LANGUAGES

    @classmethod
    def detect_language(cls, text: str) -> Tuple[str, str]:
        """Detect language code and human-readable label.

        Returns:
            (language_code, human_label)
        """
        detailed = cls.detect_language_detailed(text)
        return detailed["code"], detailed["label"]

    @classmethod
    def detect_language_detailed(cls, text: str) -> Dict[str, Any]:
        """Detailed linguistic detection identifying language, dialect, region, and flag."""
        lowered = text.lower()

        # 1. Cherokee script detection (U+13A0 to U+13FF)
        if re.search(r"[\u13A0-\u13FF]", text):
            return {
                "code": "cherokee",
                "label": "Cherokee (ᏣᎳᎩ)",
                "region": "Cherokee Nation, USA",
                "flag": "🇺🇸",
                "family": "Iroquoian",
            }

        # 2. Inuktitut syllabics (U+1400 to U+167F) or Latin markers
        if re.search(r"[\u1400-\u167F]", text) or any(w in lowered for w in ["aullaqattangittuq", "kiatsartuq", "uqaalautiga"]):
            return {
                "code": "inuktitut",
                "label": "Inuktitut (ᐃᓄᒃᑎᑐᑦ)",
                "region": "Arctic Canada",
                "flag": "🇨🇦",
                "family": "Eskimo-Aleut",
            }

        # 3. Telugu script
        if re.search(r"[\u0C00-\u0C7F]", text):
            return {"code": "te", "label": "Telugu (తెలుగు)", "region": "India", "flag": "🇮🇳", "family": "Dravidian"}

        # 4. Devanagari script (Hindi/Marathi)
        if re.search(r"[\u0900-\u097F]", text):
            return {"code": "hi", "label": "Hindi (हिन्दी)", "region": "India", "flag": "🇮🇳", "family": "Indo-Aryan"}

        # 5. Indigenous Mexican Languages
        if any(w in lowered for w in ["amo tequiti", "totonqui", "tlachiyalistli", "tlapantoc", "notepoz", "nechtominqui"]):
            return {"code": "nahuatl", "label": "Nahuatl (Mexicano)", "region": "Central Mexico", "flag": "🇲🇽", "family": "Uto-Aztecan"}

        if any(w in lowered for w in ["ma' táan", "meyaj", "choko'", "pa'ax", "taak'in", "k'iini'"]):
            return {"code": "maya", "label": "Yucatec Maya (Maaya t'aan)", "region": "Yucatan, Mexico", "flag": "🇲🇽", "family": "Mayan"}

        if any(w in lowered for w in ["cadi cayaca", "guendanabani", "bidxichi", "rilaa", "biseenda"]):
            return {"code": "zapotec", "label": "Zapotec (Diidxazá)", "region": "Oaxaca, Mexico", "flag": "🇲🇽", "family": "Oto-Manguean"}

        if any(w in lowered for w in ["kóo kánuu", "xíña", "yuchi", "chintée"]):
            return {"code": "mixtec", "label": "Mixtec (Tu'un Sávi)", "region": "Oaxaca, Mexico", "flag": "🇲🇽", "family": "Oto-Manguean"}

        if any(w in lowered for w in ["hin gi pe̱fi", "hin gi pefi", "ntsaya", "penz'ähe"]):
            return {"code": "otomi", "label": "Otomi (Hñähñu)", "region": "Central Mexico", "flag": "🇲🇽", "family": "Oto-Manguean"}

        if any(w in lowered for w in ["tuxá la", "lakgastapu", "lhuwa chichi", "pukskíwan"]):
            return {"code": "totonac", "label": "Totonac (Tachiwin)", "region": "Veracruz, Mexico", "flag": "🇲🇽", "family": "Totonacan"}

        if any(w in lowered for w in ["tási gayena", "kuira ba", "rata batería"]):
            return {"code": "tarahumara", "label": "Tarahumara (Rarámuri)", "region": "Chihuahua, Mexico", "flag": "🇲🇽", "family": "Uto-Aztecan"}

        if any(w in lowered for w in ["yab in t'ojnal", "k'ak'al an", "ts'iha'"]):
            return {"code": "huasteco", "label": "Huasteco (Teenek)", "region": "La Huasteca, Mexico", "flag": "🇲🇽", "family": "Mayan"}

        # 6. Indigenous South & North American Languages
        if any(w in lowered for w in ["doo naalnish da", "deesdoi", "béeso shaa", "béésh bee haneʼé"]):
            return {"code": "navajo", "label": "Navajo (Diné Bizaad)", "region": "Navajo Nation, USA", "flag": "🇺🇸", "family": "Na-Dene"}

        if any(w in lowered for w in ["mana allintachu", "llamk'an", "q'uñipakun", "wañukun", "yanapasaykiku"]):
            return {"code": "quechua", "label": "Quechua (Runa Simi)", "region": "Andes", "flag": "🇵🇪🇧🇴", "family": "Quechuan"}

        if any(w in lowered for w in ["ndomomba'apói", "hakueterei", "pya'e opave", "pirapire", "ropytyvõ"]):
            return {"code": "guarani", "label": "Guarani (Avañe'ẽ)", "region": "Paraguay", "flag": "🇵🇾", "family": "Tupian"}

        if any(w in lowered for w in ["janiw walikiti", "junt'utapuniwa", "kamisaraki", "yanapapxämaw"]):
            return {"code": "aymara", "label": "Aymara (Aymar aru)", "region": "Bolivia / Peru", "flag": "🇧🇴🇵🇪", "family": "Aymaran"}

        # 7. Haitian Creole
        if any(w in lowered for w in ["pa vle mache", "ap desann twò vit", "yo chaje m", "kreyòl", "modpas mwen"]):
            return {"code": "ht", "label": "Haitian Creole (Kreyòl Ayisyen)", "region": "Caribbean / US", "flag": "🇭🇹", "family": "Creole"}

        # 8. Canadian French (Québécois)
        if any(w in lowered for w in ["cellulaire", "pogné", "d'une shot", "bogue solide", "pété"]) and any(w in lowered for w in ["mon", "la", "le", "pis", "pantoute"]):
            return {"code": "fr-CA", "label": "Canadian French (Français Québécois)", "region": "Quebec, Canada", "flag": "🇨🇦", "family": "Romance"}

        # 9. Spanglish / Pocho (US-Mexico Border Code-Mixed)
        spanglish_hits = sum(1 for pat in SPANGLISH_PATTERNS if re.search(pat, lowered))
        if spanglish_hits >= 1 or (("freezeó" in lowered or "crasheando" in lowered or "loguear" in lowered) and ("phone" in lowered or "battery" in lowered or "mi" in lowered)):
            return {"code": "spanglish", "label": "Spanglish / Pocho (US-Mexico Border)", "region": "US-Mexico Border", "flag": "🇲🇽🇺🇸", "family": "Code-Mixed"}

        # 10. Brazilian Portuguese
        pt_hits = sum(1 for pat in BRAZILIAN_PORTUGUESE_PATTERNS if re.search(pat, lowered))
        if pt_hits >= 1 or any(w in lowered for w in ["meu celular", "travando", "descarrega voando", "cobrança indevida", "cobranca indevida", "cartão de crédito", "minha conta", "tela trincada"]):
            return {"code": "pt-BR", "label": "Brazilian Portuguese (Português Brasileiro)", "region": "Brazil", "flag": "🇧🇷", "family": "Romance"}

        # 11. Argentine Spanish (Español Rioplatense)
        if any(w in lowered for w in ["che", "el celu", "se tildó", "se tildo", "no dura un carajo", "la guita", "debitaron", "no funca", "mandanos"]):
            return {"code": "es-AR", "label": "Argentine Spanish (Español Rioplatense)", "region": "Argentina / Uruguay", "flag": "🇦🇷", "family": "Romance"}

        # 12. Colombian Spanish (Español Colombiano)
        if any(w in lowered for w in ["parce", "qué vaina", "que vaina", "se quedó pegado", "se quedo pegado", "se descarga de una", "una plata"]):
            return {"code": "es-CO", "label": "Colombian Spanish (Español Colombiano)", "region": "Colombia", "flag": "🇨🇴", "family": "Romance"}

        # 13. Mexican Spanish (Colloquial slang & idioms)
        mexican_hits = sum(1 for pat in MEXICAN_SPANISH_PATTERNS if re.search(pat, lowered))
        if mexican_hits >= 1 or re.search(r"\b(no jala|se trab[oó]|un chingo|de volada|la pila|se estrell[oó]|lana|el cel)\b", lowered):
            return {"code": "es-MX", "label": "Mexican Spanish (Español Mexicano)", "region": "Mexico", "flag": "🇲🇽", "family": "Romance"}

        # 14. Indic Code-Mixed: Tenglish & Hinglish
        tenglish_hits = sum(1 for pat in TENGLISH_PATTERNS if re.search(pat, lowered))
        if tenglish_hits >= 2 or any(w in lowered for w in ["cheyali", "cheyyali", "aipothundi", "ekkatle", "pagilipoindi", "marchipoya"]):
            return {"code": "te-Latn", "label": "Tenglish (Telugu in English script)", "region": "South India", "flag": "🇮🇳", "family": "Code-Mixed"}

        hinglish_hits = sum(1 for pat in HINGLISH_PATTERNS if re.search(pat, lowered))
        if hinglish_hits >= 2 or any(w in lowered for w in ["kaise kare", "nahi raha", "tut gaya", "bhool gaya"]):
            return {"code": "hi-Latn", "label": "Hinglish (Hindi in English script)", "region": "North India", "flag": "🇮🇳", "family": "Code-Mixed"}

        # 15. General Global European Languages
        if any(w in lowered for w in ["pantalla", "batería", "ayuda", "actualización", "cómo", "funciona", "cuenta", "tarjeta", "contraseña"]):
            return {"code": "es", "label": "Spanish (Español)", "region": "Global Spanish", "flag": "🌐", "family": "Romance"}

        if any(w in lowered for w in ["batterie", "écran", "mise à jour", "comment", "marche pas", "compte", "mot de passe"]):
            return {"code": "fr", "label": "French (Français)", "region": "Global French", "flag": "🇫🇷", "family": "Romance"}

        if any(w in lowered for w in ["akku", "bildschirm", "funktioniert", "nach dem update", "passwort"]):
            return {"code": "de", "label": "German (Deutsch)", "region": "Germany / Europe", "flag": "🇩🇪", "family": "Germanic"}

        # 16. American English Slang Detection
        if any(w in lowered for w in ["bricked", "bootloop", "tanking", "ghost touch", "glitching"]):
            return {"code": "en-US", "label": "American English (US Tech & Slang)", "region": "United States", "flag": "🇺🇸", "family": "Germanic"}

        return {"code": "en", "label": "English", "region": "International", "flag": "🌐", "family": "Germanic"}

    @classmethod
    def normalize_to_semantic_inquiry(cls, text: str) -> Tuple[str, str]:
        """Normalize code-mixed, slang, or indigenous text into technical diagnostic semantics.

        Returns:
            (normalized_query, detected_lang_label)
        """
        detailed = cls.detect_language_detailed(text)
        lang_code = detailed["code"]
        lang_label = detailed["label"]
        normalized = text

        # Apply specific dialect transformations
        if lang_code == "es-MX":
            for pat, repl in MEXICAN_SPANISH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        elif lang_code == "spanglish":
            for pat, repl in SPANGLISH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)
            for pat, repl in MEXICAN_SPANISH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        elif lang_code == "pt-BR":
            for pat, repl in BRAZILIAN_PORTUGUESE_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        elif lang_code == "fr-CA":
            for pat, repl in CANADIAN_FRENCH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        elif lang_code == "ht":
            for pat, repl in HAITIAN_CREOLE_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        elif lang_code == "te-Latn":
            for pat, repl in TENGLISH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        elif lang_code == "hi-Latn":
            for pat, repl in HINGLISH_PATTERNS.items():
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        # Apply indigenous American patterns
        for pat, repl in INDIGENOUS_AMERICAN_PATTERNS.items():
            if re.search(pat, normalized, flags=re.IGNORECASE):
                normalized = re.sub(pat, repl, normalized, flags=re.IGNORECASE)

        # Clean multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized, lang_label
