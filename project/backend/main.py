import os, io
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
from rag import ensure_policy_index, index_temp_pdf, retrieve

from fastapi.staticfiles import StaticFiles

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

BASE_DIR = os.path.dirname(__file__)
POLICY_DIR = os.path.join(BASE_DIR, "policies")
os.makedirs(POLICY_DIR, exist_ok=True)

app = FastAPI(title="Policy RAG API")

# CORS for frontend (served by same app below)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ---------- Models ----------
class AskPayload(BaseModel):
    question: str
    policy_name: Optional[str] = None
    temp_doc_id: Optional[str] = None

# ---------- Helpers ----------
def _build_prompt(question: str, contexts: List[str]) -> str:
    numbered = "\n\n".join([f"[{i+1}] {c}" for i, c in enumerate(contexts)])
    return (
        "You are an HR policy assistant. Answer ONLY using the snippets below. "
        "If the answer isn't present, say you don't know.\n\n"
        f"Question:\n{question}\n\n"
        f"Snippets:\n{numbered}\n\n"
        "Answer clearly and cite like [1], [2] if relevant."
    )

def _groq_answer(prompt: str) -> str:
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role":"system","content":"Be precise, concise, and grounded in provided context."},
            {"role":"user","content": prompt}
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

# ---------- API ----------
@app.get("/api/policies")
def list_policies():
    files = [f for f in os.listdir(POLICY_DIR) if f.lower().endswith(".pdf")]
    return {"policies": sorted(files)}

@app.post("/api/upload-temp")
async def upload_temp(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    doc_id = index_temp_pdf(pdf_bytes)
    return {"temp_doc_id": doc_id, "filename": file.filename}

@app.post("/api/ask")
def ask(payload: AskPayload):
    if not payload.question or not payload.question.strip():
        return {"answer": "Please provide a question."}

    if payload.temp_doc_id:
        doc_id = payload.temp_doc_id
    elif payload.policy_name:
        path = os.path.join(POLICY_DIR, payload.policy_name)
        if not os.path.exists(path):
            return {"answer": "Policy not found on server."}
        doc_id = ensure_policy_index(path)
    else:
        # general assistant (no RAG)
        prompt = (
            "You are an HR assistant. Answer the question based on general policy best practices for a consulting firm.\n\n"
            f"Question: {payload.question}"
        )
        return {"answer": _groq_answer(prompt), "context": []}

    # RAG retrieve
    top = retrieve(doc_id, payload.question, k=5)
    contexts = [t[0] for t in top]
    prompt = _build_prompt(payload.question, contexts)
    answer = _groq_answer(prompt)
    return {"answer": answer, "context": contexts}

# serve frontend
FRONT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
app.mount("/", StaticFiles(directory=FRONT_DIR, html=True), name="frontend")