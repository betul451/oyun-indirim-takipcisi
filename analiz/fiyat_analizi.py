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
    print("Veritabanına salt okunur modda bağlanıldı.")

    # Tüm veri setini çek
    query = "SELECT appid, isim, tarih, fiyat, normal_fiyat, indirim_yuzde, durum FROM fiyat"
    df = pd.read_sql_query(query, conn)
    df['tarih'] = pd.to_datetime(df['tarih'])
    df_ucretli = df[df['durum'] == 'Ücretli'].copy()

    # --- STEAM KARANLIK TEMA AYARLARI ---
    plt.style.use('dark_background')
    steam_mavi = "#66c0f4"
    steam_arkaplan = "#171a21"
    steam_panel = "#1b2838"

    # =========================================================================
    # GRAFİK 1 (Hafta 1-2): Zaman İçindeki Fiyat Değişimi
    # =========================================================================
    top_oyunlar = df_ucretli['isim'].value_counts().head(5).index
    df_top = df_ucretli[df_ucretli['isim'].isin(top_oyunlar)]

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=steam_arkaplan)
    ax.set_facecolor(steam_panel)
    sns.lineplot(data=df_top, x='tarih', y='fiyat', hue='isim', marker='o', palette="Set2", ax=ax)
    ax.set_title("Hafta 1-2: Örnek Oyunların Fiyat Değişimi", color='#ffffff', fontsize=12, fontweight='bold')
    ax.set_xlabel("Tarih", color='#c7d5e0')
    ax.set_ylabel("Fiyat (USD)", color='#c7d5e0')
    ax.grid(True, linestyle='--', alpha=0.2)
    ax.legend(title="Oyunlar", bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(grafik_klasoru, "1_fiyat_degisimi.png"), dpi=300)
    plt.close()

    # =========================================================================
    # GRAFİK 2 (Hafta 3-4): İndirim Yüzdesi Dağılımı (Histogram)
    # =========================================================================
    # Sadece indirimde olan (indirim_yuzde > 0) günleri çekiyoruz
    indirimli_veriler = df_ucretli[df_ucretli['indirim_yuzde'] > 0]

    fig, ax = plt.subplots(figsize=(9, 5), facecolor=steam_arkaplan)
    ax.set_facecolor(steam_panel)
    
    if not indirimli_veriler.empty:
        sns.histplot(indirimli_veriler['indirim_yuzde'], bins=10, kde=True, color=steam_mavi, ax=ax)
        ax.set_title("Hafta 3-4: İndirim Yüzdesi Dağılımı", color='#ffffff', fontsize=12, fontweight='bold')
        ax.set_xlabel("İndirim Oranı (%)", color='#c7d5e0')
        ax.set_ylabel("Gözlemlenen İndirim Sayısı", color='#c7d5e0')
    else:
        ax.text(0.5, 0.5, "Henüz indirimli kayıt yok", ha='center', va='center', color='#ffffff')
        ax.set_title("Hafta 3-4: İndirim Yüzdesi Dağılımı", color='#ffffff')

    ax.grid(True, linestyle='--', alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(grafik_klasoru, "2_indirim_yuzdesi_dagilimi.png"), dpi=300)
    plt.close()

    # =========================================================================
    # GRAFİK 3 (Hafta 3-4): Oyunların İndirime Girme Sıklığı
    # =========================================================================
    # Hangi oyun kaç gün indirime girmiş?
    indirim_sikligi = indirimli_veriler['isim'].value_counts().head(8)

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=steam_arkaplan)
    ax.set_facecolor(steam_panel)

    if not indirim_sikligi.empty:
        sns.barplot(x=indirim_sikligi.values, y=indirim_sikligi.index, palette="Blues_r", ax=ax)
        ax.set_title("Hafta 3-4: En Çok İndirime Giren Oyunlar (İndirim Sıklığı)", color='#ffffff', fontsize=12, fontweight='bold')
        ax.set_xlabel("İndirimde Geçirilen Gün Sayısı", color='#c7d5e0')
        ax.set_ylabel("Oyun Adı", color='#c7d5e0')
    else:
        ax.text(0.5, 0.5, "Henüz indirim verisi tespit edilmedi", ha='center', va='center', color='#ffffff')
        ax.set_title("Hafta 3-4: İndirim Sıklığı", color='#ffffff')

    ax.grid(True, linestyle='--', alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(grafik_klasoru, "3_indirim_sikligi.png"), dpi=300)
    plt.close()

    # =========================================================================
    # GRAFİK 4 (Hafta 3-4): Aylık/Mevsimsel İndirim Yoğunluğu
    # =========================================================================
    df_ucretli['ay_yil'] = df_ucretli['tarih'].dt.strftime('%Y-%m')
    aylik_indirim = df_ucretli[df_ucretli['indirim_yuzde'] > 0]['ay_yil'].value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=steam_arkaplan)
    ax.set_facecolor(steam_panel)

    if not aylik_indirim.empty:
        sns.barplot(x=aylik_indirim.index, y=aylik_indirim.values, color='#4ebd6e', ax=ax)
        ax.set_title("Hafta 3-4: Aylara Göre İndirim Yoğunluğu (Mevsimsel Trend)", color='#ffffff', fontsize=12, fontweight='bold')
        ax.set_xlabel("Yıl - Ay", color='#c7d5e0')
        ax.set_ylabel("Toplam İndirim Olayı", color='#c7d5e0')
        plt.xticks(rotation=45)
    else:
        ax.text(0.5, 0.5, "Henüz aylık indirim verisi birikmedi", ha='center', va='center', color='#ffffff')
        ax.set_title("Hafta 3-4: Mevsimsel İndirim Trendi", color='#ffffff')

    ax.grid(True, linestyle='--', alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(grafik_klasoru, "4_mevsimsel_indirimler.png"), dpi=300)
    plt.close()

    print("Hafta 3-4 EDA analizleri tamamlandı! Tüm grafikler 'analiz/grafikler/' klasörüne kaydedildi.")

except Exception as e:
    print("Hata oluştu:", e)
finally:
    if 'conn' in locals():
        conn.close()