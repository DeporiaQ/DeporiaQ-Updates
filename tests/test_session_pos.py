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

def test_quantity_buttons_receive_real_clicks(application,window,monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    monkeypatch.setattr(ServerDialog,'run',lambda self,fn,done=None:done(fn()) if done else fn())
    d=SaleDialog(Client(),'Merkez Depo',window);d.show();application.processEvents()
    QTest.mouseClick(d.increase,Qt.MouseButton.LeftButton)
    assert d.quantity.value()==2
    QTest.mouseClick(d.decrease,Qt.MouseButton.LeftButton)
    QTest.mouseClick(d.decrease,Qt.MouseButton.LeftButton)
    assert d.quantity.value()==1
    d.quantity.setValue(1000000);QTest.mouseClick(d.increase,Qt.MouseButton.LeftButton)
    assert d.quantity.value()==1000000
    assert d.grab().save(str(Path(__file__).resolve().parents[1]/'test-results'/'cashier-0.24.2.png'))
    d.close()

def test_background_cache_error_does_not_revoke_license(application,window):
    window.lisans_kilitli=False
    window.cloud.setText('Cloud bağlı · Abonelik doğrulandı')
    window.cloud_senkron_hatasi('database is locked')
    assert not window.lisans_kilitli and 'Cloud bağlı' in window.cloud.text()
    window.cloud_hatasi('Cloud sunucusuna ulaşılamadı')
    assert not window.lisans_kilitli and 'yeniden denenecek' in window.cloud.text()
    window.cloud_hatasi('Cloud isteği reddedildi (401)')
    assert window.lisans_kilitli

def test_settings_reuses_session_without_password_login(application,window,monkeypatch):
    c=window.cloud_client;c.access_token='access';c.company_id='company';c.entitlement={'allowed':True}
    calls=[]
    monkeypatch.setattr(c,'lisans_dogrula',lambda:calls.append('status'))
    monkeypatch.setattr(ui.DeporiaQCloud,'giris_yap',lambda *a:pytest.fail('must reuse active session'))
    d=ui.AyarlarPenceresi(window.vt,c,lambda:None,window)
    assert not d.pw.isEnabled() and 'tekrar parola' in d.connection_label.text()
    d.cloud_giris();assert calls==['status'];d.close()

def test_parallel_settings_writes_preserve_tokens(tmp_path,monkeypatch):
    import stok_programi_v2 as core
    monkeypatch.setattr(core,'VERI_KLASORU',tmp_path)
    monkeypatch.setattr(core,'AYARLAR_YOLU',tmp_path/'settings.json')
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i:core.yerel_ayari_kaydet('setting_'+str(i),str(i)),range(40)))
    settings=core.ayarlari_oku()
    assert all(settings['setting_'+str(i)]==str(i) for i in range(40))

def test_support_has_send_below_fields_and_footer_email(application,window):
    from PySide6.QtWidgets import QPushButton,QLabel
    d=SupportDialog(Client(),window)
    assert d.send_button.text()=='Gönder'
    assert 'bağlantısı gerekli' not in d.status_label.text()
    assert window.support_mail.text()=='deporiaq@gmail.com'
    assert not any(w.text()=='DeporiaQ Sosyal' for w in window.findChildren(QLabel))
    assert not any(w.text()=='deporiaq@gmail.com' for w in window.sosyal.findChildren(QPushButton))
    d.close()


def test_green_cloud_indicator_survives_status_check_and_navigation(application,window):
    c=window.cloud_client;c.access_token='access';c.company_id='company';c.entitlement={'allowed':True}
    window.cloud_sonucu([], '')
    verified=window.cloud.text()
    assert '#4ADE80' in verified and '●' in verified and 'Cloud bağlı' in verified
    window.yenile()
    assert window.cloud.text()==verified
    window.cloud_hatasi('Network timeout')
    waiting=window.cloud.text();assert '#FBBF24' in waiting
    window.yenile();assert window.cloud.text()==waiting
    window.cloud_sonucu([], '');assert window.cloud.text()==verified
