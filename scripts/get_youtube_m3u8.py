#!/usr/bin/env python3
import requests
import re
import json
import os
import subprocess
import time
from urllib.parse import parse_qs, urlparse, unquote

def get_youtube_m3u8_yt_dlp(video_url):
    """
    yt-dlp kullanarak YouTube M3U8 URL'sini al
    """
    try:
        print("yt-dlp ile M3U8 URL'si alınıyor...")
        
        # yt-dlp komutunu çalıştır
        cmd = [
            'yt-dlp',
            '-g',
            '--format', 'best',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            m3u8_url = result.stdout.strip()
            if m3u8_url and 'm3u8' in m3u8_url:
                print(f"yt-dlp M3U8 URL: {m3u8_url}")
                return m3u8_url
        
        print("yt-dlp ile M3U8 bulunamadı, alternatif yöntem deneniyor...")
        return None
        
    except subprocess.TimeoutExpired:
        print("yt-dlp timeout oldu")
        return None
    except Exception as e:
        print(f"yt-dlp hatası: {e}")
        return None

def get_youtube_m3u8_direct(video_url):
    """
    Direct YouTube API çağrısı ile M3U8 al
    """
    try:
        # Video ID'yi al
        video_id = parse_qs(urlparse(video_url).query).get('v', [''])[0]
        if not video_id:
            return None
            
        print(f"Video ID: {video_id}")
        
        # YouTube embed sayfası
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        # Embed sayfasını al
        response = session.get(embed_url, timeout=10)
        response.raise_for_status()
        
        # Player config'ini ara
        patterns = [
            r'\"hlsManifestUrl\"\s*:\s*\"([^\"]+)\"',
            r'hlsManifestUrl["\']?\s*:\s*["\']([^"\']+)["\']',
            r'\"liveManifestUrl\"\s*:\s*\"([^\"]+)\"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response.text)
            for match in matches:
                m3u8_url = match.replace('\\u0026', '&')
                if 'm3u8' in m3u8_url:
                    print(f"Direct M3U8 URL bulundu: {m3u8_url}")
                    return m3u8_url
        
        return None
        
    except Exception as e:
        print(f"Direct method hatası: {e}")
        return None

def create_fallback_m3u8():
    """
    Fallback M3U8 dosyası oluştur
    """
    fallback_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:1
#EXT-X-TARGETDURATION:10
#EXT-X-PLAYLIST-TYPE:EVENT
#EXTINF:10.0,
https://example.com/segment1.ts
#EXTINF:10.0,
https://example.com/segment2.ts
#EXT-X-ENDLIST"""
    
    return fallback_content

def update_master_playlist():
    """
    Ana master playlist'i güncelle
    """
    master_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-INDEPENDENT-SEGMENTS

#EXT-X-STREAM-INF:BANDWIDTH=290288,CODECS="mp4a.40.5,avc1.42C00B",RESOLUTION=256x144,FRAME-RATE=15,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/streams/144p.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=546239,CODECS="mp4a.40.5,avc1.4D4015",RESOLUTION=426x240,FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/streams/240p.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=1209862,CODECS="mp4a.40.2,avc1.4D401E",RESOLUTION=640x360,FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/streams/360p.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=1568726,CODECS="mp4a.40.2,avc1.4D401F",RESOLUTION=854x480,FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/streams/480p.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=2969452,CODECS="mp4a.40.2,avc1.4D401F",RESOLUTION=1280x720,FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/streams/720p.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=5420722,CODECS="mp4a.40.2,avc1.640028",RESOLUTION=1920x1080,FRAME-RATE=30,VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE
https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/streams/1080p.m3u8"""
    
    return master_content

def main():
    YOUTUBE_URL = "https://www.youtube.com/watch?v=ztmY_cCtUl0"
    
    print("YouTube M3U8 çekiliyor...")
    
    # Önce yt-dlp ile dene
    m3u8_url = get_youtube_m3u8_yt_dlp(YOUTUBE_URL)
    
    # Başarısız olursa direct method ile dene
    if not m3u8_url:
        print("Direct method deneniyor...")
        m3u8_url = get_youtube_m3u8_direct(YOUTUBE_URL)
    
    # streams klasörünü oluştur
    os.makedirs('streams', exist_ok=True)
    os.makedirs('playlist', exist_ok=True)
    
    if m3u8_url:
        print(f"M3U8 URL bulundu: {m3u8_url}")
        
        try:
            # M3U8 içeriğini al
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
            }
            
            response = requests.get(m3u8_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            m3u8_content = response.text
            
            # Tüm çözünürlükler için aynı M3U8'i kaydet
            resolutions = ['144p', '240p', '360p', '480p', '720p', '1080p']
            for res in resolutions:
                with open(f'streams/{res}.m3u8', 'w', encoding='utf-8') as f:
                    f.write(m3u8_content)
            
            print("Tüm stream dosyaları güncellendi!")
            
        except Exception as e:
            print(f"M3U8 içeriği alınamadı: {e}")
            # Fallback oluştur
            fallback_content = create_fallback_m3u8()
            resolutions = ['144p', '240p', '360p', '480p', '720p', '1080p']
            for res in resolutions:
                with open(f'streams/{res}.m3u8', 'w', encoding='utf-8') as f:
                    f.write(fallback_content)
            print("Fallback M3U8 dosyaları oluşturuldu")
    
    else:
        print("M3U8 URL bulunamadı, fallback dosyalar oluşturuluyor...")
        fallback_content = create_fallback_m3u8()
        resolutions = ['144p', '240p', '360p', '480p', '720p', '1080p']
        for res in resolutions:
            with open(f'streams/{res}.m3u8', 'w', encoding='utf-8') as f:
                f.write(fallback_content)
    
    # Master playlist'i güncelle
    master_content = update_master_playlist()
    with open('playlist/sozcu_tv.m3u8', 'w', encoding='utf-8') as f:
        f.write(master_content)
    
    print("Master playlist güncellendi!")
    print("İşlem tamamlandı!")

if __name__ == "__main__":
    main()
