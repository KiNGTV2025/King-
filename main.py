from httpx import Client, Timeout
import re
import os
import json
from datetime import datetime

class DomainAutoUpdater:
    def __init__(self):
        self.http = Client(
            timeout=Timeout(20.0),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://dengetv67.live/'
            },
            follow_redirects=True
        )
        
        self.known_bases = [
            "https://galaxy.zirvedesin26.sbs/",
            "https://galaxy.dengesiz26.sbs/",
            "https://galaxy.akindayim26.sbs/",
            "https://stream.dengeli26.sbs/",
            "https://cdn.dengetv26.sbs/"
        ]

    def try_direct_access(self):
        """Doğrudan m3u8 erişimi dene"""
        test_files = ["yayinzirve.m3u8", "yayin1.m3u8", "yayinb2.m3u8"]
        
        for base in self.known_bases:
            for test_file in test_files:
                test_url = base + test_file
                try:
                    response = self.http.get(test_url, timeout=5.0)
                    if response.status_code == 200:
                        print(f"✅ Çalışan base bulundu: {base}")
                        return base
                except:
                    continue
        return None

    def test_base_url(self, base_url):
        """Base URL'yi detaylı test et"""
        test_files = ["yayinzirve.m3u8", "yayin1.m3u8"]
        success_count = 0
        
        for test_file in test_files:
            test_url = base_url + test_file
            try:
                response = self.http.get(
                    test_url, 
                    headers={'Referer': 'https://dengetv67.live/'},
                    timeout=8.0
                )
                if response.status_code == 200:
                    success_count += 1
                    print(f"✅ {test_file} çalışıyor")
                else:
                    print(f"❌ {test_file} hata: {response.status_code}")
            except Exception as e:
                print(f"❌ {test_file} exception: {e}")
        
        return success_count >= 1  # En az 1 kanal çalışsın

    def find_working_base(self):
        """Çalışan base URL'yi bul"""
        print("🔍 Çalışan base URL aranıyor...")
        
        # 1. Doğrudan erişim
        working_base = self.try_direct_access()
        if working_base:
            print(f"🎯 Bulunan base: {working_base}")
            return working_base
        
        # 2. Fallback
        print("⚠️  Yeni base bulunamadı, varsayılan kullanılıyor")
        return "https://galaxy.zirvedesin26.sbs/"

    def update_domain_file(self):
        """Domain dosyasını güncelle"""
        # Çalışan base'i bul
        working_base = self.find_working_base()
        
        print("-" * 40)
        print("🧪 Base URL test ediliyor...")
        
        # Test et
        if self.test_base_url(working_base):
            print("✅ Base URL çalışıyor!")
        else:
            print("❌ Base URL çalışmıyor, ama yine de kullanılacak")
        
        # Domain içeriğini oluştur
        domain_content = f"{working_base}\nhttps://dengetv67.live/"
        
        print("-" * 40)
        print("📝 Domain içeriği:")
        print(domain_content)
        
        # GitHub Workspace'e yaz (Actions için)
        domain_file_path = os.environ.get('GITHUB_WORKSPACE', '.') + '/domian.txt'
        
        try:
            with open(domain_file_path, 'w', encoding='utf-8') as f:
                f.write(domain_content)
            print(f"✅ Domain dosyası güncellendi: {domain_file_path}")
            
            # Sonuçları JSON'a yaz (Actions output için)
            result = {
                "base_url": working_base,
                "timestamp": datetime.now().isoformat(),
                "status": "success" if self.test_base_url(working_base) else "warning"
            }
            
            with open('result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"❌ Dosya yazma hatası: {e}")
            return False

    def run(self):
        """Ana işlemi çalıştır"""
        print("🚀 GitHub Actions Domain Updater")
        print("=" * 50)
        print(f"🕐 Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        success = self.update_domain_file()
        
        print("=" * 50)
        if success:
            print("🎉 İŞLEM TAMAMLANDI!")
        else:
            print("❌ İşlem başarısız!")
        
        return success


if __name__ == "__main__":
    updater = DomainAutoUpdater()
    updater.run()
