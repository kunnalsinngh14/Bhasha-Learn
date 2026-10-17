import os
import uuid
import logging
import markdown
from dotenv import load_dotenv
from flask import Flask, request, render_template, session
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import FileField, SelectField, SubmitField
from wtforms.validators import InputRequired
from werkzeug.utils import secure_filename

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── APPLICATION SETUP ──────────────────────────────────────────────────────────
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(24)
app.config["SESSION_TYPE"] = "filesystem"

os.makedirs("uploads", exist_ok=True)

# ── MODEL & RETRIEVER CONFIGURATION ──────────────────────────────────────────
_llm = None
_cached_llm_config = None
_embeddings = None
_retriever_store = {}


def get_llm():
    """Dynamically initialize or reload the Gemini LLM with current credentials."""
    global _llm, _cached_llm_config
    load_dotenv(override=True)

    raw_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    api_key = raw_key.strip().strip('"').strip("'")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Please set your Gemini API key in the .env file.")

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    current_config = (api_key, model_name)

    if _llm is None or _cached_llm_config != current_config:
        _llm = init_chat_model(model_name, model_provider="google_genai", api_key=api_key)
        _cached_llm_config = current_config
    return _llm


def get_embeddings():
    """Lazily load HuggingFace embeddings on first use."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings


def _get_retriever():
    return _retriever_store.get(session.get("session_id"))


def _set_retriever(retriever):
    sid = session.get("session_id")
    if sid:
        _retriever_store[sid] = retriever


# ── DOCUMENT LOADER (PDF, PPT, DOCX, TXT, MD) ──────────────────────────────────
def load_document(file_path: str) -> list[Document]:
    """
    Extract readable text chunks/documents from various file formats:
    - .pdf: Uses PyPDFLoader
    - .txt, .md: Native UTF-8 parsing with fallback
    - .docx: Uses python-docx (paragraphs and tables)
    - .pptx, .ppt: Uses python-pptx (slides, text frames, and speaker notes)
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        return loader.load()

    if ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return [Document(page_content=text, metadata={"source": file_path})]

    if ext == ".docx":
        import docx
        doc = docx.Document(file_path)
        parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)
        return [Document(page_content="\n\n".join(parts), metadata={"source": file_path})]

    if ext in [".pptx", ".ppt"]:
        if ext == ".ppt":
            try:
                import pptx
                prs = pptx.Presentation(file_path)
            except Exception:
                raise ValueError("Legacy binary .ppt format is not directly supported. Please save or convert your presentation to .pptx or .pdf.")
        else:
            import pptx
            prs = pptx.Presentation(file_path)

        docs = []
        for idx, slide in enumerate(prs.slides):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_texts.append(text)
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_texts.append(f"[Notes: {notes}]")
            content = "\n".join(slide_texts)
            if content.strip():
                docs.append(Document(page_content=content, metadata={"source": file_path, "slide": idx + 1}))
        return docs

    raise ValueError(f"Unsupported file format: {ext}. Supported formats: PDF, PPTX, DOCX, TXT, MD.")


# ── SUPPORTED LANGUAGES ───────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": {
        "name": "English",
        "not_found": "I could not find the answer in the document.",
        "chat_greeting": "Hi! I've generated your chapter study notes and practice questions above. Feel free to ask any follow-up questions about the document here!",
        "error_no_pdf": "Please upload your study material first before asking questions.",
        "error_generation": "Something went wrong while generating study notes and questions. Please try again.",
        "error_retrieval": "Something went wrong while retrieving the answer. Please try again.",
    },
    "hi": {
        "name": "Hindi",
        "not_found": "मुझे दस्तावेज़ में इसका उत्तर नहीं मिला।",
        "chat_greeting": "नमस्ते! मैंने ऊपर आपके अध्याय के अध्ययन नोट्स और अभ्यास प्रश्न तैयार कर दिए हैं। आप यहाँ दस्तावेज़ से संबंधित कोई भी प्रश्न पूछ सकते हैं!",
        "error_no_pdf": "कृपया पहले अपनी अध्ययन सामग्री अपलोड करें।",
        "error_generation": "नोट्स और प्रश्न उत्पन्न करने में कुछ गड़बड़ी हुई। कृपया पुनः प्रयास करें।",
        "error_retrieval": "उत्तर प्राप्त करने में कुछ गड़बड़ी हुई। कृपया पुनः प्रयास करें।",
    },
    "sa": {
        "name": "Sanskrit",
        "not_found": "अस्मिन् दस्तावेजे उत्तरं न प्राप्तम्।",
        "chat_greeting": "नमस्ते! उपरि भवतः पाठस्य टिप्पणी (notes) अभ्यासप्रश्नाः च सज्जीकृताः। अत्र भवान् दस्तावेजाधारितं किमपि प्रश्नं प्रष्टुं शक्नोति।",
        "error_no_pdf": "कृपया प्रथमं अध्ययनसामग्रीं अपलोड करोतु।",
        "error_generation": "टिप्पणीनां प्रश्नानां च उत्पादने त्रुटिः। कृपया पुनः प्रयत्नं करोतु।",
        "error_retrieval": "उत्तरप्राप्तौ त्रुटिः। कृपया पुनः प्रयत्नं करोतु।",
    },
    "de": {
        "name": "German",
        "not_found": "Ich konnte die Antwort im Dokument nicht finden.",
        "chat_greeting": "Hallo! Ich habe oben Ihre Zusammenfassung und Übungsfragen erstellt. Sie können mir hier gerne weitere Fragen zum Dokument stellen!",
        "error_no_pdf": "Bitte laden Sie zuerst Ihre Studienunterlagen hoch.",
        "error_generation": "Bei der Erstellung der Notizen und Fragen ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
        "error_retrieval": "Bei der Antwortsuche ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
    },
    "ru": {
        "name": "Russian",
        "not_found": "Я не смог найти ответ в документе.",
        "chat_greeting": "Здравствуйте! Выше подготовлены краткие учебные заметки и практические вопросы. Задайте любой вопрос по документу здесь!",
        "error_no_pdf": "Пожалуйста, сначала загрузите учебные материалы.",
        "error_generation": "При создании заметок и вопросов произошла ошибка. Пожалуйста, попробуйте снова.",
        "error_retrieval": "При поиске ответа произошла ошибка. Пожалуйста, попробуйте снова.",
    },
}

LANGUAGE_CHOICES = [(code, details["name"]) for code, details in SUPPORTED_LANGUAGES.items()]

# ── PROMPT TEMPLATES ──────────────────────────────────────────────────────────
study_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are an expert university professor and exam creator.

Target output language: {target_language}

Your task is to carefully analyze the provided document context and generate a complete, high-quality study guide strictly grounded in the document. The uploaded document is your sole source of truth. Do not invent facts or use unrelated outside knowledge.

You MUST structure your response into two distinct, beautifully formatted sections:

---

# 📖 Part 1: Comprehensive Chapter Study Notes

Create well-structured, clear, and high-yield revision notes covering the material:
1. **Executive Overview / Chapter Summary**: A clear summary of the main subject and themes.
2. **Key Concepts & Definitions**: Clear explanations of core terms, theories, and concepts.
3. **Core Principles, Formulas, Processes & Comparisons**: Important mechanisms, algorithms, steps, diagrams, formulas, or comparisons found in the text.
4. **Key Takeaways & High-Yield Exam Points**: Critical points students should remember for exams.

Use clean Markdown formatting: headings (##, ###), bullet points, bold text for key terms, and tables or code blocks where appropriate.

---

# 🎯 Part 2: Practice Exam Questions

Generate 10 exam-oriented practice questions that test conceptual understanding and recall of the chapter:
1. Base every question strictly on the provided context.
2. Cover different sections of the document to ensure balanced coverage.
3. Include conceptual questions, definitions, application questions, and comparisons.
4. Avoid duplicate or trivial questions.
5. Under each question, clearly provide the **Correct Answer** and a concise **Explanation**.

Formatting for each question:
### Question X: [Question text]
- **Answer**: [Detailed correct answer]
- **Explanation**: [Concise explanation explaining why it is correct based on the text]

---

Language Requirements:
- Write the ENTIRE response (both Study Notes and Practice Questions) in the target output language: {target_language}.
- If the target output language is Sanskrit, write in authentic Sanskrit using the Devanagari script. Do NOT transliterate and do NOT treat it as Hindi.
"""),
    ("human", "Document context:\n{context}"),
])

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You answer questions about an uploaded document.

Target output language: {target_language}

Use only the provided document context. Do not invent information or rely
on unrelated outside knowledge. If the answer is not present in the context,
respond exactly with:
{not_found}

Generate the response entirely in the target output language, regardless of
the language of the document or the user's question. If the target output
language is Sanskrit, use Sanskrit in Devanagari and do not treat it as
Hindi or transliterate it.
"""),
    ("human", "Document context:\n{context}\n\nUser question:\n{question}"),
])


# ── FORMS & HELPERS ───────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = ["pdf", "pptx", "ppt", "docx", "doc", "txt", "md"]


class FileForm(FlaskForm):
    file = FileField(
        "Study Material",
        validators=[
            InputRequired(),
            FileAllowed(ALLOWED_EXTENSIONS, "Supported formats: PDF, PPTX, DOCX, TXT, MD"),
        ],
    )
    target_language = SelectField("Output Language", choices=LANGUAGE_CHOICES, validators=[InputRequired()])
    submit = SubmitField("Upload")


def _build_exam_context(retriever, chunks) -> str:
    """Build representative document context preserving coverage while respecting context limits."""
    if not chunks:
        return ""

    total_chars = sum(len(c.page_content) for c in chunks)
    if total_chars <= 40000:
        return "\n\n".join(c.page_content for c in chunks if c.page_content.strip())

    seed_queries = [
        "main concepts and definitions",
        "important formulas and algorithms",
        "key processes and diagrams",
        "comparisons and classifications",
        "examples and applications",
    ]
    seen = set()
    selected = []

    for query in seed_queries:
        for doc in retriever.invoke(query):
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                selected.append(doc.page_content)

    step = max(1, len(chunks) // 10)
    for i in range(0, len(chunks), step):
        content = chunks[i].page_content
        if content not in seen:
            seen.add(content)
            selected.append(content)

    return "\n\n".join(selected)


def _format_user_error(exc: Exception, default_message: str) -> str:
    """Format exceptions into safe, helpful, user-facing error messages."""
    err_str = str(exc)
    err_lower = err_str.lower()

    if "gemini_api_key is missing" in err_lower or "api_key is missing" in err_lower:
        return "Gemini API key is missing. Please add your GEMINI_API_KEY to the .env file in the RecallAI folder."
    if "api_key_invalid" in err_lower or "invalid api key" in err_lower or "unauthorized" in err_lower or "permission_denied" in err_lower:
        return "Gemini API authentication failed (Invalid API Key). Please verify your GEMINI_API_KEY in the .env file."
    if "429" in err_str or "rate limit" in err_lower or "resource_exhausted" in err_lower or "quota" in err_lower:
        return "Gemini API rate limit or quota exceeded. Please check your quota at https://aistudio.google.com/."
    if "not found" in err_lower and "model" in err_lower:
        return f"Gemini model not found: {err_str}. You can specify GEMINI_MODEL in your .env file."

    return default_message


# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def home_page():
    form = FileForm()

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    if form.validate_on_submit():
        target_language = form.target_language.data
        if target_language not in SUPPORTED_LANGUAGES:
            form.target_language.errors.append("Unsupported language selected.")
            return render_template("index.html", form=form)

        language_details = SUPPORTED_LANGUAGES[target_language]
        session["target_language"] = target_language

        try:
            data = form.file.data
            filename = secure_filename(data.filename)
            temp_path = os.path.join("uploads", filename)
            data.save(temp_path)

            docs = load_document(temp_path)

            if not docs or not any(d.page_content.strip() for d in docs):
                form.file.errors.append("The uploaded file appears empty or contains no readable text. Please try another file.")
                return render_template("index.html", form=form)

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
            chunks = text_splitter.split_documents(docs)
            if not chunks:
                form.file.errors.append("Could not extract text chunks from this file. Please try another file.")
                return render_template("index.html", form=form)

            vectordb = Chroma.from_documents(documents=chunks, embedding=get_embeddings())
            k = min(4, len(chunks))
            fetch_k = min(10, len(chunks))
            retriever = vectordb.as_retriever(
                search_type="mmr",
                search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": 0.5},
            )
            _set_retriever(retriever)

        except Exception as exc:
            logger.exception("Error during document processing: %s", exc)
            form.file.errors.append(f"Failed to process file: {str(exc)}")
            return render_template("index.html", form=form)

        try:
            context = _build_exam_context(retriever, chunks)
            if not context.strip():
                return render_template("error.html", message="Could not extract readable text from the uploaded file.")

            prompt = study_prompt.invoke({
                "target_language": language_details["name"],
                "context": context,
            })
            response = get_llm().invoke(prompt)
            result_html = markdown.markdown(response.content, extensions=["tables", "fenced_code"])
        except Exception as exc:
            logger.exception("Error during study generation: %s", exc)
            return render_template("error.html", message=_format_user_error(exc, language_details["error_generation"]))

        session["uploaded_filename"] = filename

        return render_template(
            "result.html",
            summary=result_html,
            target_language=language_details["name"],
            chat_greeting=language_details["chat_greeting"],
            filename=filename,
        )

    return render_template("index.html", form=form)


@app.route("/chat", methods=["POST"])
def chat_api():
    query = request.form.get("query", "").strip()
    if not query:
        return "Please provide a query.", 400

    target_language = session.get("target_language")
    if not target_language or target_language not in SUPPORTED_LANGUAGES:
        return "Please upload study material and select an output language first.", 400

    language_details = SUPPORTED_LANGUAGES[target_language]

    retriever = _get_retriever()
    if retriever is None:
        return language_details["error_no_pdf"], 400

    try:
        docs = retriever.invoke(query)
        context = "\n\n".join(doc.page_content for doc in docs)
        prompt = chat_prompt.invoke({
            "target_language": language_details["name"],
            "not_found": language_details["not_found"],
            "context": context,
            "question": query,
        })
        response = get_llm().invoke(prompt)
        return markdown.markdown(response.content, extensions=["tables", "fenced_code"])

    except Exception as exc:
        logger.exception("Error during chat retrieval: %s", exc)
        return _format_user_error(exc, language_details["error_retrieval"]), 500


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)