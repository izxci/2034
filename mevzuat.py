import os
import asyncio
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import google.generativeai as genai

# 1. HIZLI YAPILANDIRMA
# SentenceTransformer yerel çalışır, internet gerektirmez ve çok hızlıdır.
embed_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
genai.configure(api_key="YOUR_GEMINI_API_KEY")
llm = genai.GenerativeModel('gemini-2.5-flash')

class TurboMevzuat:
    def __init__(self):
        self.index = None
        self.mevzuat_parcalari = []
        
    def mevzuat_yukle(self, metinler):
        """Mevzuatı vektör veritabanına saniyeler içinde indeksler"""
        print("İndeksleniyor...")
        embeddings = embed_model.encode(metinler)
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(np.array(embeddings))
        self.mevzuat_parcalari = metinler
        print("Sistem hazır!")

    async def anlik_sorgu(self, soru):
        """Milisaniyeler içinde arama yapar ve sadece ilgili kısmı AI'ya sorar"""
        # Adım 1: Soru vektörünü oluştur (Yerel - Çok Hızlı)
        soru_vektoru = embed_model.encode([soru])
        
        # Adım 2: En alakalı 3 maddeyi bul (Milisaniyeler)
        D, I = self.index.search(np.array(soru_vektoru), k=3)
        ilgili_metin = "\n".join([self.mevzuat_parcalari[i] for i in I[0]])
        
        # Adım 3: Sadece ilgili kısmı Gemini'ye gönder (Hızlı Analiz)
        prompt = f"""
        Aşağıdaki mevzuat parçasına göre soruyu cevapla. 
        Eğer yetki veya ceza soruluyorsa madde numarasını belirterek net cevap ver.
        
        MEVZUAT: {ilgili_metin}
        SORU: {soru}
        """
        
        response = await llm.generate_content_async(prompt)
        return response.text

# --- KULLANIM ÖRNEĞİ ---
async def main():
    motor = TurboMevzuat()
    
    # Örnek Veri Seti (Gerçekte binlerce satır olabilir)
    veriler = [
        "Madde 41: Gübre denetiminde idari para cezalarını Bakanlık il müdürleri uygular.",
        "Madde 12: Piyasaya arz edilen gübrelerin etiketleri yönetmeliğe uygun olmalıdır.",
        "Emsal Karar: Danıştay 10. Daire, analiz raporu tebliğ edilmeden kesilen cezayı iptal etmiştir."
    ]
    
    motor.mevzuat_yukle(veriler)
    
    # Hızlı Sorgu
    sonuc = await motor.anlik_sorgu("Gübrede cezayı kim keser?")
    print(f"\nAI ANALİZİ:\n{sonuc}")

if __name__ == "__main__":
    asyncio.run(main())
