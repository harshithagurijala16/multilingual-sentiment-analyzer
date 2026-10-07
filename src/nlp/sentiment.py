import os
import logging
from typing import Dict, Any, List, Optional
import torch

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("MODEL_NAME", "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual")

# Simple multilingual sentiment dictionary fallback
FALLBACK_POSITIVE = {
    "good", "great", "excellent", "super", "awesome", "fantastic", "love", "best", "happy",
    "bagundi", "baagundi", "nachindi", "accha", "achha", "mast", "bhalo", "vadiya", "changla",
    "saras", "kollam", "chennagide", "chennagi", "superga", "dhanyawad", "nandri", "shandar"
}

FALLBACK_NEGATIVE = {
    "bad", "worst", "terrible", "poor", "waste", "horrible", "broken", "darunam", "nachaledu",
    "bekar", "kharab", "baje", "vait", "mosam", "kettadu", "disappointed", "slow", "fake",
    "ghatiya", "bakwas", "cheated", "damaged", "chandalanga"
}

class SentimentModelSingleton:
    _instance = None

    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_loaded = False
        self._load_attempted = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SentimentModelSingleton()
        return cls._instance

    def load_model(self):
        if self._load_attempted:
            return
        self._load_attempted = True
        if os.getenv("FAST_NLP", "0") == "1" or os.getenv("USE_MOCK_MODEL", "0") == "1":
            logger.info("FAST_NLP/USE_MOCK_MODEL is set. Using fast sentiment analyzer.")
            self.is_loaded = False
            return

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            model_name = DEFAULT_MODEL
            # Check local or alternative repo
            logger.info(f"Loading XLM-RoBERTa model {model_name} on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name, use_safetensors=False)
            self.model.to(self.device)
            self.model.eval()
            self.is_loaded = True
            logger.info("XLM-RoBERTa model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load XLM-RoBERTa model ({e}). Engaging graceful rule-based fallback.")
            self.is_loaded = False

    def predict_batch(self, texts: List[str], batch_size: int = 16) -> List[Dict[str, Any]]:
        self.load_model()
        if not self.is_loaded or self.model is None or self.tokenizer is None:
            return [self._fallback_predict(t) for t in texts]

        results = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            try:
                inputs = self.tokenizer(
                    chunk,
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt"
                ).to(self.device)

                with torch.no_grad():
                    logits = self.model(**inputs).logits
                    probs = torch.nn.functional.softmax(logits, dim=-1).cpu().tolist()

                for p in probs:
                    # cardiffnlp standard label indices: 0: Negative, 1: Neutral, 2: Positive
                    p_neg = round(float(p[0]), 4)
                    p_neu = round(float(p[1]), 4)
                    p_pos = round(float(p[2]), 4)

                    top_val = max(p_pos, p_neg, p_neu)
                    low_conf = top_val < 0.50

                    if low_conf:
                        label = "Neutral"
                        conf = p_neu
                    elif top_val == p_pos:
                        label = "Positive"
                        conf = p_pos
                    elif top_val == p_neg:
                        label = "Negative"
                        conf = p_neg
                    else:
                        label = "Neutral"
                        conf = p_neu

                    results.append({
                        "label": label,
                        "confidence": round(conf, 4),
                        "prob_pos": p_pos,
                        "prob_neg": p_neg,
                        "prob_neu": p_neu,
                        "low_confidence": low_conf
                    })
            except Exception as e:
                logger.warning(f"Batch prediction error ({e}). Using fallback for chunk.")
                for t in chunk:
                    results.append(self._fallback_predict(t))

        return results

    def _fallback_predict(self, text: str) -> Dict[str, Any]:
        words = set(text.lower().split())
        pos = len(words.intersection(FALLBACK_POSITIVE))
        neg = len(words.intersection(FALLBACK_NEGATIVE))

        if pos > neg:
            conf = 0.80
            return {
                "label": "Positive",
                "confidence": conf,
                "prob_pos": 0.80,
                "prob_neg": 0.10,
                "prob_neu": 0.10,
                "low_confidence": False
            }
        elif neg > pos:
            conf = 0.82
            return {
                "label": "Negative",
                "confidence": conf,
                "prob_pos": 0.08,
                "prob_neg": 0.82,
                "prob_neu": 0.10,
                "low_confidence": False
            }
        else:
            return {
                "label": "Neutral",
                "confidence": 0.60,
                "prob_pos": 0.20,
                "prob_neg": 0.20,
                "prob_neu": 0.60,
                "low_confidence": True
            }

def classify_sentiment(text: str) -> Dict[str, Any]:
    model = SentimentModelSingleton.get_instance()
    return model.predict_batch([text], batch_size=1)[0]

def classify_sentiment_batch(texts: List[str], batch_size: int = 16) -> List[Dict[str, Any]]:
    model = SentimentModelSingleton.get_instance()
    return model.predict_batch(texts, batch_size=batch_size)

def get_sentiment_pipeline():
    singleton = SentimentModelSingleton.get_instance()
    class PipelineWrapper:
        def predict(self, text: str):
            return singleton.predict_batch([text], batch_size=1)[0]
    return PipelineWrapper()

