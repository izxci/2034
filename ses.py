  import streamlit as st
  import google.generativeai as genai
  import io
  import json
  import re
  from streamlit_mic_recorder import mic_recorder

  # --- CONFIG ---
  st.set_page_config(page_title="Bakanlık Sesli Asistan", layout="wide")

  # CSS: Ses Dalgaları ve Hukuk Teması
  st.markdown("""
      <style>
      .stMicRecorder { display: flex; justify-content: center; margin: 20px; }
      .transcript-box { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 10px; color: #333; height: 300px; overflow-y: auto; }
      .legal-alert { background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 10px; margin-top: 10px; }
      </style>
  """, unsafe_allow_html=True)

  if 'transcript' not in st.session_state: st.session_state.transcript = ""
  if 'legal_analysis' not in st.session_state: st.session_state.legal_analysis = ""

  with st.sidebar:
      st.title("🎙️ Sesli Denetim Merkezi")
      api_key = st.text_input("Gemini API Key:", type="password")
      st.info("Duruşma veya denetim sırasında 'Kaydı Başlat' butonuna basın. Konuşma bittiğinde AI otomatik analiz yapacaktır.")

  st.title("⚖️ 5996 Canlı Transkript ve Hukuki Analiz Sistemi")

  if not api_key:
      st.warning("Lütfen API anahtarınızı girin.")
      st.stop()

  genai.configure(api_key=api_key)
  model = genai.GenerativeModel('gemini-2.5-flash')

  col1, col2 = st.columns([1, 1])

  with col1:
      st.subheader("🎤 Canlı Ses Kaydı")
      st.write("Duruşma, toplantı veya denetim anını kaydetmek için mikrofona basın:")
      
      # Ses Kayıt Bileşeni
      audio = mic_recorder(
          start_prompt="🔴 Kaydı Başlat",
          stop_prompt="⏹️ Kaydı Bitir ve Analiz Et",
          key='recorder'
      )

      if audio:
          st.audio(audio['bytes'])
          with st.spinner("Ses yazıya dökülüyor ve mevzuat analizi yapılıyor..."):
              # Gemini'ye ses dosyasını gönderiyoruz
              audio_data = {
                  "mime_type": "audio/wav",
                  "data": audio['bytes']
              }
              
              prompt = """
              Aşağıdaki ses kaydını önce tam metin olarak yazıya dök (transkript). 
              Ardından bu konuşma içinde 5996 Sayılı Kanun ve gıda mevzuatı açısından kritik olan noktaları tespit et.
              Eğer konuşmacı bir iddiada bulunuyorsa (örn: 'numune hatalı alındı'), buna karşı Bakanlık avukatının verebileceği hukuki cevabı hazırla.
              
              Yanıtı şu formatta ver:
              METİN: [Buraya transkripti yaz]
              ANALİZ: [Buraya hukuki notları yaz]
              SORU: [Buraya karşı tarafa sorulacak soruları yaz]
              """
              
              try:
                  response = model.generate_content([prompt, audio_data])
                  st.session_state.transcript = response.text
              except Exception as e:
                  st.error(f"Hata: {e}")

      st.markdown("### 📝 Transkript Metni")
      st.markdown(f'<div class="transcript-box">{st.session_state.transcript}</div>', unsafe_allow_html=True)

  with col2:
      st.subheader("🏛️ Anlık Hukuki Strateji")
      if st.session_state.transcript:
          # Metni analiz edip görselleştirme
          st.markdown("### 🔍 Tespit Edilen Kritik Noktalar")
          st.write(st.session_state.transcript.split("ANALİZ:")[1] if "ANALİZ:" in st.session_state.transcript else "Analiz bekleniyor...")
          
          st.divider()
          st.markdown("### 🛡️ Karşı Hamle / Soru Önerileri")
          st.info(st.session_state.transcript.split("SORU:")[1] if "SORU:" in st.session_state.transcript else "Soru önerisi yok.")
      else:
          st.info("Ses kaydı tamamlandığında stratejik notlar burada görünecektir.")

  # EKSTRA: Manuel Metin Girişi (Ses kaydı yapılamayan durumlar için)
  with st.expander("⌨️ Manuel Metin Analizi (Kopyala/Yapıştır)"):
      manual_text = st.text_area("Duruşma tutanağını veya konuşma metnini buraya yapıştırın:")
      if st.button("Metni Analiz Et"):
          res = model.generate_content(f"Aşağıdaki konuşma metnini 5996 sayılı kanun kapsamında analiz et: {manual_text}")
          st.write(res.text)