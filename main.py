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
        req = urllib.request.Request(
            test_url,
            headers={'User-Agent': USER_AGENT}
        )
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
            headers={
                'User-Agent': USER_AGENT,
                'Referer': REFERER
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"API hatası ({url}): {e}", file=sys.stderr)
        return []

def process_content(content, category_name):
    """İçerik işleme - tüm kaynakları koruyan versiyon"""
    if not isinstance(content, dict):
        return None
        
    title = str(content.get('title', '')).strip()
    if not title:
        return None
        
    sources = []
    for src in content.get('sources', []):
        if isinstance(src, dict) and src.get('type') == 'm3u8' and src.get('url'):
            sources.append({
                'url': str(src['url']),
                'quality': str(src.get('quality', ''))
            })
    
    if not sources:
        return None
        
    return {
        'id': str(content.get('id', '')),
        'title': title,
        'image': str(content.get('image', '')),
        'group': f"ÜmitVIP~{category_name}",
        'sources': sources
    }

def update_github_file(json_data, github_token):
    """GitHub'a dosya yükleme"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Mevcut dosyayı al
    response = requests.get(url, headers=headers)
    sha = response.json().get("sha", "") if response.status_code == 200 else ""
    
    # Yeni içerik
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
    print(f"Kullanılan Base URL: {base_url}")
    
    all_entries = []
    stats = {
        'total_pages': 0,
        'total_items': 0,
        'skipped': 0,
        'categories': defaultdict(int),
        'sources_count': defaultdict(int)
    }

    # CANLI YAYINLAR (4 sayfa)
    for page in range(4):
        url = f"{base_url}/api/channel/by/filtres/0/0/{page}{SUFFIX}"
        data = fetch_data(url)
        stats['total_pages'] += 1
        
        for content in data:
            entry = process_content(content, "Canlı Yayınlar")
            if entry:
                all_entries.append(entry)
                stats['categories']['canli'] += 1
                stats['sources_count'][len(entry['sources'])] += 1
            else:
                stats['skipped'] += 1

    # FİLMLER (12 kategori x 5 sayfa)
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
            stats['total_pages'] += 1
            
            for content in data:
                entry = process_content(content, category_name)
                if entry:
                    all_entries.append(entry)
                    stats['categories'][category_name] += 1
                    stats['sources_count'][len(entry['sources'])] += 1
                else:
                    stats['skipped'] += 1

    # DİZİLER (5 sayfa)
    for page in range(5):
        url = f"{base_url}/api/serie/by/filtres/0/created/{page}{SUFFIX}"
        data = fetch_data(url)
        stats['total_pages'] += 1
        
        for content in data:
            entry = process_content(content, "Son Diziler")
            if entry:
                all_entries.append(entry)
                stats['categories']['diziler'] += 1
                stats['sources_count'][len(entry['sources'])] += 1
            else:
                stats['skipped'] += 1

    # JSON verisini oluştur
    json_data = {}
    entry_count = 0
    
    for entry in all_entries:
        # Ana kaydı oluştur (ilk kaynak)
        main_id = entry['id'] or f"entry_{entry_count}"
        json_data[main_id] = {
            "baslik": entry['title'],
            "url": entry['sources'][0]['url'],
            "logo": entry['image'],
            "grup": entry['group'],
            "kalite": entry['sources'][0]['quality']
        }
        entry_count += 1
        
        # Eğer birden fazla kaynak varsa ek kayıtlar oluştur
        if len(entry['sources']) > 1:
            for i, source in enumerate(entry['sources'][1:], 1):
                json_data[f"{main_id}_alt{i}"] = {
                    "baslik": f"{entry['title']} ({source['quality']})" if source['quality'] else entry['title'],
                    "url": source['url'],
                    "logo": entry['image'],
                    "grup": entry['group'],
                    "kalite": source['quality']
                }

    # İstatistikleri yazdır
    print("\nDETAYLI İSTATİSTİKLER:")
    print(f"Toplam Sayfa: {stats['total_pages']}")
    print(f"İşlenen Öğe: {len(all_entries)}")
    print(f"Atlanan Öğe: {stats['skipped']}")
    print("Kategori Dağılımı:")
    for cat, count in stats['categories'].items():
        print(f"- {cat}: {count}")
    print("Kaynak Sayıları:")
    for count, freq in sorted(stats['sources_count'].items()):
        print(f"- {count} kaynaklı: {freq} öğe")
    print(f"Toplam JSON Kaydı: {len(json_data)}")

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
