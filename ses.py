import streamlit as st
import google.generativeai as genai
import io
import json
import re
from streamlit_mic_recorder 
import mic_recorder

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bakanlık Sesli Asistan", layout="wide")

# CSS: Mobil Uyumlu Tasarım
st.markdown("""
    <style>
    .stMicRecorder { display: flex; justify-content: center; margin: 20px; }
    button { height: 70px !important; width: 100% !important; font-size: 18px !important; border-radius: 15px !important; }
    .transcript-box { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 1px solid #d1d5db; }
    </style>
""", unsafe_allow_html=True)

if 'transcript' not in st.session_state:
    st.session_state.transcript = ""

# Sidebar
with st.sidebar:
    st.title("🏛️ Bakanlık Asistan")
    api_key = st.text_input("Gemini API Key:", type="password")
    st.info("API anahtarınızı girip kaydı başlatın.")

# Ana Ekran
st.title("⚖️ 5996 Canlı Transkript")

if not api_key:
    st.warning("Devam etmek için lütfen API anahtarınızı girin.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# Kayıt Bileşeni
audio = mic_recorder(
    start_prompt="🔴 KAYDI BAŞLAT",
    stop_prompt="⏹️ KAYDI BİTİR VE ANALİZ ET",
    key='recorder'
)

if audio:
    with st.spinner("Ses işleniyor..."):
        try:
            audio_data = {"mime_type": "audio/wav", "data": audio['bytes']}
            prompt = "Bu ses kaydını yazıya dök ve 5996 sayılı kanun kapsamında hukuki analizini yap."
            response = model.generate_content([prompt, audio_data])
            st.session_state.transcript = response.text
        except Exception as e:
            st.error(f"Hata: {e}")

if st.session_state.transcript:
    st.markdown("### 📝 Analiz ve Transkript")
    st.markdown(f'<div class="transcript-box">{st.session_state.transcript}</div>', unsafe_allow_html=True)
