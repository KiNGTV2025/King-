import json
import urllib.request
import urllib.error
import re
import os
import sys
import requests
from datetime import datetime
from base64 import b64encode

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
    """Base URL'nin çalışıp çalışmadığını kontrol et"""
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
    """GitHub'dan dinamik olarak Base URL'yi al"""
    try:
        with urllib.request.urlopen(SOURCE_URL) as response:
            content = response.read().decode('utf-8')
            if match := re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content):
                return match.group(1)
    except Exception as e:
        print(f"GitHub'dan URL alınamadı: {e}", file=sys.stderr)
    return DEFAULT_BASE_URL

def fetch_data(url):
    """API'den veri çek"""
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
            # API yanıtının beklenen formatta olduğunu kontrol et
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            return data
    except Exception as e:
        print(f"API hatası ({url}): {e}", file=sys.stderr)
        return None

def generate_unique_id(entry, index, category):
    """Benzersiz ID oluşturma fonksiyonu"""
    # Entry'nin dictionary olduğundan emin ol
    if not isinstance(entry, dict):
        return f"entry_{index}"
    
    base_id = str(entry.get('id', '')).strip()
    title = str(entry.get('title', '')).strip().replace(' ', '_')
    quality = str(entry.get('quality', '')).strip()
    
    # Özel karakterleri temizle
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', base_id) if base_id else ""
    clean_title = re.sub(r'[^a-zA-Z0-9_-]', '', title)
    
    if clean_id:
        return f"{category[:3]}_{clean_id}_{quality}" if quality else f"{category[:3]}_{clean_id}"
    else:
        return f"{category[:3]}_{clean_title}_{index}_{quality}" if quality else f"{category[:3]}_{clean_title}_{index}"

def process_content(content, category_name):
    """İçeriği işle ve tüm kayıtları döndür"""
    entries = []
    
    # İçeriğin beklenen formatta olduğunu kontrol et
    if not isinstance(content, dict) or not content.get('sources'):
        return entries
    
    for source in content['sources']:
        if not isinstance(source, dict):
            continue
            
        if source.get('type') == 'm3u8' and source.get('url'):
            if not all([content.get('title'), source.get('url')]):
                continue
                
            entries.append({
                'id': str(content.get('id', '')),
                'title': str(content.get('title', '')),
                'image': str(content.get('image', '')),
                'group': f"ÜmitVIP~{category_name}",
                'url': str(source['url']),
                'quality': str(source.get('quality', '')),
                'category': category_name
            })
    return entries

def update_github_file(json_data, github_token):
    """JSON dosyasını GitHub'a yükle"""
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
    # Base URL'yi belirle
    base_url = DEFAULT_BASE_URL if is_base_url_working(DEFAULT_BASE_URL) else get_dynamic_base_url()
    print(f"Kullanılan Base URL: {base_url}", file=sys.stderr)
    
    all_entries = []
    total_count = 0
    
    # CANLI YAYINLAR (0-3 arası sayfalar)
    for page in range(4):
        url = f"{base_url}/api/channel/by/filtres/0/0/{page}{SUFFIX}"
        if data := fetch_data(url):
            if isinstance(data, list):
                for content in data:
                    entries = process_content(content, "Canlı Yayınlar")
                    all_entries.extend(entries)
                    total_count += len(entries)
    
    # FİLMLER (Tüm kategoriler)
    film_kategorileri = {
        "0": "Son Filmler",
        "14": "Aile",
        "1": "Aksiyon",
        "13": "Animasyon",
        "19": "Belgesel Filmleri",
        "4": "Bilim Kurgu",
        "2": "Dram",
        "10": "Fantastik",
        "3": "Komedi",
        "8": "Korku",
        "17": "Macera",
        "5": "Romantik"
    }
    
    for category_id, category_name in film_kategorileri.items():
        for page in range(8):  # 0-7 arası sayfalar
            url = f"{base_url}/api/movie/by/filtres/{category_id}/created/{page}{SUFFIX}"
            if data := fetch_data(url):
                if isinstance(data, list):
                    for content in data:
                        entries = process_content(content, category_name)
                        all_entries.extend(entries)
                        total_count += len(entries)
    
    # DİZİLER (0-7 arası sayfalar)
    for page in range(8):
        url = f"{base_url}/api/serie/by/filtres/0/created/{page}{SUFFIX}"
        if data := fetch_data(url):
            if isinstance(data, list):
                for content in data:
                    entries = process_content(content, "Son Diziler")
                    all_entries.extend(entries)
                    total_count += len(entries)
    
    # JSON verisini oluştur
    json_data = {}
    duplicate_count = 0
    
    for idx, entry in enumerate(all_entries, 1):
        try:
            unique_id = generate_unique_id(entry, idx, entry['category'])
            
            if unique_id in json_data:
                duplicate_count += 1
                unique_id = f"{unique_id}_{duplicate_count}"
            
            json_data[unique_id] = {
                "baslik": entry['title'],
                "url": entry['url'],
                "logo": entry['image'],
                "grup": entry['group'],
                "kalite": entry['quality']
            }
        except Exception as e:
            print(f"Hatalı kayıt atlandı (index {idx}): {e}", file=sys.stderr)
            continue
    
    print(f"Toplam işlenen kayıt: {total_count}")
    print(f"Oluşturulan JSON girişi: {len(json_data)}")
    print(f"Çakışma sayısı: {duplicate_count}")
    print(f"Atlanan kayıt sayısı: {total_count - len(json_data)}")
    
    # GitHub'a yükle
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("GITHUB_TOKEN environment variable not set!", file=sys.stderr)
        sys.exit(1)
    
    if update_github_file(json_data, github_token):
        print("GitHub güncellemesi başarılı!")
    else:
        print("GitHub güncellemesi başarısız!", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
