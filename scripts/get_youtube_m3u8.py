#!/usr/bin/env python3
import requests
import re
import json
import os
from urllib.parse import parse_qs, urlparse

def get_youtube_m3u8(video_url):
    """
    YouTube video URL'sinden M3U8 playlist'ini çeker
    """
    try:
        # YouTube'dan video sayfasını al
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(video_url, headers=headers)
        response.raise_for_status()
        
        # YouTube player config'ini bul
        patterns = [
            r'var ytInitialPlayerResponse\s*=\s*({.+?});',
            r'ytInitialPlayerResponse\s*=\s*({.+?});',
            r'window\["ytInitialPlayerResponse"\]\s*=\s*({.+?});'
        ]
        
        player_response = None
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                player_response = json.loads(match.group(1))
                break
        
        if not player_response:
            raise Exception("YouTube player response bulunamadı")
        
        # Streaming data'yı kontrol et
        streaming_data = player_response.get('streamingData', {})
        hls_url = streaming_data.get('hlsManifestUrl')
        
        if not hls_url:
            # Formatları kontrol et
            formats = streaming_data.get('formats', [])
            adaptive_formats = streaming_data.get('adaptiveFormats', [])
            
            if not formats and not adaptive_formats:
                raise Exception("Streaming data bulunamadı")
            
            # M3U8 URL'si oluştur
            video_id = parse_qs(urlparse(video_url).query).get('v', [''])[0]
            if video_id:
                hls_url = f"https://www.youtube.com/watch?v={video_id}"
        
        return hls_url
        
    except Exception as e:
        print(f"Hata: {e}")
        return None

def extract_m3u8_from_url(hls_url):
    """
    HLS URL'sinden M3U8 içeriğini al
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(hls_url, headers=headers)
        response.raise_for_status()
        
        return response.text
    except Exception as e:
        print(f"M3U8 çekme hatası: {e}")
        return None

def main():
    YOUTUBE_URL = "https://www.youtube.com/watch?v=ztmY_cCtUl0"
    
    print("YouTube M3U8 çekiliyor...")
    m3u8_url = get_youtube_m3u8(YOUTUBE_URL)
    
    if m3u8_url:
        print(f"M3U8 URL bulundu: {m3u8_url}")
        
        # M3U8 içeriğini al
        m3u8_content = extract_m3u8_from_url(m3u8_url)
        
        if m3u8_content:
            # streams klasörünü oluştur
            os.makedirs('streams', exist_ok=True)
            
            # Ana M3U8 dosyasını kaydet
            with open('streams/master.m3u8', 'w', encoding='utf-8') as f:
                f.write(m3u8_content)
            
            print("M3U8 dosyası güncellendi!")
        else:
            print("M3U8 içeriği alınamadı")
    else:
        print("M3U8 URL bulunamadı")

if __name__ == "__main__":
    main()
