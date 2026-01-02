import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def kaysis_ara(arama_terimi):
    print(f"\n--- KAYSİS Seleniumsuz Arama (Requests + BeautifulSoup) ---")
    
    # Tarayıcı gibi davranmak için User-Agent ayarı
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    url = "https://kms.kaysis.gov.tr/Home/Kurum/24308110"
    
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        print("Sayfa yükleniyor...")
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        print(f"Sayfa başlığı: {soup.title.string.strip() if soup.title else 'Yok'}")

        # Arama formunu ve input alanını bulmaya çalış
        search_input = None
        target_form = None
        
        # Tüm formları tara
        for form in soup.find_all("form"):
            inputs = form.find_all("input", type=["text", "search"])
            for inp in inputs:
                input_name = inp.get("name", "").lower()
                input_id = inp.get("id", "").lower()
                placeholder = inp.get("placeholder", "").lower()
                
                if any(x in input_name for x in ['search', 'ara', 'query', 'keyword']) or \
                   any(x in input_id for x in ['search', 'ara', 'query']) or \
                   any(x in placeholder for x in ['ara', 'search']):
                    search_input = inp
                    target_form = form
                    break
            if search_input:
                break
        
        if not search_input or not target_form:
            print("Uyarı: Standart bir arama formu bulunamadı. Sayfa JavaScript ile çalışıyor olabilir.")
            if arama_terimi.lower() in soup.get_text().lower():
                print(f"'{arama_terimi}' kelimesi sayfa içeriğinde bulundu (HTML içinde).")
            else:
                print("Arama formu bulunamadı ve kelime sayfa metninde yok.")
            return

        print(f"Arama formu bulundu. Action: {target_form.get('action')}")
        
        # Form verilerini hazırla
        form_data = {}
        for inp in target_form.find_all("input"):
            name = inp.get("name")
            value = inp.get("value", "")
            if name:
                form_data[name] = value
        
        form_data[search_input.get("name")] = arama_terimi
        
        action_url = urljoin(url, target_form.get("action", ""))
        
        print("Arama yapılıyor...")
        method = target_form.get("method", "get").lower()
        
        if method == "post":
            search_response = session.post(action_url, data=form_data, headers=headers)
        else:
            search_response = session.get(action_url, params=form_data, headers=headers)
            
        search_response.raise_for_status()
        
        # Sonuçları işle
        results_soup = BeautifulSoup(search_response.text, "html.parser")
        
        print("\n--- ARAMA SONUÇLARI ---")
        results = results_soup.find_all(["tr", "li", "div"], class_=lambda x: x and ('result' in x or 'item' in x))
        
        if not results:
            results = results_soup.find_all("tr")
            
        found_count = 0
        for res in results:
            text = res.get_text(" | ", strip=True)
            if text and len(text) > 10 and arama_terimi.lower() in text.lower():
                print(f"SONUÇ: {text}")
                found_count += 1
                
        if found_count == 0:
            print("Belirgin bir sonuç bulunamadı veya sonuçlar JavaScript ile yükleniyor.")
            
    except requests.exceptions.RequestException as e:
        print(f"Bağlantı hatası: {e}")
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    term = input("Aramak istediğiniz kelime: ")
    kaysis_ara(term)