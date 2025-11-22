import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Borsa Pro", layout="wide", initial_sidebar_state="expanded")

# --- SABİTLER ---
HISSE_DOSYASI = 'hisse_listesi.csv'
PORTFOY_DOSYASI = 'portfoy.csv'
SIFRE = "1234"  # Sitenin şifresi burada

# --- FONKSİYONLAR ---
@st.cache_data
def hisse_listesi_yukle():
    try:
        if os.path.exists(HISSE_DOSYASI):
            try:
                df = pd.read_csv(HISSE_DOSYASI)
            except:
                df = pd.read_excel(HISSE_DOSYASI.replace('.csv', '.xlsx'))
            if 'Sembol' in df.columns:
                return df['Sembol'].astype(str).str.strip().unique().tolist()
        return []
    except:
        return []

def portfoy_yukle():
    if not os.path.exists(PORTFOY_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Sembol", "IslemTuru", "Adet", "Fiyat", "Tutar"])
        df.to_csv(PORTFOY_DOSYASI, index=False)
        return df
    return pd.read_csv(PORTFOY_DOSYASI)

def islem_kaydet(tarih, sembol, islem_turu, adet, fiyat):
    df = portfoy_yukle()
    tutar = adet * fiyat
    yeni_veri = pd.DataFrame({
        "Tarih": [tarih], "Sembol": [sembol], "IslemTuru": [islem_turu],
        "Adet": [adet], "Fiyat": [fiyat], "Tutar": [tutar]
    })
    pd.concat([df, yeni_veri], ignore_index=True).to_csv(PORTFOY_DOSYASI, index=False)

# --- GİRİŞ KONTROLÜ ---
if "giris" not in st.session_state: st.session_state["giris"] = False
if not st.session_state["giris"]:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.header("🔒 Güvenli Giriş")
        if st.text_input("Şifre", type="password") == SIFRE:
            if st.button("Giriş"): st.session_state["giris"] = True; st.rerun()
        else: st.stop()

# --- MENÜ VE SAYFALAR ---
sayfa = st.sidebar.radio("Menü", ["Canlı Piyasa", "Portföy Yönetimi", "Ayarlar"])
tum_hisseler = hisse_listesi_yukle()

if sayfa == "Canlı Piyasa":
    st.title("📈 Canlı Piyasa")
    secilenler = st.multiselect("Hisseler", tum_hisseler, default=tum_hisseler[:5] if tum_hisseler else [])
    filtre = st.selectbox("Filtre", ["Tümü", "Yükselenler", "Düşenler"])
    
    if st.button("Verileri Getir 🔄"):
        veriler = []
        for s in secilenler:
            try:
                t = yf.Ticker(s); h = t.history(period="2d")
                if not h.empty:
                    son = h['Close'].iloc[-1]; onceki = h['Close'].iloc[0] if len(h)>1 else son
                    veriler.append({"Sembol": s, "Fiyat": son, "Değişim %": ((son-onceki)/onceki)*100})
            except: pass
            
        if veriler:
            df = pd.DataFrame(veriler)
            if filtre == "Yükselenler": df = df[df["Değişim %"] > 0]
            if filtre == "Düşenler": df = df[df["Değişim %"] < 0]
            st.dataframe(df.style.applymap(lambda v: f'color: {"green" if v>0 else "red"}', subset=['Değişim %'])
                         .format({"Fiyat": "{:.2f}", "Değişim %": "%{:.2f}"}), use_container_width=True)
            
            # GRAFİK
            g_sembol = st.selectbox("Grafik Çiz", secilenler)
            if g_sembol:
                d = yf.download(g_sembol, period="3mo", interval="1d", progress=False)
                if not d.empty:
                    st.plotly_chart(go.Figure(data=[go.Candlestick(x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'])])
                                    .update_layout(title=f"{g_sembol} Mum Grafiği", template="plotly_dark", height=500), use_container_width=True)

elif sayfa == "Portföy Yönetimi":
    st.title("💼 Portföyüm")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("islem"):
            s = st.selectbox("Hisse", tum_hisseler); tur = st.radio("Tip", ["ALIS", "SATIS"])
            a = st.number_input("Adet", 1); f = st.number_input("Fiyat", 0.01)
            if st.form_submit_button("Kaydet"): islem_kaydet(datetime.now(), s, tur, a, f); st.success("Kaydedildi")
    with c2:
        df = portfoy_yukle()
        if not df.empty:
            st.dataframe(df.sort_values("Tarih", ascending=False), use_container_width=True)
            # Basit özet
            st.info(f"Toplam İşlem Hacmi: {df['Tutar'].sum():,.2f}")

elif sayfa == "Ayarlar":
    st.title("⚙️ Ayarlar")
    up = st.file_uploader("Listeyi Güncelle", type=['csv','xlsx'])
    if up: 
        with open(HISSE_DOSYASI, "wb") as f: f.write(up.getbuffer())
        st.success("Yüklendi! Sayfayı yenileyin.")