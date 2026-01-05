import streamlit as st
import google.generativeai as genai
import re
import difflib
from PyPDF2 import PdfReader
import numpy as np

# Sayfa Ayarları
st.set_page_config(page_title="Mevzuat Analiz Sistemi", layout="wide", page_icon="⚖️")

# --- GELİŞMİŞ ARAMA MOTORU (STANDART KÜTÜPHANE İLE) ---
def akilli_ara(sorgu, mevzuat_listesi, limit=5):
    sorgu = sorgu.lower().strip()
    sonuclar = []
    
    for madde in mevzuat_listesi:
        skor = 0
        madde_lower = madde.lower()
        
        # 1. Tam Eşleşme (En yüksek puan)
        if sorgu in madde_lower:
            skor += 100
        
        # 2. Kelime Bazlı Eşleşme
        sorgu_kelimeleri = sorgu.split()
        eslesen_kelime_sayisi = sum(1 for k in sorgu_kelimeleri if k in madde_lower)
        skor += (eslesen_kelime_sayisi * 20)
        
        # 3. Benzerlik (Fuzzy) Skoru (difflib ile - Kurulum gerektirmez)
        # Maddenin ilk 200 karakteriyle sorgu arasındaki benzerliğe bakar
        benzerlik = difflib.SequenceMatcher(None, sorgu, madde_lower[:200]).ratio()
        skor += (benzerlik * 50)
        
        if skor > 10: # Belirli bir eşiğin üzerindekileri getir
            sonuclar.append((madde, skor))
    
    # Skorlara göre sırala
    return sorted(sonuclar, key=lambda x: x[1], reverse=True)[:limit]

# --- VERİ YÖNETİMİ ---
if 'mevzuat_verisi' not in st.session_state:
    st.session_state.mevzuat_verisi = [
        "Tarımda Kullanılan Gübrelerin Piyasa Gözetimi ve Denetimi Yönetmeliği Madde 41: İdari yaptırımlar Bakanlık il müdürlükleri tarafından uygulanır.",
        "5996 Sayılı Kanun: Teknik düzenlemelere aykırı gübre arzına 20.000 TL idari para cezası verilir.",
        "Gübre Denetimi Yönetmeliği Madde 15: Denetçiler numune alırken tutanak tutmak zorundadır.",
        "Resmi Gazete 28956: Gübrelerin piyasaya arzı ve denetimi esasları."
    ]

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Mevzuat Paneli")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.subheader("📂 Mevzuat Ekle")
    uploaded_file = st.file_uploader("PDF Yükle", type="pdf")
    
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        yeni_metin = ""
        for page in reader.pages:
            yeni_metin += page.extract_text() + "\n"
        # Paragraf bazlı bölme (Noktadan sonra yeni satır olan yerler)
        paragraflar = [p.strip() for p in yeni_metin.split('\n') if len(p.strip()) > 40]
        st.session_state.mevzuat_verisi.extend(paragraflar)
        st.success(f"Sisteme {len(paragraflar)} yeni madde eklendi!")

    st.divider()
    st.subheader("🔍 Direkt Madde Bul")
    hizli_sorgu = st.text_input("Anahtar kelimeler (Örn: gübre ceza yetki)")
    
    if hizli_sorgu:
        bulunanlar = akilli_ara(hizli_sorgu, st.session_state.mevzuat_verisi)
        if bulunanlar:
            for metin, skor in bulunanlar:
                # Vurgulama
                vurgulu = metin
                for k in hizli_sorgu.split():
                    vurgulu = re.sub(f"({re.escape(k)})", r'<b style="color:red; background:yellow;">\1</b>', vurgulu, flags=re.IGNORECASE)
                
                st.markdown(f"""
                <div style="background:#f0f2f6; padding:10px; border-radius:10px; margin-bottom:5px; border-left:4px solid #ff4b4b; font-size:0.8rem; color: black;">
                {vurgulu}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Eşleşen madde bulunamadı.")

# --- ANA EKRAN ---
st.title("🤖 Mevzuat Analiz Yapay Zekası")

if not api_key:
    st.info("Lütfen sol menüden Gemini API anahtarınızı girin.")
else:
    genai.configure(api_key=api_key)
    soru = st.text_area("Hukuki sorunuzu yazın:", placeholder="Örn: Gübre denetiminde idari yaptırım yetkisi kimdedir?")
    
    if st.button("Analiz Et"):
        # En alakalı 10 maddeyi AI'ya gönder
        en_alakali = akilli_ara(soru, st.session_state.mevzuat_verisi, limit=10)
        baglam = "\n".join([m[0] for m in en_alakali])
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Sen uzman bir hukuk danışmanısın. Aşağıdaki mevzuat metinlerine dayanarak soruyu cevapla. 
        Cevabında madde numaralarına atıf yap. Eğer bilgi metinde yoksa 'Veritabanında bulunamadı' de.
        
        MEVZUAT:
        {baglam}
        
        SORU: {soru}
        """
        
        with st.spinner("Düşünüyor..."):
            response = model.generate_content(prompt)
            st.subheader("📝 Analiz Sonucu")
            st.write(response.text)
            
            with st.expander("Analizde Kullanılan Kaynak Maddeler"):
                for m, s in en_alakali:
                    st.write(f"- {m}")
