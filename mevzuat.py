import streamlit as st
import google.generativeai as genai
import numpy as np
import faiss

# Sayfa Yapılandırması
st.set_page_config(page_title="Mevzuat AI Pro", page_icon="⚖️", layout="wide")

# API Anahtarı Girişi
with st.sidebar:
    st.title("⚙️ Ayarlar")
    api_key = st.text_input("Gemini API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    st.info("Gemini 1.5 Flash modeli ile yüksek hızlı analiz yapılır.")

# Örnek Mevzuat Veritabanı (Gerçekte bir dosyadan okunabilir)
MEVZUAT_DATA = [
    "Tarımda Kullanılan Gübrelerin Piyasa Gözetimi Yönetmeliği Madde 15: Denetimler Bakanlıkça yetkilendirilen personel tarafından yapılır.",
    "Gübre Yönetmeliği Madde 41: İdari para cezaları 5996 sayılı Kanun hükümlerine göre Valilikler veya Bakanlık merkez teşkilatı tarafından uygulanır.",
    "5996 Sayılı Kanun Madde 41: Teknik düzenlemelere aykırı ürün arz edenlere 20.000 TL'den başlayan idari para cezası verilir.",
    "Emsal Karar: Danıştay, savunma alınmadan verilen idari para cezalarını usulden iptal etmektedir."
]

def get_embedding(text):
    """Metni vektöre dönüştürür (Gemini Embedding API kullanır)"""
    result = genai.embed_content(
        model="models/embedding-001",
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']

st.title("⚖️ Mevzuat Analiz ve Yaptırım Sorgulama")
st.markdown("---")

if not api_key:
    st.warning("Lütfen sol menüden API anahtarınızı girin.")
else:
    # Arama Arayüzü
    query = st.text_input("🔍 Mevzuat veya konu arayın (Örn: gübre cezası yetki)", placeholder="Eksik yazsanız bile AI tamamlar...")

    if query:
        with st.spinner("Hızla analiz ediliyor..."):
            try:
                # 1. Adım: Mevzuatı Vektörize Et (Önbelleğe alınabilir)
                # Not: Gerçek uygulamada bu işlem bir kez yapılır.
                embeddings = []
                for text in MEVZUAT_DATA:
                    embeddings.append(get_embedding(text))
                
                index = faiss.IndexFlatL2(len(embeddings[0]))
                index.add(np.array(embeddings).astype('float32'))

                # 2. Adım: Soruyu Ara
                query_vec = np.array([get_embedding(query)]).astype('float32')
                D, I = index.search(query_vec, k=2) # En yakın 2 maddeyi bul
                
                context = "\n".join([MEVZUAT_DATA[i] for i in I[0]])

                # 3. Adım: Gemini 1.5 Flash ile Yanıtla
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"""
                Sen bir hukuk uzmanısın. Kullanıcının sorusunu aşağıdaki mevzuat parçalarına göre yanıtla.
                Yanıtında 'Yetkili Makam', 'Ceza Miktarı' ve 'Hukuki Dayanak' başlıklarını kullan.
                
                MEVZUAT:
                {context}
                
                SORU: {query}
                """
                
                response = model.generate_content(prompt)
                
                # Sonuçları Göster
                st.success("Analiz Tamamlandı!")
                st.markdown(response.text)
                
                with st.expander("İlgili Mevzuat Maddeleri (Kaynak)"):
                    st.write(context)
                    
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

# Alt Bilgi
st.sidebar.markdown("---")
st.sidebar.caption("Mevzuat Pro AI v2.0 - Gemini 1.5 Flash Engine")
