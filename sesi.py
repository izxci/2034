import streamlit as st
import google.generativeai as genai
import io
import json
import re
from streamlit_mic_recorder import mic_recorder

# --- CONFIG ---
st.set_page_config(page_title="Bakanlık Sesli Asistan", layout="wide")

# CSS: Mobil Uyumlu ve Büyük Butonlu Tasarım
st.markdown("""
    <style>
    .stMicRecorder { display: flex; justify-content: center; margin: 20px; }
    button { height: 80px !important; font-size: 20px !important; }
    .transcript-box { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 10px; color: #333; min-height: 200px; }
    </style>
""", unsafe_allow_html=True)

if 'transcript' not in st.session_state: st.session_state.transcript = ""

with st.sidebar:
    st.title("🎙️ Bakanlık Mobil Asistan")
    api_key = st.text_input("Gemini API Key:", type="password")
    st.info("Duruşma veya denetim anında kaydı başlatın.")

st.title("⚖️ 5996 Canlı Transkript")

if not api_key:
    st.warning("Lütfen API anahtarınızı girin.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# Ses Kayıt Alanı
st.subheader("🎤 Sesli Kayıt ve Analiz")
audio = mic_recorder(
    start_prompt="🔴 KAYDI BAŞLAT",
    stop_prompt="⏹️ KAYDI BİTİR VE ANALİZ ET",
    key='recorder'
)

if audio:
    with st.spinner("Yapay zeka sesi analiz ediyor..."):
        audio_data = {"mime_type": "audio/wav", "data": audio['bytes']}
        prompt = """
        Bu ses kaydını yazıya dök ve 5996 Sayılı Kanun kapsamında:
        1. Kritik iddiaları listele.
        2. Bakanlık avukatı için hukuki savunma argümanları üret.
        3. Karşı tarafa sorulacak teknik soruları hazırla.
        """
        try:
            response = model.generate_content([prompt, audio_data])
            st.session_state.transcript = response.text
        except Exception as e:
            st.error(f"Hata oluştu: {e}")

if st.session_state.transcript:
    st.markdown("### 📝 Analiz Sonuçları")
    st.markdown(f'<div class="transcript-box">{st.session_state.transcript}</div>', unsafe_allow_html=True)
