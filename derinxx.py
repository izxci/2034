import streamlit as st
import google.generativeai as genai
import re
from PyPDF2 import PdfReader

# Sayfa Yapılandırması
st.set_page_config(page_title="Hukuki Karar Destek", layout="wide")

# --- SESSION STATE ---
if 'mevzuat_havuzu' not in st.session_state:
    st.session_state.mevzuat_havuzu = [] # {kaynak: "", metin: ""}
if 'secili_madde' not in st.session_state:
    st.session_state.secili_madde = None

# --- YARDIMCI FONKSİYONLAR ---
def metin_temizle(text):
    return re.sub(r'\s+', ' ', text).strip()

def tam_ibare_ara(sorgu, havuz):
    """Metin içinde birebir geçen yerleri bulur"""
    sonuclar = []
    sorgu_pattern = re.compile(re.escape(sorgu), re.IGNORECASE)
    
    for item in havuz:
        if sorgu_pattern.search(item['metin']):
            sonuclar.append(item)
    return sonuclar

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Sistem Ayarları")
    api_key = st.text_input("Gemini API Key", type="password")
    
    if st.button("🗑️ Yeni Oturum / Hafızayı Boşalt"):
        st.session_state.mevzuat_havuzu = []
        st.session_state.secili_madde = None
        st.rerun()
    
    st.divider()
    st.subheader("📂 Kaynak Yükle")
    uploaded_files = st.file_uploader("Mevzuat PDF'lerini Yükleyin", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        for f in uploaded_files:
            # Dosya zaten yüklenmiş mi kontrol et
            if not any(d['kaynak'] == f.name for d in st.session_state.mevzuat_havuzu):
                reader = PdfReader(f)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        # Maddelere bölme (Basit Madde/Art. ayrımı)
                        maddeler = re.split(r'(?i)(Madde\s+\d+)', text)
                        for j in range(1, len(maddeler), 2):
                            st.session_state.mevzuat_havuzu.append({
                                "kaynak": f"{f.name} - Sayfa {i+1}",
                                "metin": metin_temizle(maddeler[j] + maddeler[j+1])
                            })
        st.success(f"Havuzda {len(st.session_state.mevzuat_havuzu)} madde/parça var.")

# --- ANA EKRAN ---
st.title("🚀 Mevzuat Nokta Atışı ve Analiz")

if not api_key:
    st.warning("Lütfen API anahtarınızı girin.")
else:
    genai.configure(api_key=api_key)
    
    query = st.text_input("🔍 Aramak istediğiniz ibare (Örn: 'idari yaptırım kararı')", placeholder="Birebir eşleşme ve anlamsal analiz yapılır...")

    if query:
        # 1. ADIM: BİREBİR EŞLEŞMELERİ BUL
        tam_eslesmeler = tam_ibare_ara(query, st.session_state.mevzuat_havuzu)
        
        st.subheader(f"📍 '{query}' İbaresi Geçen Yerler")
        
        if not tam_eslesmeler:
            st.info("Birebir eşleşme bulunamadı, yapay zeka anlamsal benzerlikleri tarıyor...")
            # Burada anlamsal arama (Semantic search) devreye girebilir
        
        # SONUÇLARI KARTLAR HALİNDE GÖSTER
        cols = st.columns(2)
        for idx, res in enumerate(tam_eslesmeler[:6]): # İlk 6 sonucu göster
            with cols[idx % 2]:
                st.markdown(f"""
                <div style="border:1px solid #ddd; padding:15px; border-radius:10px; background:#f9f9f9; margin-bottom:10px; height: 200px; overflow: hidden; color: black;">
                    <strong style="color: #d32f2f;">Kaynak: {res['kaynak']}</strong><br>
                    <p style="font-size: 0.9rem;">{res['metin'][:300]}...</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🔎 Bu maddeyi detaylı analiz et", key=f"btn_{idx}"):
                    st.session_state.secili_madde = res

        # 2. ADIM: DETAYLI ANALİZ (Kullanıcı seçince tetiklenir)
        if st.session_state.secili_madde:
            st.divider()
            st.subheader("🤖 Seçili Madde Üzerine Detaylı AI Analizi")
            
            with st.spinner("Hukuki analiz hazırlanıyor..."):
                model = genai.GenerativeModel('gemini-2.5-flash')
                secili = st.session_state.secili_madde
                prompt = f"""
                Aşağıdaki mevzuat maddesini detaylıca analiz et. 
                1. Bu madde neyi yasaklar/emreder?
                2. Uygulanacak yaptırım nedir?
                3. Yetkili makam kimdir?
                4. Bu maddeyle ilgili dikkat edilmesi gereken kritik 'püf noktası' nedir?
                
                MADDE İÇERİĞİ:
                {secili['metin']}
                
                KAYNAK: {secili['kaynak']}
                """
                response = model.generate_content(prompt)
                
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.info(f"**İncelenen Kaynak:**\n{secili['kaynak']}")
                    st.write(secili['metin'])
                with col_b:
                    st.success("**AI Analiz Raporu**")
                    st.markdown(response.text)

    # EĞER HİÇBİR ŞEY YÜKLENMEMİŞSE GENEL ARAMA
    if not st.session_state.mevzuat_havuzu and query:
        st.info("Şu an yüklü belge yok. Gemini genel hukuk bilgisiyle cevap veriyor...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        res = model.generate_content(f"Türkiye'deki mevzuata göre '{query}' konusundaki temel hükümleri ve yaptırımları maddeler halinde açıkla.")
        st.markdown(res.text)
