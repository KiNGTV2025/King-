import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
from datetime import datetime

OUTPUT_DIR = "."
OUTPUT_FILE = "kanald_playlist.m3u"
CACHE_FILE = "kanald_cache.json"

BASE_URL = "https://www.kanald.com.tr"
ARCHIVE_URL = "https://www.kanald.com.tr/diziler/arsiv?page="

# Cloudflare Worker URL'in
WORKER_URL = "https://mak.sadecenjoy.workers.dev"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"episodes": {}}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_real_m3u8(scraper, bolum_url, cache):
    """Worker üzerinden M3U8 linkini çek"""
    if bolum_url in cache.get("episodes", {}):
        return cache["episodes"][bolum_url]

    try:
        r1 = scraper.get(bolum_url, timeout=10)
        embed_match = re.search(r'<link[^>]+itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        
        if not embed_match:
            for pattern in [r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', r'data-url=["\']([^"\']+\.m3u8[^"\']*)["\']']:
                m = re.search(pattern, r1.text)
                if m:
                    url = m.group(1).replace('\\/', '/')
                    cache.setdefault("episodes", {})[bolum_url] = url
                    return url
            cache.setdefault("episodes", {})[bolum_url] = bolum_url
            return bolum_url
            
        embed_url = embed_match.group(1)
        print(f"      🔗 Embed: {embed_url[:60]}...")
        
        worker_req_url = f"{WORKER_URL}/?url={embed_url}"
        r2 = scraper.get(worker_req_url, timeout=15)
        
        if r2.status_code == 200:
            embed_html = r2.text
            m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', embed_html)
            if m3u8_match:
                url = m3u8_match.group(0).replace('\\/', '/')
                cache.setdefault("episodes", {})[bolum_url] = url
                return url
        
        final_url = r2.url if r2.url != worker_req_url else embed_url
        cache.setdefault("episodes", {})[bolum_url] = final_url
        return final_url
        
    except Exception as e:
        print(f"      ⚠️ Worker hatası: {e}")
        cache.setdefault("episodes", {})[bolum_url] = bolum_url
        return bolum_url

def fetch_all_episodes(scraper, series_url):
    """Bir dizinin TÜM bölümlerini çek - dropdown + sayfadaki linkler + sayfalama"""
    episodes = []
    bolum_url = series_url.rstrip('/') + "/bolumler"
    seen = set()

    try:
        # 1. Ana bölümler sayfasını tara
        def parse_page(url):
            r = scraper.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')

            # Dropdown
            select_box = soup.find('select', id='video-finder-changer')
            if select_box:
                for opt in select_box.find_all('option', {'data-target': True}):
                    name = opt.get_text(strip=True)
                    target = opt['data-target']
                    if target not in seen:
                        seen.add(target)
                        episodes.append({'name': name, 'url': target})

            # Sayfadaki tüm bölüm linkleri
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if '/bolum/' not in href:
                    continue

                name = a.get_text(strip=True)
                if not name or len(name) < 3:
                    title_tag = a.select_one('.title, h3, h2, .name, .caption')
                    if title_tag:
                        name = title_tag.get_text(strip=True)
                    else:
                        match = re.search(r'/(\d+)-bolum', href)
                        if match:
                            name = f"{match.group(1)}. Bölüm"

                if not name or len(name) < 2:
                    continue

                if href.startswith('/'):
                    full_url = BASE_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = bolum_url.rstrip('/') + '/' + href.lstrip('/')

                if full_url not in seen:
                    seen.add(full_url)
                    episodes.append({'name': name, 'url': full_url})

            # Sayfalama varsa sonraki sayfaları tara
            pagination = soup.select('.pagination a, .page-numbers a, a[href*="/bolumler/"]')
            next_urls = []
            for p in pagination:
                phref = p.get('href', '')
                if phref and '/bolumler/' in phref and phref not in seen:
                    if phref.startswith('/'):
                        next_urls.append(BASE_URL + phref)
                    else:
                        next_urls.append(phref)

            return next_urls

        # İlk sayfayı tara
        next_pages = parse_page(bolum_url)

        # Varsa sonraki sayfaları tara (max 5 sayfa)
        for next_url in next_pages[:5]:
            if next_url not in seen:
                seen.add(next_url)
                more_pages = parse_page(next_url)

        # Sırala
        def extract_num(ep):
            match = re.search(r'(\d+)', ep['name'])
            return int(match.group(1)) if match else 0

        episodes.sort(key=extract_num)
        print(f"      📑 {len(episodes)} bölüm bulundu")
        return episodes

    except Exception as e:
        print(f"      ⚠️ Bölüm hatası: {e}")
        return []

def run_scraper():
    print("🚀 Kanal D M3U (Worker Proxy)")
    print("=" * 60)
    
    cache = load_cache()
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    m3u_entries = []
    total_series = 0
    total_episodes = 0
    new_episodes = 0
    
    for page in range(1, 11):
        print(f"📄 Sayfa {page}/10")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.select('a.poster-card')
            
            if not cards:
                break
            
            print(f"  {len(cards)} dizi")
            
            for idx, card in enumerate(cards, 1):
                title = card.get('title') or (card.find('img') or {}).get('alt', 'Dizi')
                href = card.get('href')
                
                if not title or not href:
                    continue
                
                print(f"  [{idx}/{len(cards)}] {title}")
                full_url = BASE_URL + href if href.startswith('/') else href
                
                img = card.find('img')
                poster = img.get('data-src') or img.get('src', '') if img else ''
                
                try:
                    # YENİ: fetch_all_episodes kullan
                    episodes = fetch_all_episodes(scraper, full_url)
                    
                    if not episodes:
                        continue
                    
                    for ep in episodes:
                        if ep['url'] in cache.get("episodes", {}):
                            m3u8_link = cache["episodes"][ep['url']]
                        else:
                            m3u8_link = get_real_m3u8(scraper, ep['url'], cache)
                            new_episodes += 1
                        
                        m3u_entries.append({
                            'dizi_adi': title,
                            'bolum_adi': ep['name'],
                            'video_url': m3u8_link,
                            'poster_url': poster,
                            'group': 'Kanal D'
                        })
                        total_episodes += 1
                    
                    total_series += 1
                    print(f"    ✅ {len(episodes)} bölüm")
                        
                except Exception as e:
                    print(f"    ❌ {str(e)[:50]}")
                
                time.sleep(0.2)
                    
        except Exception as e:
            continue
    
    save_cache(cache)
    print(f"\n📊 {total_series} dizi, {total_episodes} bölüm ({new_episodes} yeni)")
    
    if m3u_entries:
        create_m3u(m3u_entries, total_series, total_episodes)

def create_m3u(entries, total_series, total_episodes):
    today = datetime.now().strftime("%d.%m.%Y %H:%M")
    content = '#EXTM3U\n'
    content += f'#PLAYLIST: Kanal D - {today}\n'
    content += f'# {total_series} dizi, {total_episodes} bölüm\n\n'
    
    groups = {}
    for e in entries:
        groups.setdefault(e['dizi_adi'], []).append(e)
    
    for dizi_adi, eps in sorted(groups.items()):
        eps.sort(key=lambda x: int(re.search(r'(\d+)', x['bolum_adi']).group(1)) if re.search(r'(\d+)', x['bolum_adi']) else 0, reverse=True)
        poster = eps[0]['poster_url']
        for ep in eps:
            content += f'#EXTINF:-1 tvg-logo="{poster}" group-title="Kanal D",{dizi_adi} - {ep["bolum_adi"]}\n'
            content += f'{ep["video_url"]}\n\n'
    
    path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {OUTPUT_FILE} ({os.path.getsize(path):,} bytes)")

if __name__ == "__main__":
    run_scraper()
