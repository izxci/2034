import streamlit as st
import pandas as pd
import requests
import io
import zipfile
import xml.etree.ElementTree as ET
import re
import json
import os
import time
import concurrent.futures
import urllib.parse
import importlib.metadata
from datetime import datetime, timedelta, date
from io import BytesIO

# Third-party libraries
import google.generativeai as genai
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document
from fpdf import FPDF
from gtts import gTTS
import speech_recognition as sr
from PIL import Image
from PIL.ExifTags import TAGS
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# --- PERFORMANCE OPTIMIZATION (CACHING) ---
@st.cache_data(ttl=3600)
def get_cached_ai_response(prompt, api_key, model_name='gemini-1.5-flash'):
    """AI yanıtlarını önbelleğe alarak hızı artırır."""
    if not api_key: return "API Key Eksik"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Hata: {str(e)}"

@st.cache_data
def parse_udf_cached(file_bytes_val):
    """UDF dosyalarını önbelleğe alarak tekrar okumayı hızlandırır."""
    try:
        with zipfile.ZipFile(BytesIO(file_bytes_val)) as z:
            if 'content.xml' in z.namelist():
                with z.open('content.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    text_content = [elem.text.strip() for elem in root.iter() if elem.text]
                    return " ".join(text_content)
            return "HATA: UDF içeriği okunamadı."
    except Exception as e:
        return f"HATA: {str(e)}"

@st.cache_data
def parse_pdf_cached(file_bytes_val):
    """PDF dosyalarını önbelleğe alarak tekrar okumayı hızlandırır."""
    try:
        reader = PdfReader(BytesIO(file_bytes_val))
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text if len(text.strip()) > 50 else ""
    except:
        return ""

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="Hukuk Asistanı AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GELİŞMİŞ CSS (Arayüz Verimliliği) ---
st.markdown("""
    <style>
    /* Ana Tema İyileştirmeleri */
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 4px 4px 0px 0px;
        padding: 8px 16px;
        border: 1px solid #e0e0e0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2196f3 !important;
        color: white !important;
    }
    
    /* Mevcut Kutuların Korunması ve İyileştirilmesi */
    .kanun-kutusu { background-color: #fff3e0; padding: 15px; border-left: 5px solid #ff9800; border-radius: 5px; margin-bottom: 10px; white-space: pre-wrap; }
    .ictihat-kutusu { background-color: #e3f2fd; padding: 15px; border-left: 5px solid #2196f3; border-radius: 5px; margin-bottom: 10px; }
    .buyur-abi-kutusu { background-color: #f3e5f5; padding: 15px; border-left: 5px solid #9c27b0; border-radius: 5px; margin-bottom: 10px; }
    .alarm-kutusu { background-color: #ffebee; padding: 15px; border-left: 5px solid #f44336; border-radius: 5px; margin-bottom: 10px; font-weight: bold; color: #b71c1c; }
    .arsiv-kutusu { background-color: #e0f2f1; padding: 15px; border-left: 5px solid #009688; border-radius: 5px; margin-bottom: 10px; }
    .uyap-kutusu { background-color: #fce4ec; padding: 15px; border-left: 5px solid #c2185b; border-radius: 5px; margin-bottom: 20px; }
    
    /* Kart Görünümü */
    .legal-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- KALICILIK (VERİ TABANI) FONKSİYONLARI ---
DURUSMA_FILE = "durusma_kayitlari.json"

def save_durusma_data(data):
    serializable_data = []
    for item in data:
        temp = item.copy()
        if isinstance(temp.get('dtstart'), datetime):
            temp['dtstart'] = temp['dtstart'].isoformat()
        serializable_data.append(temp)
    try:
        with open(DURUSMA_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Kaydetme hatası: {e}")

def load_durusma_data():
    if not os.path.exists(DURUSMA_FILE): return []
    try:
        with open(DURUSMA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            if 'dtstart' in item and item['dtstart']:
                item['dtstart'] = datetime.fromisoformat(item['dtstart'])
        return data
    except: return []

# --- YARDIMCI FONKSİYONLAR (Mevcut Mantık Korundu) ---
def extract_metadata(text):
    if not isinstance(text, str) or text.startswith(("HATA", "UYARI")):
        return {"mahkeme": "-", "esas": "-", "karar": "-", "tarih": "-"}
    esas = re.search(r"(?i)Esas\s*No\s*[:\-]?\s*(\d{4}/\d+)", text)
    karar = re.search(r"(?i)Karar\s*No\s*[:\-]?\s*(\d{4}/\d+)", text)
    tarih = re.search(r"(\d{1,2}[./]\d{1,2}[./]\d{4})", text)
    mahkeme = "Tespit Edilemedi"
    for line in text.split('\n')[:40]:
        clean = line.strip()
        if ("MAHKEMESİ" in clean.upper() or "DAİRESİ" in clean.upper()) and len(clean) > 5:
            mahkeme = clean
            break
    return {
        "mahkeme": mahkeme,
        "esas": esas.group(1) if esas else "Bulunamadı",
        "karar": karar.group(1) if karar else "Bulunamadı",
        "tarih": tarih.group(1) if tarih else "Bulunamadı"
    }

# --- DOSYA OLUŞTURMA FONKSİYONLARI ---
def create_word_file(text):
    doc = Document()
    for line in text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    byte_io = BytesIO()
    doc.save(byte_io)
    byte_io.seek(0)
    return byte_io

def create_udf_file(text):
    root = ET.Element("content")
    body = ET.SubElement(root, "body")
    for line in text.split('\n'):
        p = ET.SubElement(body, "p")
        p.text = line
    xml_str = ET.tostring(root, encoding='utf-8', method='xml')
    byte_io = BytesIO()
    with zipfile.ZipFile(byte_io, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('content.xml', xml_str)
    byte_io.seek(0)
    return byte_io

# --- ANA UYGULAMA ---
def main():
    st.title("⚖️ Hukuk Asistanı (v10.0 - Optimized)")
    
    # Kütüphane Sürümü
    try: lib_ver = importlib.metadata.version("google-generativeai")
    except: lib_ver = "Bilinmiyor"

    # Session State Başlatma
    if "durusma_listesi" not in st.session_state: st.session_state.durusma_listesi = load_durusma_data()
    states = ["doc_text", "last_file_id", "messages", "mevzuat_sonuc", "ictihat_sonuc", "dilekce_taslak", "soru_cevap", "ses_metni", "ocr_metni"]
    for s in states:
        if s not in st.session_state: st.session_state[s] = "" if "text" in s or "sonuc" in s or "taslak" in s else []
    if "last_file_id" not in st.session_state: st.session_state.last_file_id = None

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        api_key = st.text_input("Google Gemini API Key", type="password")
        st.caption(f"Kütüphane Sürümü: {lib_ver}")
        
        st.divider()
        st.header("📁 Dosya Bilgileri")
        input_davaci = st.text_input("Davacı")
        input_davali = st.text_input("Davalı")
        input_mahkeme = st.text_input("Mahkeme")
        input_dosya_no = st.text_input("Dosya No")
        
        if st.button("🗑️ Ekranı Temizle"):
            for key in list(st.session_state.keys()):
                if key != "durusma_listesi": del st.session_state[key]
            st.rerun()

    # Dosya Yükleme
    uploaded_file = st.file_uploader("Dosya Yükle (UDF/PDF)", type=['udf', 'pdf'])

    if uploaded_file and st.session_state.get('last_file_id') != uploaded_file.file_id:
        with st.spinner("Dosya işleniyor..."):
            file_bytes_val = uploaded_file.getvalue()
            ext = uploaded_file.name.split('.')[-1].lower()
            if ext == 'udf':
                raw_text = parse_udf_cached(file_bytes_val)
            else:
                raw_text = parse_pdf_cached(file_bytes_val)
            st.session_state.doc_text = raw_text
            st.session_state.last_file_id = uploaded_file.file_id
            st.session_state.messages = []

    if st.session_state.doc_text.startswith(("HATA", "UYARI")):
        st.warning(st.session_state.doc_text)
    
    auto_data = extract_metadata(st.session_state.doc_text)

    # --- SEKMELER ---
    st.markdown("### 🛠️ Hukuk Araç Seti")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Analiz", "💬 Sohbet", "📕 Mevzuat", "⚖️ İçtihat", "✍️ Dilekçe Yaz"])

    with tab1:
        st.markdown("<div class='legal-card'>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Mahkeme:** {input_mahkeme or auto_data['mahkeme']}")
            st.write(f"**Dosya No:** {input_dosya_no or auto_data['esas']}")
        with col2:
            st.write(f"**Davacı:** {input_davaci or '-'}")
            st.write(f"**Davalı:** {input_davali or '-'}")
        st.text_area("Metin Önizleme", st.session_state.doc_text, height=200)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("Soru sor..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("AI Yanıtlıyor..."):
                    context = f"BELGE: {st.session_state.doc_text[:15000]}\nSORU: {prompt}"
                    reply = get_cached_ai_response(f"Sen bir avukatsın. Şuna cevap ver: {context}", api_key)
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

    with tab3:
        c1, c2 = st.columns([3,1])
        q = c1.text_input("Kanun Madde No", key="mq")
        if c2.button("Getir", key="mb") and q:
            with st.spinner("Aranıyor..."):
                res = get_cached_ai_response(f"GÖREV: '{q}' maddesini tam metin yaz.", api_key)
                st.session_state.mevzuat_sonuc = res
        if st.session_state.mevzuat_sonuc:
            st.markdown(f"<div class='kanun-kutusu'>{st.session_state.mevzuat_sonuc}</div>", unsafe_allow_html=True)

    with tab4:
        c3, c4 = st.columns([3,1])
        iq = c3.text_input("İçtihat Konusu", key="iq")
        if c4.button("Ara", key="ib") and iq:
            with st.spinner("Taranıyor..."):
                res = get_cached_ai_response(f"GÖREV: '{iq}' hakkında Yargıtay kararlarını özetle.", api_key)
                st.session_state.ictihat_sonuc = res
        if st.session_state.ictihat_sonuc:
            st.markdown(f"<div class='ictihat-kutusu'>{st.session_state.ictihat_sonuc}</div>", unsafe_allow_html=True)

    with tab5:
        st.subheader("✍️ Otomatik Dilekçe Yazımı")
        if not st.session_state.doc_text:
            st.info("Lütfen önce bir dosya yükleyin.")
        else:
            col_d1, col_d2 = st.columns([2, 1])
            with col_d1:
                dilekce_turu = st.selectbox("Dilekçe Türü", ["Cevap Dilekçesi", "İtiraz Dilekçesi", "Beyan Dilekçesi"])
                ozel_talimat = st.text_area("Özel Talimatlar", placeholder="Örn: Zamanaşımı itirazı ekle...")
            with col_d2:
                if st.button("Dilekçeyi Oluştur", type="primary"):
                    with st.spinner("Yazılıyor..."):
                        prompt = f"GÖREV: {dilekce_turu} yaz. Talimat: {ozel_talimat}. Belge Özeti: {st.session_state.doc_text[:10000]}"
                        st.session_state.dilekce_taslak = get_cached_ai_response(prompt, api_key)
            
            if st.session_state.dilekce_taslak:
                st.text_area("Taslak", st.session_state.dilekce_taslak, height=400)
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    st.download_button("Word İndir", create_word_file(st.session_state.dilekce_taslak), "Dilekce.docx")
                with c_btn2:
                    st.download_button("UDF İndir", create_udf_file(st.session_state.dilekce_taslak), "Dilekce.udf")

if __name__ == "__main__":
    main()
