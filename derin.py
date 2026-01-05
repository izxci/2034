import streamlit as st
import google.generativeai as genai
import re
import difflib
from PyPDF2 import PdfReader

# Sayfa Ayarları
st.set_page_config(page_title="Mevzuat Analiz Sistemi", layout="wide", page_icon="⚖️")

# --- VARSAYILAN VERİ ---
BASE_DATA = [
    "Sistem hazır. Lütfen analiz etmek istediğiniz mevzuat metinlerini yükleyin veya buraya yazın."
]

# --- SESSION STATE YÖNETİMİ ---
if 'mevzuat_verisi' not in st.session_state:
    st.session_state.mevzuat_verisi = BASE_DATA.copy()

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

# --- HAFIZAYI SİLME FONKSİYONU ---
def hafizayi_temizle():
    st.session_state.mevzuat_verisi = BASE_DATA.copy()
    st.session_state.uploader_key += 1  # File uploader'ı sıfırlamak için key değiştiriyoruz
    st.rerun()

# --- ARAMA MOTORU ---
def akilli_ara(sorgu, mevzuat_listesi, limit=5):
    sorgu = sorgu.lower().strip()
    sonuclar = []
    for madde in mevzuat_listesi:
        skor = 0
        madde_lower = madde.lower()
        if sorgu in madde_lower: skor += 100
        sorgu_kelimeleri = sorgu.split()
        eslesen_kelime_sayisi = sum(1 for k in sorgu_kelimeleri if k in madde_lower)
        skor += (eslesen_kelime_sayisi * 20)
        benzerlik = difflib.SequenceMatcher(None, sorgu, madde_lower[:200]).ratio()
        skor += (benzerlik * 50)
        if skor > 10: sonuclar.append((madde, skor))
    return sorted(sonuclar, key=lambda x: x[1], reverse=True)[:limit]

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Mevzuat Yönetimi")
    
    # HAFIZA SİLME BUTONU (İstediğiniz Özellik)
    if st.button("🗑️ TÜM HAFIZAYI SİL / YENİ KONU", use_container_width=True):
        hafizayi_temizle()
    
    st.divider()
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.subheader("📂 Yeni Mevzuat Yükle")
    # key={st.session_state.uploader_key} sayesinde hafıza silinince bu alan da temizlenir
    uploaded_file = st.file_uploader("PDF Yükle", type="pdf", key=f"pdf_up_{st.session_state.uploader_key}")
    
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        yeni_metin = ""
        for page in reader.pages:
            yeni_metin += page.extract_text() + "\n"
        paragraflar = [p.strip() for p in yeni_metin.split('\n') if len(p.strip()) > 40]
        st.session_state.mevzuat_verisi.extend(paragraflar)
        st.success(f"Hafızaya {len(paragraflar)} yeni madde eklendi!")

    st.divider()
    st.subheader("🔍 Direkt Madde Bul")
    hizli_sorgu = st.text_input("Anahtar kelimeler", key=f"search_{st.session_state.uploader_key}")
    
    if hizli_sorgu:
        bulunanlar = akilli_ara(hizli_sorgu, st.session_state.mevzuat_verisi)
        for metin, skor in bulunanlar:
            vurgulu = metin
            for k in hizli_sorgu.split():
                vurgulu = re.sub(f"({re.escape(k)})", r'<b style="color:red; background:yellow;">\1</b>', vurgulu, flags=re.IGNORECASE)
            st.markdown(f'<div style="background:#f0f2f6; padding:8px; border-radius:5px; margin-bottom:5px; border-left:3px solid red; font-size:0.8rem; color:black;">{vurgulu}</div>', unsafe_allow_html=True)

# --- ANA EKRAN ---
st.title("🤖 Mevzuat Analiz İstasyonu")
st.caption(f"Şu an hafızada **{len(st.session_state.mevzuat_verisi)}** mevzuat parçası kayıtlı.")

if not api_key:
    st.warning("Lütfen sol menüden API anahtarınızı girin.")
else:
    genai.configure(api_key=api_key)
    soru = st.text_area("Hukuki sorunuzu yazın:", placeholder="Hafızadaki belgelere göre analiz yapılır...")
    
    if st.button("Analiz Et"):
        en_alakali = akilli_ara(soru, st.session_state.mevzuat_verisi, limit=10)
        baglam = "\n".join([m[0] for m in en_alakali])
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Aşağıdaki mevzuat metinlerine dayanarak soruyu cevapla:\n\n{baglam}\n\nSoru: {soru}"
        
        with st.spinner("Analiz ediliyor..."):
            response = model.generate_content(prompt)
            st.markdown(response.text)
