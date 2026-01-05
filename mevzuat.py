import streamlit as st
import google.generativeai as genai
import numpy as np
import faiss
import re
from PyPDF2 import PdfReader

# Sayfa Yapılandırması
st.set_page_config(page_title="Mevzuat Pro AI", page_icon="⚖️", layout="wide")

# CSS ile vurgulama stili
st.markdown("""
    <style>
    .highlight { background-color: #fff3cd; padding: 2px 5px; border-radius: 3px; font-weight: bold; color: #856404; }
    .sidebar-result { font-size: 0.85rem; border-bottom: 1px solid #eee; padding: 10px 0; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE (Veri Saklama) ---
if 'mevzuat_listesi' not in st.session_state:
    st.session_state.mevzuat_listesi = [
        "Tarımda Kullanılan Gübrelerin Piyasa Gözetimi Yönetmeliği Madde 15: Denetimler Bakanlıkça yetkilendirilen personel tarafından yapılır.",
        "Gübre Yönetmeliği Madde 41: İdari para cezaları 5996 sayılı Kanun hükümlerine göre Valilikler veya Bakanlık merkez teşkilatı tarafından uygulanır.",
        "5996 Sayılı Kanun Madde 41: Teknik düzenlemelere aykırı ürün arz edenlere 20.000 TL'den başlayan idari para cezası verilir."
    ]

# --- YAN MENÜ (Sidebar) ---
with st.sidebar:
    st.title("⚖️ Mevzuat Kontrol Paneli")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    
    # Dosya Yükleme
    st.subheader("📂 Belge Yükle")
    uploaded_file = st.file_uploader("PDF Mevzuat Yükle", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text()
        # Metni maddelere bölme simülasyonu (noktaya göre)
        new_maddeler = [m.strip() for m in text_content.split('\n') if len(m) > 20]
        st.session_state.mevzuat_listesi.extend(new_maddeler)
        st.success(f"{len(new_maddeler)} yeni satır eklendi!")

    st.divider()

    # DİREKT KAVRAM ARAMA (İstediğin Özellik)
    st.subheader("🔍 Direkt Kavram Bul")
    search_term = st.text_input("Mevzuatta geçen kelimeyi yazın")
    
    if search_term:
        st.markdown(f"**'{search_term}'** için sonuçlar:")
        found = False
        for m in st.session_state.mevzuat_listesi:
            if search_term.lower() in m.lower():
                found = True
                # Kelimeyi vurgula
                highlighted = re.sub(f"({re.escape(search_term)})", r'<span class="highlight">\1</span>', m, flags=re.IGNORECASE)
                st.markdown(f'<div class="sidebar-result">{highlighted}</div>', unsafe_allow_html=True)
        if not found:
            st.caption("Eşleşme bulunamadı.")

# --- ANA PANEL ---
st.title("🚀 Akıllı Mevzuat Analiz Motoru")
st.info("Gemini 2.5 Flash ile hızlı analiz modundasınız.")

if not api_key:
    st.warning("Lütfen sol menüden API anahtarınızı girerek sistemi aktif edin.")
else:
    genai.configure(api_key=api_key)
    
    # Soru Sorma Alanı
    query = st.text_input("🤖 Yapay Zekaya Sorun", placeholder="Örn: Gübre denetiminde yetki kimde ve cezası ne kadar?")

    if query:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.spinner("Mevzuat taranıyor ve analiz ediliyor..."):
                try:
                    # 1. Embedding ve FAISS (Hızlı Arama)
                    def get_emb(text):
                        return genai.embed_content(model="models/embedding-001", content=text, task_type="retrieval_query")['embedding']

                    embeddings = [get_emb(m) for m in st.session_state.mevzuat_listesi[:50]] # Hız için ilk 50 madde
                    index = faiss.IndexFlatL2(len(embeddings[0]))
                    index.add(np.array(embeddings).astype('float32'))

                    query_vec = np.array([get_emb(query)]).astype('float32')
                    D, I = index.search(query_vec, k=3)
                    
                    context = "\n".join([st.session_state.mevzuat_listesi[i] for i in I[0]])

                    # 2. Gemini Analizi
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt = f"""
                    Aşağıdaki mevzuat metinlerine dayanarak soruyu cevapla. 
                    Eksik bilgi varsa 'Mevzuatta bulunamadı' de.
                    
                    MEVZUAT:
                    {context}
                    
                    SORU: {query}
                    """
                    response = model.generate_content(prompt)
                    
                    st.subheader("📝 AI Analiz Raporu")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Hata: {e}")

        with col2:
            st.subheader("📌 İlgili Maddeler")
            for i in I[0]:
                st.caption(f"• {st.session_state.mevzuat_listesi[i]}")

# Karşılaştırma ve Analiz Butonları
st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("⚖️ Emsal Karar Analizi"):
        st.write("Gemini emsal kararları tarıyor...")
with c2:
    if st.button("🔄 Mevzuat Karşılaştır"):
        st.write("Eski ve yeni hükümler analiz ediliyor...")
with c3:
    if st.button("📄 Belge Denetimi Yap"):
        st.write("Yüklenen belge mevzuata uygunluk testinden geçiyor...")
