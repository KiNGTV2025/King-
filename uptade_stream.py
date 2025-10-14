import subprocess
import os
from datetime import datetime

YOUTUBE_URL = "https://www.youtube.com/watch?v=ztmY_cCtUl0"
OUTPUT_FILE = "playlist/playlist.m3u8"

def get_stream_url():
    try:
        # yt-dlp ile en iyi kaliteyi al
        result = subprocess.run(
            ["yt-dlp", "-g", "-f", "best", YOUTUBE_URL],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("Hata: yt-dlp çalıştırılamadı:", e)
        return None

def update_m3u8(url):
    content = f"#EXTM3U\n#EXTINF:-1,Live Stream (Updated at {datetime.utcnow()} UTC)\n{url}\n"
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{OUTPUT_FILE} güncellendi.")

def main():
    url = get_stream_url()
    if url:
        update_m3u8(url)
    else:
        print("Yeni URL alınamadı.")

if __name__ == "__main__":
    main()
