# 🧠 RecallAI — Multilingual Study & Revision Assistant

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=chainlink&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/ChromaDB-FF6F00?style=flat-square&logo=databricks&logoColor=white" alt="ChromaDB">
  <img src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=flat-square&logo=google&logoColor=white" alt="Google Gemini">
</p>

## 📌 Summary

**RecallAI** is an AI-powered, multilingual revision companion. Upload any study PDF — in any language — and the AI reads it, identifies the core concepts, and instantly generates 10 exam-ready practice questions **in the language of your choice**. A built-in RAG chatbot lets you ask follow-up questions about the document, all in your selected output language.

> **PDF language and output language are completely independent.** English PDF → Hindi output. German PDF → Russian output. Any combination works.

## 🎯 Problem Statement

Students often struggle with "information overload" when preparing for exams, and face an extra barrier when studying materials in a foreign language. **RecallAI** solves both problems using a multilingual RAG pipeline: the PDF is the source of truth; the LLM generates every response in the student's chosen language.

## ✨ Key Features

- **🌐 Multilingual Output**: Choose English, Hindi, Sanskrit, German, or Russian as your output language. Adding new languages requires a single dictionary entry.
- **📄 Seamless PDF Upload**: Drag-and-drop web interface. Any text-based PDF in any language.
- **🔍 Smart RAG Pipeline**: ChromaDB + MMR retrieval + HuggingFace embeddings — the document is your single source of truth.
- **📝 Exam Question Generation**: 10 conceptual, exam-oriented questions with answers and explanations, all in the selected language.
- **💬 Multilingual RAG Chatbot**: Ask follow-up questions; the bot always replies in your selected language regardless of how you phrase the question.
- **🕉️ Sanskrit Support**: Proper Devanagari output — not a transliteration of Hindi.
- **🛡️ Graceful Error Handling**: No stack traces exposed; localized error messages in your selected language.

## 🛠️ Tech Stack

**Frontend:**
- HTML5 / CSS3 / JavaScript (Vanilla)
- Jinja2 templating
- Custom Light Glassmorphism UI (Inter Font)

**Backend:**
- **Flask** — web server and routing
- **Flask-WTF** — secure file uploading and form validation
- **Gunicorn** — production WSGI server

**AI & Machine Learning (RAG Pipeline):**
- **LangChain** — orchestration framework
- **Google Gemini (`gemini-2.5-flash`)** — core LLM via `langchain-google-genai`
- **ChromaDB** — in-memory vector database (per-session, no persistence required)
- **HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`)** — embedding model
- **PyPDF** — text extraction from PDF files

## 📁 Project Structure

```text
RecallAI/
│
├── uploads/                  # Temporary storage for uploaded PDFs (gitignored)
│
├── templates/
│   ├── index.html            # Upload page with language selector
│   ├── result.html           # Exam questions + RAG chatbot UI
│   └── error.html            # Graceful error page
│
├── main.py                   # Flask server + LangChain RAG pipeline
├── requirements.txt          # All pip dependencies
├── Procfile                  # Gunicorn entry point (Render / Heroku)
├── runtime.txt               # Pinned Python version
├── .env.example              # Template for required environment variables
└── .gitignore
```

## 🚀 Getting Started (Local)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/RecallAI.git
cd RecallAI
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```env
SECRET_KEY=your_flask_secret_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
```

Get your Mistral API key at [console.mistral.ai](https://console.mistral.ai/).

### 5. Run the Application

```bash
python main.py
```

Open `http://127.0.0.1:5000/` in your browser.

---

## ☁️ Deploying to Render

1. Push your repository to GitHub (ensure `.env` is **not** committed).
2. Create a new **Web Service** on [Render](https://render.com/).
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn main:app`
5. Add the following **Environment Variables** in the Render dashboard:
   - `SECRET_KEY` — a long random string
   - `MISTRAL_API_KEY` — your Mistral API key
   - `FLASK_DEBUG` — `0`

> **Note on ChromaDB**: The app uses an **in-memory** Chroma instance per session, so no persistent database directory is needed on the server. Each PDF upload creates a fresh vector store for that session.

---

## 🌐 Supported Output Languages

| Code | Language  | Not-found fallback |
|------|-----------|--------------------|
| `en` | English   | "I could not find the answer in the document." |
| `hi` | Hindi     | "मुझे दस्तावेज़ में इसका उत्तर नहीं मिला।" |
| `sa` | Sanskrit  | "अस्मिन् दस्तावेजे उत्तरं न प्राप्तम्।" |
| `de` | German    | "Ich konnte die Antwort im Dokument nicht finden." |
| `ru` | Russian   | "Я не смог найти ответ в документе." |

Adding a new language requires only a new entry in the `SUPPORTED_LANGUAGES` dict in `main.py`.

---

## 🤝 Contributing

Contributions, suggestions, and feature requests are welcome. Feel free to fork the repository, open issues, and submit pull requests.

---

© 2026 Kunal Singh