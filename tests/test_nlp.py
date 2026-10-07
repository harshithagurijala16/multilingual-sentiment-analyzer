import pytest
from src.nlp.language import detect_language_and_script
from src.nlp.transliterate import transliterate_to_native, normalize_romanized_text
from src.nlp.sentiment import get_sentiment_pipeline
from src.nlp.keywords import extract_aspects, extract_top_keywords
from src.nlp.pipeline import analyze_review, analyze_batch

def test_language_detection_native_script():
    # Hindi
    res_hi = detect_language_and_script("यह उत्पाद वास्तव में बहुत अच्छा और टिकाऊ है।")
    assert res_hi["language"] == "Hindi"
    assert res_hi["script"] == "Devanagari"
    assert not res_hi["is_romanized"]

    # Telugu
    res_te = detect_language_and_script("ఈ మొబైల్ కెమెరా క్వాలిటీ చాలా బాగుంది.")
    assert res_te["language"] == "Telugu"
    assert res_te["script"] == "Telugu"

    # Tamil
    res_ta = detect_language_and_script("இந்த தயாரிப்பு மிகவும் பயனுள்ளதாக உள்ளது.")
    assert res_ta["language"] == "Tamil"
    assert res_ta["script"] == "Tamil"

    # Bengali
    res_bn = detect_language_and_script("পণ্যটি সত্যিই খুব ভালো এবং কার্যকর।")
    assert res_bn["language"] == "Bengali"
    assert res_bn["script"] == "Bengali"

def test_language_detection_romanized():
    # Telugu Romanized
    res_te = detect_language_and_script("chala bagundi ee smartphone")
    assert res_te["language"] == "Telugu"
    assert res_te["is_romanized"] is True

    # Tamil Romanized
    res_ta = detect_language_and_script("romba nalla irukku delivery late")
    assert res_ta["language"] == "Tamil"
    assert res_ta["is_romanized"] is True

    # Kannada Romanized
    res_kn = detect_language_and_script("chennagide tumba ishta aayithu")
    assert res_kn["language"] == "Kannada"
    assert res_kn["is_romanized"] is True

    # Hindi Romanized
    res_hi = detect_language_and_script("bahut accha phone hai bhai paisa vasool")
    assert res_hi["language"] == "Hindi"
    assert res_hi["is_romanized"] is True

def test_normalization_and_transliteration():
    raw = "superrrr coool phoone"
    norm = normalize_romanized_text(raw)
    assert "super" in norm
    assert "cool" in norm

    # Transliteration of Telugu Romanized
    translit = transliterate_to_native("bagundi", "Telugu")
    assert translit != ""

def test_sentiment_pipeline():
    pipeline = get_sentiment_pipeline()
    res = pipeline.predict("Very good quality and fast delivery!")
    assert res["label"] in ["Positive", "Negative", "Neutral"]
    assert 0.0 <= res["confidence"] <= 1.0
    assert "prob_pos" in res and "prob_neg" in res and "prob_neu" in res

def test_aspect_extraction():
    text = "The delivery was delayed and packaging was torn but quality is awesome."
    aspects = extract_aspects(text)
    assert "delivery" in aspects
    assert "packaging" in aspects
    assert "quality" in aspects

def test_full_nlp_pipeline():
    res = analyze_review("Camera quality chala bagundi, battery superb")
    assert res["language"] == "Telugu"
    assert res["is_romanized"] is True
    assert res["sentiment"] in ["Positive", "Negative", "Neutral"]
    assert isinstance(res["aspects"], list)
    assert "quality" in res["aspects"]

    # Batch test
    batch_res = analyze_batch([
        "Bahut accha product hai",
        "Worst experience ever, totally useless"
    ])
    assert len(batch_res) == 2
    assert batch_res[0]["sentiment"] in ["Positive", "Negative", "Neutral"]
    assert batch_res[1]["sentiment"] in ["Positive", "Negative", "Neutral"]
