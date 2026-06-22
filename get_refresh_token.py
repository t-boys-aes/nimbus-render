import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# We need the client ID and secret from the env
client_id = os.environ.get("YOUTUBE_CLIENT_ID")
client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")

if not client_id or not client_secret or "your_youtube" in client_id:
    print("\n[ERROR] YOUTUBE_CLIENT_ID dan YOUTUBE_CLIENT_SECRET belum dikonfigurasi di file .env!")
    print("Harap isi dulu kedua nilai tersebut di file .env sebelum menjalankan script ini.")
    sys.exit(1)

# Configure OAuth2 Client (compatible with Desktop Application credentials)
client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}

# Selection menu for scope generation
print("Pilih tipe token yang ingin Anda generate:")
print("1. KEDUA LAYANAN (YouTube + Drive + Sheets) -> Gunakan jika channel Anda BUKAN Brand Account")
print("2. HANYA YOUTUBE (Pilih ini lalu pilih Channel 'The Strategic Brief' saat login)")
print("3. HANYA GOOGLE DRIVE & SHEETS (Pilih ini lalu pilih email utama 'artisaneternal@gmail.com' saat login)")

choice = input("Pilihan Anda (1/2/3): ").strip()

if choice == "2":
    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl"
    ]
    token_name = "YOUTUBE_REFRESH_TOKEN"
elif choice == "3":
    scopes = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    token_name = "GDRIVE_REFRESH_TOKEN"
else:
    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    token_name = "YOUTUBE_REFRESH_TOKEN"

print("==================================================")
print("     NIMBUS YOUTUBE REFRESH TOKEN GENERATOR       ")
print("==================================================")
print("Langkah yang akan berjalan:")
print("1. Browser akan terbuka otomatis untuk meminta persetujuan akses Google Account.")
print("2. Pilih Google Account / Channel YouTube Anda.")
print("3. Jika ada peringatan 'Google hasn't verified this app', klik 'Advanced' -> 'Go to youtube-upload (unsafe)'.")
print("4. Setujui semua izin (YouTube Upload & Manage).")
print("5. Setelah berhasil, salin Refresh Token yang muncul di terminal ini ke .env.")
print("==================================================\n")

print("Memulai otorisasi OAuth2...")
try:
    # Run a local webserver to receive the OAuth2 callback (port 0 selects any free port)
    flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
    credentials = flow.run_local_server(
        port=0,
        authorization_prompt_message="Silakan buka URL ini jika browser tidak terbuka otomatis: {url}",
        success_message="Otorisasi berhasil! Anda sudah bisa menutup halaman ini dan kembali ke terminal."
    )
    
    print("\n" + "="*50)
    print("OTORISASI BERHASIL!")
    print("="*50)
    print(f"Refresh Token Anda adalah:\n\n{credentials.refresh_token}\n")
    print("="*50)
    print("Salin token di atas dan tempel di file .env pada baris:")
    print(f"{token_name}=<token_di_atas>")
    print("="*50)
except Exception as e:
    print(f"\nGagal mendapatkan refresh token: {e}")
