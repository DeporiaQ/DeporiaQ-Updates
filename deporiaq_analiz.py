"""Read-only operational analysis. No network, schema changes or stock writes."""
from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil
import csv
import unicodedata


def normalize(value):
    text = str(value).replace('ı', 'i').replace('İ', 'i').casefold()
    return ''.join(c for c in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(c))


def matches(values, query):
    text = normalize(' '.join(map(str, values)))
    return all(part in text for part in normalize(query).split())


def excel_safe(value):
    # Preserve barcode strings and prevent spreadsheet formula execution.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def export_csv(path, headers, rows):
    with open(path, 'w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream, delimiter=';')
        writer.writerow(headers)
        writer.writerows([[excel_safe(v) for v in row] for row in rows])


def parse_date(value):
    for fmt in ('%d.%m.%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(str(value)[:19], fmt)
        except ValueError:
            pass
    return None


REPORTS = [
    ('search', '01 · Tüm Depolarda Arama'),
    ('runway', '02 · Stok Tükenme Analizi'),
    ('abc', '03 · ABC Satış Analizi'),
    ('idle', '04 · Hareketsiz Stoklar'),
    ('transfer', '05 · Depolar Arası Dengeleme'),
    ('purchase', '06 · Satın Alma Planı'),
    ('locations', '07 · Depo / Şube Karşılaştırması'),
    ('daily', '08 · Günlük Satış ve Brüt Kâr'),
    ('count', '09 · Sayım Çalışma Listesi'),
]


class Analysis:
    def __init__(self, connection, now=None):
        self.now = now or datetime.now()
        self.locations = [dict(r) for r in connection.execute(
            'SELECT id,ad,tur FROM konumlar WHERE aktif=1 ORDER BY ad')]
        self.products = {r['id']: dict(r) for r in connection.execute(
            'SELECT id,barkod,ad,fiyat,alis_fiyati,kritik_stok FROM urunler WHERE aktif=1')}
        self.stock = {(r['urun_id'], r['konum_id']): r['miktar']
                      for r in connection.execute('SELECT urun_id,konum_id,miktar FROM stoklar')}
        self.movements = []
        self.invalid_dates = 0
        # Ignore future-dated records for forecasts and historical reports.
        for r in connection.execute('SELECT * FROM stok_hareketleri'):
            item = dict(r)
            item['date'] = parse_date(item['tarih_saat'])
            if item['date'] is None:
                self.invalid_dates += 1
            elif item['date'] <= self.now:
                self.movements.append(item)

    def sales(self, days, location=None):
        start = (self.now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return [dict(h,miktar=-h['miktar']) if h['hareket_turu']=='IADE' else h for h in self.movements if h['hareket_turu'] in ('SATIS','IADE')
                and h['date'] >= start
                and (location is None or h['kaynak_konum_id'] == location)]

    def entries(self, location=None):
        for loc in self.locations:
            if location is not None and loc['id'] != location:
                continue
            for uid, p in self.products.items():
                yield loc, p, self.stock.get((uid, loc['id']), 0)

    def report(self, kind, location=None, days=30, cover=14):
        if not 1 <= days <= 365 or not 1 <= cover <= 365:
            raise ValueError('Gün aralığı 1–365 olmalıdır.')
        sales = self.sales(days, location)
        demand = defaultdict(int)
        for h in sales:
            demand[(h['urun_id'], h['kaynak_konum_id'])] += h['miktar']
        rows = []
        if kind == 'search':
            headers = ['Konum', 'Barkod', 'Ürün', 'Stok', 'Kritik', 'Satış fiyatı', 'Stok satış değeri']
            for loc, p, qty in self.entries(location):
                rows.append([loc['ad'], p['barkod'], p['ad'], qty, p['kritik_stok'], p['fiyat'], round(qty*p['fiyat'], 2)])
            note = 'Ürün adı, barkod ve konumu birlikte arayın. Stok kaydı olmayan aktif ürünler 0 gösterilir.'
        elif kind in ('runway', 'purchase'):
            headers = (['Konum', 'Barkod', 'Ürün', 'Stok', 'Satılan adet', 'Günlük satış', 'Tahmini gün', 'Durum']
                       if kind == 'runway' else ['Konum', 'Barkod', 'Ürün', 'Stok', 'Hedef stok', 'Önerilen adet', 'Tahmini alış tutarı'])
            for loc, p, qty in self.entries(location):
                sold = demand[(p['id'], loc['id'])]
                rate = max(0,sold) / days
                remaining = qty/rate if rate else None
                if kind == 'runway':
                    state = 'Stok yok' if qty == 0 else ('Satış verisi yok' if remaining is None else ('7 gün içinde' if remaining <= 7 else 'İzle'))
                    rows.append([loc['ad'], p['barkod'], p['ad'], qty, sold, round(rate, 2), round(remaining, 1) if remaining is not None else '—', state])
                else:
                    target = max(ceil(rate*cover), max(0, p['kritik_stok'])*2)
                    need = max(0, target - qty)
                    if need:
                        rows.append([loc['ad'], p['barkod'], p['ad'], qty, target, need, round(need*p['alis_fiyati'], 2)])
            note = (f'Son {days} takvim gününün ortalama satışına dayanır; kesin tahmin değildir. Transfer talebi dahil değildir.'
                    if kind == 'runway' else f'Hedef = {cover} günlük satış ihtiyacı veya kritik stok × 2 değerlerinden büyüğü. Transfer fazlasını önce kontrol edin. Alış tutarı ürün kartı maliyetidir.')
        elif kind == 'abc':
            totals = defaultdict(lambda: [0, 0.0])
            for h in sales:
                totals[h['urun_id']][0] += h['miktar']
                totals[h['urun_id']][1] += float(h['toplam_tutar'] or 0)
            total = sum(v[1] for v in totals.values())
            cumulative = 0
            headers = ['Barkod', 'Ürün', 'Satılan adet', 'Ciro', 'Ciro payı %', 'Kümülatif %', 'Sınıf']
            for uid, (qty, revenue) in sorted(totals.items(), key=lambda x: (-x[1][1], x[0])):
                p = self.products.get(uid, {'barkod': '—', 'ad': f'Pasif ürün #{uid}'})
                group = ('A' if cumulative < .8*total else ('B' if cumulative < .95*total else 'C')) if total else '—'
                cumulative += revenue
                rows.append([p['barkod'], p['ad'], qty, round(revenue, 2), round(revenue/total*100, 2) if total else 0, round(cumulative/total*100, 2) if total else 0, group])
            note = 'Ciroya göre sıralanır: ilk %80 A, sonraki %15 B, kalanı C. Sınırı aşan ürün başladığı sınıfta kalır. Satış kaydı olmayan ürünler dahil edilmez.'
        elif kind == 'idle':
            latest = {}
            for h in self.movements:
                for lid in (h['kaynak_konum_id'], h['hedef_konum_id']):
                    key = h['urun_id'], lid
                    latest[key] = max(latest.get(key, datetime.min), h['date'])
            headers = ['Konum', 'Barkod', 'Ürün', 'Stok', 'Son hareket', 'Hareketsiz gün', 'Bağlı alış değeri']
            for loc, p, qty in self.entries(location):
                last = latest.get((p['id'], loc['id']))
                age = (self.now-last).days if last else None
                if qty > 0 and (age is None or age >= days):
                    rows.append([loc['ad'], p['barkod'], p['ad'], qty, last.strftime('%d.%m.%Y') if last else 'Kayıt yok', age if age is not None else 'Bilinmiyor', round(qty*p['alis_fiyati'], 2)])
            note = f'En az {days} gündür giriş, satış veya transfer hareketi olmayan stoklar. Kayıt yoksa yaş uydurulmaz.'
        elif kind == 'transfer':
            headers = ['Barkod', 'Ürün', 'Kaynak', 'Hedef', 'Önerilen adet']
            for uid, p in self.products.items():
                threshold = max(0, p['kritik_stok'])
                donors = [[loc, max(0, self.stock.get((uid,loc['id']),0)-threshold*2)] for loc in self.locations]
                donors.sort(key=lambda item: (-item[1], item[0]['id']))
                for dest in self.locations:
                    if location is not None and dest['id'] != location:
                        continue
                    need = max(0, threshold-self.stock.get((uid,dest['id']),0))
                    for donor in donors:
                        if donor[0]['id'] == dest['id'] or not need:
                            continue
                        amount = min(need, donor[1])
                        if amount:
                            rows.append([p['barkod'], p['ad'], donor[0]['ad'], dest['ad'], amount])
                            donor[1] -= amount
                            need -= amount
            note = 'Kaynakta kritik stok × 2 korunur; hedef kritik seviyeye tamamlanır. Aynı fazla stok iki kez önerilmez. Bu liste stokları değiştirmez.'
        elif kind == 'locations':
            headers = ['Konum', 'Tür', 'Stok adedi', 'Alış değeri', 'Satış değeri', 'Kritik ürün', 'Dönem cirosu', 'Dönem brüt kâr']
            for loc in self.locations:
                if location is not None and loc['id'] != location:
                    continue
                entries = list(self.entries(loc['id']))
                relevant = [h for h in sales if h['kaynak_konum_id'] == loc['id']]
                revenue = sum(float(h['toplam_tutar'] or 0) for h in relevant)
                profit = sum(float(h['toplam_tutar'] or 0)-float(h['alis_fiyati'] or 0)*h['miktar'] for h in relevant)
                rows.append([loc['ad'], loc['tur'], sum(q for _,_,q in entries), round(sum(q*p['alis_fiyati'] for _,p,q in entries),2), round(sum(q*p['fiyat'] for _,p,q in entries),2), sum(q <= p['kritik_stok'] for _,p,q in entries), round(revenue,2), round(profit,2)])
            note = 'Stok bugünkü anlık değerdir; ciro ve brüt kâr seçilen döneme aittir. Eksik geçmiş maliyet 0 kabul edilir; brüt kâr net kâr değildir.'
        elif kind == 'daily':
            headers = ['Tarih', 'Satış satırı', 'Satılan adet', 'Ciro', 'Brüt kâr']
            by_day = defaultdict(list)
            for h in sales:
                by_day[h['date'].date()].append(h)
            for offset in range(days):
                day = (self.now-timedelta(days=offset)).date()
                values = by_day[day]
                revenue = sum(float(h['toplam_tutar'] or 0) for h in values)
                cost = sum(float(h['alis_fiyati'] or 0)*h['miktar'] for h in values)
                rows.append([day.strftime('%d.%m.%Y'), len(values), sum(h['miktar'] for h in values), round(revenue,2), round(revenue-cost,2)])
            note = 'Satış satırı fiş sayısı değildir. Satış olmayan günler 0 görünür. Brüt kâr, kayıtlı ciro eksi kayıtlı alış maliyetidir; gider/vergi içermez.'
        elif kind == 'count':
            headers = ['Konum', 'Barkod', 'Ürün', 'Sistem stoğu', 'Sayılan', 'Not']
            rows = [[loc['ad'],p['barkod'],p['ad'],qty,'',''] for loc,p,qty in self.entries(location)]
            note = 'CSV veya PDF çıktısını sayımda kullanın. Sayılan ve Not alanları boş bırakılır. Sayımı uygulamak için mevcut Stok Sayımı ekranını kullanın.'
        else:
            raise ValueError('Bilinmeyen rapor')
        if self.invalid_dates:
            note += f' Tarihi okunamayan {self.invalid_dates} hareket tarih analizine alınmadı.'
        return headers, rows, note
