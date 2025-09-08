import requests
import json
import os
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# LangChain imports
# LangChain imports
try:
    from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
    from langchain_huggingface import HuggingFaceEmbeddings  # Updated import
    from langchain_community.vectorstores import FAISS
    from langchain.schema import Document
except ImportError:
    print("⚠️ LangChain not installed. Install with: pip install langchain langchain-community langchain-huggingface")
    exit(1)

import requests
import json


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
        print(f"❌ Error reading API key: {e}")
        return None
    


#RAG TOOLS CLASS
class FitbotRAGSystem:
    """
    RAG System untuk Fitbot yang menggunakan PDF rujukan ilmiah
    untuk memberikan jawaban yang lebih akurat dan berdasar penelitian
    """
    
    def __init__(self, 
                 pdf_directory: str = "../Document Training",
                 vector_store_path: str = "./vector_store",
                 gemini_api_key: str = None,
                 embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        
        from pathlib import Path
        self.pdf_directory = Path(__file__).parent.parent / "Dokumen Training"
        self.vector_store_path = Path(vector_store_path)
        self.gemini_api_key = gemini_api_key or self._get_api_key_from_file()
        self.embedding_model = embedding_model
        
        # Initialize components
        self.embeddings = None
        self.vector_store = None
        self.is_initialized = False
        self.document_metadata = {}
        
        # Create directories if not exist
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        self._initialize_embeddings()
        
    def _get_api_key_from_file(self) -> Optional[str]:
        """Get API key from api_key.txt file"""
        possible_paths = ["api_key.txt", "../api_key.txt", "./google/api_key.txt"]
        
        for path in possible_paths:
            try:
                if Path(path).exists():
                    with open(path, "r", encoding='utf-8') as f:
                            api_key = f.read().strip()
                            if api_key:
                                return api_key
            except Exception as e:
                continue
        
        logger.warning("⚠️ No API key found. Set GEMINI_API_KEY environment variable or create api_key.txt")
        return None
    
    
    def initialize_system(self, force_recreate: bool = False) -> bool:
        """Initialize the RAG system"""
        try:
            if not self.pdf_directory.exists():
                logger.warning(f"📁 PDF directory not found: {self.pdf_directory}")
                return False
        
            # Check if vector store exists
            vector_store_exists = (self.vector_store_path / "index.faiss").exists()
        
            if force_recreate or not vector_store_exists:
                logger.info("🔄 Creating new vector store...")
                return self._create_vector_store()
            else:
                logger.info("📂 Loading existing vector store...")
                return self._load_vector_store()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG system: {e}")
            return False

    def _create_vector_store(self) -> bool:
        """Create vector store from PDF documents"""
        try:
            if not self.embeddings:
                logger.error("❌ Embeddings not initialized")
                return False
        
            # Load PDF documents
            logger.info("📖 Loading PDF documents...")
            loader = DirectoryLoader(
                str(self.pdf_directory),
                glob="**/*.pdf",
                loader_cls=PyPDFLoader,
                show_progress=True
            )
        
            documents = loader.load()
        
            if not documents:
                logger.warning("📁 No PDF documents found")
                return False
        
            logger.info(f"📚 Loaded {len(documents)} document chunks")
        
            # Create vector store
            logger.info("🔍 Creating vector store...")
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
        
            # Save vector store
            self.vector_store.save_local(str(self.vector_store_path))
            logger.info(f"💾 Vector store saved to {self.vector_store_path}")
        
            self.is_initialized = True
            return True
        
        except Exception as e:
            logger.error(f"❌ Error creating vector store: {e}")
            return False

    def _load_vector_store(self) -> bool:
        """Load existing vector store"""
        try:
            if not self.embeddings:
                logger.error("❌ Embeddings not initialized")
                return False
        
            self.vector_store = FAISS.load_local(
                str(self.vector_store_path), 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        
            logger.info("✅ Vector store loaded successfully")
            self.is_initialized = True
            return True
        
        except Exception as e:
            logger.error(f"❌ Error loading vector store: {e}")
            return False

    def query_with_rag(self, question: str, use_rag: bool = True, k: int = 3) -> Dict[str, Any]:
        """Query using RAG system"""
        import time
        start_time = time.time()
    
        try:
            if not self.is_initialized or not self.vector_store:
                return {
                    "use_rag": False,
                    "answer": "RAG system not initialized",
                    "sources": [],
                    "processing_time": time.time() - start_time
                }
            # Search similar documents
            docs = self.vector_store.similarity_search(question, k=k)
            if not docs:
                return {
                    "use_rag": False,
                    "answer": "No relevant documents found",
                    "sources": [],
                    "processing_time": time.time() - start_time
                }
        
            # Create context from retrieved documents
            context = "\n\n".join([doc.page_content for doc in docs])
        
            # Generate answer using Gemini with context
            prompt = f"""
            Berdasarkan konteks dokumen ilmiah berikut, jawab pertanyaan user tentang fitness/gym.
        
            KONTEKS:
            {context}
        
            PERTANYAAN: {question}
        
            INSTRUKSI:
            1. Jawab berdasarkan informasi dari konteks yang diberikan
            2. Jika konteks tidak cukup, katakan "informasi tidak tersedia dalam dokumen rujukan"
            3. Berikan jawaban yang praktis dan actionable
            4. Maksimal 300 kata
            """
            # Call Gemini API
            answer = self._call_gemini_api(prompt)
            return {
                "use_rag": True,
                "answer": answer,
                "sources": [doc.metadata for doc in docs],
                "processing_time": time.time() - start_time,
                "retrieved_docs": len(docs)
            }
        except Exception as e:
            logger.error(f"❌ Error in RAG query: {e}") 
            return {
                "use_rag": False,
                "answer": f"Error: {str(e)}",
                "sources": [],
                "processing_time": time.time() - start_time
            }

    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API with prompt"""
        if not self.gemini_api_key:
            return "❌ Gemini API key not available"

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.gemini_api_key
        }
    
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800
            }
        }
    
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
        
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return "No response generated"
        
        except Exception as e:
            logger.error(f"❌ Gemini API error: {e}")
            return f"API Error: {str(e)}"

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "rag_available": self.is_initialized,
            "embeddings_loaded": self.embeddings is not None,
            "vector_store_loaded": self.vector_store is not None,
            "pdf_directory_exists": self.pdf_directory.exists(),
            "api_key_available": self.gemini_api_key is not None
        }

    def search_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search documents in vector store"""
        if not self.is_initialized or not self.vector_store:
            return []
    
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            return [
                {
                    "content": doc.page_content[:500],  # First 500 chars
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "Unknown")
                }
                for doc in docs
            ]
        except Exception as e:
            logger.error(f"❌ Error searching documents: {e}")
            return []

    def add_new_document(self, pdf_path: str) -> bool:
        """Add new document to knowledge base"""
        try:
            if not Path(pdf_path).exists():
                logger.error(f"❌ PDF file not found: {pdf_path}")
                return False
        
            # Load new document
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
        
            if not docs:
                logger.error("❌ No content loaded from PDF")
                return False
        
            # Add to existing vector store
            if self.vector_store:
                self.vector_store.add_documents(docs)
                # Save updated vector store
                self.vector_store.save_local(str(self.vector_store_path))
                logger.info(f"✅ Added document: {pdf_path}")
                return True
            else:
                logger.error("❌ Vector store not initialized")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error adding document: {e}")
            return False


    def _initialize_embeddings(self):
        """Initialize the HuggingFace embedding model."""
        try:
            logger.info(f"📦 Loading embedding model: {self.embedding_model}...")
            
            # Pastikan gunakan tf-keras, bukan keras 3
            try:
                import tf_keras  # type: ignore
                logger.info("✅ tf-keras terdeteksi, kompatibel dengan Transformers.")
            except ImportError:
                logger.error("❌ tf-keras belum terinstall. Jalankan: pip install tf-keras")
                self.embeddings = None
                self.is_initialized = False
                return

            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model,
                model_kwargs={'device': 'cpu'}  # Gunakan CPU untuk kompatibilitas
            )
            logger.info("✅ Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            self.embeddings = None
            # Jika model gagal dimuat, sistem RAG tidak bisa berjalan
            self.is_initialized = False


    def chat_with_rag(self, user_question: str, use_rag: bool = True, k: int = 3) -> str:
        """
        Chat method yang menggunakan RAG jika tersedia
        """
        # Check if question is fitness-related
        if not self._is_fitness_related(user_question):
            return self._get_non_fitness_response()
        
        # Try RAG first if available and enabled
        if use_rag and self.rag_enabled and self.rag_system and self.rag_system.is_initialized:
            try:
                logger.info(f"🤖 Processing query with RAG: {user_question[:50]}...")
                rag_result = self.rag_system.query_with_rag(user_question, use_rag=True, k=k)
                
                if rag_result["use_rag"] and rag_result["answer"]:
                    # Add source information
                    response = rag_result["answer"]
                    
                    # Add processing info
                    if rag_result.get("processing_time"):
                        response += f"\n\n⏱️ *Diproses dalam {rag_result['processing_time']:.2f} detik*"
                    
                    if rag_result.get("query_enhanced"):
                        response += f"\n🔍 *Query diperluas untuk pencarian yang lebih baik*"
                    
                    response += "\n\n⚠️ **DISCLAIMER:** Informasi ini bersifat umum dan berdasarkan dokumen rujukan. Konsultasikan dengan trainer atau dokter untuk program yang sesuai kondisi Anda."
                    return response
                
            except Exception as e:
                logger.error(f"❌ RAG query failed: {e}")
            # Fallback to original chatbot
            logger.info("💬 Using fallback chatbot (no RAG)")
            return self._original_chat(user_question)
    
    def chat_regular(self, user_question: str) -> str:
        """Regular chat without RAG"""
        return self.chat_with_rag(user_question, use_rag=False)
    
    def _is_fitness_related(self, user_question: str) -> bool:
        """Check if question is fitness-related"""
        fitness_keywords = [
            # English terms
            'gym', 'fitness', 'workout', 'exercise', 'training', 'sport', 'muscle', 'strength',
            'cardio', 'weight', 'lift', 'rep', 'set', 'routine', 'program', 'bodybuilding',
            'powerlifting', 'crossfit', 'yoga', 'pilates', 'running', 'cycling', 'swimming',
            'nutrition', 'protein', 'carbs', 'diet', 'supplement', 'recovery', 'rest',
            'injury', 'form', 'technique', 'squat', 'deadlift', 'bench', 'pull', 'push',
            
            # Indonesian terms
            'latihan', 'olahraga', 'kebugaran', 'angkat beban', 'otot', 'kekuatan',
            'kardio', 'berat badan', 'repetisi', 'set', 'rutin', 'program latihan',
            'binaraga', 'nutrisi', 'protein', 'karbohidrat', 'diet', 'suplemen',
            'pemulihan', 'istirahat', 'cedera', 'bentuk', 'teknik', 'squat', 'deadlift',
            'bench press', 'pull up', 'push up', 'abs', 'core', 'chest', 'dada',
            'punggung', 'kaki', 'lengan', 'bahu', 'perut'
        ]
        
        user_question_lower = user_question.lower()
        return any(keyword in user_question_lower for keyword in fitness_keywords)
    
    def _get_non_fitness_response(self) -> str:
        """Response untuk pertanyaan non-fitness"""
        return """
            🚫 **Maaf, saya khusus membantu pertanyaan FITNESS & GYM**

            ✅ **YANG BISA SAYA BANTU:**
            • **Latihan:** Program gym, teknik, form, split routine
            • **Nutrisi:** Protein, karbohidrat, meal timing, suplemen
            • **Recovery:** Istirahat, sleep, pemulihan otot
            • **Penjadwalan:** Jadwal latihan optimal, periodisasi
            • **Equipment:** Penggunaan alat gym, home workout
            • **Goals:** Muscle gain, fat loss, strength, endurance

            💡 **CONTOH PERTANYAAN:**
            • "Bagaimana cara melakukan squat yang benar?"
            • "Program latihan untuk pemula 3x seminggu?"
            • "Kapan waktu terbaik konsumsi protein?"
            • "Berapa lama istirahat antara set?"

            🔄 **Silakan ajukan pertanyaan fitness Anda!**
        """
    
    def _original_chat(self, user_question: str) -> str:
        """Original chat method sebagai fallback"""
        specific_prompt = f"""
        {self.system_prompt}
        
        PERTANYAAN USER: {user_question}
        
        INSTRUKSI JAWABAN:
        1. Jawab HANYA jika terkait fitness/gym/lifestyle untuk performa
        2. WAJIB berikan referensi ilmiah: (Sumber: ACSM, 2022) atau (Phillips et al., Journal, 2020)
        3. Jika TIDAK ada referensi → katakan "Tidak ada referensi ilmiah yang akurat, konsultasi ahli"
        4. Format: pendahuluan, poin dengan referensi, kesimpulan
        5. Maksimal 350 kata
        6. Aspek medis → rujuk ke profesional + sebutkan spesialis yang tepat
        """
        
        data = {
            "contents": [{"parts": [{"text": specific_prompt}]}],
            "generationConfig": {
                "temperature": 0.6,
                "topK": 40,
                "topP": 0.9,
                "maxOutputTokens": 800
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
        }
        
        try:
            if not self.API_KEY:
                return "❌ Error: API key tidak tersedia"
            
            response = requests.post(self.url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    answer = parts[0].get("text", "Maaf, tidak ada respons yang diterima.")
                    return answer + "\n\n⚠️ **DISCLAIMER:** Informasi ini bersifat umum. Konsultasikan dengan trainer atau dokter untuk program yang sesuai kondisi Anda."
                    
            return "Maaf, terjadi kesalahan dalam memproses respons."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return f"❌ Maaf, terjadi kesalahan koneksi: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"❌ Maaf, terjadi kesalahan tidak terduga: {str(e)}"
    
    def get_rag_status(self) -> Dict[str, Any]:
        """Get RAG system status"""
        if self.rag_system:
            status = self.rag_system.get_system_status()
            status.update({
                "rag_enabled": self.rag_enabled,
                "chatbot_api_available": self.API_KEY is not None
            })
            return status
        else:
            return {
                "rag_available": False, 
                "reason": "RAG system not initialized",
                "rag_enabled": self.rag_enabled,
                "chatbot_api_available": self.API_KEY is not None
            }
    
    def search_knowledge_base(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search the RAG knowledge base"""
        if self.rag_system and self.rag_system.is_initialized:
            return self.rag_system.search_documents(query, k=k)
        else:
            return []
    
    def add_document_to_knowledge_base(self, pdf_path: str) -> bool:
        """Add new document to RAG knowledge base"""
        if self.rag_system:
            return self.rag_system.add_new_document(pdf_path)
        else:
            logger.warning("⚠️ RAG system not available")
            return False
    
    def reinitialize_rag(self, force_recreate: bool = False) -> bool:
        """Reinitialize RAG system"""
        if self.rag_system:
            return self.rag_system.initialize_system(force_recreate=force_recreate)
        else:
            logger.warning("⚠️ RAG system not available")
            return False

# GOOGLE CALENDAR TOOLS CLASS
class GoogleCalendarTools:
    def __init__(self, credentials_file='client_secret.json', token_file='token.pickle'):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.initialize_service()

    def get_flow(self):
        with open(self.credentials_file, 'r') as f:
            client_config = json.load(f)
        
        # Ensure the redirect URI is set for the web flow
        if 'web' not in client_config:
            raise Exception("client_secret.json is not configured for web application")

        # The redirect_uri must match the one registered in Google Cloud Console.
        # For this local setup, it's our /auth/callback endpoint.
        client_config['web']['redirect_uris'] = ["http://localhost:8000/auth/callback"]

        return Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri="http://localhost:8000/auth/callback"
        )

    def initialize_service(self):
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
                    print(f"❌ Token refresh failed: {e}")
                    self.service = None
                    return
            else:
                self.service = None
                return

        try:
            self.service = build('calendar', 'v3', credentials=creds)
            print("✅ Google Calendar service initialized")
        except Exception as e:
            print(f"❌ Error initializing Google Calendar: {e}")
            self.service = None

    def create_workout_event(self, title: str, date: str, time: str, duration_hours: int = 1, description: str = ""):
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
                'colorId': '4',
                'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 30}, {'method': 'popup', 'minutes': 10}]},
            }
            
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            
            return {
                "success": True, 
                "event_id": created_event['id'],
                "event_link": created_event.get('htmlLink'),
                "message": f"✅ Workout '{title}' berhasil dijadwalkan pada {date} {time}"
            }
        except Exception as e:
            return {"success": False, "error": f"Error creating event: {str(e)}"}

    def get_upcoming_workouts(self, days_ahead: int = 7):
        if not self.service:
            return {"success": False, "error": "Google Calendar service not initialized"}
        
        try:
            now = datetime.utcnow()
            time_max = now + timedelta(days=days_ahead)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                q='workout OR gym OR fitness OR latihan'
            ).execute()
            
            events = events_result.get('items', [])
            
            workout_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                workout_events.append({
                    'title': event.get('summary', 'No Title'),
                    'start_time': start,
                    'description': event.get('description', ''),
                    'event_id': event['id']
                })
            
            return {"success": True, "events": workout_events}
        except Exception as e:
            return {"success": False, "error": f"Error fetching events: {str(e)}"}

    def delete_workout_event(self, event_id: str):
        if not self.service:
            return {"success": False, "error": "Google Calendar service not initialized"}
        
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return {"success": True, "message": "✅ Event berhasil dihapus"}
        except Exception as e:
            return {"success": False, "error": f"Error deleting event: {str(e)}"}

# GYM FITNESS CHATBOT CLASS
class GymFitnessChatbot:
    def __init__(self, api_key):
        self.API_KEY = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        self.headers = {"Content-Type": "application/json", "x-goog-api-key": self.API_KEY}
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

        CONTOH/PRA-KONFIRMASI (JANGAN DIEKSEKUSI, TANPA KURUNG KURAWAL/QUOTE/KOMA AKHIR, BUKAN CODE BLOCK):
        - action: create_calendar_event
        - title: Upper Body Workout
        - date: 2024-12-15
        - time: 07:00
        - duration: 1
        - description: Latihan dada, bahu, triceps

        PENTING: Pada contoh atau saat belum confirmed, JANGAN gunakan kurung kurawal { }, JANGAN pakai tanda kutip, dan JANGAN gunakan code block (```). Tulis sebagai teks biasa/bullet list.

        EKSEKUSI KALENDER (HANYA SAAT SLOT LENGKAP):
        - Hanya jika semua slot sudah lengkap dan user menyetujui, keluarkan JSON VALID siap dieksekusi (boleh pakai kurung kurawal) berikut:
        {
          "action": "create_calendar_event",
          "confirmed": true,
          "title": "...",
          "date": "YYYY-MM-DD",
          "time": "HH:MM",
          "duration": 1,
          "description": "..."
        }

        SELF-CHECK sebelum kirim jawaban:
        - Apakah topik valid? Apakah struktur Markdown dipenuhi? Apakah referensi 2–4 butir? Apakah JSON hanya muncul bila confirmed?
        """
        self.valid_sources = [
            'ACSM', 'American College of Sports Medicine', 'WHO', 'World Health Organization', 
            'NSCA', 'National Strength and Conditioning Association', 'ISSN', 'International Society of Sports Nutrition',
            'ADA', 'American Dietetic Association', 'Journal of Sports Medicine', 'Sports Medicine',
            'Journal of Strength and Conditioning Research', 'Medicine & Science in Sports & Exercise',
            'Phillips', 'Helms', 'Schoenfeld', 'Aragon'
        ]

    def create_specific_prompt(self, user_question):
        fitness_keywords = [
            'gym', 'fitness', 'latihan', 'workout', 'olahraga', 'exercise', 'training', 'sesi latihan', 
            'program latihan', 'routine', 'plan', 'angkat beban', 'resistance training', 'weightlifting', 
            'strength training', 'hypertrophy', 'powerlifting', 'crossfit', 'set', 'rep', 'repetisi', 
            'superset', 'dropset', 'circuit', 'compound', 'isolation', 'push', 'pull', 'legs', 'squat', 
            'otot', 'muscle', 'abs', 'core', 'chest', 'dada', 'punggung', 'nutrisi', 'nutrition', 'protein', 
            'karbohidrat', 'carbs', 'rest', 'istirahat', 'recovery', 'pemulihan', 'sleep untuk recovery', 
            'jadwal', 'split', 'bro split', 'push pull legs', 'upper lower', 'buat jadwal', 'atur waktu', 
            'schedule', 'reminder', 'calendar', 'penjadwalan', 'jadwal latihan', 'waktu gym', 
            'reminder workout', 'kapan latihan', 'hari apa latihan', 'jam berapa gym'
        ]
        
        if not any(keyword in user_question.lower() for keyword in fitness_keywords):
            return None
            
        return f"""
        {self.system_prompt}
        
        PERTANYAAN USER: {user_question}
        
        INSTRUKSI JAWABAN:
        1. Jawab HANYA jika terkait fitness/gym/lifestyle untuk performa/penjadwalan latihan
        2. WAJIB berikan referensi ilmiah: (Sumber: ACSM, 2022) atau (Phillips et al., Journal, 2020)
        3. Jika TIDAK ada referensi → katakan "Tidak ada referensi ilmiah yang akurat, konsultasi ahli"
        4. Jika tentang penjadwalan → tanyakan detail dan berikan JSON response
        5. Format: pendahuluan, poin dengan referensi, kesimpulan
        6. Maksimal 300 kata
        7. Aspek medis → rujuk ke profesional + sebutkan spesialis yang tepat
        """

    def send_request(self, prompt):
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.6,
                "topK": 40,
                "topP": 0.9,
                "maxOutputTokens": 700,
                "stopSequences": ["Contoh:", "contoh:"]
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
        }
        
        try:
            response = requests.post(self.url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "Maaf, tidak ada respons yang diterima.")
            return "Maaf, terjadi kesalahan dalam memproses respons."
        except requests.exceptions.RequestException as e:
            return f"Maaf, terjadi kesalahan koneksi: {str(e)}"
        except Exception as e:
            return f"Maaf, terjadi kesalahan tidak terduga: {str(e)}"

    def _is_valid_calendar_payload(self, data: dict) -> bool:
        try:
            if not isinstance(data, dict):
                return False
            if data.get("action") != "create_calendar_event":
                return False
            if data.get("confirmed") is not True:
                return False
            title = data.get("title")
            if not isinstance(title, str) or not title.strip():
                return False
            date_str = data.get("date")
            time_str = data.get("time")
            duration_val = data.get("duration", 1)
            # Validate date and time format strictly
            datetime.strptime(str(date_str), "%Y-%m-%d")
            datetime.strptime(str(time_str), "%H:%M")
            # Duration must be a positive small integer (avoid unrealistic values from examples)
            if isinstance(duration_val, bool):
                return False
            duration_int = int(duration_val)
            if duration_int < 1 or duration_int > 6:
                return False
            if "description" in data and not isinstance(data.get("description"), str):
                return False
            return True
        except Exception:
            return False

    def parse_calendar_request(self, response):
        # Find all minimal JSON objects that contain an "action" key
        try:
            candidates = list(re.finditer(r'\{[^\{\}]*"action"[^\{\}]*\}', response, flags=re.DOTALL))
            for match in candidates:
                # Skip if this looks like an example block (preceded by the word "contoh"/"example")
                prefix_window = response[max(0, match.start()-80):match.start()].lower()
                if "contoh" in prefix_window or "example" in prefix_window:
                    continue
                try:
                    data = json.loads(match.group())
                except Exception:
                    continue
                if self._is_valid_calendar_payload(data):
                    return data
        except Exception:
            pass
        return None

    def chat(self, user_question, calendar_tools=None):
        specific_prompt = self.create_specific_prompt(user_question)
        
        if specific_prompt is None:
            return """
            🚫 Maaf, saya khusus membantu pertanyaan FITNESS & GYM seperti:
            
            ✅ YANG BISA SAYA BANTU:
            • Pola latihan gym (strength, hypertrophy, endurance)
            • Program latihan (split, full body, dll)
            • Waktu istirahat dan recovery
            • Jadwal latihan optimal
            • Nutrisi untuk fitness (protein, carbs, meal timing)
            • Lifestyle factors untuk performa gym
            • 🆕 MEMBUAT JADWAL LATIHAN DI GOOGLE CALENDAR
            
            💡 CONTOH PERTANYAAN BARU:
            "Buatkan jadwal latihan upper body besok pagi"
            "Atur reminder gym untuk hari Senin"
            "Schedule workout push-pull-legs minggu ini"
            """
        
        response = self.send_request(specific_prompt)
        
        calendar_request = self.parse_calendar_request(response)
        if calendar_request and calendar_tools:
            result = calendar_tools.create_workout_event(
                title=calendar_request.get("title"),
                date=calendar_request.get("date"),
                time=calendar_request.get("time"),
                duration_hours=calendar_request.get("duration", 1),
                description=calendar_request.get("description", "")
            )
            
            if result["success"]:
                response += f"\n\n📅 {result['message']}"
                if result.get("event_link"):
                    response += f"\n🔗 Link: {result['event_link']}"
            else:
                response += f"\n\n❌ Gagal membuat jadwal: {result['error']}"
        
        return response + "\n\n⚠️ DISCLAIMER: Informasi ini bersifat umum. Konsultasikan dengan trainer atau dokter untuk program yang sesuai kondisi Anda."

# =============================================================
# ENHANCED FITBOT CLASS
# =============================================================
class EnhancedFitBot:
    """
    Kelas FitBot terpadu yang menggabungkan RAG, LLM, dan Google Calendar Tools.
    """
    def __init__(self, gemini_api_key, google_credentials_file='client_secret.json'):
        # Inisialisasi Kunci API dan URL
        if not gemini_api_key:
            raise ValueError("API Key for Gemini is required.")
        self.API_KEY = gemini_api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        self.headers = {"Content-Type": "application/json", "x-goog-api-key": self.API_KEY}
        
        # Inisialisasi Tools
        logger.info("🔧 Initializing Google Calendar Tools...")
        self.calendar_tools = GoogleCalendarTools(google_credentials_file)
        
        logger.info("📚 Initializing RAG System...")
        try:
            # Sistem RAG untuk menjawab pertanyaan berbasis pengetahuan dari dokumen
            self.rag_system = FitbotRAGSystem(gemini_api_key=self.API_KEY)
            # Langsung bangun database vektor saat pertama kali dijalankan
            if self.rag_system.embeddings:  # Only initialize if embeddings loaded
                self.rag_system.initialize_system()
            else:
                logger.warning("⚠️ RAG system disabled - embeddings not loaded")
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG system: {e}")
            self.rag_system = None
            
        # Prompt untuk penjadwalan (diambil dari kelas GymFitnessChatbot lama)
        self.calendar_system_prompt = """
        PERAN: Kamu adalah FitBot, asisten fitness yang membantu penjadwalan latihan dengan aman.
        TUJUAN: Mengumpulkan informasi untuk membuat jadwal di Google Calendar.
        GAYA: Ramah, ringkas, dan to the point.

        SLOT-FILLING PENJADWALAN:
        - Kumpulkan HANYA slot yang belum ada: jenis latihan (title), tanggal (date: YYYY-MM-DD), jam (time: HH:MM 24h), durasi (duration: 1–6 jam).
        - Jika ada ambiguitas (mis. jam 7 pagi vs 7 malam) minta klarifikasi.
        - Jika tanggal di masa lalu, sarankan tanggal valid terdekat.
        - Jika semua slot lengkap dan user setuju, keluarkan HANYA JSON VALID siap dieksekusi berikut:
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

    def chat(self, user_question: str):
        """
        Metode chat utama yang mengatur alur ke RAG atau Calendar.
        """
        # 1. Cek apakah pertanyaan relevan dengan fitness
        if self.rag_system and not self.rag_system._is_fitness_related(user_question):
            return self.rag_system._get_non_fitness_response()

        # 2. Cek kata kunci untuk penjadwalan kalender
        calendar_keywords = [
            'jadwal', 'atur waktu', 'schedule', 'reminder', 'calendar', 
            'penjadwalan', 'jadwalin', 'buat jadwal', 'ingatkan saya'
        ]
        if any(keyword in user_question.lower() for keyword in calendar_keywords):
            logger.info("🗓️ Calendar keyword detected. Routing to calendar logic.")
            return self._handle_calendar_request(user_question)

        # 3. Jika bukan penjadwalan, gunakan RAG untuk jawaban berbasis pengetahuan
        if self.rag_system and self.rag_system.is_initialized:
            logger.info("🧠 Routing to RAG system for knowledge-based question.")
            # Menggunakan metode chat_with_rag dari FitbotRAGSystem
            return self.rag_system.chat_with_rag(user_question)
        
        # 4. Fallback: Jika RAG tidak siap, gunakan LLM secara langsung
        logger.warning("⚠️ RAG system not ready. Using direct LLM call as fallback.")
        if self.rag_system:
             return self.rag_system._original_chat(user_question)
        else:
             return "Maaf, sistem chatbot sedang tidak dapat memproses permintaan berbasis pengetahuan saat ini."


    def _handle_calendar_request(self, user_question: str):
        """
        Menangani permintaan khusus untuk penjadwalan dengan slot-filling.
        """
        prompt = f"{self.calendar_system_prompt}\n\nPERTANYAAN USER: {user_question}"
        
        # Mengirim prompt penjadwalan ke Gemini
        response_text = self._send_gemini_request(prompt)

        # Parsing dan eksekusi jika ada JSON valid
        calendar_request = self._parse_calendar_request(response_text)
        if calendar_request:
            logger.info(f"✅ Valid calendar JSON found: {calendar_request}")
            result = self.calendar_tools.create_workout_event(
                title=calendar_request.get("title"),
                date=calendar_request.get("date"),
                time=calendar_request.get("time"),
                duration_hours=calendar_request.get("duration", 1),
                description=calendar_request.get("description", "")
            )
            
            # Tambahkan pesan sukses atau gagal ke respons
            if result.get("success"):
                final_response = f"{response_text}\n\n---\n\n📅 **Status:** {result.get('message')}"
                if result.get("event_link"):
                    final_response += f"\n🔗 **Link Event:** {result.get('event_link')}"
                return final_response
            else:
                return f"{response_text}\n\n---\n\n❌ **Status:** Gagal membuat jadwal: {result.get('error')}"

        return response_text + "\n\n⚠️ DISCLAIMER: Informasi ini bersifat umum. Konsultasikan dengan trainer atau dokter untuk program yang sesuai kondisi Anda."


    def _send_gemini_request(self, prompt: str) -> str:
        """
        Helper function untuk mengirim request ke Gemini API.
        """
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6, "topK": 40, "topP": 0.9, "maxOutputTokens": 700},
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
        }
        try:
            response = requests.post(self.url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return "Maaf, terjadi kesalahan dalam memproses respons."
        except requests.exceptions.RequestException as e:
            return f"Maaf, terjadi kesalahan koneksi: {str(e)}"
    
    def _parse_calendar_request(self, response: str) -> Optional[Dict]:
        """
        Mengekstrak JSON permintaan kalender dari teks respons LLM.
        """
        # Implementasi parsing yang sama dari kelas GymFitnessChatbot lama
        try:
            match = re.search(r'\{[\s\S]*"action":\s*"create_calendar_event"[\s\S]*\}', response)
            if match:
                data = json.loads(match.group())
                if data.get("confirmed") is True:
                    return data
        except (json.JSONDecodeError, AttributeError):
            return None
        return None

    # Tambahkan metode lain yang diperlukan dari calendar_tools
    def get_upcoming_workouts(self, days=7):
        return self.calendar_tools.get_upcoming_workouts(days)
    
    def delete_workout(self, event_id):
        return self.calendar_tools.delete_workout_event(event_id)

# =============================================================
# FASTAPI SERVER
# =============================================================
app = FastAPI(title="Enhanced FitBot API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = get_api_key_from_file()
fitbot = EnhancedFitBot(API_KEY) if API_KEY else None

# Pydantic models
class ChatRequest(BaseModel):
    question: str

# API Endpoints
@app.get("/auth/login")
def auth_login():
    if not fitbot:
        raise HTTPException(status_code=500, detail="FitBot not initialized")
    flow = fitbot.calendar_tools.get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
def auth_callback(code: str):
    if not fitbot:
        raise HTTPException(status_code=500, detail="FitBot not initialized")
    try:
        flow = fitbot.calendar_tools.get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        with open(fitbot.calendar_tools.token_file, 'wb') as token:
            pickle.dump(credentials, token)
        
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
    return {"status": "already_logged_out"}

@app.get("/auth/status")
def auth_status():
    if not fitbot:
        return {"authenticated": False}
    
    return {"authenticated": fitbot.calendar_tools.service is not None}

@app.post("/chat")
def handle_chat(req: ChatRequest):
    if not fitbot:
        return {"answer": "❌ Error: API Key tidak ditemukan, chatbot tidak aktif."}
    return {"answer": fitbot.chat(req.question)}

@app.get("/upcoming-workouts")
def get_upcoming_workouts(days: int = 7):
    if not fitbot or not fitbot.calendar_tools.service:
        raise HTTPException(status_code=403, detail="Not authenticated")
    return fitbot.get_upcoming_workouts(days)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "fitbot_active": fitbot is not None,
        "calendar_ready": fitbot.calendar_tools.service is not None if fitbot else False
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Enhanced FitBot Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
