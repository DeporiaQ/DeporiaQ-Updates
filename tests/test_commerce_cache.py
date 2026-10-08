import sys
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stok_programi_v2 import Veritabani
from deporiaq_commerce import CommerceClient
from deporiaq_analiz import Analysis

def test_server_sales_and_returns_import_once_without_outbound_queue(tmp_path):
 db=Veritabani(tmp_path/'test.db');db.ilk_kurulumu_tamamla('TEST','Kitap','Merkez Depo','TL','TEST','Fixture!Password2026')
 db.ayar_kaydet('cloud_etkin','1');db.baglanti.commit()
 cloud=SimpleNamespace(vt=db,company_id='company',cihaz_kimligi='device')
 client=CommerceClient(cloud)
 data={'locations':[{'id':'l','name':'Merkez Depo','location_type':'center','active':True}],
 'products':[{'id':'p','barcode':'001','name':'Kitap','sale_price':100,'purchase_price':60,'critical_stock':0,'active':True}],
 'inventory':[{'product_id':'p','location_id':'l','quantity':3,'available':1}],
 'sales':[{'id':key,'product_id':'p','location_id':'l','quantity':qty,'kind':kind,'unit_price':100,'unit_cost':60,'created_at':datetime.now(timezone.utc).isoformat()} for key,qty,kind in [('s',2,'sale'),('r',1,'return')]]}
 client.snapshot=lambda:data
 client.sync_cache();client.sync_cache()
 assert db.baglanti.execute('select count(*) from stok_hareketleri').fetchone()[0]==2
 assert db.baglanti.execute('select count(*) from senkron_kuyrugu').fetchone()[0]==0
 assert db.ayar_getir('cloud_etkin')=='1'
 assert sum(r['ciro'] for r in db.kar_raporu_getir())==100
 assert sum(r['brut_kar'] for r in db.kar_raporu_getir())==40
 assert sum(x['miktar'] for x in Analysis(db.baglanti).sales(1))==1
 db.kapat()
