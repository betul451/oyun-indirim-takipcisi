# SteamSpy'dan popüler ücretli oyunları çekip oyunlar.csv oluşturur
import csv
import time

import requests

ISTEKLER = ['top100in2weeks', 'top100forever', 'top100owned', 'all']
HEDEF = 300


def main():
    secilen = {}
    for istek in ISTEKLER:
        r = requests.get('https://steamspy.com/api.php',
                         params={'request': istek}, timeout=30)
        r.raise_for_status()
        for appid, v in r.json().items():
            if int(v.get('initialprice') or 0) > 0:  # sadece ücretli oyunlar
                secilen[int(appid)] = v.get('name', str(appid))
        time.sleep(2)  # sunucuya nazik ol
    liste = list(secilen.items())[:HEDEF]
    with open('oyunlar.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['appid', 'isim'])
        w.writerows(liste)
    print(f'{len(liste)} oyun yazıldı: oyunlar.csv')


if __name__ == '__main__':
    main()