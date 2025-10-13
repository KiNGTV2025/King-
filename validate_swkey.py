import requests, time, os

API_BASE = "https://m.prectv60.lol"
FILE_PATH = "playwright_capture/found_swkeys.txt"
OUT_FILE = "playwright_capture/found_swkeys_valid.txt"

os.makedirs("playwright_capture", exist_ok=True)

if not os.path.exists(FILE_PATH):
    print(f"[!] {FILE_PATH} bulunamadı.")
    exit(1)

with open(FILE_PATH, "r", encoding="utf-8") as f:
    keys = [line.strip() for line in f if line.strip()]

print(f"[i] {len(keys)} anahtar bulundu, doğrulama başlıyor...")

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Referer": "https://twitter.com/",
}

valid = []

for key in keys:
    url = f"{API_BASE}/api/movie/by/filtres/0/created/0/{key}/"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"[*] {key[:8]}... → {r.status_code}")
        if r.status_code == 200 and '"title"' in r.text:
            print(f"[+] Geçerli key bulundu → {key}")
            valid.append(key)
            # Birden fazla geçerli olursa, hepsini ekleyelim
        elif r.status_code == 401:
            print(f"[-] 401 Unauthorized")
        time.sleep(2)  # istekler arasında kısa bekleme
    except Exception as e:
        print(f"[!] {key[:8]}... hata: {e}")

if valid:
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(valid))
    print(f"[✓] {len(valid)} geçerli anahtar bulundu, kaydedildi → {OUT_FILE}")
else:
    print("[x] Hiç geçerli anahtar bulunamadı.")
