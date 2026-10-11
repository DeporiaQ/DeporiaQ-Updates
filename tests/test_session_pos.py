import sys, threading
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stok_programi_v2 import DeporiaQCloud
from test_operations_ui import application,window
from test_commerce_ui import Client,DATA
from deporiaq_commerce_ui import ServerDialog,SaleDialog,SupportDialog
import deporiaq_qt as ui

def test_parallel_expired_calls_rotate_once_and_keep_identity(tmp_path):
    c=DeporiaQCloud(SimpleNamespace(yol=tmp_path/'test.db'),'device')
    c.access_token='expired';c.refresh_token='old';c.user_id='user';c.company_id='company'
    calls=[];saved=[]
    def raw(path,method='GET',data=None,prefer=None,auth=True):
        calls.append(path)
        if 'grant_type=refresh_token' in path:return {'access_token':'new','refresh_token':'rotated','user':{'id':'user'}}
        if c.access_token=='expired':raise RuntimeError('Cloud isteği reddedildi (401): expired')
        return {'ok':True}
    c._ham_istek=raw;c.on_token_rotated=lambda session:saved.append(session.refresh_token)
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:c._istek('/rpc'),range(12)))
    assert all(x['ok'] for x in results)
    assert sum('grant_type=refresh_token' in x for x in calls)==1
    assert saved==['rotated'] and c.company_id=='company'

def test_network_timeout_is_not_replayed_or_logged_out(tmp_path):
    c=DeporiaQCloud(SimpleNamespace(yol=tmp_path/'test.db'),'device');c.access_token='ok';c.company_id='company';c.refresh_token='r';calls=[]
    def raw(*args):calls.append(args);raise RuntimeError('Cloud sunucusuna ulaşılamadı')
    c._ham_istek=raw
    with pytest.raises(RuntimeError):c._istek('/rpc','POST',{'sale':1})
    assert len(calls)==1 and c.bagli

def test_rotation_cannot_change_user(tmp_path):
    c=DeporiaQCloud(SimpleNamespace(yol=tmp_path/'test.db'),'device');c.access_token='old';c.refresh_token='r';c.user_id='u';c.company_id='company'
    def raw(path,*a,**k):
        if 'grant_type' in path:return {'access_token':'other','user':{'id':'different'}}
        raise RuntimeError('Cloud isteği reddedildi (401): expired')
    c._ham_istek=raw
    with pytest.raises(RuntimeError,match='aynı kullanıcı'):c._istek('/rpc')
    assert c.access_token=='old' and c.user_id=='u'

def test_cashier_exact_barcode_quantity_and_other_stores(application,window,monkeypatch):
    monkeypatch.setattr(ServerDialog,'run',lambda self,fn,done=None:done(fn()) if done else fn())
    d=SaleDialog(Client(),'Merkez Depo',window);d.show();application.processEvents()
    assert not d.sell.isEnabled() and not d.other.isVisible()
    d.barcode.setText('9780000000001');d.lookup()
    assert not d.sell.isEnabled() and 'bulunmamaktadır' in d.info.text()
    d.other_stock();assert d.grid.rowCount()==3
    d.location.setCurrentIndex(d.location.findData('1'));assert d.sell.isEnabled()
    d.quantity.setValue(2);assert not d.sell.isEnabled()
    d.quantity.setValue(1);d.barcode.setText('unknown');d.lookup();assert not d.sell.isEnabled()
    d.barcode.setText('9780000000001');d.lookup();d.other_stock()
    out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
    assert d.grab().save(str(out/'cashier-0.24.1.png'))
    d.clear_sale();assert not d.sell.isEnabled() and not d.barcode.text();d.close()

def test_support_short_input_explained_before_server(application,window):
    c=Client();calls=[];c.mutate=lambda *a:calls.append(a)
    d=SupportDialog(c,window);d.subject.setText('1');d.message.setPlainText('111');d.contact.setText('test@example.com');d.send()
    assert 'Konu 3' in d.status_label.text() and not calls
    d.subject.setText('Test');d.send();assert 'Açıklama 5' in d.status_label.text() and not calls
    d.close()

def test_saved_configuration_is_not_reapplied_to_live_session(monkeypatch):
    # Regression: main login used embedded config, timer used empty/stale local config.
    c=SimpleNamespace(bagli=True)
    c.yapilandir=lambda *a:pytest.fail('live session must not be reconfigured')
    seen=[]
    class Signal:
        def connect(self,*a):pass
    class Worker:
        def __init__(self,cloud,token,parent):seen.append(cloud);self.tamamlandi=Signal();self.hata=Signal()
        def start(self):pass
    monkeypatch.setattr(ui,'ayarlari_oku',lambda:{})
    monkeypatch.setattr(ui,'cloud_yapilandirmasi_oku',lambda:('https://test.supabase.co','valid-key'))
    monkeypatch.setattr(ui,'CloudKontrolu',Worker)
    w=SimpleNamespace(cloud_client=c,kullanici={'id':1},cloud_sonucu=lambda *a:None,cloud_hatasi=lambda *a:None)
    ui.AnaPencere.cloud_oturumunu_yenile(w)
    assert seen==[c]
