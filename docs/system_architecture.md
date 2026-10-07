# System Architecture & Technical Specifications

**Project Title:** Multilingual Sentiment and Feedback Analytics for Indian Languages  
**Core Model:** XLM-RoBERTa (Cross-lingual Language Model)  
**NLP Pipeline:** Text Cleaning • Language Detection • Romanized Identification • Indic Transliteration • Transformer Sentiment Classification  
**Backend:** FastAPI • PyTorch • Transformers • indic-transliteration • langdetect • motor  
**Frontend:** Next.js 16 • TypeScript • Tailwind CSS • Recharts  
**Database:** MongoDB Document Store with Resilient Local Persistence Engine  

---

## 1. High-Level System Architecture

The following diagram illustrates the complete end-to-end architecture across Client, API Gateway, ML Processing Engine, and Database layers:

```mermaid
graph TD
    Client["Client Web Browser<br/>(Next.js App / Recharts)"]
    API["FastAPI REST API Gateway<br/>(Asynchronous ASGI Server)"]
    
    subgraph ML_Pipeline["NLP / ML Pipeline Subsystem"]
        Clean["Text Cleaning & Normalization<br/>(NFKC, URL Stripping, Noise Removal)"]
        LangDetect["Language & Script Detection<br/>(langdetect & Unicode Script Matcher)"]
        RomDetect{"Is Romanized<br/>Indian Text?"}
        Translit["Indic Transliteration Engine<br/>(indic-transliteration sanscript)"]
        Model["XLM-RoBERTa Deep Learning Model<br/>(Sequence Classification & PyTorch Softmax)"]
    end
    
    subgraph Data_Layer["Persistence Layer"]
        DB["MongoDB Database<br/>(Reviews & Telemetry Collection)"]
        Cache["Resilient Local Fallback Engine<br/>(Auto Failover Store)"]
    end

    Client -->|"HTTP / REST API (JSON / Multipart CSV)"| API
    API --> Clean
    Clean --> LangDetect
    LangDetect --> RomDetect
    RomDetect -->|"Yes (e.g. 'chala bagundi')"| Translit
    RomDetect -->|"No (Native Script / English)"| Model
    Translit -->|"Converted Native Script"| Model
    Model -->|"Predicted Sentiment & Probabilities"| API
    API -->|"Persist Record"| DB
    DB -.->|"Offline Fallback"| Cache
    DB -->|"Aggregation Pipeline"| API
    API -->|"Dashboard Metrics & Insights"| Client
```

---

## 2. Data Flow Diagram (DFD - Level 1)

```mermaid
sequenceDiagram
    autonumber
    actor User as Business / End User
    participant Frontend as Next.js Web UI
    participant Backend as FastAPI Backend
    participant Pipeline as ML Pipeline (NLP)
    participant Model as XLM-RoBERTa (PyTorch)
    participant Database as MongoDB Store

    User->>Frontend: Submit customer review text or upload CSV
    Frontend->>Backend: POST /api/analyze or POST /api/analyze/bulk
    Backend->>Pipeline: Clean and normalize text input
    Pipeline->>Pipeline: Detect language and check Romanization
    alt Is Romanized Indian Language
        Pipeline->>Pipeline: Transliterate phonetic text to native Indic script
    end
    Pipeline->>Model: Tokenize & forward pass through XLM-RoBERTa
    Model-->>Pipeline: Return logits & calculate softmax probabilities
    Pipeline-->>Backend: Compiled prediction (Sentiment, Confidence, Probabilities)
    Backend->>Database: Save review record and telemetry
    Backend-->>Frontend: Standardized JSON response
    Frontend-->>User: Display badges, probabilities, transliteration, and analytics
```

---

## 3. Use Case Diagram

```mermaid
graph LR
    actor User["Business Analyst / Reviewer"]

    subgraph System["Multilingual Sentiment Analytics Platform"]
        UC1["Analyze Single Customer Review"]
        UC2["Detect Language & Romanized Script"]
        UC3["Transliterate Phonetic Text to Native Script"]
        UC4["Upload & Process Bulk Reviews (CSV)"]
        UC5["View Feedback Analytics Dashboard"]
        UC6["Filter Metrics by Language, Date, Sentiment"]
        UC7["Read Automated Business Feedback Insights"]
        UC8["Inspect Historical Review Records"]
        UC9["Export Analyzed Dataset as CSV"]
        UC10["Delete Review Records"]
    end

    User --> UC1
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC7
    User --> UC8
    User --> UC9
    User --> UC10

    UC1 -.-> UC2
    UC2 -.-> UC3
    UC4 -.-> UC2
```

---

## 4. Activity Diagram: Review Analysis Lifecycle

```mermaid
stateDiagram-v2
    [*] --> ReceiveInput: User inputs review text
    ReceiveInput --> TextCleaning: Preprocess & normalize unicode
    TextCleaning --> CheckNativeScript: Check Unicode range (Telugu, Devanagari, Tamil, etc.)
    
    state ScriptBranch <<choice>>
    CheckNativeScript --> ScriptBranch
    
    ScriptBranch --> NativeIdentified: Native script found (>=2 chars)
    ScriptBranch --> CheckLatinLetters: Only Latin characters found
    
    CheckLatinLetters --> CheckRomanizedLexicon: Match against regional phonetic lexicons
    
    state RomanizedBranch <<choice>>
    CheckRomanizedLexicon --> RomanizedBranch
    
    RomanizedBranch --> RomanizedDetected: Matched (e.g. Telugu 'chala bagundi')
    RomanizedBranch --> LangDetectEnglish: No match (Standard English fallback)
    
    RomanizedDetected --> TransliterateToNative: indic-transliteration (sanscript)
    TransliterateToNative --> TokenizeModel: Tokenize native script for XLM-R
    
    NativeIdentified --> TokenizeModel: Tokenize native script
    LangDetectEnglish --> TokenizeModel: Tokenize English text
    
    TokenizeModel --> XLMRoBERTaInference: Run PyTorch eval in torch.no_grad()
    XLMRoBERTaInference --> CalculateSoftmax: Softmax -> Positive, Negative, Neutral
    CalculateSoftmax --> PersistToDatabase: Write document to MongoDB collection
    PersistToDatabase --> ReturnResult: Send response to user & update dashboard
    ReturnResult --> [*]
```

---

## 5. Component Diagram

```mermaid
graph TB
    subgraph UI_Layer["Presentation Layer (Next.js)"]
        PageHome["Home Landing (/)"]
        PageAnalyze["Single Review (/analyze)"]
        PageBulk["Bulk Upload (/bulk-analysis)"]
        PageDash["Analytics Dashboard (/dashboard)"]
        PageHistory["Review Archive (/reviews)"]
        PageDetail["Review Detail (/reviews/[id])"]
        PageAbout["About & Docs (/about)"]
    end

    subgraph API_Layer["Service Gateway (FastAPI)"]
        RouterMain["Routes Controller (/api/analyze, /api/reviews)"]
        RouterDash["Dashboard Controller (/api/dashboard/*)"]
        Middleware["CORS & Error Handlers"]
    end

    subgraph Service_Layer["Business Logic Layer"]
        ServiceAnalysis["AnalysisService"]
        ServiceBulk["BulkAnalysisService"]
        ServiceDashboard["DashboardService"]
    end

    subgraph ML_Subsystem["Machine Learning Subsystem"]
        PipeCore["MultilingualSentimentPipeline"]
        DetectorLang["LanguageDetector"]
        TranslitMgr["IndicTransliterationManager"]
        ModelMgr["ModelManager (XLM-RoBERTa)"]
        TokMgr["TokenizerManager"]
        SentClassifier["SentimentClassifier"]
    end

    subgraph Persistence_Subsystem["Data Storage Layer"]
        Repo["ReviewRepository"]
        MongoMgr["DatabaseManager (Motor)"]
        LocalStore["Local Fallback Store"]
    end

    UI_Layer --> API_Layer
    API_Layer --> Service_Layer
    Service_Layer --> ML_Subsystem
    Service_Layer --> Persistence_Subsystem
    Persistence_Subsystem --> MongoMgr
    Persistence_Subsystem --> LocalStore
```
