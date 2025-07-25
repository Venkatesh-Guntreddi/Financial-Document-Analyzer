import os
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq

load_dotenv()

def build_qa_chain_from_text(text: str):
    # ✅ 1. Split the plain text into smaller chunks with optimized separators
    # Prioritize splitting by paragraph, then lines, then words, to maintain semantic coherence.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""] # Try splitting by double newline (paragraph), then single newline, then space
    )
    chunks = text_splitter.split_text(text)

    documents = [Document(page_content=chunk) for chunk in chunks]

    print(f"\n✅ Total chunks created: {len(documents)}")
    print(f"Example chunk length: {len(documents[0].page_content) if documents else 0}") # For debugging chunk size


    # ✅ 2. Create sentence embeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # ✅ 3. Create FAISS vector store from chunked documents
    vectorstore = FAISS.from_documents(documents, embeddings)

    # ✅ 4. Create retriever
    # Consider increasing k (number of documents to retrieve) for more context, e.g., retriever = vectorstore.as_retriever(k=5)
    retriever = vectorstore.as_retriever()

    # ✅ 5. Load Groq LLM
    llm = ChatGroq(model_name="llama3-8b-8192", api_key=os.getenv("GROQ_API_KEY"))

    # ✅ 6. Create refined prompt
    prompt_template = """
    You are an expert financial analyst. Your task is to answer the user's question ONLY based on the provided financial document excerpts (context).

    If the question cannot be answered from the given context, respond clearly with "I am sorry, but the answer to your question is not available in the provided document excerpts." Do not try to make up an answer.
    Keep your answers concise, accurate, and to the point. Avoid conversational filler.

    Context:
    {context}

    Question:
    {question}

    Answer:
    """
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])


    # ✅ 7. Build Q&A chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    return qa_chain