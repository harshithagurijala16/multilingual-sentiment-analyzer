from typing import Dict, Any, List
from src.nlp.language import detect_language
from src.nlp.transliterate import transliterate_to_native
from src.nlp.sentiment import classify_sentiment, classify_sentiment_batch
from src.nlp.keywords import extract_aspects

def analyze_review(text: str) -> Dict[str, Any]:
    """Single review end-to-end NLP analysis."""
    lang_info = detect_language(text)
    language = lang_info["language"]
    is_romanized = lang_info["is_romanized"]

    if is_romanized and language != "English":
        transliterated_text = transliterate_to_native(text, language)
        model_input = transliterated_text
    else:
        transliterated_text = text
        model_input = text

    sentiment_info = classify_sentiment(model_input)
    aspects = extract_aspects(text)

    return {
        "original_text": text,
        "language": language,
        "script": lang_info["script"],
        "is_romanized": is_romanized,
        "is_code_mixed": lang_info["is_code_mixed"],
        "transliterated_text": transliterated_text,
        "sentiment": sentiment_info["label"],
        "confidence": sentiment_info["confidence"],
        "prob_pos": sentiment_info["prob_pos"],
        "prob_neg": sentiment_info["prob_neg"],
        "prob_neu": sentiment_info["prob_neu"],
        "low_confidence": sentiment_info["low_confidence"],
        "aspects": aspects
    }

def analyze_batch(texts: List[str]) -> List[Dict[str, Any]]:
    """Batch review end-to-end NLP analysis."""
    if not texts:
        return []

    lang_infos = [detect_language(t) for t in texts]
    model_inputs = []
    transliterated_list = []

    for i, t in enumerate(texts):
        info = lang_infos[i]
        if info["is_romanized"] and info["language"] != "English":
            trans = transliterate_to_native(t, info["language"])
            model_inputs.append(trans)
            transliterated_list.append(trans)
        else:
            model_inputs.append(t)
            transliterated_list.append(t)

    sentiments = classify_sentiment_batch(model_inputs, batch_size=16)

    results = []
    for i, t in enumerate(texts):
        s_info = sentiments[i]
        l_info = lang_infos[i]
        results.append({
            "original_text": t,
            "language": l_info["language"],
            "script": l_info["script"],
            "is_romanized": l_info["is_romanized"],
            "is_code_mixed": l_info["is_code_mixed"],
            "transliterated_text": transliterated_list[i],
            "sentiment": s_info["label"],
            "confidence": s_info["confidence"],
            "prob_pos": s_info["prob_pos"],
            "prob_neg": s_info["prob_neg"],
            "prob_neu": s_info["prob_neu"],
            "low_confidence": s_info["low_confidence"],
            "aspects": extract_aspects(t)
        })

    return results
