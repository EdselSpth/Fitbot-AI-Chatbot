import requests
import json
import os
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# =============================================================
# UTILITY FUNCTIONS - PINDAHKAN KE SINI
# =============================================================
def get_api_key_from_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))  
    key_file_path = os.path.join(base_dir, "api_key.txt")  
    try:
        with open(key_file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error baca API key: {e}")
        return None

# =============================================================
# GOOGLE CALENDAR TOOLS CLASS
# =============================================================
class GoogleCalendarTools:
    def __init__(self, credentials_file='client_secret.json'):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials_file = credentials_file
        self.token_file = 'token.pickle'
        self.service = None
        self.initialize_service()
    
    
    def setup_auth(self):
        try:
            with open(self.credentials_file, 'r') as f:
                client_config = json.load(f)

            if 'web' in client_config:
                web_config = client_config['web']
                client_config = {
                    'installed': {
                        'client_id': web_config['client_id'],
                        'client_secret': web_config['client_secret'],
                        'auth_uri': web_config['auth_uri'],
                        'token_uri': web_config['token_uri'],
                        'auth_provider_x509_cert_url': web_config['auth_provider_x509_cert_url'],
                        'redirect_uris': ['http://localhost']
                    }
                }

            flow = InstalledAppFlow.from_client_config(
                client_config,
                scopes=self.SCOPES,
            )
            creds = flow.run_local_server(port=8080)

            # ✅ simpan ke file biar tidak login ulang
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
                return creds

        except Exception as e:
            print(f"❌ Auth setup error: {e}")
            return None

    def initialize_service(self):
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    print(f"❌ Token refresh failed: {e}")
                    self.service = None
                    return
            else:
                print("⚠️ Token belum ada/invalid. Jalankan setup_auth() sekali untuk login.")
                self.service = None
                return

        # Build service dengan credentials yang valid
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            print("✅ Google Calendar service initialized")
        except Exception as e:
            print(f"❌ Error initializing Google Calendar: {e}")
            self.service = None

    
    def create_workout_event(self, title: str, date: str, time: str, duration_hours: int = 1, description: str = ""):
        """
        Create workout event in Google Calendar
        
        Args:
            title: Event title (e.g., "Upper Body Workout")
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format (24-hour)
            duration_hours: Duration in hours
            description: Additional details
        """
        if not self.service:
            return {"success": False, "error": "Google Calendar service not initialized"}
        
        try:
            # Parse datetime
            start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Jakarta',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Jakarta',
                },
                'colorId': '4',  # Green color for fitness events
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
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
        """Get upcoming workout events"""
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
                q='workout OR gym OR fitness OR latihan'  # Filter workout-related events
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
        """Delete workout event by ID"""
        if not self.service:
            return {"success": False, "error": "Google Calendar service not initialized"}
        
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return {"success": True, "message": "✅ Event berhasil dihapus"}
        except Exception as e:
            return {"success": False, "error": f"Error deleting event: {str(e)}"}

# =============================================================
# GYM FITNESS CHATBOT CLASS (ORIGINAL)
# =============================================================
class GymFitnessChatbot:
    def __init__(self, api_key):
        self.API_KEY = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.API_KEY
        }
        
        # Enhanced system prompt with calendar integration
        self.system_prompt = """
        Anda adalah asisten fitness dan gym yang berbasis evidence-based science,
        tetapi gunakan bahasa yang lebih santai, ramah, dan mudah dipahami seperti
        ngobrol dengan teman di gym. Tetap sertakan referensi ilmiah bila perlu,
        tapi jangan terlalu kaku atau terlalu akademis.

        🆕 FITUR BARU: Anda sekarang dapat membantu user membuat jadwal latihan di Google Calendar!
        
        Jika user menanyakan tentang:
        - "buat jadwal latihan"
        - "atur waktu gym"
        - "reminder workout"
        - "schedule latihan"
        
        Tanyakan detail berikut:
        1. Jenis latihan (Upper Body, Lower Body, Cardio, dll)
        2. Tanggal (YYYY-MM-DD)
        3. Jam (HH:MM format 24 jam)
        4. Durasi (berapa jam)
        
        Kemudian berikan response dalam format JSON seperti ini:
        {
            "action": "create_calendar_event",
            "title": "Upper Body Workout",
            "date": "2024-12-15",
            "time": "07:00",
            "duration": 1,
            "description": "Latihan dada, bahu, triceps dengan fokus strength training"
        }

        =====================
        ⚡ ATURAN FORMATTING (PALING PENTING & WAJIB DIIKUTI):
        - **SELURUH JAWABAN HARUS MENGGUNAKAN FORMAT MARKDOWN YANG RAPI.**
        - **WAJIB GUNAKAN JUDUL/SUB-JUDUL** dengan `###`. Contoh: `### Program Latihan Pemula`
        - **WAJIB GUNAKAN DAFTAR (LIST)** dengan tanda `* ` untuk item seperti tips atau jadwal latihan.
        - **WAJIB GUNAKAN SPASI PARAGRAF** (dua kali enter) agar jawaban tidak padat.
        - Gunakan `**teks tebal**` untuk menekankan kata kunci penting.

        =====================
        ⚠️ ATURAN KETAT:
        1. HANYA jawab pertanyaan tentang:
            - Pola latihan gym (hypertrophy, strength, endurance, fat loss)
            - Waktu istirahat (antar set, antar sesi, recovery mingguan)
            - Jadwal olahraga (mingguan/bulanan)
            - Nutrisi dasar untuk fitness (protein, karbohidrat, lemak, hidrasi)
            - Pola hidup sehat TERKAIT FITNESS (tidur untuk recovery, hidrasi untuk performa)
            - 🆕 PENJADWALAN LATIHAN DI GOOGLE CALENDAR
        2. **WAJIB** gunakan referensi ilmiah yang valid:
            - Organisasi resmi: ACSM, WHO, NSCA, ADA, ISSN
            - Jurnal peer-reviewed: Journal of Sports Medicine, Sports Medicine, etc.
            - Format: "(Sumber: ACSM, 2022)" atau "(Phillips et al., Journal of Sports Medicine, 2020)"
        3. DILARANG memberikan diagnosa medis atau saran pengobatan.
        4. Jika ada kondisi khusus (cedera, penyakit), SELALU sarankan konsultasi profesional.
        5. Jika **TIDAK ADA referensi ilmiah**, jawab: "Saya tidak menemukan referensi ilmiah yang akurat untuk hal tersebut. Silakan konsultasi dengan ahli."

        ⚡ Aturan tambahan:
        - Gunakan emoji 2–3 kali per jawaban untuk menambah kesan fun (💪🔥😴😉).
        - Tetap sertakan referensi ilmiah (ACSM, WHO, jurnal olahraga).
        - Jangan terlalu kaku atau akademis, gunakan bahasa sehari-hari.
        - Jawaban tetap ringkas, jelas, dan bermanfaat.
        
        =====================
        📌 BATASAN PENGETAHUAN:
        - Fokus HANYA pada: program latihan, recovery, jadwal optimal, nutrisi fitness, lifestyle factors untuk performa, dan penjadwalan latihan
        - Tolak pertanyaan umum kesehatan yang tidak terkait fitness/gym
        - Jika ragu → rujuk ke profesional dengan referensi yang tepat
        """
        
        # Daftar sumber referensi yang valid untuk validasi
        self.valid_sources = [
            'ACSM', 'American College of Sports Medicine',
            'WHO', 'World Health Organization', 
            'NSCA', 'National Strength and Conditioning Association',
            'ISSN', 'International Society of Sports Nutrition',
            'ADA', 'American Dietetic Association',
            'Journal of Sports Medicine', 'Sports Medicine',
            'Journal of Strength and Conditioning Research',
            'Medicine & Science in Sports & Exercise',
            'Phillips', 'Helms', 'Schoenfeld', 'Aragon'
        ]

    def create_specific_prompt(self, user_question):
        """Membuat prompt yang spesifik untuk mengurangi halusinasi"""
        
        # Enhanced fitness keywords with calendar-related terms
        fitness_keywords = [
            # Original fitness keywords
            'gym', 'fitness', 'latihan', 'workout', 'olahraga', 'exercise', 
            'training', 'sesi latihan', 'program latihan', 'routine', 'plan',
            'angkat beban', 'resistance training', 'weightlifting', 
            'strength training', 'hypertrophy', 'powerlifting', 'crossfit',
            'set', 'rep', 'repetisi', 'superset', 'dropset', 'circuit', 
            'compound', 'isolation', 'push', 'pull', 'legs', 'squat', 
            'otot', 'muscle', 'abs', 'core', 'chest', 'dada', 'punggung',
            'nutrisi', 'nutrition', 'protein', 'karbohidrat', 'carbs',
            'rest', 'istirahat', 'recovery', 'pemulihan', 'sleep untuk recovery',
            'jadwal', 'split', 'bro split', 'push pull legs', 'upper lower',
            
            # New calendar-related keywords
            'buat jadwal', 'atur waktu', 'schedule', 'reminder', 'calendar',
            'penjadwalan', 'jadwal latihan', 'waktu gym', 'reminder workout',
            'kapan latihan', 'hari apa latihan', 'jam berapa gym'
        ]
        
        is_fitness_related = any(keyword in user_question.lower() for keyword in fitness_keywords)
        
        if not is_fitness_related:
            return None
            
        specific_prompt = f"""
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
        
        return specific_prompt
    
    def send_request(self, prompt):
        """Mengirim request ke Gemini API dengan error handling"""
        data = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.75,
                "topK": 40,
                "topP": 0.9,
                "maxOutputTokens": 1000,
                "stopSequences": []
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        try:
            response = requests.post(self.url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                if parts and len(parts) > 0:
                    return parts[0].get("text", "Maaf, tidak ada respons yang diterima.")
            
            return "Maaf, terjadi kesalahan dalam memproses respons."
            
        except requests.exceptions.Timeout:
            return "Maaf, request timeout. Silakan coba lagi."
        except requests.exceptions.RequestException as e:
            return f"Maaf, terjadi kesalahan koneksi: {str(e)}"
        except json.JSONDecodeError:
            return "Maaf, terjadi kesalahan dalam memproses data."
        except Exception as e:
            return f"Maaf, terjadi kesalahan tidak terduga: {str(e)}"
    
    def has_scientific_reference(self, response):
        """Cek apakah response mengandung referensi ilmiah"""
        patterns = [
            r'\(.*?\d{4}.*?\)',
            r'\(Sumber:.*?\)',
            r'Menurut.*?(\d{4}|ACSM|WHO|NSCA)',
            r'Penelitian.*?menunjukkan',
            r'Studi.*?(Journal|Medicine)'
        ]
        
        for pattern in patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        for source in self.valid_sources:
            if source.lower() in response.lower():
                return True
                
        return False
    
    def parse_calendar_request(self, response):
        """Parse JSON calendar request from response"""
        try:
            # Look for JSON in the response
            json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except:
            pass
        return None
    
    def chat(self, user_question, calendar_tools=None):
        """Enhanced chat function with calendar integration"""
        print(f"\n🏋️ Gym Fitness Assistant")
        print(f"📝 Pertanyaan: {user_question}")
        print("-" * 50)
        
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
        
        # Check if response contains calendar request
        calendar_request = self.parse_calendar_request(response)
        if calendar_request and calendar_tools:
            # Process calendar request
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
        
        disclaimer = "\n\n⚠️ DISCLAIMER: Informasi ini bersifat umum. Konsultasikan dengan trainer atau dokter untuk program yang sesuai kondisi Anda."
        
        return response + disclaimer

# =============================================================
# ENHANCED FITBOT CLASS (COMBINES BOTH)
# =============================================================
class EnhancedFitBot:
    def __init__(self, gemini_api_key, google_credentials_file='client_secret.json'):
        self.chatbot = GymFitnessChatbot(gemini_api_key)
        self.calendar_tools = GoogleCalendarTools(google_credentials_file)
        
        print("🤖 Enhanced FitBot initialized!")
        print("✅ Gemini AI: Ready")
        print("📅 Google Calendar: Ready" if self.calendar_tools.service else "❌ Google Calendar: Need authentication")
    
    def setup_calendar_auth(self):
        """Setup Google Calendar authentication"""
        return self.calendar_tools.setup_auth()
    
    def chat(self, user_question):
        """Main chat function with calendar integration"""
        return self.chatbot.chat(user_question, self.calendar_tools)
    
    def get_upcoming_workouts(self, days=7):
        """Get upcoming workout events"""
        return self.calendar_tools.get_upcoming_workouts(days)
    
    def delete_workout(self, event_id):
        """Delete workout event"""
        return self.calendar_tools.delete_workout_event(event_id)

# =============================================================
# FASTAPI SERVER
# =============================================================
app = FastAPI(title="Enhanced FitBot API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================
# AUTO AUTHENTICATION SETUP
# =============================================================

def setup_calendar_authentication():
    if fitbot and not fitbot.calendar_tools.service:
        print("🔐 Setting up Google Calendar authentication...")
        creds = fitbot.setup_calendar_auth()
        if creds:
            print("✅ Google Calendar authentication successful!")
            fitbot.calendar_tools.initialize_service()
        else:
            print("❌ Google Calendar authentication failed!")
    elif fitbot:
        print("✅ Google Calendar already authenticated")

API_KEY = get_api_key_from_file()
fitbot = EnhancedFitBot(API_KEY) if API_KEY else None

# Run auto-authentication when imported
setup_calendar_authentication()

def get_api_key_from_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))  
    key_file_path = os.path.join(base_dir, "api_key.txt")  
    try:
        with open(key_file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error baca API key: {e}")
        return None

# Initialize Enhanced FitBot
API_KEY = get_api_key_from_file()
fitbot = EnhancedFitBot(API_KEY) if API_KEY else None

# Pydantic models
class ChatRequest(BaseModel):
    question: str

class WorkoutEventRequest(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    duration: int = 1
    description: str = ""

class DeleteEventRequest(BaseModel):
    event_id: str

# API Endpoints
@app.post("/chat")
def handle_chat(req: ChatRequest):
    """Main chat endpoint with calendar integration"""
    if not fitbot:
        return {"answer": "❌ Error: API Key tidak ditemukan, chatbot tidak aktif."}
    return {"answer": fitbot.chat(req.question)}

@app.post("/create-workout-event")
def create_workout_event(req: WorkoutEventRequest):
    """Create workout event in Google Calendar"""
    if not fitbot:
        return {"success": False, "error": "FitBot tidak aktif"}
    
    result = fitbot.calendar_tools.create_workout_event(
        title=req.title,
        date=req.date,
        time=req.time,
        duration_hours=req.duration,
        description=req.description
    )
    return result

@app.get("/upcoming-workouts")
def get_upcoming_workouts(days: int = 7):
    """Get upcoming workout events"""
    if not fitbot:
        return {"success": False, "error": "FitBot tidak aktif"}
    
    return fitbot.get_upcoming_workouts(days)

@app.delete("/delete-workout")
def delete_workout(req: DeleteEventRequest):
    """Delete workout event"""
    if not fitbot:
        return {"success": False, "error": "FitBot tidak aktif"}
    
    return fitbot.delete_workout(req.event_id)

@app.get("/setup-auth")
def setup_calendar_auth():
    """Setup Google Calendar authentication"""
    if not fitbot:
        return {"success": False, "error": "FitBot tidak aktif"}
    
    # This should be handled in a secure way in production
    return {"message": "Run fitbot.setup_calendar_auth() manually for security"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "fitbot_active": fitbot is not None,
        "calendar_ready": fitbot.calendar_tools.service is not None if fitbot else False
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Enhanced FitBot Server...")
    print("📋 Available endpoints:")
    print("   POST /chat - Main chat with calendar integration")
    print("   POST /create-workout-event - Create calendar event")
    print("   GET /upcoming-workouts - Get upcoming workouts")
    print("   DELETE /delete-workout - Delete workout event")
    print("   GET /health - Health check")
    fitbot = EnhancedFitBot(API_KEY)
    fitbot.setup_calendar_auth()  # Ini akan buka browser untuk login
    
    if fitbot and not fitbot.calendar_tools.service:
        print("\n⚠️  Google Calendar not authenticated!")
        print("   Run: python main.py and call fitbot.setup_calendar_auth()")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)