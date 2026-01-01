import streamlit as st
import pandas as pd
import json
import os
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO

# --- 1. MODERN GÖRSEL YAPILANDIRMA (THEME) ---
class LegalTheme:
    """Uygulamanın tüm görsel kimliğini yöneten sınıf."""
    PRIMARY = "#1E3A8A"  # Lacivert (Hukuk ciddiyeti)
    SECONDARY = "#3B82F6" # Mavi
    ACCENT = "#F59E0B"    # Altın/Turuncu (Vurgu)
    BG_LIGHT = "#F8FAFC"
    
    @staticmethod
    def apply():
        st.markdown(f"""
        <style>
            /* Ana Arka Plan */
            .stApp {{ background-color: {LegalTheme.BG_LIGHT}; }}
            
            /* Kart Tasarımı */
            .legal-card {{
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.05);
                border-left: 6px solid {LegalTheme.PRIMARY};
                margin-bottom: 1.5rem;
            }}
            
            /* Başlıklar */
            h1, h2, h3 {{ color: {LegalTheme.PRIMARY}; font-family: 'Inter', sans-serif; }}
            
            /* Butonlar */
            .stButton>button {{
                width: 100%;
                border-radius: 10px;
                background-color: {LegalTheme.PRIMARY};
                color: white;
                font-weight: 600;
                border: none;
                padding: 0.6rem;
                transition: all 0.3s ease;
            }}
            .stButton>button:hover {{
                background-color: {LegalTheme.SECONDARY};
                transform: translateY(-2px);
            }}
            
            /* Özel Kutular */
            .info-box {{ background: #E0F2FE; border-left: 4px solid #0EA5E9; padding: 1rem; border-radius: 8px; }}
            .warning-box {{ background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 1rem; border-radius: 8px; }}
            .error-box {{ background: #FEE2E2; border-left: 4px solid #EF4444; padding: 1rem; border-radius: 8px; }}
        </style>
        """, unsafe_allow_html=True)

# --- 2. AKILLI AI MOTORU (AI ENGINE) ---
class LegalAI:
    """AI modellerini ve prompt yönetimini standardize eden sınıf."""
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def analyze(self, prompt, context=""):
        if not self.model:
            return "⚠️ Lütfen geçerli bir API anahtarı girin."
        try:
            full_prompt = f"Sistem: Sen uzman bir hukuk asistanısın.\nBağlam: {context}\nSoru: {prompt}"
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"❌ Analiz Hatası: {str(e)}"

# --- 3. YARDIMCI ARAÇLAR (UTILS) ---
class LegalUtils:
    @staticmethod
    def parse_file(uploaded_file):
        """Dosya türüne göre otomatik ayrıştırma yapar."""
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext == 'pdf':
            from pypdf import PdfReader
            reader = PdfReader(uploaded_file)
            return "\n".join([p.extract_text() for p in reader.pages])
        elif ext == 'udf':
            with zipfile.ZipFile(uploaded_file) as z:
                with z.open('content.xml') as f:
                    tree = ET.parse(f)
                    return " ".join([e.text.strip() for e in tree.getroot().iter() if e.text])
        return "Desteklenmeyen format."

# --- 4. MODÜL YÖNETİCİSİ (MODULES) ---
def render_aym_module(ai):
    st.markdown("### 🏛️ AYM & AİHM Uygunluk Testi")
    st.info("Dilekçenizi veya kararınızı yükleyin, AI hak ihlali riskini analiz etsin.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        text_input = st.text_area("Hukuki Metin", height=250, placeholder="Metni buraya yapıştırın...")
    with col2:
        file = st.file_uploader("Veya Dosya Yükleyin", type=['pdf', 'udf'])
        if file:
            text_input = LegalUtils.parse_file(file)
            st.success("Dosya okundu!")

    if st.button("⚖️ Analizi Başlat"):
        with st.spinner("Hukuki içtihatlar taranıyor..."):
            res = ai.analyze("Bu metni AYM ve AİHM kriterlerine göre analiz et, ihlal riskini % olarak ver.", text_input)
            st.markdown(f"<div class='legal-card'>{res}</div>", unsafe_allow_html=True)

def render_forensics_module(ai):
    st.markdown("### 🕵️‍♂️ Adli Bilişim & Deepfake Analizi")
    # ... Benzer yapı ...
    st.warning("Bu modül dosya metadata ve içerik analizi yapar.")

# --- 5. ANA UYGULAMA DÖNGÜSÜ ---
def main():
    LegalTheme.apply()
    
    # Sidebar: Ayarlar ve Navigasyon
    with st.sidebar:
        st.title("⚖️ Hukuk Asistanı")
        api_key = st.text_input("Gemini API Key", type="password")
        st.divider()
        menu = st.selectbox("Modül Seçin", [
            "🏠 Ana Sayfa", 
            "⚖️ AYM/AİHM Analizi", 
            "🕵️‍♂️ Adli Bilişim", 
            "📅 Duruşma Takibi",
            "🧠 Semantik Arşiv"
        ])
        st.info("v2.0 - Profesyonel Sürüm")

    ai = LegalAI(api_key)

    # Dinamik İçerik Yönetimi
    if menu == "🏠 Ana Sayfa":
        st.markdown("""
        <div class='legal-card'>
            <h1>Hoş Geldiniz</h1>
            <p>Türkiye'nin en kapsamlı yapay zeka destekli hukuk platformuna hoş geldiniz.</p>
            <p>Sol menüden bir modül seçerek başlayabilirsiniz.</p>
        </div>
        """, unsafe_allow_html=True)
        
    elif menu == "⚖️ AYM/AİHM Analizi":
        render_aym_module(ai)
        
    elif menu == "🕵️‍♂️ Adli Bilişim":
        render_forensics_module(ai)

    # ... Diğer modüller ...

if __name__ == "__main__":
    main()
