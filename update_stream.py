import subprocess
import os

# GitHub Secrets üzerinden cookies alıyoruz
COOKIES_FILE = "yt_cookies.txt"
cookies_content = os.environ.get("YT_COOKIES")

if not cookies_content:
    raise Exception("YT_COOKIES secret bulunamadı!")

# Cookies dosyasını oluştur
with open(COOKIES_FILE, "w") as f:
    f.write(cookies_content)

# YouTube video URL'si
VIDEO_URL = "https://www.youtube.com/watch?v=ztmY_cCtUl0"

# yt-dlp komutu
cmd = [
    "yt-dlp",
    "--cookies", COOKIES_FILE,
    "-f", "best",
    VIDEO_URL
]

try:
    print("Video indiriliyor...")
    subprocess.run(cmd, check=True)
    print("İndirme tamamlandı!")
except subprocess.CalledProcessError as e:
    print("İndirme sırasında hata oluştu:", e)
