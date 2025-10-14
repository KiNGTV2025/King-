import os
import subprocess

# YouTube canlı yayını URL’si
url = "https://www.youtube.com/watch?v=ztmY_cCtUl0"

try:
    # HLS manifest URL’si al
    hls_url = subprocess.check_output(
        ["yt-dlp", "-g", url], text=True
    ).strip()
except subprocess.CalledProcessError:
    print("Yeni URL alınamadı.")
    exit(1)

# playlist dizini yoksa oluştur
os.makedirs("playlist", exist_ok=True)

# playlist.m3u8 dosyasına yaz
playlist_file = "playlist/playlist.m3u8"
with open(playlist_file, "w") as f:
    f.write(f"#EXTM3U\n{hls_url}\n")

print("playlist.m3u8 oluşturuldu:", playlist_file)
