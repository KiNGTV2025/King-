import requests
import re
import os

# M3U dosya yolu
M3U_PATH = "1UmitTV.m3u"

# Proxy veya domain bilgisi (GitHub raw URL’den çekilebilir)
DOMAIN_RAW_URL = "https://raw.githubusercontent.com/KiNGTV2025/King-/main/domian.txt"
REFERER = "https://dengetv66.live/"

# Dengetv54 grubu için örnek grup ismi
GROUP_TITLE = "Dengetv54"

# .m3u dosyası için User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"

# --- Yardımcı Fonksiyonlar ---

def get_domain():
    try:
        resp = requests.get(DOMAIN_RAW_URL, timeout=10)
        resp.raise_for_status()
        domain = resp.text.strip()
        if not domain.startswith("http"):
            domain = "https://" + domain
        return domain
    except Exception as e:
        print(f"❌ Domain alınamadı: {e}")
        return None

def fetch_channels():
    url = "https://sportsobama.com/channels.php"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": REFERER
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.text

def extract_m3u_links(html_content):
    # Basit regex ile .m3u8 linklerini çek
    links = re.findall(r'(https?://[^\s"\']+\.m3u8)', html_content)
    return list(dict.fromkeys(links))  # tekrarları sil

def generate_m3u(links):
    m3u_lines = ["#EXTM3U"]
    for idx, link in enumerate(links, start=1):
        name = f"Channel {idx}"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{idx}" tvg-name="{name}" group-title="{GROUP_TITLE}",{name}')
        m3u_lines.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT}')
        m3u_lines.append(f'#EXTVLCOPT:http-referer={REFERER}')
        m3u_lines.append(link)
        m3u_lines.append("")  # boş satır
    return "\n".join(m3u_lines)

def save_m3u(content):
    with open(M3U_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {M3U_PATH} oluşturuldu! Toplam kanal sayısı: {content.count('#EXTINF')}")

# --- Ana Script ---
def main():
    domain = get_domain()
    if not domain:
        print("❌ Domain alınamadı, script durdu.")
        return
    
    try:
        html = fetch_channels()
        links = extract_m3u_links(html)
        if not links:
            print("❌ Hiçbir .m3u8 linki bulunamadı.")
            return
        m3u_content = generate_m3u(links)
        save_m3u(m3u_content)
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()
