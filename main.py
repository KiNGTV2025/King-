import json
import urllib.request
import urllib.error
import re
import os
import sys
import requests
from datetime import datetime
from base64 import b64encode
from collections import defaultdict

# Yapılandırma Ayarları
DEFAULT_BASE_URL = 'https://m.prectv50.sbs'
SOURCE_URL = 'https://raw.githubusercontent.com/kerimmkirac/cs-kerim2/main/RecTV/src/main/kotlin/com/kerimmkirac/RecTV.kt'
API_KEY = '4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452'
SUFFIX = f'/{API_KEY}'

# GitHub Ayarları
GITHUB_REPO = "KiNGTV2025/King-"
GITHUB_FILE_PATH = "qdene.json"

# Kullanıcı ayarları
USER_AGENT = 'okhttp/4.12.0'
REFERER = 'https://twitter.com/'

def is_base_url_working(base_url):
    """Base URL kontrolü"""
    test_url = f"{base_url}/api/channel/by/filtres/0/0/0{SUFFIX}"
    try:
        req = urllib.request.Request(test_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except:
        return False

def get_dynamic_base_url():
    """Dinamik base URL alımı"""
    try:
        with urllib.request.urlopen(SOURCE_URL) as response:
            content = response.read().decode('utf-8')
            if match := re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content):
                return match.group(1)
    except Exception as e:
        print(f"GitHub'dan URL alınamadı: {e}", file=sys.stderr)
    return DEFAULT_BASE_URL

def fetch_data(url):
    """API'den veri çekme"""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': USER_AGENT, 'Referer': REFERER}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"API hatası ({url}): {e}", file=sys.stderr)
        return []

def get_best_source(sources):
    """En iyi kaliteyi seçme"""
    quality_order = ['4K', '2160p', '1080p', 'HD', '720p', 'SD', '']
    best_source = None
    
    for source in sources:
        if isinstance(source, dict) and source.get('type') == 'm3u8' and source.get('url'):
            current_quality = source.get('quality', '')
            
            if not best_source:
                best_source = source
            else:
                try:
                    if quality_order.index(current_quality) < quality_order.index(best_source.get('quality', '')):
                        best_source = source
                except ValueError:
                    pass
    return best_source

def process_content(content, category_name):
    """İçerik işleme"""
    if not isinstance(content, dict) or not content.get('sources'):
        return None
    
    best_source = get_best_source(content['sources'])
    if not best_source or not content.get('title'):
        return None
        
    return {
        'id': str(content.get('id', '')),
        'title': str(content.get('title', '')).strip(),
        'image': str(content.get('image', '')),
        'group': f"ÜmitVIP~{category_name}",
        'url': str(best_source['url']),
        'quality': str(best_source.get('quality', '')),
        'unique_id': f"{content.get('id')}_{best_source['url'].split('?')[0]}"
    }

def update_github_file(json_data, github_token):
    """GitHub'a dosya yükleme"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    sha = response.json().get("sha", "") if response.status_code == 200 else ""
    
    content = json.dumps(json_data, ensure_ascii=False, indent=2)
    encoded_content = b64encode(content.encode("utf-8")).decode("utf-8")
    
    data = {
        "message": f"Otomatik güncelleme: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": encoded_content,
        "sha": sha
    }
    
    response = requests.put(url, headers=headers, json=data)
    return response.status_code in [200, 201]

def main():
    base_url = DEFAULT_BASE_URL if is_base_url_working(DEFAULT_BASE_URL) else get_dynamic_base_url()
    print(f"Kullanılan Base URL: {base_url}", file=sys.stderr)
    
    all_entries = []
    seen_ids = set()
    stats = defaultdict(int)

    # CANLI YAYINLAR (4 sayfa)
    for page in range(4):
        url = f"{base_url}/api/channel/by/filtres/0/0/{page}{SUFFIX}"
        data = fetch_data(url)
        stats['canli_sayfa'] += 1
        
        for content in data:
            entry = process_content(content, "Canlı Yayınlar")
            if entry and entry['unique_id'] not in seen_ids:
                seen_ids.add(entry['unique_id'])
                all_entries.append(entry)
                stats['canli_kayit'] += 1

    # FİLMLER (8 kategori x 5 sayfa)
    film_kategorileri = {
        "0": "Son Filmler", "14": "Aile", "1": "Aksiyon", 
        "13": "Animasyon", "19": "Belgesel", "4": "Bilim Kurgu",
        "2": "Dram", "10": "Fantastik", "3": "Komedi",
        "8": "Korku", "17": "Macera", "5": "Romantik"
    }
    
    for category_id, category_name in film_kategorileri.items():
        for page in range(5):
            url = f"{base_url}/api/movie/by/filtres/{category_id}/created/{page}{SUFFIX}"
            data = fetch_data(url)
            stats['film_sayfa'] += 1
            
            for content in data:
                entry = process_content(content, category_name)
                if entry and entry['unique_id'] not in seen_ids:
                    seen_ids.add(entry['unique_id'])
                    all_entries.append(entry)
                    stats['film_kayit'] += 1

    # DİZİLER (5 sayfa)
    for page in range(5):
        url = f"{base_url}/api/serie/by/filtres/0/created/{page}{SUFFIX}"
        data = fetch_data(url)
        stats['dizi_sayfa'] += 1
        
        for content in data:
            entry = process_content(content, "Son Diziler")
            if entry and entry['unique_id'] not in seen_ids:
                seen_ids.add(entry['unique_id'])
                all_entries.append(entry)
                stats['dizi_kayit'] += 1

    # JSON verisini oluştur
    json_data = {}
    for idx, entry in enumerate(all_entries, 1):
        json_data[f"{entry['id']}_{idx}"] = {
            "baslik": entry['title'],
            "url": entry['url'],
            "logo": entry['image'],
            "grup": entry['group'],
            "kalite": entry['quality']
        }

    # İstatistikleri yazdır
    print("\nİSTATİSTİKLER:")
    print(f"Toplam Sayfa: {stats['canli_sayfa'] + stats['film_sayfa'] + stats['dizi_sayfa']}")
    print(f"Canlı Yayınlar: {stats['canli_kayit']} kayıt")
    print(f"Filmler: {stats['film_kayit']} kayıt")
    print(f"Diziler: {stats['dizi_kayit']} kayıt")
    print(f"Toplam Benzersiz Kayıt: {len(all_entries)}")

    # GitHub'a yükle
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("GITHUB_TOKEN bulunamadı!", file=sys.stderr)
        sys.exit(1)

    if update_github_file(json_data, github_token):
        print("GitHub güncellemesi başarılı!")
    else:
        print("GitHub güncellemesi başarısız!", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
