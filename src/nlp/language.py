import re
from typing import Dict, Any, Tuple, Optional
import langdetect
from langdetect import DetectorFactory

# Deterministic seed per requirements
DetectorFactory.seed = 0

UNICODE_SCRIPTS = [
    (r'[\u0C00-\u0C7F]', 'Telugu', 'Telugu'),
    (r'[\u0B80-\u0BFF]', 'Tamil', 'Tamil'),
    (r'[\u0C80-\u0CFF]', 'Kannada', 'Kannada'),
    (r'[\u0D00-\u0D7F]', 'Malayalam', 'Malayalam'),
    (r'[\u0A80-\u0AFF]', 'Gujarati', 'Gujarati'),
    (r'[\u0A00-\u0A7F]', 'Punjabi', 'Gurmukhi'),
    (r'[\u0B00-\u0B7F]', 'Odia', 'Odia'),
    (r'[\u0980-\u09FF]', 'Bengali', 'Bengali'),
    (r'[\u0900-\u097F]', 'Hindi', 'Devanagari'),
]

# Lexicons with at least 25 common words/phrases each
ROMANIZED_LEXICONS = {
    "Telugu": [
        "bagundi", "baagundi", "chala", "chaala", "nachindi", "nachaledu", "ledu", "kaadu",
        "kadu", "meeru", "nenu", "naku", "naaku", "meeku", "manchi", "darunam", "superga",
        "bavundi", "baga", "baaga", "undhi", "undi", "vachindi", "konanu", "ivvandi", "ippudu",
        "eppudu", "ekkada", "chesaru", "cheppali", "ammayi", "abbayi", "kothaga"
    ],
    "Tamil": [
        "romba", "nalla", "nalladhu", "nallairukku", "mosam", "seriyilla", "illai", "illa",
        "idhu", "adhu", "enakku", "ungalukku", "pudichirukku", "pidikavillai", "superaa",
        "varala", "vandhadhu", "perusu", "chinna", "nandri", "kudutha", "vanginen", "veena",
        "semma", "kaasu", "panam", "paravala", "marukkalaam", "mudiyathu"
    ],
    "Kannada": [
        "chennagide", "chennagi", "tumba", "thumba", "ide", "illa", "idhu", "adhu", "namage",
        "nimge", "ishta", "aaythu", "sari", "kettadu", "beda", "bekagide", "dayavittu",
        "dhanyavada", "madida", "madidare", "hege", "yaake", "channagide", "uthtama", "kevala",
        "baralla", "kodi", "khushi"
    ],
    "Hindi": [
        "bahut", "accha", "achha", "achhi", "acchi", "achhe", "bura", "bekar", "kharab",
        "nahi", "nahin", "hai", "hain", "tha", "thi", "the", "mujhe", "hume", "hum", "yeh",
        "ye", "woh", "wo", "kya", "kaise", "kyun", "pasand", "aaya", "aayi", "laga", "lagi",
        "mat", "lena", "lo", "sundar", "mast", "zabardast", "bakwas", "ghatiya", "paisa", "vasool"
    ],
    "Malayalam": [
        "nallath", "nallathoru", "nalla", "valare", "mosham", "kollam", "kollaam", "kollilla",
        "nannayittundu", "nannayi", "ithu", "athu", "enikku", "ishtapettu", "ishtamayi", "alla",
        "venda", "nandi", "pattilla", "shari", "thettu", "ariyilla", "njan", "adipoli",
        "valareye", "cheyyilla"
    ],
    "Bengali": [
        "khub", "bhalo", "baje", "kharap", "eta", "ota", "amader", "amar", "pochondo",
        "pochondoi", "hoyeche", "ache", "nei", "na", "dhonnobad", "kemon", "shundor",
        "shobcheye", "dami", "dourbhe", "ektu", "onnorokom", "kinte", "parlam", "oshadharon"
    ],
    "Marathi": [
        "khup", "chhan", "changla", "changli", "changale", "vait", "ahe", "aahe", "nahi",
        "mala", "ha", "he", "kharidi", "sundar", "dhanyawad", "aavadla", "aavadli", "barobar",
        "kiti", "kashe", "phukat", "nakko", "jhaale", "zhala", "ekdum"
    ],
    "Gujarati": [
        "bahu", "saras", "kharab", "chhe", "nathi", "mane", "aa", "gamyu", "aabhar",
        "kem", "kevu", "kharekhar", "joiye", "lejo", "najik", "saroo", "saru", "ekdam",
        "aapyo", "aavi", "tamane", "maro", "mari", "lidhu", "ghano"
    ]
}

LANGDETECT_MAP = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi"
}

def detect_language(text: str) -> Dict[str, Any]:
    """
    Detects language, script, romanization, code-mixing and confidence score.
    Returns: {language, script, is_romanized, is_code_mixed, confidence}
    """
    if not text or not text.strip():
        return {
            "language": "Unknown",
            "script": "Unknown",
            "is_romanized": False,
            "is_code_mixed": False,
            "confidence": 0.0
        }

    raw = text.strip()
    words = re.findall(r'[a-zA-Z]+', raw.lower())
    has_latin = len(words) > 0
    has_indic = False
    detected_native_lang = None
    detected_native_script = "Latin"

    # 1. Check Unicode ranges for native scripts
    for pattern, lang_name, script_name in UNICODE_SCRIPTS:
        matches = re.findall(pattern, raw)
        if len(matches) >= 2 or (len(matches) == 1 and len(raw) < 10):
            has_indic = True
            detected_native_lang = lang_name
            detected_native_script = script_name
            if lang_name == "Hindi" and re.search(r'(आहे|नाही|खूप|छान|झाले)', raw):
                detected_native_lang = "Marathi"
            break

    if has_indic:
        is_code_mixed = has_latin
        return {
            "language": detected_native_lang,
            "script": detected_native_script,
            "is_romanized": False,
            "is_code_mixed": is_code_mixed,
            "confidence": 0.98 if not is_code_mixed else 0.92
        }

    # 2. Check Romanized Indian keyword lexicons
    words_set = set(words)
    best_match_lang = None
    max_matches = 0

    for lang, lexicon in ROMANIZED_LEXICONS.items():
        matched = [w for w in words if w in lexicon]
        if len(matched) > max_matches:
            max_matches = len(matched)
            best_match_lang = lang

    if best_match_lang and max_matches >= 1:
        ratio = max_matches / max(1, len(words))
        conf = min(0.96, max(0.65, ratio * 1.5))
        is_code_mixed = ratio < 0.8
        return {
            "language": best_match_lang,
            "script": "Latin",
            "is_romanized": True,
            "is_code_mixed": is_code_mixed,
            "confidence": round(conf, 2)
        }

    # 3. Fallback to langdetect
    try:
        langs = langdetect.detect_langs(raw)
        if langs:
            top = langs[0]
            mapped = LANGDETECT_MAP.get(top.lang, "English" if top.lang == "en" else "Unknown")
            return {
                "language": mapped,
                "script": "Latin",
                "is_romanized": mapped not in ["English", "Unknown"],
                "is_code_mixed": False,
                "confidence": round(float(top.prob), 2)
            }
    except Exception:
        pass

    return {
        "language": "English",
        "script": "Latin",
        "is_romanized": False,
        "is_code_mixed": False,
        "confidence": 0.50
    }

# Alias for compatibility
detect_language_and_script = detect_language
