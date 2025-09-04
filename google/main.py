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
    def __init__(self, gemini_api_key, google_credentials_file='client_secret.json'):
        self.chatbot = GymFitnessChatbot(gemini_api_key)
        self.calendar_tools = GoogleCalendarTools(google_credentials_file)
    
    def chat(self, user_question):
        return self.chatbot.chat(user_question, self.calendar_tools)
    
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
