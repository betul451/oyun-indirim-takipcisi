import csv
import os
import sys
import time
import requests

KEY = os.environ.get('ITAD_KEY')
BASE = 'https://api.isthereanydeal.com'
ULKE = 'US'
STEAM_SHOP_ID = 61
BEKLEME = 0.5
CIKTI = 'veri/gecmis_itad_us.csv'

def oyunlari_oku(yol='oyunlar.csv'):
    with open(yol, encoding='utf-8') as f:
        return {int(s['appid']): s['isim'] for s in csv.DictReader(f)}

def istek(oturum, metot, yol, **kw):
    for _ in range(4):
        r = oturum.request(metot, BASE + yol, timeout=30, **kw)
        if r.status_code == 429:
            time.sleep(int(r.headers.get('Retry-After', 30)))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError('Çok fazla 429 hatası: ' + yol)

def main():
    if not KEY:
        sys.exit('ITAD_KEY ayarlı değil. Önce API anahtarını ortam değişkenine koyun.')
    
    oyunlar = oyunlari_oku()
    oturum = requests.Session()
    oturum.headers.update({'ITAD-API-Key': KEY})

    idler = {}
    appler = list(oyunlar)
    for i in range(0, len(appler), 100):
        parca = ['app/' + str(a) for a in appler[i:i + 100]]
        cevap = istek(oturum, 'POST', f'/lookup/id/shop/{STEAM_SHOP_ID}/v1', json=parca)
        for anahtar, itad_id in cevap.items():
            if itad_id:
                idler[int(anahtar.split('/')[1])] = itad_id
        time.sleep(BEKLEME)
    print(f'{len(idler)}/{len(oyunlar)} oyun ITAD üzerinde bulundu.')

    satirlar, hatali = [], []
    for n, (appid, itad_id) in enumerate(idler.items(), 1):
        try:
            olaylar = istek(oturum, 'GET', '/games/history/v2', params={'id': itad_id, 'country': ULKE, 'shops': STEAM_SHOP_ID})
            for o in olaylar:
                d = o['deal']
                satirlar.append([
                    appid, oyunlar[appid], itad_id, o['timestamp'],
                    d['price']['amount'], d['regular']['amount'],
                    d['cut'], d['price']['currency']
                ])
        except Exception as e:
            hatali.append(appid)
            print('Hata:', appid, e)
        if n % 25 == 0:
            print(f'{n}/{len(idler)} oyun işlendi...')
        time.sleep(BEKLEME)

    os.makedirs('veri', exist_ok=True)
    with open(CIKTI, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['appid', 'isim', 'itad_id', 'zaman', 'fiyat', 'normal_fiyat', 'indirim_yuzde', 'para_birimi'])
        w.writerows(satirlar)
    print(f'Bitti! {len(satirlar)} fiyat değişimi kaydedildi: {CIKTI}')

if __name__ == '__main__':
    main()