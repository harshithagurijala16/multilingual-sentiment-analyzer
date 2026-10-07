import re
from collections import Counter
from typing import List, Dict, Any, Tuple

# Small built-in stopword lists for Indian languages + English (no downloads needed)
STOPWORDS = {
    "English": {
        "the", "is", "at", "which", "on", "this", "that", "it", "with", "for", "and", "a", "an",
        "of", "in", "to", "was", "are", "have", "had", "be", "been", "as", "by", "from", "or",
        "too", "my", "we", "they", "them", "their", "so", "just", "very", "i", "you", "he", "she"
    },
    "Telugu": {
        "ee", "idi", "adi", "lo", "ki", "ku", "kuda", "ga", "unna", "unnayi", "nenu", "naku",
        "meeru", "meeku", "kani", "mariyu", "ani", "kani", "ante", "ippudu", "eppudu", "gurinchi",
        "ఈ", "మరియు", "కూడా", "లో", "కి", "కు", "అని", "కానీ", "నాకు", "మీకు", "ఉన్న", "ఉంది"
    },
    "Hindi": {
        "hai", "hain", "tha", "thi", "the", "ka", "ki", "ke", "ko", "se", "mein", "aur", "ye",
        "wo", "yeh", "woh", "bhi", "toh", "kya", "kyun", "hume", "mujhe", "aap", "tum",
        "है", "हैं", "था", "थी", "का", "की", "के", "को", "से", "में", "और", "भी", "यह", "वह"
    },
    "Tamil": {
        "idhu", "adhu", "in", "ku", "um", "illai", "aanaal", "endru", "enakku", "ungalukku",
        "இந்த", "அந்த", "மற்றும்", "இல்லை", "ஆனால்", "என்று", "எனக்கு", "உங்களுக்கு"
    },
    "Kannada": {
        "idhu", "adhu", "alli", "illi", "ge", "inda", "mattu", "illa", "namage", "nimge",
        "ಈ", "ಆ", "మత్తు", "ಇದು", "ಅದು", "ಮತ್ತು", "ಇಲ್ಲ", "ನಮಗೆ", "ನಿಮಗೆ"
    },
    "Malayalam": {
        "ithu", "athu", "il", "nnu", "enikku", "pakshe", "alla", "koodi",
        "ഇത്", "അത്", "പക്ഷെ", "എനിക്ക്", "ഇല്ല", "കൂടി"
    },
    "Bengali": {
        "eta", "ota", "te", "er", "o", "ar", "ebong", "kintu", "amar", "amader",
        "এই", "ওই", "এবং", "কিন্তু", "আমার", "আমাদের", "আছে", "নেই"
    },
    "Marathi": {
        "ha", "he", "ahe", "aahe", "nahi", "ani", "pan", "mala", "amhi",
        "हा", "हे", "आहे", "नाही", "आणि", "पण", "मला", "आम्ही"
    }
}

ASPECT_MAPS = {
    "delivery": {
        "delivery", "shipping", "courier", "package", "arrived", "late", "fast", "speed",
        "time", "delivered", "dispatch", "order", "reach", "వచ్చింది", "డెలివరీ", "समय",
        "पहुंचा", "டெலிவரி", "டெலிவரி", "ತಲುಪಿದೆ"
    },
    "price": {
        "price", "cost", "money", "worth", "expensive", "cheap", "value", "paisa", "vasool",
        "budget", "rate", "rupees", "offer", "discount", "ధర", "పైసలు", "दाम", "पैसे",
        "किफायती", "விலை", "ಬೆಲೆ", "പണം"
    },
    "quality": {
        "quality", "material", "build", "durability", "premium", "cheap", "broken", "finish",
        "working", "performance", "defect", "flimsy", "నాణ్యత", "గుణమట్టం", "गुणवत्ता",
        "खराब", "तगड़ा", "தரம்", "ಗುಣಮಟ್ಟ", "നിലവാരം"
    },
    "service": {
        "service", "support", "customer", "care", "agent", "call", "help", "warranty",
        "replacement", "refund", "return", "సహాయం", "సేవ", "सेवा", "वारंटी", "ரிட்டர்ன்",
        "ಸೇವೆ", "സേവനം"
    },
    "packaging": {
        "packaging", "packing", "box", "bubble", "wrap", "seal", "open", "damaged", "cover",
        "ప్యాకింగ్", "పెట్టె", "पैकिंग", "डिब्बा", "பேக்கேஜிங்", "ಪ್ಯಾಕಿಂಗ್"
    }
}

def extract_aspects(text: str) -> List[str]:
    """Detects product aspects mentioned in review text."""
    lower = text.lower()
    detected = []
    for aspect, terms in ASPECT_MAPS.items():
        if any(re.search(r'\b' + re.escape(term) + r'\b', lower) or term in lower for term in terms):
            detected.append(aspect)
    return detected

def extract_top_keywords(reviews: List[Dict[str, Any]], language: str = "English", top_k: int = 10) -> Dict[str, List[Tuple[str, int]]]:
    """Extracts top positive and negative keywords for a given language."""
    stop_set = STOPWORDS.get(language, STOPWORDS["English"])
    pos_words = []
    neg_words = []

    for r in reviews:
        if language and r.get("language") != language:
            continue
        text = r.get("original_text", "").lower()
        words = re.findall(r'[a-zA-Z\u0900-\u0D7F]+', text)
        filtered = [w for w in words if len(w) > 2 and w not in stop_set]
        
        sent = r.get("sentiment", "Neutral")
        if sent == "Positive":
            pos_words.extend(filtered)
        elif sent == "Negative":
            neg_words.extend(filtered)

    return {
        "positive": Counter(pos_words).most_common(top_k),
        "negative": Counter(neg_words).most_common(top_k)
    }
