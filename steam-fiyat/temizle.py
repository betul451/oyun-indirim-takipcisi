import os
import sqlite3

import pandas as pd

BOT_DB = 'steam_fiyat_v2.db'
ITAD_CSV = 'veri/gecmis_itad.csv'
CIKTI = 'veri/temiz_veri.csv'


def botu_oku():
    con = sqlite3.connect(BOT_DB)
    df = pd.read_sql('SELECT * FROM fiyat', con)
    con.close()
    print('Bot ham satır sayısı:', len(df))
    df = df[df['durum'] == 'Ücretli']
    df['tarih'] = pd.to_datetime(df['tarih'])
    df = df.drop_duplicates(['appid', 'tarih'])
    df = df[(df['fiyat'] > 0) & (df['normal_fiyat'] > 0)]
    df = df[df['indirim_yuzde'].between(0, 100)]
    df = df[['appid', 'isim', 'tarih', 'fiyat', 'normal_fiyat',
             'indirim_yuzde', 'para_birimi']].copy()
    df['kaynak'] = 'bot'
    print('Bot temiz satır sayısı:', len(df))
    return df


def itad_gunluge_cevir(ev):
    ev['zaman'] = pd.to_datetime(ev['zaman'], utc=True)
    ev['tarih'] = ev['zaman'].dt.tz_convert(None).dt.normalize()
    ev = ev.sort_values('zaman').drop_duplicates(['appid', 'tarih'], keep='last')
    ev = ev[(ev['fiyat'] > 0) & (ev['normal_fiyat'] > 0)]
    bugun = pd.Timestamp.today().normalize()
    parcalar = []
    for appid, g in ev.groupby('appid'):
        g = g.set_index('tarih')
        gunler = pd.date_range(g.index.min(), bugun, freq='D')
        d = g.reindex(gunler).ffill()
        d.index.name = 'tarih'
        d['appid'] = appid
        parcalar.append(d.reset_index())
    d = pd.concat(parcalar, ignore_index=True)
    d = d[['appid', 'isim', 'tarih', 'fiyat', 'normal_fiyat', 'indirim_yuzde', 'para_birimi']]
    d['kaynak'] = 'itad'
    print('ITAD günlük satır sayısı:', len(d))
    return d


def main():
    bot = botu_oku()
    if os.path.exists(ITAD_CSV):
        itad = itad_gunluge_cevir(pd.read_csv(ITAD_CSV))
        df = pd.concat([itad, bot], ignore_index=True)
        df = df.drop_duplicates(['appid', 'tarih'], keep='last')
    else:
        print('UYARI: ITAD dosyası yok, sadece bot verisi kullanılıyor.')
        df = bot

    para = df['para_birimi'].value_counts()
    print('Para birimleri:')
    print(para)
    if len(para) > 1:
        print('UYARI: birden fazla para birimi var, sadece', para.index[0], 'tutuluyor')
        df = df[df['para_birimi'] == para.index[0]]

    df = df.sort_values(['appid', 'tarih']).reset_index(drop=True)

    os.makedirs('veri', exist_ok=True)
    df.to_csv(CIKTI, index=False)
    print('--- ÖZET ---')
    print('Toplam satır:', len(df), '| Oyun sayısı:', df['appid'].nunique())
    print('Tarih aralığı:', df['tarih'].min().date(), '->', df['tarih'].max().date())
    print(df['kaynak'].value_counts().to_string())
    print('Yazıldı:', CIKTI)


if __name__ == '__main__':
    main()