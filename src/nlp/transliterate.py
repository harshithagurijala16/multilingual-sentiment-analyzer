import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

TARGET_SCHEMES = {
    "Telugu": sanscript.TELUGU,
    "Tamil": sanscript.TAMIL,
    "Kannada": sanscript.KANNADA,
    "Hindi": sanscript.DEVANAGARI,
    "Malayalam": sanscript.MALAYALAM,
    "Bengali": sanscript.BENGALI,
    "Marathi": sanscript.DEVANAGARI,
    "Gujarati": sanscript.GUJARATI,
    "Punjabi": getattr(sanscript, "GURMUKHI", sanscript.DEVANAGARI),
}

ENGLISH_COMMON_WORDS = {
    "the", "is", "at", "which", "on", "this", "that", "it", "with", "for", "product",
    "delivery", "quality", "service", "worst", "great", "good", "bad", "phone", "mobile",
    "battery", "camera", "display", "screen", "price", "packaging", "packing", "super",
    "fast", "slow", "sound", "speaker", "earphones", "headphones", "laptop", "watch",
    "charger", "money", "item", "replacement", "return", "support", "amazon", "flipkart"
}

def normalize_casual_spelling(text: str) -> str:
    """Collapses elongated letters (e.g. 'superrr' -> 'super', 'cooool' -> 'cool')."""
    # For vowels, keep max 2 (e.g. cooool -> cool, feeeel -> feel)
    collapsed = re.sub(r'([aeiouAEIOU])\1{2,}', r'\1\1', text)
    # For consonants, collapse 3+ down to 1 (e.g. superrrr -> super)
    collapsed = re.sub(r'([^aeiouAEIOU\s\d])\1{2,}', r'\1', collapsed)
    return collapsed

normalize_romanized_text = normalize_casual_spelling


def transliterate_to_native(text: str, language: str) -> str:
    """
    Transliterates Romanized text to the target native Indic script.
    Preserves English words in code-mixed inputs.
    """
    if not text or language not in TARGET_SCHEMES:
        return text

    target_scheme = TARGET_SCHEMES[language]
    tokens = text.split()
    converted_tokens = []

    for token in tokens:
        clean_word = re.sub(r'[^a-zA-Z]', '', token).lower()
        if clean_word in ENGLISH_COMMON_WORDS:
            converted_tokens.append(token)
            continue

        norm_token = normalize_casual_spelling(token.lower())
        try:
            native_word = transliterate(norm_token, sanscript.ITRANS, target_scheme)
            converted_tokens.append(native_word)
        except Exception:
            converted_tokens.append(token)

    return " ".join(converted_tokens)
