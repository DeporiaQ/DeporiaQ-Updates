import csv
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deporiaq_analiz import Analysis, REPORTS, export_csv, matches

@pytest.fixture
def db():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('''
    CREATE TABLE konumlar(id,ad,tur,aktif);
    CREATE TABLE urunler(id,barkod,ad,fiyat,alis_fiyati,kritik_stok,aktif);
    CREATE TABLE stoklar(urun_id,konum_id,miktar);
    CREATE TABLE stok_hareketleri(id,urun_id,kaynak_konum_id,hedef_konum_id,miktar,hareket_turu,tarih_saat,birim_fiyat,toplam_tutar,alis_fiyati);
    INSERT INTO konumlar VALUES(1,'Merkez','MERKEZ',1),(2,'İzmir','SUBE',1),(3,'Manisa','SUBE',1),(4,'Kapalı','SUBE',0);
    INSERT INTO urunler VALUES(1,'00123','Kitap',10,4,10,1),(2,'00234','Çizgi Roman',20,8,5,1),(3,'00999','Pasif',3,1,5,0);
    INSERT INTO stoklar VALUES(1,1,35),(1,2,0),(1,3,0),(2,1,3),(2,2,5),(3,1,99);
    INSERT INTO stok_hareketleri VALUES
    (1,1,2,NULL,30,'SATIS','06.10.2026 10:00:00',10,300,4),
    (2,2,3,NULL,5,'SATIS','06.10.2026 11:00:00',20,100,8),
    (3,1,2,NULL,3,'SATIS','07.09.2026 00:00:00',10,30,4),
    (4,1,2,NULL,900,'SATIS','06.09.2026 23:59:59',10,9000,4),
    (5,1,2,NULL,999,'SATIS','07.10.2026 00:00:00',10,9990,4),
    (6,2,NULL,1,3,'GIRIS','01.01.2026 10:00:00',20,60,8),
    (7,1,2,NULL,999,'SATIS','bozuk',10,9990,4);
    ''')
    yield c
    c.close()

def engine(db):return Analysis(db,datetime(2026,10,6,12))

@pytest.mark.parametrize('kind',[k for k,_ in REPORTS])
def test_reports_do_not_write_and_have_consistent_columns(db,kind):
    before='\n'.join(db.iterdump())
    headers,rows,note=engine(db).report(kind)
    assert all(len(r)==len(headers) for r in rows)
    assert note
    assert before=='\n'.join(db.iterdump())

def test_search_includes_missing_stock_and_excludes_inactive(db):
    rows=engine(db).report('search')[1]
    assert len(rows)==6
    assert [r for r in rows if r[0]=='Manisa' and r[1]=='00234'][0][3]==0
    assert not any('Pasif' in r for r in rows)
    assert matches(['İZMİR','Çizgi Roman'],'izmir cizgi')
    assert not matches(['İZMİR','Çizgi Roman'],'izmir kitap')

def test_date_boundaries_and_forecast(db):
    a=engine(db)
    assert len(a.sales(30,2))==2
    row=a.report('runway',2)[1][0]
    assert row[4]==33 and row[5]==1.1 and row[-1]=='Stok yok'
    row=a.report('runway',1)[1][0]
    assert row[-2]=='—' and row[-1]=='Satış verisi yok'

def test_purchase_rounding_and_no_negative_orders(db):
    rows=engine(db).report('purchase',2,30,30)[1]
    row=next(r for r in rows if r[1]=='00123')
    assert row[4:]==[33,33,132]
    assert all(r[5]>0 for r in rows)

def test_donors_are_not_double_spent(db):
    rows=engine(db).report('transfer')[1]
    assert sum(r[-1] for r in rows if r[0]=='00123')==15
    assert [r[-1] for r in rows if r[0]=='00123']==[10,5]
    assert all(r[2]!=r[3] for r in rows)

def test_abc_conserves_revenue(db):
    rows=engine(db).report('abc')[1]
    assert sum(r[3] for r in rows)==430
    assert rows[0][-1]=='A' and rows[-1][-2]==100

def test_idle_stock_age_uses_movement_not_sales(db):
    row=next(r for r in engine(db).report('idle',1,90)[1] if r[1]=='00234')
    assert row[-2]==278 and row[-1]==24

def test_daily_includes_zero_days_and_profit(db):
    rows=engine(db).report('daily',None,30)[1]
    assert len(rows)==30
    assert rows[0]==['06.10.2026',2,35,400,240]
    assert rows[1][1:]==[0,0,0,0]

def test_location_filter_and_cost(db):
    rows=engine(db).report('locations',1)[1]
    assert len(rows)==1
    assert rows[0][2:5]==[38,164,410]

def test_count_blanks_remain_blank(db):
    assert all(r[-2:]==['',''] for r in engine(db).report('count')[1])

def test_empty_database(db):
    db.execute('DELETE FROM stok_hareketleri');db.execute('DELETE FROM stoklar');db.execute('DELETE FROM urunler')
    for kind,_ in REPORTS:
        headers,rows,note=engine(db).report(kind)
        assert headers and note

def test_excel_injection_and_unicode(tmp_path):
    dest=tmp_path/'export.csv'
    export_csv(dest,['Barkod','Ürün'],[['00123','=HYPERLINK("url")'],['Çığ',' @SUM(1)']])
    with dest.open(encoding='utf-8-sig') as f:rows=list(csv.reader(f,delimiter=';'))
    assert rows[1][0]=='00123' and rows[1][1].startswith("'=")
    assert rows[2][0]=='Çığ' and rows[2][1].startswith("'")

@pytest.mark.parametrize('days,cover',[(0,14),(30,0),(366,14)])
def test_invalid_periods(db,days,cover):
    with pytest.raises(ValueError):engine(db).report('purchase',days=days,cover=cover)
