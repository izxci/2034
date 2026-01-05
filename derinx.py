import streamlit as st
import google.generativeai as genai
import numpy as np
import faiss
import re
from PyPDF2 import PdfReader

# Sayfa Ayarları
st.set_page_config(page_title="Nokta Atışı Mevzuat", layout="wide")

# --- FONKSİYONLAR ---
def get_embeddings(texts, api_key):
    """Metinleri yapay zeka vektörlerine dönüştürür (Anlamsal Hafıza)"""
    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model="models/embedding-001",
        content=texts,
        task_type="retrieval_document"
    )
    return result['embedding']

def chunk_legal_text(text):
    """Hukuki metni 'Madde' bazlı akıllıca böler"""
    # 'Madde 1', 'MADDE 24', 'Ek Madde' gibi başlıkları yakalar
    pattern = r'(?i)(Madde\s+\d+|Geçici\s+Madde\s+\d+|Ek\s+Madde\s+\d+)'
    parts = re.split(pattern, text)
    
    chunks = []
    for i in range(1, len(parts), 2):
        header = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        chunks.append(f"{header}: {content.strip()}")
    
    # Eğer madde yapısı yoksa paragraflara böl
    if not chunks:
        chunks = [p.strip() for p in text.split('\n\n') if len(p) > 50]
    return chunks

# --- SESSION STATE ---
if 'vector_index' not in st.session_state:
    st.session_state.vector_index = None
    st.session_state.chunks = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Profesyonel Denetim")
    api_key = st.text_input("Gemini API Key", type="password")
    
    if st.button("🗑️ Hafızayı Sıfırla"):
        st.session_state.vector_index = None
        st.session_state.chunks = []
        st.rerun()

    st.divider()
    uploaded_file = st.file_uploader("Mevzuat PDF Yükle", type="pdf")
    
    if uploaded_file and api_key and st.session_state.vector_index is None:
        with st.status("Mevzuat Endeksleniyor (Nokta Atışı Hazırlığı)..."):
            reader = PdfReader(uploaded_file)
            full_text = "\n".join([p.extract_text() for p in reader.pages])
            
            # 1. Akıllı Bölme
            chunks = chunk_legal_text(full_text)
            st.session_state.chunks = chunks
            
            # 2. Vektörleştirme (AI Anlamlandırma)
            # Not: Çok büyük dosyalarda batch işlemi yapılır, burada hızlı örnek için:
            embeddings = get_embeddings(chunks, api_key)
            
            # 3. FAISS İndeksi Oluşturma (Işık hızında arama için)
            dim = len(embeddings[0])
            index = faiss.IndexFlatL2(dim)
            index.add(np.array(embeddings).astype('float32'))
            
            st.session_state.vector_index = index
            st.success(f"{len(chunks)} madde hafızaya alındı.")

# --- ANA EKRAN ---
st.title("🔍 Nokta Atışı Mevzuat Tarama")

if not api_key:
    st.warning("Lütfen API anahtarınızı girin.")
elif st.session_state.vector_index is None:
    st.info("Lütfen bir mevzuat PDF'i yükleyerek taramayı başlatın.")
else:
    query = st.text_input("🔎 Aramak istediğiniz kavram veya olay (Örn: gübre idari yaptırım yetkisi)", 
                         placeholder="AI burada kelimeye değil, anlama bakar...")

    if query:
        with st.spinner("Mevzuat taranıyor..."):
            # Sorguyu vektöre çevir
            query_vec = np.array([get_embeddings([query], api_key)[0]]).astype('float32')
            
            # En yakın 5 maddeyi bul (Işık hızında)
            D, I = st.session_state.vector_index.search(query_vec, k=5)
            
            st.subheader("📍 En Alakalı Mevzuat Maddeleri")
            
            for i, idx in enumerate(I[0]):
                score = D[0][i]
                madde_metni = st.session_state.chunks[idx]
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: black;">
                        <small style="color: gray;">Eşleşme Kalitesi: {max(0, int(100 - score))}%</small><br>
                        {madde_metni[:500]}...
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Bu Maddeyi AI ile Analiz Et", key=f"btn_{idx}"):
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        response = model.generate_content(f"Şu maddeyi açıkla ve yaptırımını söyle: {madde_metni}")
                        st.info(response.text)
