import streamlit as st
import google.generativeai as genai
import re
from rank_bm25 import BM25Okapi
from rapidfuzz import process, fuzz
from PyPDF2 import PdfReader

# Sayfa Ayarları
st.set_page_config(page_title="Hukuk Arama Motoru", layout="wide")

# --- ARAMA MOTORU SINIFI ---
class MevzuatSearchEngine:
    def __init__(self, belgeler):
        self.belgeler = belgeler
        # BM25 için kelimelere ayırma (Tokenization)
        self.tokenized_corpus = [doc.lower().split() for doc in belgeler]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def ara(self, query, top_n=5):
        # 1. BM25 Skoru (Kelime bazlı en iyi eşleşme)
        query_tokens = query.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)
        
        # 2. Fuzzy Matching (Yazım hataları ve benzerlik için)
        fuzzy_results = process.extract(query, self.belgeler, scorer=fuzz.PartialRatio, limit=20)
        
        # Sonuçları birleştir ve puanla
        combined_results = []
        for idx, doc in enumerate(self.belgeler):
            score = bm25_scores[idx]
            # Eğer fuzzy sonuçlarda varsa puanı artır
            for f_doc, f_score, f_idx in fuzzy_results:
                if doc == f_doc:
                    score += (f_score / 10) # Fuzzy bonusu
            
            if score > 0:
                combined_results.append((doc, score))
        
        # Puanlara göre sırala
        return sorted(combined_results, key=lambda x: x[1], reverse=True)[:top_n]

# --- SESSION STATE ---
if 'mevzuat_listesi' not in st.session_state:
    st.session_state.mevzuat_listesi = [
        "Tarımda Kullanılan Gübrelerin Piyasa Gözetimi ve Denetimi Yönetmeliği Madde 1: Amaç ve Kapsam.",
        "Gübrelerin Piyasa Gözetimi Madde 41: İdari yaptırımlar ve para cezaları Bakanlıkça uygulanır.",
        "5996 Sayılı Kanun Madde 41: Teknik düzenlemelere aykırı ürün arz edenlere 20.000 TL idari para cezası verilir.",
        "Denetim Personeli Eğitimi Tebliği: Denetçilerin sahip olması gereken nitelikler.",
        "Gübre Analiz Metodları Rehberi: Numune alma usul ve esasları."
    ]

# --- SIDEBAR (Gelişmiş Arama) ---
with st.sidebar:
    st.title("🔍 Gelişmiş Arama")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    
    # Dosya Yükleme (PDF okuma geliştirildi)
    uploaded_file = st.file_uploader("Mevzuat PDF Yükle", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text = page.extract_text()
            # Satırları temizle ve ekle
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 30]
            st.session_state.mevzuat_listesi.extend(lines)
        st.success("Belge sisteme entegre edildi.")

    st.divider()
    
    # AKILLI ARAMA KUTUSU
    search_query = st.text_input("Mevzuat İçinde Ara", placeholder="Örn: 'para cezası yetki'")
    
    if search_query:
        engine = MevzuatSearchEngine(st.session_state.mevzuat_listesi)
        results = engine.ara(search_query)
        
        st.markdown(f"### 📍 En Alakalı {len(results)} Madde")
        for doc, score in results:
            # Arama terimlerini metin içinde vurgula
            highlighted = doc
            for word in search_query.split():
                highlighted = re.sub(f"({re.escape(word)})", r'<mark style="background: #FFD700; color: black;">\1</mark>', highlighted, flags=re.IGNORECASE)
            
            st.markdown(f"""
            <div style="background: white; padding: 10px; border-radius: 5px; border-left: 5px solid #007BFF; margin-bottom: 10px; color: black; font-size: 0.9rem;">
                {highlighted}
                <br><small style="color: gray;">Alakalılık Puanı: {round(score, 2)}</small>
            </div>
            """, unsafe_allow_html=True)

# --- ANA PANEL (AI ANALİZ) ---
st.title("⚖️ Mevzuat Pro AI: Akıllı Analiz İstasyonu")

if not api_key:
    st.info("Sistemi tam kapasite kullanmak için API anahtarınızı girin. Yan menüdeki 'Gelişmiş Arama' her zaman çalışır.")
else:
    genai.configure(api_key=api_key)
    user_ask = st.text_area("Mevzuat hakkında hukuki sorunuzu sorun:", placeholder="Örn: Gübre denetiminde numune alma usulü nedir?")
    
    if st.button("Analiz Et"):
        # AI için en alakalı bağlamı getir
        engine = MevzuatSearchEngine(st.session_state.mevzuat_listesi)
        relevant_docs = [r[0] for r in engine.ara(user_ask, top_n=10)]
        context = "\n".join(relevant_docs)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        full_prompt = f"Şu mevzuat metinlerine göre soruyu profesyonelce cevapla:\n\n{context}\n\nSoru: {user_ask}"
        
        with st.spinner("AI Karar Veriyor..."):
            response = model.generate_content(full_prompt)
            st.markdown("### 🤖 AI Yanıtı")
            st.write(response.text)
            
            with st.expander("Kullanılan Kaynak Maddeler"):
                st.write(relevant_docs)
