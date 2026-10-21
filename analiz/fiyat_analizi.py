import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. READ-ONLY VERİTABANI BAĞLANTISI
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)
db_path = os.path.join(repo_dir, "steam-fiyat", "steam_fiyat_v2.db")

db_path_uri = db_path.replace("\\", "/")
uri = f"file:///{db_path_uri}?mode=ro"

grafik_klasoru = os.path.join(script_dir, "grafikler")
os.makedirs(grafik_klasoru, exist_ok=True)

try:
    conn = sqlite3.connect(uri, uri=True)

    # Verileri okuma
    query = "SELECT appid, isim, tarih, fiyat, durum FROM fiyat"
    df = pd.read_sql_query(query, conn)
    df['tarih'] = pd.to_datetime(df['tarih'])
    
    df_ucretli = df[df['durum'] == 'Ücretli'].copy()

    # En çok veri kaydı olan ilk 5 oyunu seçme
    top_oyunlar = df_ucretli['isim'].value_counts().head(20).index
    df_top = df_ucretli[df_ucretli['isim'].isin(top_oyunlar)]

    # --- MODERN STEAM DARK THEME AYARLARI ---
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='#171a21')
    ax.set_facecolor('#1b2838')  # Steam koyu mavi arka planı

    # Modern canlı renk paleti
    steam_paleti = ["#66c0f4", "#c7d5e0", "#2a475e", "#ff6b6b", "#4ebd6e"]

    sns.lineplot(
        data=df_top, 
        x='tarih', 
        y='fiyat', 
        hue='isim', 
        marker='o', 
        markersize=6,
        linewidth=2.5,
        palette=steam_paleti,
        ax=ax
    )

    # Başlık ve Eksen Düzenlemeleri
    ax.set_title("Hafta 1-2: Steam Fiyat Değişim Analizi", fontsize=14, fontweight='bold', color='#ffffff', pad=15)
    ax.set_xlabel("Tarih", fontsize=11, color='#c7d5e0', labelpad=10)
    ax.set_ylabel("Fiyat (USD)", fontsize=11, color='#c7d5e0', labelpad=10)
    
    # Izgara (Grid) ve Kenarlık Ayarları
    ax.grid(True, linestyle='--', alpha=0.2, color='#ffffff')
    for spine in ax.spines.values():
        spine.set_color('#2a475e')

    # Lejant (Kutucuk) Şekillendirme
    legend = ax.legend(title="Oyunlar", bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
    legend.get_frame().set_facecolor('#171a21')
    legend.get_frame().set_edgecolor('#2a475e')
    for text in legend.get_texts():
        text.set_color('#c7d5e0')
    legend.get_title().set_color('#ffffff')

    plt.tight_layout()
    
    grafik_yolu = os.path.join(grafik_klasoru, "ilk_fiyat_grafigi.png")
    plt.savefig(grafik_yolu, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    
    print(f"Modern Steam temalı grafik kaydedildi: {grafik_yolu}")

except Exception as e:
    print("Hata oluştu:", e)
finally:
    if 'conn' in locals():
        conn.close()