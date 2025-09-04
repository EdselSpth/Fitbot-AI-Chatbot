import sys
import os
sys.path.append('.')

# Import fungsi utility terlebih dahulu
def get_api_key_from_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))  
    key_file_path = os.path.join(base_dir, "api_key.txt")  
    try:
        with open(key_file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error baca API key: {e}")
        return None

# Sekarang import main
from main import EnhancedFitBot

# Setup fitbot manually
API_KEY = get_api_key_from_file()
if API_KEY:
    fitbot = EnhancedFitBot(API_KEY)
    print("🔐 Setting up Google Calendar authentication...")
    creds = fitbot.setup_calendar_auth()
    if creds:
        print("✅ Google Calendar authentication successful!")
        # Reinitialize service with new credentials
        fitbot.calendar_tools.initialize_service()
        print("✅ FitBot is ready with calendar access!")
    else:
        print("❌ Google Calendar authentication failed!")
else:
    print("❌ API key not found. Please check api_key.txt file")