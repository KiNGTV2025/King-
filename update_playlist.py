# update_playlist.py
import subprocess
import datetime
import os

# YouTube canlı yayının URL'si
YOUTUBE_URL = "https://www.youtube.com/live/ztmY_cCtUl0"

# Hedef M3U8 dosyası (repo içindeki playlist klasörü)
OUTPUT_FILE = "playlist/Sozcu_Tv.m3u8"

# yt-dlp ile HLS linkini al
try:
    result = subprocess.run(
        ["yt-dlp", "-f", "best", "-g", YOUTUBE_URL],
        capture_output=True, text=True, check=True
    )
    stream_url = result.stdout.strip()
except subprocess.CalledProcessError as e:
    print("Hata: yt-dlp ile link alınamadı")
    print(e.output)
    stream_url = ""

if stream_url:
    # M3U8 içeriğini oluştur
    m3u8_content = f"""#EXTM3U
#EXT-X-INDEPENDENT-SEGMENTS
#EXT-X-STREAM-INF:BANDWIDTH=1000000,CODECS="mp4a.40.2,avc1.4D401F",RESOLUTION=1280x720,FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
{stream_url}
# Generated: {datetime.datetime.utcnow().isoformat()} UTC
"""

    # Klasör yoksa oluştur
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Dosyaya yaz
    with open(OUTPUT_FILE, "w") as f:
        f.write(m3u8_content)

    print(f"M3U8 dosyası güncellendi: {OUTPUT_FILE}")
else:
    print("Stream URL alınamadı, M3U8 güncellenmedi.")
