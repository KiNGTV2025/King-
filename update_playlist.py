import subprocess
import datetime
import os

# YouTube canlı yayını URL
YOUTUBE_URL = "https://www.youtube.com/live/ztmY_cCtUl0"

# Secret olarak workflow'dan gelen cookie dosyası yolu
COOKIES_FILE = os.environ.get("YOUTUBE_COOKIES")  # örn: /home/runner/cookies.txt

# Çıkacak playlist dosyası
OUTPUT_FILE = "Sozcu_Tv.m3u8"

def get_stream(itag):
    """Belirtilen itag için akış URL'sini döndürür"""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-g",
                "-f", str(itag),
                "--cookies", COOKIES_FILE,
                "--add-header", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "--add-header", "Referer: https://www.youtube.com",
                YOUTUBE_URL
            ],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Itag {itag} için akış bulunamadı: {e}")
        return None

# Yaygın YouTube canlı yayını itag'ları ve çözünürlükler
itag_map = {
    91: "256x144",
    92: "426x240",
    93: "640x360",
    94: "854x480",
    95: "1280x720",
    96: "1920x1080"
}

lines = ["#EXTM3U", "#EXT-X-INDEPENDENT-SEGMENTS"]

for itag, res in itag_map.items():
    url = get_stream(itag)
    if url:
        lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH=1000000,CODECS="mp4a.40.2,avc1.4D401F",RESOLUTION={res},FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE')
        lines.append(url)

lines.append(f"# Generated: {datetime.datetime.utcnow().isoformat()} UTC")

# Klasör yoksa oluştur
os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)

# Dosyayı yaz
with open(OUTPUT_FILE, "w") as f:
    f.write("\n".join(lines))

print("✅ Sözcü TV playlist güncellendi:", OUTPUT_FILE)
