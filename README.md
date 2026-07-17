# 📝 Revision Room 

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Web%20App-lightgrey.svg)
![LangChain](https://img.shields.io/badge/LangChain-AI-green.svg)
![ChromaDB](https://img.shields.io/badge/Chroma-VectorDB-orange.svg)

## 📌 Summary
**Revision Room** is an intelligent, AI-powered study companion designed to help students prepare for their exams efficiently. Instead of manually skimming through hundreds of pages of textbooks or lecture notes, students can simply upload their syllabus or course PDF. The AI reads the document, identifies the core concepts, and instantly generates **10 highly relevant, exam-ready practice questions** with correct answers and explanations.

## 🎯 Problem Statement
Students often struggle with "information overload" when preparing for exams. They spend hours reading dense PDFs without knowing what topics are actually important or how they will be tested on them. Traditional study methods lack active recall testing. **Revision Room** solves this by using Retrieval-Augmented Generation (RAG) to instantly transform static reading materials into an active, question-based learning experience.

## ✨ Key Features
- **Seamless PDF Upload**: A beautifully designed, drag-and-drop web interface to upload course materials.
- **Smart Chunking & Vectorization**: Automatically splits large PDFs into manageable chunks and stores them mathematically in a local vector database.
- **Automated Exam Generation**: AI agent strictly analyzes your document to generate 10 challenging, conceptual exam questions along with answers.
- **Interactive Chat Interface**: Ask follow-up questions! If an exam answer is confusing, you can use the built-in RAG chatbot to ask the AI to explain specific parts of the PDF in more detail.
- **Premium UI/UX**: Built with a "Light Glassmorphism" aesthetic for a distraction-free, highly professional study environment.

## 🛠️ Tech Stack
**Frontend:**
- HTML5 / CSS3 / JavaScript (Vanilla)
- Jinja2 (Templating)
- Custom Light Glassmorphism UI (Inter Font)

**Backend:**
- **Flask**: Web server and routing.
- **Flask-WTF**: Secure file uploading and form validation.

**AI & Machine Learning (RAG Pipeline):**
- **LangChain**: Orchestration framework for LLM chaining.
- **Mistral (via LangChain Chat Models)**: The core Large Language Model that acts as the expert examiner.
- **ChromaDB**: The local Vector Database used to store document embeddings.
- **HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`)**: Open-source embedding model to convert text into searchable vectors.
- **PyPDF**: Extracts raw text from uploaded PDF files.

## 📁 Project Structure
```text
RevisionRoom/
│
├── uploads/                     # Temporary storage for uploaded user PDFs
├── chroma_langchain_db/         # Local Vector Database storage
│
├── templates/                   # Frontend UI
│   ├── index.html               # The Drag & Drop upload homepage
│   └── result.html              # The Exam Questions display and Chat UI
│
├── main.py                      # Main Flask server and LangChain AI Pipeline
├── DBcreation.py                # Standalone script for PDF Chunking & Vector Embedding
├── requirement.txt              # Complete list of PIP dependencies
└── .env                         # Environment variables (API Keys, Secret Keys)
```

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/RevisionRoom.git
cd RevisionRoom
```

### 2. Install Dependencies
Make sure you have Python 3.10+ installed. Install the required libraries using pip:
```bash
pip install -r requirement.txt
```

### 3. Setup Environment Variables
Create a `.env` file in the root directory and add your API keys:
```env
SECRET_KEY=your_flask_secret_key_here
# Add your specific LLM provider API keys here (e.g., OPENAI_API_KEY, MISTRAL_API_KEY, etc.)
```

### 4. Run the Application
Start the Flask web server:
```bash
python main.py
```

### 5. Start Studying
Open your browser and navigate to:
```text
http://127.0.0.1:5000/
```
Upload your first PDF and let the AI generate your practice exam!
# 🤝 Contributing

Contributions, suggestions, and feature requests are welcome.

Feel free to fork the repository, open issues, and submit pull requests to improve Revision Room.

---

© 2026 Kunal Singh