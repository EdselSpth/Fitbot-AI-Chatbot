import requests
import json
import os
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class GymFitnessChatbot:
    def __init__(self, api_key):
        self.API_KEY = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.API_KEY
        }
        
        # System prompt panjang seperti pre-train
        self.system_prompt = """
        Anda adalah asisten fitness dan gym yang **spesifik, akurat, dan berbasis evidence-based science**. 
        Jawaban Anda ditujukan untuk **membantu latihan fitness dan gym secara umum**, bukan untuk kondisi medis individual.

        =====================
        ⚠️ ATURAN KETAT:
        1. HANYA jawab pertanyaan tentang:
            - Pola latihan gym (hypertrophy, strength, endurance, fat loss)
            - Waktu istirahat (antar set, antar sesi, recovery mingguan)
            - Jadwal olahraga (mingguan/bulanan)
            - Nutrisi dasar untuk fitness (protein, karbohidrat, lemak, hidrasi)
            - Pola hidup sehat TERKAIT FITNESS (tidur untuk recovery, hidrasi untuk performa)
        2. **WAJIB** gunakan referensi ilmiah yang valid:
            - Organisasi resmi: ACSM, WHO, NSCA, ADA, ISSN
            - Jurnal peer-reviewed: Journal of Sports Medicine, Sports Medicine, etc.
            - Format: "(Sumber: ACSM, 2022)" atau "(Phillips et al., Journal of Sports Medicine, 2020)"
        3. DILARANG memberikan diagnosa medis atau saran pengobatan.
        4. Jika ada kondisi khusus (cedera, penyakit), SELALU sarankan konsultasi profesional.
        5. Jika **TIDAK ADA referensi ilmiah**, jawab: "Saya tidak menemukan referensi ilmiah yang akurat untuk hal tersebut. Silakan konsultasi dengan ahli."
        
        =====================
        📌 BATASAN PENGETAHUAN:
        - Fokus HANYA pada: program latihan, recovery, jadwal optimal, nutrisi fitness, lifestyle factors untuk performa
        - Tolak pertanyaan umum kesehatan yang tidak terkait fitness/gym
        - Jika ragu → rujuk ke profesional dengan referensi yang tepat
        =====================
        """
        
        # daftar keyword untuk filter
        self.fitness_keywords = [
            "gym","fitness","latihan","workout","olahraga","exercise","training",
            "strength","hypertrophy","cardio","protein","nutrisi","kalori","cutting",
            "bulking","split","jadwal","recovery","otot","sleep","hidrasi"
        ]

    def create_specific_prompt(self, user_question: str):
        """Membuat prompt spesifik & menolak kalau bukan fitness"""
        is_fitness_related = any(k in user_question.lower() for k in self.fitness_keywords)
        if not is_fitness_related:
            return None
        return f"{self.system_prompt}\n\nPERTANYAAN USER: {user_question}"

    def send_request(self, prompt: str):
        """Kirim request ke Gemini API"""
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 20,
                "topP": 0.8,
                "maxOutputTokens": 800
            }
        }
        try:
            resp = requests.post(self.url, headers=self.headers, json=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "Maaf, tidak ada respons.")
            return "Maaf, error parsing respons."
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def has_scientific_reference(self, response: str):
        """Cek apakah respons mengandung referensi ilmiah"""
        patterns = [r'\(.*?\d{4}.*?\)', r'\(Sumber:.*?\)', r'ACSM', r'WHO', r'NSCA', r'Journal']
        for p in patterns:
            if re.search(p, response, re.IGNORECASE):
                return True
        return False

    def chat(self, user_question: str):
        """Chat utama dengan validasi"""
        specific_prompt = self.create_specific_prompt(user_question)
        if not specific_prompt:
            return "🚫 Pertanyaanmu bukan tentang FITNESS/GYM. Silakan tanya seputar fitness ya 🏋️‍♂️"
        
        response = self.send_request(specific_prompt)
        disclaimer = "\n\n⚠️ DISCLAIMER: Informasi ini bersifat umum, silakan konsultasi ke profesional."
        
        # Kalau tidak ada referensi ilmiah → beri warning tambahan
        if not self.has_scientific_reference(response):
            return "❌ Jawaban tidak memiliki referensi ilmiah yang valid. Silakan konsultasi dengan ahli."
        
        return response + disclaimer

# =============================================================
# FASTAPI SERVER
# =============================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_api_key_from_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))  
    key_file_path = os.path.join(base_dir, "api_key.txt")  
    try:
        with open(key_file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error baca API key: {e}")
        return None

API_KEY = get_api_key_from_file()
chatbot = GymFitnessChatbot(API_KEY) if API_KEY else None

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
def handle_chat(req: ChatRequest):
    if not chatbot:
        return {"answer": "❌ Error: API Key tidak ditemukan, chatbot tidak aktif."}
    return {"answer": chatbot.chat(req.question)}
