# LOADING LIBRARIES
import os
from flask import Flask, request, redirect, render_template
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import InputRequired
from werkzeug.utils import secure_filename
from flask_wtf.file import FileAllowed
import markdown
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
load_dotenv()

# FIX: Created the 'uploads' directory automatically so data.save() doesn't crash with FileNotFoundError
os.makedirs('uploads', exist_ok=True)

llm = init_chat_model("mistral-small-2603")

# Embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# We will initialize the retriever dynamically when a user uploads a file!
global_retriever = None

#templates
template =  ChatPromptTemplate.from_messages([
    ('system', """
You are an expert teacher and exam creator.

Your task is to carefully read the entire uploaded PDF and 
identify the most important and exam-relevant topics based only on the contents of the document. 
Do not use outside knowledge unless it is necessary to clarify a concept, and clearly indicate when you do.

Using those topics, 
generate 10 highly important exam questions that are most likely to be asked in a university or competitive examination.
Requirements:
1. Read the complete document before generating any questions.
2. Base every question only on the information present in the PDF.
3. Focus on concepts, definitions, formulas, diagrams, processes, algorithms, comparisons, and topics that appear important or are emphasized in the document.
4. Prioritize questions that test conceptual understanding rather than simple memorization.
5. Cover different sections of the PDF instead of selecting all questions from a single topic.
6. Do not create duplicate or very similar questions.
7. Ensure every question is clear, specific, and unambiguous.
8. Provide the correct answer and a brief explanation immediately below each question.

Formatting requirements:
Use clear markdown headings (e.g., ### Question 1).
Use bullet points or bold text to highlight the answers.
Make the output well-organized, easy to read, and strictly focused on testing the student's knowledge of the document.
     """),
    ('human',"""
     PDF: {pdf}
     """)
])

class FileForm(FlaskForm):
    file = FileField("PDF File", validators=[InputRequired(), FileAllowed(['pdf'], 'PDFs only!')])
    submit = SubmitField("Upload")
    
@app.route('/', methods=['GET','POST'])
def home_page():
    form = FileForm()
    result1 = None
    
    if form.validate_on_submit():
        data = form.file.data
        filename = secure_filename(data.filename)
        temp_path = os.path.join('uploads', filename)
        data.save(temp_path)
        
        data = PyPDFLoader(temp_path)
        docs = data.load()
        

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        chunks = text_splitter.split_documents(docs)
        
        # 2. Create a temporary in-memory vector database just for this PDF!
        global global_retriever
        vectordb = Chroma.from_documents(documents=chunks, embedding=embeddings)
        
        # 3. Save the retriever globally so the /chat route can use it
        global_retriever = vectordb.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 4, "fetch_k": 10, "lambda_mult": 0.5}
        )

        prompt = template.invoke({
            "pdf": docs
        })

        response1 = llm.invoke(prompt)
        result1 = markdown.markdown(response1.content)
        
        return render_template('result.html', summary=result1)

    return render_template('index.html', form=form)

@app.route('/chat', methods=['POST'])
def chat_api():
    query = request.form.get('query')
    if not query:
        return "Please provide a query."
        
    global global_retriever
    if not global_retriever:
        return "Error: Please upload a PDF first before asking questions."
        
    docs = global_retriever.invoke(query)
    context_list = [doc.page_content for doc in docs]
    
    response = llm.invoke(f""" 
    Use ONLY the provided context to answer the question.
    If the answer is not present in the context,
    say: I could not find the answer in the document.
    provided details : {context_list}, question : {query}.
    """)
    
    return markdown.markdown(response.content)

if __name__ == "__main__":
    app.run(debug=True)
    