import streamlit as st
import sqlite3
import pandas as pd
import os
import random

# --- SAYFA VE CSS AYARLARI ---
st.set_page_config(page_title="Steam Fiyat Takipçisi", page_icon="🎮", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #171a21; color: #c7d5e0; }
    h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
    [data-testid="stMetricValue"] { color: #66c0f4 !important; font-size: 2rem !important; }
    div[data-testid="stVerticalBlock"] { gap: 1rem; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🎮 Steam Fiyat Analizi")
st.markdown("Yapay Zeka Destekli Al/Bekle Önerisi")
st.divider()

# --- VERİTABANI BAĞLANTISI ---
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)
db_path = os.path.join(repo_dir, "steam-fiyat", "steam_fiyat_v2.db")
db_path_uri = db_path.replace("\\", "/")
uri = f"file:///{db_path_uri}?mode=ro"

def sahte_tahmin(oyun_adi):
    karar = random.choice(["ŞİMDİ AL!", "İNDİRİMİ BEKLE!"])
    skor = round(random.uniform(0.60, 0.99), 2)
    return karar, skor

# --- ARAMA BÖLÜMÜ ---
aranan_oyun = st.text_input("🔍 İncelemek İstediğiniz Oyunu Arayın:", placeholder="Örn: Palworld, Among Us...")

if aranan_oyun:
    try:
        conn = sqlite3.connect(uri, uri=True)
        query = "SELECT tarih, fiyat, normal_fiyat, indirim_yuzde FROM fiyat WHERE isim LIKE ? COLLATE NOCASE"
        df = pd.read_sql_query(query, conn, params=('%' + aranan_oyun + '%',))
        
        if not df.empty:
            df['tarih'] = pd.to_datetime(df['tarih'])
            df['fiyat'] = pd.to_numeric(df['fiyat'], errors='coerce') 
            
            # Verileri tarihe göre sırala ve çoklu bölge çakışmasını engelle
            df = df.sort_values(by='tarih')
            df = df.drop_duplicates(subset=['tarih'], keep='last')
            df = df.reset_index(drop=True)
            
            son_fiyat = df.iloc[-1]['fiyat']
            normal_fiyat = df.iloc[-1]['normal_fiyat']
            indirim = df.iloc[-1]['indirim_yuzde']
            
            # --- METRİKLER YAN YANA ---
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Satış Fiyatı", value=f"${son_fiyat:.2f}", delta=f"-%{indirim} İndirim" if indirim > 0 else None)
            with col2:
                st.metric(label="Normal Fiyat", value=f"${normal_fiyat:.2f}")
            with col3:
                karar, skor = sahte_tahmin(aranan_oyun)
                if "AL" in karar:
                    st.success(f"**🤖 {karar}**\n\nGüven: %{int(skor*100)}")
                else:
                    st.warning(f"**🤖 {karar}**\n\nGüven: %{int(skor*100)}")
            
            st.divider()
            
            # --- YENİ VE KESİN ÇÖZÜM: YERLEŞİK GRAFİK ---
            st.subheader("📈 Fiyat Geçmişi")
            
            # Sadece tarih ve fiyatı Streamlit'in kendi grafiğine ver
            df_grafik = df[['tarih', 'fiyat']].set_index('tarih')
            st.line_chart(df_grafik, use_container_width=True)
            
            # Geliştirici modu: Verinin arka planda nasıl göründüğünü kontrol etmek için
            with st.expander("🛠️ Geliştirici Modu (Veri Tablosunu Göster)"):
                st.dataframe(df)

        else:
            st.error("❌ Oyun veritabanında bulunamadı. Lütfen adını tam yazmayı deneyin.")
            
    except Exception as e:
        st.error(f"Veritabanı hatası: {e}")
    finally:
        if 'conn' in locals():
            conn.close()