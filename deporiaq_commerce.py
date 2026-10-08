"""Server-authoritative commerce client; no offline mutation fallback."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path

PLANS = [('demo','Demo',1,'30 gün • stok girişi ve satış'),('single','Single',1,'Tek bilgisayar'),
         ('duo','Duo',3,'Patron dahil 3 bilgisayar'),('plus','Plus',6,'Patron dahil 6 bilgisayar'),
         ('ultra','Ultra',20,'Patron dahil 20 bilgisayar')]
SHORTCUTS = [('Ctrl+K','Komut arama','komut_paleti_ac'),('Ctrl+1','Genel Bakış','yenile'),
             ('Ctrl+2','Stok ve Ürünler','stok_merkezi_ac'),('Ctrl+3','Şube Satış','satis_ac'),
             ('Ctrl+4','İnternet Siparişleri','internet_ac')]

class CommerceError(ValueError):
    pass

class CommerceClient:
    def __init__(self,cloud):
        self.cloud=cloud
        path=Path(cloud.vt.yol).with_name('commerce_requests.db')
        self.path=path
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, scope TEXT, action TEXT, body TEXT, state TEXT, result TEXT)')
        self.last_snapshot=None
        self.last_warning=''

    def _db(self):
        return sqlite3.connect(self.path,timeout=15)

    def read(self,action,payload=None):
        if not self.cloud.bagli:
            raise CommerceError('Cloud oturumu gerekli. Çevrimdışı satış veya stok değişikliği yapılamaz.')
        try:
            return self.cloud._istek('/rest/v1/rpc/dpq_call','POST',{
                'p_action':action,'p_payload':payload or {},'p_device':self.cloud.cihaz_kimligi})
        except Exception as e:
            raise CommerceError(str(e)) from e

    def register(self):
        import platform
        return self.read('register',{'name':platform.node() or 'Bilgisayar'})

    def status(self):
        return self.read('status')

    def mutate(self,action,payload):
        """Persist UUID before request. Ambiguous network failures retain the same UUID.
        A different command is blocked until the pending command is reconciled.
        A rejected SQL call is atomic; safe to abandon only explicit DPQ_* errors.
        """
        scope=f'{self.cloud.company_id}:{getattr(self.cloud,"user_id","")}:{self.cloud.cihaz_kimligi}'
        body=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT id,action,body FROM requests WHERE scope=? AND state='pending'",(scope,)).fetchone()
            if row:
                request_id,old_action,old_body=row
                if old_action!=action or old_body!=body:
                    raise CommerceError('Son işlemin sonucu belirsiz. Önce İnternet Satışları / Bekleyen İşlemi Kontrol Et düğmesini kullanın.')
            else:
                request_id=str(uuid.uuid4())
                db.execute('INSERT INTO requests VALUES(?,?,?,?,?,NULL)',(request_id,scope,action,body,'pending'))
        if row:
            # Even if the license expired after a committed sale, resolve its result
            # without issuing a fresh sale or throwing away the persisted UUID.
            status=self.read('operation_status',{'request_id':request_id})
            if status.get('found'):
                result=status['result']
                with self._db() as db:
                    db.execute("UPDATE requests SET state='confirmed',result=? WHERE id=?",(json.dumps(result),request_id))
                return result
        try:
            result=self.read(action,{**payload,'request_id':request_id})
        except CommerceError as e:
            # Server-raised business error means the SQL transaction rolled back.
            if any(f'Cloud isteği reddedildi ({code})' in str(e) for code in (400,401,403,404,409,422)):
                with self._db() as db:db.execute("UPDATE requests SET state='rejected' WHERE id=?",(request_id,))
            raise
        with self._db() as db:
            db.execute("UPDATE requests SET state='confirmed',result=? WHERE id=?",(json.dumps(result),request_id))
        return result

    def reconcile(self):
        scope=f'{self.cloud.company_id}:{getattr(self.cloud,"user_id","")}:{self.cloud.cihaz_kimligi}'
        with self._db() as db:row=db.execute("SELECT action,body FROM requests WHERE scope=? AND state='pending'",(scope,)).fetchone()
        if not row:return {'message':'Bekleyen işlem yok.'}
        return self.mutate(row[0],json.loads(row[1]))

    def snapshot(self):
        self.last_snapshot=self.read('snapshot')
        return self.last_snapshot

    def sync_cache(self):
        """Read-only server snapshot becomes a disposable local reporting cache.
        Does not upload local stock and does not insert historical sales twice.
        """
        data=self.snapshot(); vt=self.cloud.vt
        if vt.ayar_getir('dpq_company_id',self.cloud.company_id)!=self.cloud.company_id:
            raise CommerceError('Bu önbellek başka bir işletmeye ait. Ayrı kurulum gerekir.')
        with vt.baglanti:
            previous=vt.ayar_getir('cloud_etkin','0')
            vt.ayar_kaydet('cloud_etkin','0')
            vt.ayar_kaydet('dpq_company_id',self.cloud.company_id)
            vt.baglanti.execute('CREATE TABLE IF NOT EXISTS dpq_imported_events(id TEXT PRIMARY KEY)')
            for l in data['locations']:
                vt.baglanti.execute('INSERT INTO konumlar(ad,tur,aktif) VALUES(?,?,?) ON CONFLICT(ad) DO UPDATE SET tur=excluded.tur,aktif=excluded.aktif',
                    (l['name'],{'center':'MERKEZ','warehouse':'DEPO','branch':'SUBE'}[l['location_type']],int(l['active'])))
            for p in data['products']:
                vt.baglanti.execute('INSERT INTO urunler(barkod,ad,fiyat,alis_fiyati,kritik_stok,aktif) VALUES(?,?,?,?,?,?) ON CONFLICT(barkod) DO UPDATE SET ad=excluded.ad,fiyat=excluded.fiyat,alis_fiyati=excluded.alis_fiyati,kritik_stok=excluded.kritik_stok,aktif=excluded.aktif',
                    (p['barcode'],p['name'],float(p['sale_price']),float(p['purchase_price']),int(p['critical_stock']),int(p['active'])))
            lm={l['id']:vt.baglanti.execute('SELECT id FROM konumlar WHERE ad=?',(l['name'],)).fetchone()[0] for l in data['locations']}
            pm={p['id']:vt.baglanti.execute('SELECT id FROM urunler WHERE barkod=?',(p['barcode'],)).fetchone()[0] for p in data['products']}
            for row in data['inventory']:
                vt.baglanti.execute('INSERT INTO stoklar(urun_id,konum_id,miktar) VALUES(?,?,?) ON CONFLICT(urun_id,konum_id) DO UPDATE SET miktar=excluded.miktar',
                    (pm[row['product_id']],lm[row['location_id']],row['quantity']))
            from datetime import datetime
            for event in data.get('sales',[]):
                if vt.baglanti.execute('SELECT 1 FROM dpq_imported_events WHERE id=?',(event['id'],)).fetchone():continue
                dt=datetime.fromisoformat(event['created_at'].replace('Z','+00:00')).astimezone().strftime('%d.%m.%Y %H:%M:%S')
                sign=-1 if event['kind']=='return' else 1
                vt.baglanti.execute("INSERT INTO stok_hareketleri(urun_id,kaynak_konum_id,miktar,hareket_turu,tarih_saat,aciklama,birim_fiyat,toplam_tutar,alis_fiyati) VALUES(?,?,?,?,?,?,?,?,?)",
                    (pm[event['product_id']],lm[event['location_id']],event['quantity'],'IADE' if sign<0 else 'SATIS',dt,
                     'Sunucu işlemi '+event['id'],event['unit_price'],sign*float(event['unit_price'])*float(event['quantity']),event['unit_cost']))
                vt.baglanti.execute('INSERT INTO dpq_imported_events VALUES(?)',(event['id'],))
            vt.ayar_kaydet('cloud_etkin',previous)
        return data
