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
        
        # System prompt yang sangat spesifik untuk mengurangi halusinasi
        self.system_prompt = """
        Anda adalah asisten fitness dan gym yang berbasis evidence-based science,
        tetapi gunakan bahasa yang lebih santai, ramah, dan mudah dipahami seperti
        ngobrol dengan teman di gym. Tetap sertakan referensi ilmiah bila perlu,
        tapi jangan terlalu kaku atau terlalu akademis.

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
        - Fokus HANYA pada: program latihan, recovery, jadwal optimal, nutrisi fitness, lifestyle factors untuk performa
        - Tolak pertanyaan umum kesehatan yang tidak terkait fitness/gym
        - Jika ragu → rujuk ke profesional dengan referensi yang tepat
        
       

        =====================
        ✅ CONTOH JAWABAN DENGAN REFERENSI:
        - "Menurut ACSM (American College of Sports Medicine, 2022), pemula disarankan resistance training 2-3x per minggu dengan recovery 48 jam untuk muscle group yang sama."
        - "Penelitian menunjukkan tidur 7-9 jam optimal untuk recovery otot (Walker, Journal of Sports Sciences, 2019)."
        - "Asupan protein 1.6-2.2g/kg berat badan untuk hipertrofi (Phillips & Van Loon, Journal of Sports Medicine, 2011)."
        - "WHO merekomendasikan minimal 150 menit moderate-intensity exercise per minggu untuk kesehatan umum."
        =====================
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
            'Phillips', 'Helms', 'Schoenfeld', 'Aragon'  # Peneliti terkenal
        ]

    def create_specific_prompt(self, user_question):
        """Membuat prompt yang spesifik untuk mengurangi halusinasi"""
        
        # Validasi apakah pertanyaan relevan dengan fitness/gym
        fitness_keywords = [
        # Umum
        'gym', 'fitness', 'latihan', 'workout', 'olahraga', 'exercise', 
        'training', 'sesi latihan', 'program latihan', 'routine', 'plan',

        # Intensitas & beban
        'angkat beban', 'resistance training', 'weightlifting', 
        'strength training', 'hypertrophy', 'powerlifting', 'crossfit',
        'functional training', 'calisthenics', 'bodyweight',

        # Pola set & repetisi
        'set', 'rep', 'repetisi', 'superset', 'dropset', 'circuit', 'pyramid', 
        'failure', 'volume', 'intensity', 'progressive overload',

        # Jenis latihan
        'compound', 'isolation', 'push', 'pull', 'legs', 'squat', 
        'deadlift', 'bench press', 'overhead press', 'row', 'pull up', 'dip',
        'cardio', 'HIIT', 'low intensity', 'endurance', 'conditioning',

        # Otot & anatomi
        'otot', 'muscle', 'abs', 'core', 'chest', 'dada', 'punggung', 'back', 
        'bahu', 'shoulder', 'biceps', 'triceps', 'kaki', 'legs', 'quads', 
        'hamstring', 'glutes', 'calves', 'forearm',

        # Nutrisi & gizi KHUSUS FITNESS
        'nutrisi', 'nutrition', 'protein', 'karbohidrat', 'carbs', 'lemak', 
        'fat', 'kalori', 'surplus kalori', 'defisit kalori', 'bulking', 'cutting', 
        'maintenance', 'hydration', 'hidrasi', 'supplement', 'suplemen', 
        'creatine', 'bcaa', 'whey', 'pre workout', 'post workout',

        # Istirahat & pemulihan
        'rest', 'istirahat', 'recovery', 'pemulihan', 'sleep untuk recovery', 
        'tidur untuk recovery', 'durasi', 'frekuensi', 'waktu', 'jam', 
        'overtraining', 'deload', 'active recovery',

        # Jadwal & metode latihan
        'jadwal', 'split', 'bro split', 'push pull legs', 'upper lower', 
        'full body', 'frekuensi latihan', 'weekly plan', 'mesocycle', 'microcycle',

        # Lifestyle factors TERKAIT FITNESS
        'pola hidup fitness', 'lifestyle fitness', 'tidur untuk gym', 'hidrasi untuk latihan',
        'stress management untuk recovery', 'pola makan fitness', 'meal timing',
        'intermittent fasting untuk gym', 'cheat meal', 'refeed day'
        ]
        
        is_fitness_related = any(keyword in user_question.lower() for keyword in fitness_keywords)
        
        if not is_fitness_related:
            return None  # Akan ditolak
            
        # Buat prompt yang sangat spesifik
        specific_prompt = f"""
        {self.system_prompt}
        
        PERTANYAAN USER: {user_question}
        
        INSTRUKSI JAWABAN:
        1. Jawab HANYA jika terkait fitness/gym/lifestyle untuk performa
        2. WAJIB berikan referensi ilmiah: (Sumber: ACSM, 2022) atau (Phillips et al., Journal, 2020)
        3. Jika TIDAK ada referensi → katakan "Tidak ada referensi ilmiah yang akurat, konsultasi ahli"
        4. Format: pendahuluan, poin dengan referensi, kesimpulan
        5. Maksimal 300 kata
        6. Aspek medis → rujuk ke profesional + sebutkan spesialis yang tepat
        """
        
        return specific_prompt
    
    def send_request(self, prompt):
        """Mengirim request ke Gemini API dengan error handling"""
        data = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.75,  # Rendah untuk mengurangi kreativitas berlebih
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
            response.raise_for_status()  # Raise exception untuk HTTP error
            
            result = response.json()
            
            # Ekstrak jawaban dengan error handling
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
        # Pattern untuk mencari referensi
        patterns = [
            r'\(.*?\d{4}.*?\)',  # (Author, 2020) atau (ACSM, 2022)
            r'\(Sumber:.*?\)',    # (Sumber: ACSM)
            r'Menurut.*?(\d{4}|ACSM|WHO|NSCA)',  # Menurut ACSM/WHO
            r'Penelitian.*?menunjukkan',  # Penelitian menunjukkan
            r'Studi.*?(Journal|Medicine)'  # Studi dari Journal
        ]
        
        for pattern in patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        # Cek apakah ada sumber yang valid
        for source in self.valid_sources:
            if source.lower() in response.lower():
                return True
                
        return False
    
    def evaluate_response_quality(self, response):
        """Evaluasi kualitas response dengan scoring"""
        score = 0
        feedback = []
        
        # 1. Cek referensi ilmiah (40 poin)
        if self.has_scientific_reference(response):
            score += 40
            feedback.append("✅ Ada referensi ilmiah")
        else:
            feedback.append("❌ TIDAK ada referensi ilmiah")
        
        # 2. Cek panjang response (20 poin)
        word_count = len(response.split())
        if 50 <= word_count <= 300:
            score += 20
            feedback.append(f"✅ Panjang optimal ({word_count} kata)")
        else:
            feedback.append(f"⚠️ Panjang tidak optimal ({word_count} kata)")
        
        # 3. Cek disclaimer (20 poin)
        if "disclaimer" in response.lower() or "konsultasi" in response.lower():
            score += 20
            feedback.append("✅ Ada disclaimer")
        else:
            feedback.append("❌ TIDAK ada disclaimer")
        
        # 4. Cek struktur (20 poin)
        if any(marker in response for marker in ['•', '-', '1.', '2.', '*']):
            score += 20
            feedback.append("✅ Format terstruktur")
        else:
            feedback.append("⚠️ Format kurang terstruktur")
        
        return score, feedback

    def chat(self, user_question, show_quality_check=False):
        """Fungsi utama untuk chat dengan validasi ketat + optional quality check"""
        print(f"\n🏋️ Gym Fitness Assistant")
        print(f"📝 Pertanyaan: {user_question}")
        print("-" * 50)
        
        # Buat prompt spesifik
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
            • Lifestyle factors untuk performa gym (tidur untuk recovery, hidrasi)
            
            ❌ YANG TIDAK BISA SAYA BANTU:
            • Pola hidup sehat umum (bukan khusus fitness)
            • Masalah kesehatan/medis
            • Diet untuk penyakit tertentu
            • Pengobatan atau diagnosa
            
            💡 CONTOH PERTANYAAN YANG TEPAT:
            "Berapa jam tidur yang dibutuhkan untuk recovery otot?"
            "Pola makan seperti apa untuk bulking?"
            "Kapan waktu terbaik latihan gym?"
            
            Silakan tanya yang lebih spesifik tentang FITNESS & GYM! 🏋️‍♂️
            """
        
        # Kirim request
        response = self.send_request(specific_prompt)
        
        # Tambahkan disclaimer untuk keamanan
        disclaimer = "\n\n⚠️ DISCLAIMER: Informasi ini bersifat umum. Konsultasikan dengan trainer atau dokter untuk program yang sesuai kondisi Anda."
        
        final_response = response + disclaimer
        
        # Quality check jika diminta
        if show_quality_check:
            score, feedback = self.evaluate_response_quality(final_response)
            print(f"\n📊 QUALITY SCORE: {score}/100")
            print("📋 FEEDBACK:")
            for fb in feedback:
                print(f"   {fb}")
            print("-" * 50)
        
        return final_response
    
    def interactive_mode(self):
        """Mode interaktif untuk chat berkelanjutan"""
        print("🏋️ GYM & FITNESS CHATBOT - AI for Good Health & Well-being")
        print("="*60)
        print("Saya adalah asisten khusus untuk konsultasi fitness dan gym!")
        print("🎯 Ketik 'test' untuk menjalankan auto-testing")
        print("🔍 Ketik 'check' setelah pertanyaan untuk melihat quality score")
        print("Ketik 'quit' untuk keluar\n")
        
        while True:
            try:
                user_input = input("💬 Tanya seputar fitness/gym: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'keluar']:
                    print("👋 Terima kasih! Tetap semangat berolahraga!")
                    break
                elif user_input.lower() == 'test':
                    print("\n🧪 MENJALANKAN AUTO-TESTING...")
                    self.run_comprehensive_test()
                    continue
                elif user_input.lower().endswith(' check'):
                    # Hapus 'check' dari pertanyaan
                    question = user_input[:-6].strip()
                    print("\n🤔 Sedang memproses dengan quality check...")
                    response = self.chat(question, show_quality_check=True)
                    print(f"\n🤖 Jawaban:\n{response}")
                elif not user_input:
                    print("⚠️ Silakan masukkan pertanyaan Anda.")
                    continue
                else:
                    print("\n🤔 Sedang memproses...")
                    response = self.chat(user_input)
                    print(f"\n🤖 Jawaban:\n{response}")
                
                print("\n" + "="*60)
                
            except KeyboardInterrupt:
                print("\n👋 Terima kasih! Tetap semangat berolahraga!")
                break
            except Exception as e:
                print(f"\n❌ Terjadi kesalahan: {str(e)}")

    def run_comprehensive_test(self):
        """Jalankan testing otomatis yang comprehensive"""
        test_questions = [
            "Berapa jam tidur yang dibutuhkan untuk recovery otot?",
            "Berapa gram protein per kg berat badan untuk hipertrofi?",
            "Berapa lama istirahat antar set untuk strength training?",
            "Kapan waktu terbaik untuk latihan gym?",
            "Pola makan seperti apa untuk bulking?",
            "Frekuensi latihan yang optimal untuk pemula?",
            "Berapa menit cardio untuk fat loss?",
            "Hidrasi yang dibutuhkan saat latihan?",
        ]
        
        rejection_questions = [
            "Bagaimana cara mengobati diabetes?",
            "Apa resep masakan sehat?",
            "Pola hidup sehat untuk umur panjang?",
            "Vitamin apa yang bagus untuk imunitas?",
        ]
        
        print("="*60)
        print("🧪 COMPREHENSIVE AUTO-TESTING")
        print("="*60)
        
        # Test 1: Fitness Questions
        print("\n🏋️ TESTING FITNESS QUESTIONS:")
        total_score = 0
        
        for i, question in enumerate(test_questions):
            print(f"\n📋 TEST {i+1}/8: {question}")
            response = self.send_request(self.create_specific_prompt(question))
            score, feedback = self.evaluate_response_quality(response)
            total_score += score
            
            print(f"📊 SKOR: {score}/100")
            if score < 60:
                print("⚠️ NEEDS IMPROVEMENT!")
                print("📝 FEEDBACK:")
                for fb in feedback:
                    print(f"   {fb}")
        
        average_score = total_score / len(test_questions)
        print(f"\n🎯 FITNESS QUESTIONS RESULT:")
        print(f"Average Score: {average_score:.1f}/100")
        
        # Test 2: Rejection Questions
        print(f"\n🚫 TESTING REJECTION QUESTIONS:")
        reject_success = 0
        
        for i, question in enumerate(rejection_questions):
            print(f"\n❌ REJECT TEST {i+1}: {question}")
            specific_prompt = self.create_specific_prompt(question)
            
            if specific_prompt is None:
                print("✅ BERHASIL ditolak - tidak ada prompt")
                reject_success += 1
            else:
                print("❌ GAGAL ditolak - prompt dibuat")
        
        reject_rate = (reject_success / len(rejection_questions)) * 100
        print(f"\n🎯 REJECTION TEST RESULT:")
        print(f"Success Rate: {reject_rate:.1f}%")
        
        # Overall Result
        print(f"\n🏆 OVERALL ASSESSMENT:")
        if average_score >= 80 and reject_rate >= 75:
            print("🎉 EXCELLENT - Chatbot ready for production!")
        elif average_score >= 60 and reject_rate >= 50:
            print("👍 GOOD - Minor improvements needed")
        else:
            print("⚠️ NEEDS MAJOR IMPROVEMENT - Check system prompt")
        
        print("="*60)

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
