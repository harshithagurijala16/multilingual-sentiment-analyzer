"""
Fine-tuning XLM-RoBERTa on Human-Corrected Multilingual Indian Reviews
====================================================================
Designed for execution on Google Colab with GPU Runtime (T4 / V100 / A100).
DO NOT RUN IN LOCAL TEST ENVIRONMENTS.

Instructions for Google Colab:
1. In Colab menu: Runtime -> Change runtime type -> Hardware accelerator -> GPU (T4).
2. Upload this script or copy-paste into a notebook cell.
3. Export reviews from IndicSentiment web app (Reports -> Export Dataset as CSV)
   and upload as `reviews_export.csv`.
4. Run:
   !pip install -q transformers datasets torch scikit-learn pandas accelerate
   !python train.py --data reviews_export.csv --epochs 3 --batch_size 16
"""

import os
import argparse
import logging
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("train")

# Label mapping consistent with cardiffnlp twitter-xlm-roberta
LABEL2ID = {"Negative": 0, "Neutral": 1, "Positive": 2}
ID2LABEL = {0: "Negative", 1: "Neutral", 2: "Positive"}

class MultilingualReviewDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item

    def __len__(self):
        return len(self.labels)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    acc = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average="macro", zero_division=0)
    return {
        "accuracy": acc,
        "macro_f1": f1,
        "macro_precision": precision,
        "macro_recall": recall,
    }

def train_model(
    data_path: str = "reviews_export.csv",
    base_model: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual",
    output_dir: str = "./fine_tuned_indic_xlm_roberta",
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    max_length: int = 256,
):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using compute device: {device}")
    if device != "cuda":
        logger.warning("GPU not detected. Training on CPU will be extremely slow. Recommend Colab GPU.")

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file '{data_path}' not found. Please export CSV from the web app first.")

    logger.info(f"Loading dataset from {data_path}...")
    df = pd.read_csv(data_path)

    # Use corrected_label if present, otherwise fall back to initial sentiment
    text_col = "original_text" if "original_text" in df.columns else "review"
    label_col = "corrected_label" if "corrected_label" in df.columns else "sentiment"

    df["final_label"] = df[label_col].fillna(df.get("sentiment", "Neutral"))
    df = df.dropna(subset=[text_col, "final_label"])
    df = df[df["final_label"].isin(LABEL2ID.keys())]

    logger.info(f"Total valid training samples: {len(df)}")
    logger.info(f"Class distribution:\n{df['final_label'].value_counts()}")

    texts = df[text_col].astype(str).tolist()
    labels = [LABEL2ID[lbl] for lbl in df["final_label"].tolist()]

    # Stratified Train/Validation Split
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels if len(set(labels)) > 1 else None
    )

    logger.info(f"Train set: {len(train_texts)} | Validation set: {len(val_texts)}")

    # Load Tokenizer & Model
    logger.info(f"Loading base tokenizer and model: {base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # Tokenize
    logger.info("Tokenizing text batches...")
    train_encodings = tokenizer(train_texts, truncation=True, max_length=max_length, padding="max_length")
    val_encodings = tokenizer(val_texts, truncation=True, max_length=max_length, padding="max_length")

    train_dataset = MultilingualReviewDataset(train_encodings, train_labels)
    val_dataset = MultilingualReviewDataset(val_encodings, val_labels)

    # Training Arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_dir="./logs",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        learning_rate=learning_rate,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
    )

    logger.info("Beginning fine-tuning...")
    trainer.train()

    logger.info(f"Saving fine-tuned model and tokenizer to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info("Fine-tuning completed successfully! To use this model in the app, update MODEL_NAME in .env.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune XLM-RoBERTa on Indian Language Reviews")
    parser.add_argument("--data", type=str, default="reviews_export.csv", help="Path to exported CSV")
    parser.add_argument("--base_model", type=str, default="cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual")
    parser.add_argument("--output_dir", type=str, default="./fine_tuned_indic_xlm_roberta")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    args = parser.parse_args()

    train_model(
        data_path=args.data,
        base_model=args.base_model,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )
