import requests
import json
import os
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from pathlib import Path

# LangChain imports
try:
    from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.schema import Document
except ImportError:
    print("⚠️ LangChain/FAISS/HuggingFace not installed. Please run: pip install langchain langchain-community langchain-huggingface faiss-cpu pypdf sentence-transformers")
    exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# UTILITY FUNCTIONS
def get_api_key_from_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(base_dir, "api_key.txt")
    try:
        with open(key_file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error reading API key from api_key.txt: {e}")
        return None

# RAG TOOLS CLASS
class FitbotRAGSystem:
    def __init__(self, pdf_directory: str, vector_store_path: str, gemini_api_key: str, embedding_model: str):
        self.pdf_directory = Path(pdf_directory)
        self.vector_store_path = Path(vector_store_path)
        self.gemini_api_key = gemini_api_key
        self.embedding_model_name = embedding_model
        self.embeddings = None
        self.vector_store = None
        self.is_initialized = False
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        try:
            logger.info(f"📦 Loading embedding model: {self.embedding_model_name}...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': 'cpu'}
            )
            logger.info("✅ Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")

    def initialize_system(self, force_recreate: bool = False):
        if not self.embeddings:
            logger.error("❌ Cannot initialize vector store without embeddings.")
            return
        try:
            vector_store_exists = (self.vector_store_path / "index.faiss").exists()
            if force_recreate or not vector_store_exists:
                self._create_vector_store()
            else:
                self._load_vector_store()
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG system: {e}")
            self.is_initialized = False

    def _create_vector_store(self):
        logger.info("🔄 Creating new vector store...")
        if not self.pdf_directory.exists():
            logger.warning(f"📁 PDF directory not found: {self.pdf_directory}")
            return
        loader = DirectoryLoader(
            str(self.pdf_directory),
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True
        )
        documents = loader.load()
        if not documents:
            logger.warning("📁 No PDF documents found.")
            return
        logger.info(f"📚 Loaded {len(documents)} document pages.")
        self.vector_store = FAISS.from_documents(documents, self.embeddings)
        self.vector_store.save_local(str(self.vector_store_path))
        logger.info(f"💾 Vector store saved to {self.vector_store_path}")
        self.is_initialized = True

    def _load_vector_store(self):
        logger.info("📂 Loading existing vector store...")
        try:
            self.vector_store = FAISS.load_local(
                str(self.vector_store_path), 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("✅ Vector store loaded successfully")
            self.is_initialized = True
        except Exception as e:
            logger.error(f"❌ Error loading vector store: {e}. Attempting to recreate.")
            self._create_vector_store()

    def query_with_rag(self, question: str, k: int = 3) -> Dict[str, Any]:
        if not self.is_initialized or not self.vector_store:
            return {"answer": "Sistem RAG belum siap.", "sources": []}
        
        docs = self.vector_store.similarity_search(question, k=k)
        if not docs:
            return {"answer": "Tidak ditemukan dokumen yang relevan.", "sources": []}
            
        context = "\n\n".join([doc.page_content for doc in docs])
        prompt = f"""
        Berdasarkan konteks dokumen ilmiah berikut, jawab pertanyaan user.
        
        KONTEKS:
        {context}
        
        PERTANYAAN: {question}
        
        INSTRUKSI:
        1. Jawab HANYA berdasarkan informasi dari konteks yang diberikan.
        2. Jika informasi tidak ada di konteks, katakan "Informasi tidak tersedia dalam dokumen rujukan saya".
        3. Berikan jawaban yang praktis dan actionable.
        """
        answer = self._call_gemini_api(prompt)
        sources = [os.path.basename(doc.metadata.get('source', 'Unknown')) for doc in docs]
        return {"answer": answer, "sources": list(set(sources))}

    def _call_gemini_api(self, prompt: str) -> str:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.gemini_api_key}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return "Tidak ada respons yang dihasilkan."
        except Exception as e:
            logger.error(f"❌ Gemini API error: {e}")
            return f"Error API: {str(e)}"

# GOOGLE CALENDAR TOOLS CLASS
class GoogleCalendarTools:
    def __init__(self, credentials_file='client_secret.json', token_file='token.pickle'):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.initialize_service()

    def get_flow(self):
        # ... (Kode GoogleCalendarTools kamu tidak berubah, jadi saya persingkat di sini)
        # Pastikan kode lengkapmu dari file asli ada di sini
        with open(self.credentials_file, 'r') as f:
            client_config = json.load(f)
        if 'web' not in client_config:
            raise Exception("client_secret.json is not configured for web application")
        client_config['web']['redirect_uris'] = ["http://localhost:8000/auth/callback"]
        return Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri="http://localhost:8000/auth/callback"
        )

    def initialize_service(self):
        # ... (Kode lengkapmu dari file asli ada di sini)
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    self.service = None
                    return
            else:
                self.service = None
                return
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("✅ Google Calendar service initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing Google Calendar: {e}")
            self.service = None

    def create_workout_event(self, title, date, time, duration_hours=1, description=""):
        # ... (Kode lengkapmu dari file asli ada di sini)
        if not self.service:
            return {"success": False, "error": "Google Calendar service not initialized"}
        try:
            start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            event = {
                'summary': title,
                'description': description,
                'start': {'dateTime': start_datetime.isoformat(), 'timeZone': 'Asia/Jakarta'},
                'end': {'dateTime': end_datetime.isoformat(), 'timeZone': 'Asia/Jakarta'},
            }
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            return {
                "success": True, 
                "message": f"✅ Workout '{title}' berhasil dijadwalkan.",
                "event_link": created_event.get('htmlLink')
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# ENHANCED FITBOT CLASS
class EnhancedFitBot:
    def __init__(self, api_key, credentials_file='client_secret.json'):
        if not api_key:
            raise ValueError("API Key for Gemini is required.")
        self.API_KEY = api_key
        
        logger.info("🔧 Initializing Google Calendar Tools...")
        self.calendar_tools = GoogleCalendarTools(credentials_file)
        
        logger.info("📚 Initializing RAG System...")
        pdf_dir = Path(__file__).parent.parent / "Dokumen Training"
        vector_store_dir = Path(__file__).parent / "vector_store"
        self.rag_system = FitbotRAGSystem(
            pdf_directory=str(pdf_dir),
            vector_store_path=str(vector_store_dir),
            gemini_api_key=self.API_KEY,
            embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        if self.rag_system.embeddings:
            self.rag_system.initialize_system()

        self.system_prompt = """
        PERAN: Kamu adalah FitBot, asisten fitness berbasis evidence-based untuk pengguna umum (bukan pasien).
        TUJUAN: Memberi saran latihan, nutrisi terkait fitness, dan membantu penjadwalan latihan dengan aman.
        GAYA: Ramah, ringkas, mudah dipahami, emoji maks 2 per jawaban (jangan di heading).

        TOPIK YANG DIIJINKAN: latihan gym, program, recovery/istirahat, jadwal, nutrisi fitness, penjadwalan kalender.
        TOPIK DITOLAK: diagnosis medis/terapi, keluhan penyakit, topik non-fitness. Jawab singkat menolak dan arahkan ke topik fitness.

        STRUKTUR OUTPUT WAJIB (Markdown):
        1) ### Ringkas — 2–3 kalimat inti jawaban.
        2) ### Rekomendasi — daftar bullet (maks 5) dengan tips/struktur latihan praktis.
        3) ### Referensi — 2–4 butir sumber ilmiah valid (ACSM/WHO/NSCA/ISSN/jurnal). Format: (Sumber: ACSM, 2022) atau (Phillips et al., 2020).

        SLOT-FILLING PENJADWALAN:
        - Kumpulkan hanya slot yang belum ada: jenis latihan, tanggal (YYYY-MM-DD), jam (HH:MM 24h), durasi (1–6 jam).
        - Jika ada ambiguitas (mis. 07:00 vs 19:00) minta klarifikasi dengan opsi.
        - Jika tanggal di masa lalu, sarankan tanggal terdekat yang valid.
        
        EKSEKUSI KALENDER (HANYA SAAT SLOT LENGKAP):
        - Hanya jika semua slot sudah lengkap dan user menyetujui, keluarkan JSON VALID siap dieksekusi berikut:
        {
          "action": "create_calendar_event",
          "confirmed": true,
          "title": "...",
          "date": "YYYY-MM-DD",
          "time": "HH:MM",
          "duration": 1,
          "description": "..."
        }
        """

    def _parse_calendar_request(self, response: str) -> Optional[Dict]:
        try:
            match = re.search(r'\{[\s\S]*"action":\s*"create_calendar_event"[\s\S]*\}', response)
            if match:
                data = json.loads(match.group())
                # Validasi sederhana
                if data.get("confirmed") is True and all(k in data for k in ["title", "date", "time"]):
                    return data
        except (json.JSONDecodeError, AttributeError):
            return None
        return None

    def chat_general(self, user_question: str) -> Dict[str, Any]:
        """Menangani permintaan umum (non-RAG) yang mungkin termasuk penjadwalan."""
        prompt = f"{self.system_prompt}\n\nPERTANYAAN USER: {user_question}"
        
        response_text = self.rag_system._call_gemini_api(prompt)
        
        calendar_request = self._parse_calendar_request(response_text)
        if calendar_request:
            logger.info(f"✅ Valid calendar JSON found: {calendar_request}")
            result = self.calendar_tools.create_workout_event(**calendar_request)
            if result.get("success"):
                final_response = f"{response_text}\n\n---\n\n📅 **Status:** {result.get('message')}"
                if result.get("event_link"):
                    final_response += f"\n🔗 **Link Event:** {result.get('event_link')}"
                return {"answer": final_response}
            else:
                return {"answer": f"{response_text}\n\n---\n\n❌ **Status:** Gagal: {result.get('error')}"}

        return {"answer": response_text + "\n\n⚠️ DISCLAIMER: Informasi ini bersifat umum. Konsultasikan dengan ahli."}


    def chat_rag(self, user_question: str) -> Dict[str, Any]:
        """Menangani permintaan khusus RAG."""
        if not self.rag_system or not self.rag_system.is_initialized:
            return {"answer": "Maaf, sistem pencarian dokumen sedang tidak tersedia."}
        
        logger.info(f"🤖 Processing query with RAG: {user_question[:50]}...")
        rag_result = self.rag_system.query_with_rag(user_question)
        
        response = rag_result.get('answer', 'Tidak ada jawaban yang ditemukan.')
        sources = rag_result.get('sources', [])
        
        if sources:
            response += "\n\n*Sumber: " + ", ".join(sources) + "*"
        
        response += "\n\n⚠️ **DISCLAIMER:** Informasi ini dari dokumen. Selalu konsultasi dengan ahli."
        return {"answer": response}

# FASTAPI APP
app = FastAPI(title="Enhanced FitBot API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = get_api_key_from_file()
fitbot = EnhancedFitBot(API_KEY) if API_KEY else None

class ChatRequest(BaseModel):
    question: str
    use_rag: bool = False

@app.post("/chat")
def handle_chat(req: ChatRequest):
    if not fitbot:
        raise HTTPException(status_code=500, detail="Chatbot not initialized.")
    
    if req.use_rag:
        return fitbot.chat_rag(req.question)
    else:
        return fitbot.chat_general(req.question)

# --- Endpoint Kalender Tetap Ada ---
@app.get("/auth/login")
def auth_login():
    if not fitbot:
        raise HTTPException(status_code=500, detail="FitBot not initialized")
    flow = fitbot.calendar_tools.get_flow()
    authorization_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
def auth_callback(code: str):
    if not fitbot:
        raise HTTPException(status_code=500, detail="FitBot not initialized")
    try:
        flow = fitbot.calendar_tools.get_flow()
        flow.fetch_token(code=code)
        with open(fitbot.calendar_tools.token_file, 'wb') as token:
            pickle.dump(flow.credentials, token)
        fitbot.calendar_tools.initialize_service()
        return RedirectResponse(url="http://localhost:3000?auth=success")
    except Exception as e:
        return RedirectResponse(url=f"http://localhost:3000?auth=failed&error={str(e)}")

@app.get("/auth/logout")
def auth_logout():
    if not fitbot:
        raise HTTPException(status_code=500, detail="FitBot not initialized")
    token_path = fitbot.calendar_tools.token_file
    if os.path.exists(token_path):
        os.remove(token_path)
        fitbot.calendar_tools.service = None
    return {"status": "logged_out"}

@app.get("/auth/status")
def auth_status():
    if not fitbot:
        return {"authenticated": False}
    return {"authenticated": fitbot.calendar_tools.service is not None}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Enhanced FitBot Server v3.0...")
    uvicorn.run(app, host="0.0.0.0", port=8000)