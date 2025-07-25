import json
import urllib.request
import urllib.error
import re
import sys

# Sabit tanımlamalar
VARSayılan_URL = 'https://m.prectv50.sbs'  # Varsayılan API adresi
KAYNAK_URL = 'https://raw.githubusercontent.com/kerimmkirac/cs-kerim2/main/RecTV/src/main/kotlin/com/kerimmkirac/RecTV.kt'  # Yedek URL kaynağı
API_ANAHTARI = '4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452'  # API erişim anahtarı
SON_EK = f'/{API_ANAHTARI}'  # API isteklerine eklenecek son ek
KULLANICI_AGENTI = 'googleusercontent'  # Kullanıcı kimliği
REFERANS = 'https://twitter.com/'  # Referans adres

def url_calisiyor_mu(base_url: str) -> bool:
    """Verilen URL'nin çalışıp çalışmadığını kontrol eder"""
    try:
        istek = urllib.request.Request(
            f"{base_url}/api/channel/by/filtres/0/0/0{SON_EK}",
            headers={'User-Agent': 'okhttp/4.12.0'}
        )
        with urllib.request.urlopen(istek, timeout=10) as yanit:
            return yanit.status == 200
    except:
        return False

def dinamik_url_al() -> str:
    """Yedek kaynaktan güncel URL'yi almaya çalışır"""
    try:
        with urllib.request.urlopen(KAYNAK_URL) as yanit:
            icerik = yanit.read().decode('utf-8')
            eslesme = re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', icerik)
            if eslesme:
                return eslesme.group(1)
    except:
        pass
    return VARSayılan_URL

def veri_cek(url: str):
    """Belirtilen URL'den JSON verisi çeker"""
    try:
        istek = urllib.request.Request(
            url,
            headers={'User-Agent': KULLANICI_AGENTI, 'Referer': REFERANS}
        )
        with urllib.request.urlopen(istek, timeout=15) as yanit:
            return json.loads(yanit.read().decode('utf-8'))
    except Exception as hata:
        print(f"API hatası ({url}): {hata}", file=sys.stderr)
        return None

def tum_verileri_topla():
    """Tüm verileri toplar ve kategorilere ayırır"""
    base_url = VARSayılan_URL if url_calisiyor_mu(VARSayılan_URL) else dinamik_url_al()
    print(f"Kullanılan Base URL: {base_url}", file=sys.stderr)

    tum_veri = {"canli": [], "filmler": [], "diziler": []}

    # Canlı yayın verileri (4 sayfa)
    for sayfa in range(4):
        url = f"{base_url}/api/channel/by/filtres/0/0/{sayfa}{SON_EK}"
        veri = veri_cek(url)
        if veri:
            tum_veri["canli"].extend(veri)

    # Film kategorileri
    film_kategorileri = {
        "0": "Son Filmler", "14": "Aile", "1": "Aksiyon", "13": "Animasyon",
        "19": "Belgesel", "4": "Bilim Kurgu", "2": "Dram", "10": "Fantastik",
        "3": "Komedi", "8": "Korku", "17": "Macera", "5": "Romantik"
    }

    # Film verileri (her kategori için 8 sayfa)
    for kategori_id in film_kategorileri:
        for sayfa in range(8):
            url = f"{base_url}/api/movie/by/filtres/{kategori_id}/created/{sayfa}{SON_EK}"
            veri = veri_cek(url)
            if veri:
                tum_veri["filmler"].extend(veri)

    # Dizi verileri (8 sayfa)
    for sayfa in range(8):
        url = f"{base_url}/api/serie/by/filtres/0/created/{sayfa}{SON_EK}"
        veri = veri_cek(url)
        if veri:
            tum_veri["diziler"].extend(veri)

    return tum_veri

def main():
    """Ana işlem fonksiyonu"""
    veri = tum_verileri_topla()
    with open("recTV_verileri.json", "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, indent=2, ensure_ascii=False)
    print("Veriler başarıyla kaydedildi!")

if __name__ == "__main__":
    main()
