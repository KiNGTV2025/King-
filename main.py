import json
import urllib.request
import urllib.error
import re
import sys
import requests
from datetime import datetime, timezone, timedelta
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
    test_url = f"{base_url}/api/channel/by/filtres/0/0/0{SUFFIX}"
    try:
        req = urllib.request.Request(test_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except:
        return False

def get_dynamic_base_url():
    try:
        with urllib.request.urlopen(SOURCE_URL) as response:
            content = response.read().decode('utf-8')
            if match := re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content):
                return match.group(1)
    except Exception as e:
        print(f"GitHub'dan URL alınamadı: {e}", file=sys.stderr)
    return DEFAULT_BASE_URL

def fetch_data(url):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': USER_AGENT, 'Referer': REFERER}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"API hatası ({url}): {e}", file=sys.stderr)
        return None

def process_content(content, category_name):
    entries = []
    if not content.get('sources'):
        return entries
    
    for source in content['sources']:
        if source.get('type') == 'm3u8' and source.get('url'):
            entries.append({
                'id': content.get('id', ''),
                'title': content.get('title', ''),
                'image': content.get('image', ''),
                'group': f"ÜmitVIP~{category_name}",
                'url': source['url'],
                'quality': source.get('quality', '')
            })
    return entries

def generate_m3u_content(entries):
    m3u_lines = ['#EXTM3U']
    for entry in entries:
        quality_str = f" [{entry['quality']}]" if entry['quality'] and entry['quality'].lower() != "none" else ""
        m3u_lines.extend([
            f'#EXTINF:-1 tvg-id="{entry["id"]}" tvg-name="{entry["title"]}" '
            f'tvg-logo="{entry["image"]}" group-title="{entry["group"]}", {entry["title"]}{quality_str}',
            f'#EXTVLCOPT:http-user-agent={USER_AGENT}',
            f'#EXTVLCOPT:http-referrer={REFERER}',
            entry['url']
        )
    return m3u_lines

def update_github_file(json_data, github_token):
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
    
    # CANLI YAYINLAR
    for page in range(4):
        url = f"{base_url}/api/channel/by/filtres/0/0/{page}{SUFFIX}"
        if data := fetch_data(url):
            for content in data:
                all_entries.extend(process_content(content, "Canlı Yayınlar"))
    
    # FİLMLER
    film_kategorileri = {
        "0": "Son Filmler", "14": "Aile", "1": "Aksiyon", "13": "Animasyon",
        "19": "Belgesel Filmleri", "4": "Bilim Kurgu", "2": "Dram",
        "10": "Fantastik", "3": "Komedi", "8": "Korku", "17": "Macera", "5": "Romantik"
    }
    
    for category_id, category_name in film_kategorileri.items():
        for page in range(8):
            url = f"{base_url}/api/movie/by/filtres/{category_id}/created/{page}{SUFFIX}"
            if data := fetch_data(url):
                for content in data:
                    all_entries.extend(process_content(content, category_name))
    
    # DİZİLER
    for page in range(8):
        url = f"{base_url}/api/serie/by/filtres/0/created/{page}{SUFFIX}"
        if data := fetch_data(url):
            for content in data:
                all_entries.extend(process_content(content, "Son Diziler"))
    
    # JSON verisini oluştur
    json_data = {
        entry['id'] if entry['id'] else entry['title']: {
            "baslik": entry['title'],
            "url": entry['url'],
            "logo": entry['image'],
            "grup": entry['group']
        } for entry in all_entries
    }
    
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
