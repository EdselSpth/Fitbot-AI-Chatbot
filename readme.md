
# `FITBOT - Your Personal Fitness Assistant`

**Description**  
FitBot adalah asisten fitness personal berbasis artificial intelligence yang dirancang untuk menjadi teman andalanmu. Mendukung misi SDGs "AI for Good Health and Well-being," FitBot fokus pada sisi kebugaran melalui fitness dengan menyediakan program latihan yang disesuaikan, tips nutrisi berbasis sains, dan semua jawaban dari pertanyaan kamu. FitBot siap membantumu berlatih lebih cerdas dan mencapai targetmu lebih cepat.

**Theme** 
AI for Good Health and Well-being

## 🧑‍💻 Team

| **Name**                   | **Role**               |
|--------------------------- |------------------------|
| Edsel Septa Haryanto       | Backend                |
| Falah Razan Hibrizi        | Frontend               |
| Farhan Hamzah              | Backend                |
| Fazari Razka Davira        | Frontend               |


---

## 🚀 Features
- **🤖 Asisten Fitness Pribadimu**: Dapatkan jawaban instan dan berbasis ilmiah untuk semua pertanyaanmu seputar program latihan, nutrisi, hingga pemulihan (recovery), didukung oleh kecerdasan buatan Google Gemini.
- **🥗 Saran Nutrisi Cerdas**: Memberikan rekomendasi pola makan sehat yang disesuaikan dengan profil pengguna, seperti kebutuhan kalori harian dan preferensi diet.
- **📊 Tingkat Kesulitan Latihan yang Adaptif**: Menyesuaikan intensitas latihan secara otomatis berdasarkan progres dan feedback pengguna, sehingga program tetap menantang namun aman.
- **🎯 Pencocokan Program Latihan Cerdas**: Menawarkan latihan alternatif serupa jika peralatan tertentu tidak tersedia atau jika pengguna memiliki batasan fisik.
- **🌐 Aksesibilitas UI**: Antarmuka yang mudah diakses (accessible design), mendukung navigasi keyboard dan screen reader, serta memiliki kontras warna yang optimal.
- **📆 Buat jadwal latihan di google kalender**: Memudahkan pengguna untuk menjadwalkan latihan fitness dengan integrasi langsung dengan google calendar
- **⚙️ Pencarian lebih faktual dan kredibel**: Dengan implementasi Retrieval-augmented generation chatbot memiliki kemampuan mempelajari jurnal-jurnal pilihan untuk memberikan jawaban yang berdasarkan fakta
- **❤️‍🩹 Koneksi langung dengan Google Fit** : Dengan implementasi Ai Agentic yang terkoneksi langsung dengan google fit dapat mentracking gerakan pengguna untuk memberikan hasil jawaban yang lebih personal



## 🛠 Tech Stack

**Frontend:**
- Bahasa Pemrograman : Typescript
- Framework : Next.js dengan react
- Styling : Tailwind CSS
- Markdown Renderer : React Markdown

**Backend:**
- Bahasa Pemrograman : Python
- Framework : FastAPI
- API : Google AI Gemini
- Validasi Data : Pydantic

---

## 🚀 How to Run the Project

### Step 1. Clone the Repository
```bash
git clone https://github.com/EdselSpth/Fitbot-AI-Chatbot.git
```


### Step 2 Run API Backend pada Python di Terminal Baru
```bash
cd Fitbot-AI-Chatbot
cd google
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3 Run Frontend di Terminal Baru
```bash
cd Fitbot-AI-Chatbot
cd fe
npm install
npm run dev
```

### Step 4 Buka localhost:3000 di browser

### Login Authentikasi Google dengan Akun berikut
```bash
email : devtestingedsel@gmail.com
password : DevTesting130904
```

## 📋 Requirements (optional)
- Node.js versi 18.18 atau lebih baru.
- Python versi 3.10 atau lebih baru.

## Video Demo Tugas 1
[![<Teks Alt>](https://img.youtube.com/vi/FLGonXn21D8/0.jpg)](https://www.youtube.com/watch?v=FLGonXn21D8)

## Video Demo Tugas 2
[![Video Demo Enhanced FitBot](https://img.youtube.com/vi/anXcXKllBnY/0.jpg)](https://www.youtube.com/watch?v=anXcXKllBnY)

## Video Demo Tugas 3
[![Video Demo Enhanced FitBot](https://img.youtube.com/vi/X1tAmENjQ5w/0.jpg)](https://www.youtube.com/watch?v=X1tAmENjQ5w)
