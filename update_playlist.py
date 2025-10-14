import subprocess
import datetime
import os

YOUTUBE_URL = "https://www.youtube.com/live/ztmY_cCtUl0"
OUTPUT_FILE = "playlist/Sozcu_Tv.m3u8"
FORMAT_ID = "96"  # En yüksek kalite
COOKIES_FILE = "cookies.txt"

try:
    result = subprocess.run(
        ["yt-dlp", "-f", FORMAT_ID, "--cookies", COOKIES_FILE, "-g", YOUTUBE_URL],
        capture_output=True, text=True, check=True
    )
    stream_url = result.stdout.strip()
except subprocess.CalledProcessError as e:
    print("Hata: yt-dlp ile link alınamadı")
    print(e.stderr)
    stream_url = ""

if stream_url:
    m3u8_content = f"""#EXTM3U
#EXT-X-INDEPENDENT-SEGMENTS
#EXT-X-STREAM-INF:BANDWIDTH=5421000,CODECS="mp4a.40.2,avc1.640028",RESOLUTION=1920x1080,FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
{stream_url}
# Generated: {datetime.datetime.utcnow().isoformat()} UTC
"""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write(m3u8_content)
    print(f"M3U8 dosyası güncellendi: {OUTPUT_FILE}")
else:
    print("Stream URL alınamadı, M3U8 güncellenmedi.")
