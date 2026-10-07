# Multilingual Sentiment and Feedback Analytics for Indian Languages

An end-to-end full-stack analytics platform built to classify and analyze customer reviews in 9 Indian languages (Telugu, Tamil, Kannada, Hindi, Malayalam, Bengali, Marathi, Gujarati, English), supporting native scripts, Romanized transliterations, and code-mixed vernacular text.

> **Assumptions**: Romanized text language detection utilizes 25+ high-frequency linguistic marker lexicons combined with script ranges; SQLite is employed for zero-config persistence.

---

## 🏛️ System Architecture

```text
+-----------------------------------------------------------------------------------+
|                            SPA Frontend (FastAPI Served)                         |
|   Vanilla JS + Tailwind CSS (CDN) + Chart.js (CDN)                                |
|   [Dashboard] [Live Analyzer] [Bulk CSV Upload] [Reviews Explorer] [Insights]    |
+-----------------------------------------------------------------------------------+
                                       |
                           REST / JWT (Bearer Auth)
                                       v
+-----------------------------------------------------------------------------------+
|                               FastAPI Backend                                     |
|  - Auth Routes (/api/auth)      - Reviews CRUD & Bulk (/api/reviews)             |
|  - Analytics (/api/analytics)   - ReportLab PDF & CSV Export (/api/reports)       |
+-----------------------------------------------------------------------------------+
                                       |
              +------------------------+------------------------+
              |                                                 |
              v                                                 v
+-----------------------------+               +-------------------------------------+
|        NLP Pipeline         |               |           Persistence Layer         |
|  1. Language & Script       |               |  - SQLAlchemy 2.x                   |
|     (Unicode + Lexicons)    |               |  - SQLite (sentiment.db)            |
|  2. Normalization &         |               |  - User, Product, Review Models     |
|     Indic-Transliteration   |               |  - Human-in-the-Loop Corrections   |
|  3. XLM-RoBERTa Singleton   |               +-------------------------------------+
|     (Batch Inference / Fallback)                                                  
|  4. Multilingual Aspects &  |                                                     
|     Stopword Keyword Engine |                                                     
+-----------------------------+                                                     
```

---

## 🚀 Key Features

1. **Multilingual & Multi-Script Coverage**:
   - Supports **Hindi, Telugu, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, and English**.
   - Unicode block detection for native Indic scripts (Devanagari, Telugu, Tamil, Kannada, Malayalam, Bengali, Gujarati).
   - Custom Romanized marker lexicons (25+ words per language) detecting casual phonetics (e.g., *"chala bagundi"*, *"romba nalla"*, *"chennagide"*, *"bahut accha"*).

2. **Indic Transliteration & Normalization**:
   - Normalizes elongated casual spellings (*"superrr"* -> *"super"*, *"cooool"* -> *"cool"*).
   - Uses `indic-transliteration` (ITRANS / Harvard-Kyoto) to transliterate Romanized tokens into native Indic script while preserving English loanwords.

3. **Batched XLM-RoBERTa Inference**:
   - Wraps `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`.
   - Returns full class probabilities (`prob_pos`, `prob_neg`, `prob_neu`), model confidence, and automated `< 0.50` low-confidence neutral fallbacks.
   - Zero-dependency rule-based fallback if transformer is absent or running offline (`FAST_NLP=1`).

4. **Feedback Analytics & Plain-Language Insights**:
   - Automated Net Sentiment Score (NPS-style: `% Positive - % Negative`).
   - Aspect sentiment extraction across 5 major customer domains: **Quality, Delivery, Price, Service, Packaging**.
   - Top positive and negative signal keyword extraction with built-in Indic stopword filters.
   - Dynamic plain-language executive takeaway generator.

5. **Human-in-the-Loop Active Learning**:
   - Reviews Explorer with search, multi-filter dropdowns, and inline label correction.
   - Low-confidence review review queue for manual triage.
   - Training script (`training/train.py`) to fine-tune XLM-RoBERTa on user-corrected samples in Google Colab.

6. **Executive PDF & CSV Reports**:
   - Boardroom-ready PDF reports generated dynamically in Python via `ReportLab`.
   - Filterable raw dataset CSV export.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy 2.x, SQLite, Pydantic v2, JWT Auth (`python-jose`, `bcrypt`).
- **NLP**: `langdetect` (seed=0), `indic-transliteration`, Hugging Face `transformers` + `torch`, XLM-RoBERTa.
- **Frontend**: Static multi-page SPA served by FastAPI (Vanilla JS + Tailwind CSS CDN + Chart.js CDN, zero Node/build steps).
- **Reports**: `reportlab` 5.x, `pandas`.
- **Testing**: `pytest` (100% offline with mocked transformers).
- **Containerization**: Docker & Docker Compose.

---

## 📦 Setup & Installation

### Option 1: Local Setup

1. **Clone & Navigate**:
   ```bash
   git clone <repo-url>
   cd multilingual-sentiment-analyzer
   ```

2. **Create Virtual Environment & Install**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate

   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   ```

4. **Seed Database**:
   Seeds demo user (`demo@example.com` / `demo1234`), 3 products, and 125 reviews across 8 languages spread over 90 days:
   ```bash
   python scripts/seed.py
   ```

5. **Start Application**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   Open your browser at `http://localhost:8000`.

---

### Option 2: Docker & Docker Compose

```bash
# Build and run container
docker-compose up -d --build

# Inspect logs
docker-compose logs -f web
```
The app will be available at `http://localhost:8000`.

---

## 🧪 Testing

Run the automated pytest test suite (executes offline with mocked models in seconds):
```bash
pytest tests/ -v
```

---

## 📡 API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register new organization account |
| `POST` | `/api/auth/login` | Obtain JWT access token |
| `GET` | `/api/auth/me` | Fetch active user profile |
| `POST` | `/api/reviews/analyze` | Live single review analysis & optional persistence |
| `POST` | `/api/reviews/bulk` | Multipart CSV bulk upload and batched inference |
| `GET` | `/api/reviews` | Paginated, filterable reviews explorer |
| `PUT` | `/api/reviews/{id}/correct`| Submit human feedback label correction |
| `DELETE`| `/api/reviews/{id}` | Delete review |
| `GET` | `/api/reviews/products` | Retrieve registered user products |
| `GET` | `/api/reviews/template` | Download CSV template for bulk ingestion |
| `GET` | `/api/reviews/export` | Export filtered dataset as CSV |
| `GET` | `/api/analytics/summary` | KPI cards (totals, % pos/neg/neu, NPS, avg confidence) |
| `GET` | `/api/analytics/distribution` | Sentiment distribution counts and percentages |
| `GET` | `/api/analytics/by-language` | Language sentiment breakdown |
| `GET` | `/api/analytics/by-product` | Product sentiment breakdown and ranking |
| `GET` | `/api/analytics/trend` | Sentiment trend timeline (`daily`, `weekly`, `monthly`) |
| `GET` | `/api/analytics/aspects` | Domain aspect sentiment matrix (quality, delivery, etc.) |
| `GET` | `/api/analytics/keywords` | Stopword-filtered signal keywords per language |
| `GET` | `/api/analytics/low-confidence`| Human-in-the-loop review triage queue |
| `GET` | `/api/analytics/insights` | Plain-language automated business takeaways |
| `GET` | `/api/reports/pdf` | Generate and download executive ReportLab PDF report |

---

## 🖼️ Application Screenshots

<!-- Placeholder for interface screenshots -->
- **Executive Dashboard**: KPI Cards, Sentiment Donut, Language Stacked Bar, Sentiment Trendline, Product Rankings.
- **Live Review Analyzer**: Instant language/script detection, ITRANS transliteration pill, confidence & probability meters.
- **Bulk CSV Upload**: Drag-and-drop zone with validation and progress tracking.
- **Reviews Explorer**: Dynamic data table with inline human correction modal.
- **Deep Insights**: Automated plain-language takeaways and keyword chips.
- **Reports Export**: 1-click ReportLab PDF and CSV download.

---

## ⚠️ Limitations

1. **Romanized Detection Ambiguity**: Casual transliterations exhibit heavy dialectal variance (e.g. *"chala"* vs *"chaala"* vs *"chalaa"* in Telugu; *"accha"* vs *"achha"* vs *"acha"* in Hindi). Short sentences (< 3 words) without distinct lexical roots may default to English.
2. **Code-Mixing Complexity**: High-density code-switching (e.g. English technical terminology mixed with Dravidian grammar particles) can dilute model confidence.
3. **Hardware Requirements**: Full XLM-RoBERTa GPU inference is recommended for real-time latency in enterprise production settings.

---

## 🔮 Future Scope

- **LLM-Assisted Aspect-Based Sentiment Analysis (ABSA)**: Fine-grained sentiment per individual clause (e.g., *"Camera is great but delivery was late"* -> Camera: +1, Delivery: -1).
- **Speech-to-Text Support**: Integration with Indic speech models (e.g., Whisper-Indic or AI4Bharat Bhashini) for voice feedback transcription.
- **Automated Fine-Tuning Pipeline**: Scheduled GitHub Actions or Celery worker that automatically retrains XLM-RoBERTa once 500+ human-corrected labels are recorded.

---

## 📜 License
MIT License. Developed for research and enterprise feedback analytics.
