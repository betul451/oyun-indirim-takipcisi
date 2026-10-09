"""
Steam günlük fiyat toplayıcı (v2)

Kullanım:
  python steam_toplayici_v2.py              # verileri topla, sonra rapor yaz
  python steam_toplayici_v2.py --rapor      # toplama yapmadan sadece rapor
  python steam_toplayici_v2.py --cc us      # başka mağaza bölgesi (cc kodu)
  python steam_toplayici_v2.py --kur 36.5   # USD->TL kuru verirseniz fiyat_tl de yazılır

Gerekenler: pip install requests
"""
import argparse
import csv
import logging
import os
import sqlite3
import time
from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DB_DOSYASI = "steam_fiyat_v2.db"
VARSAYILAN_CC = "tr"
BEKLEME = 1.5  # oyunlar arası saniye
URL = "https://store.steampowered.com/api/appdetails"

# Ücretsiz oyunlarda API para birimi vermez; bölgeye göre varsayılan.
# Ücretli oyunlarda para birimi her zaman API cevabından okunur (sabit değil).
BOLGE_PARA = {"tr": "USD", "us": "USD", "eu": "EUR", "uk": "GBP"}

# Örnek liste: kendi 200-500 oyunluk listenizle değiştirin (appid: isim)
OYUNLAR_ORNEK = {
    730: "Counter-Strike 2",
    570: "Dota 2",
    1091500: "Cyberpunk 2077",
    1245620: "Elden Ring",
    292030: "The Witcher 3",
}


def oyunlari_yukle(yol="oyunlar.csv"):
    """oyunlar.csv varsa ondan okur, yoksa yukarıdaki örnek listeyi kullanır."""
    if not os.path.exists(yol):
        return OYUNLAR_ORNEK
    with open(yol, encoding="utf-8") as f:
        return {int(s["appid"]): s["isim"] for s in csv.DictReader(f)}


logging.basicConfig(
    filename="toplayici.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


# ---------- Oturum (retry + backoff) ----------
def oturum_olustur():
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=2,  # 2, 4, 8, 16 sn
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
        raise_on_status=False,  # tükenince cevabı döndür, biz yakalarız
    )
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "okul-projesi-fiyat-toplayici/2.0"})
    return s


# ---------- Veritabanı ----------
def db_hazirla(yol=DB_DOSYASI):
    con = sqlite3.connect(yol)
    con.execute(
        """CREATE TABLE IF NOT EXISTS fiyat (
            appid INTEGER,
            isim TEXT,
            tarih TEXT,
            bolge TEXT,
            fiyat REAL,
            normal_fiyat REAL,
            indirim_yuzde INTEGER,
            para_birimi TEXT,
            durum TEXT,
            fiyat_tl REAL,
            UNIQUE(appid, tarih, bolge)
        )"""
    )
    con.commit()
    return con


# ---------- Veri çekme ----------
def fiyat_cek(oturum, appid, cc):
    """
    Başarılıysa sözlük döner:
      durum = 'Ücretli' | 'Ücretsiz' | 'Fiyat yok'
    API gerçekten başarısızsa None döner (kayıt yazılmaz).
    """
    try:
        r = oturum.get(
            URL,
            params={"appids": appid, "cc": cc, "filters": "basic,price_overview"},
            timeout=15,
        )
        r.raise_for_status()
        veri = r.json().get(str(appid), {})
    except (requests.RequestException, ValueError) as e:
        logging.error("İstek başarısız appid=%s: %s", appid, e)
        return None

    if not veri.get("success"):
        logging.info("success=false appid=%s", appid)
        return None
    data = veri.get("data")
    if not isinstance(data, dict):
        return None

    po = data.get("price_overview")
    if po:
        return {
            "fiyat": po["final"] / 100,  # Steam minör birim verir
            "normal": po["initial"] / 100,
            "indirim": po["discount_percent"],
            "para": po["currency"],
            "durum": "Ücretli",
        }

    para = BOLGE_PARA.get(cc, "?")
    if data.get("is_free"):
        return {"fiyat": 0.0, "normal": 0.0, "indirim": 0, "para": para, "durum": "Ücretsiz"}

    # Ücretsiz değil ama fiyat da yok (çıkmamış, satıştan kalkmış, bölgede yok...)
    # Fiyat=0 yazılır ama durum ayrı tutulur ki model eğitiminde ayıklayabilin.
    return {"fiyat": 0.0, "normal": 0.0, "indirim": 0, "para": para, "durum": "Fiyat yok"}


def kaydet(con, appid, isim, bugun, cc, k, kur):
    fiyat_tl = round(k["fiyat"] * kur, 2) if (kur and k["para"] == "USD") else None
    con.execute(
        "INSERT OR IGNORE INTO fiyat VALUES (?,?,?,?,?,?,?,?,?,?)",
        (appid, isim, bugun, cc, k["fiyat"], k["normal"], k["indirim"],
         k["para"], k["durum"], fiyat_tl),
    )
    con.commit()


# ---------- Rapor ----------
def rapor_yaz(con, cc, limit=50):
    satirlar = con.execute(
        """SELECT f.isim, f.tarih, f.fiyat, f.normal_fiyat, f.indirim_yuzde,
                  f.para_birimi, f.durum, f.fiyat_tl
           FROM fiyat f
           JOIN (SELECT appid, MAX(tarih) t FROM fiyat WHERE bolge=? GROUP BY appid) m
             ON f.appid = m.appid AND f.tarih = m.t AND f.bolge = ?
           ORDER BY f.indirim_yuzde DESC, f.isim
           LIMIT ?""",
        (cc, cc, limit),
    ).fetchall()

    if not satirlar:
        print("Veritabanında kayıt yok.")
        return

    basliklar = ["Oyun", "Tarih", "Fiyat", "Normal", "İnd.%", "Para", "Durum", "TL"]
    tablo = [basliklar]
    for isim, tarih, fiyat, normal, ind, para, durum, tl in satirlar:
        tablo.append([
            (isim or "")[:28], tarih, f"{fiyat:.2f}", f"{normal:.2f}",
            str(ind), para or "", durum or "", f"{tl:.2f}" if tl is not None else "-",
        ])
    genislik = [max(len(str(s[i])) for s in tablo) for i in range(len(basliklar))]

    def satir(s):
        return " | ".join(str(h).ljust(genislik[i]) for i, h in enumerate(s))

    print(f"\nSon kayıtlar (bölge: {cc}, en yüksek indirim üstte)")
    print(satir(tablo[0]))
    print("-+-".join("-" * g for g in genislik))
    for s in tablo[1:]:
        print(satir(s))
    print(f"\nToplam {len(satirlar)} oyun gösterildi.")


# ---------- Ana akış ----------
def main():
    ap = argparse.ArgumentParser(description="Steam günlük fiyat toplayıcı")
    ap.add_argument("--rapor", action="store_true", help="toplama yapma, sadece rapor yaz")
    ap.add_argument("--cc", default=VARSAYILAN_CC, help="mağaza bölgesi kodu (varsayılan: tr)")
    ap.add_argument("--kur", type=float, default=None, help="USD->TL kuru (ör. 36.5)")
    a = ap.parse_args()

    con = db_hazirla()

    if not a.rapor:
        oturum = oturum_olustur()
        bugun = date.today().isoformat()
        sayac = {"Ücretli": 0, "Ücretsiz": 0, "Fiyat yok": 0, "Hata": 0}

        for appid, isim in oyunlari_yukle().items():
            try:
                k = fiyat_cek(oturum, appid, a.cc)
                if k is None:
                    sayac["Hata"] += 1
                else:
                    kaydet(con, appid, isim, bugun, a.cc, k, a.kur)
                    sayac[k["durum"]] += 1
            except Exception as e:  # tek oyun yüzünden her şey durmasın
                sayac["Hata"] += 1
                logging.error("Beklenmeyen hata %s: %s", appid, e)
            time.sleep(BEKLEME)

        logging.info("Bitti: %s", sayac)
        print("Toplama bitti:", sayac)

    rapor_yaz(con, a.cc)
    con.close()


if __name__ == "__main__":
    main()
