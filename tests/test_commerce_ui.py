import os,sys,tempfile
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_operations_ui import application,window
import deporiaq_qt as ui
from deporiaq_commerce_ui import PlansDialog,OrdersDialog,StockDialog,ServerDialog,SupportDialog
from deporiaq_commerce import SHORTCUTS

DATA={'products':[{'id':'p','name':'X Kitabı','barcode':'9780000000001','active':True}],
'locations':[{'id':str(i),'name':name,'active':True,'location_type':'center' if i==0 else 'branch'} for i,name in enumerate(['Merkez Depo','A Şubesi','B Şubesi','C Şubesi'])],
'inventory':[{'product_id':'p','location_id':str(i),'quantity':n,'available':a} for i,(n,a) in enumerate([(2,0),(1,1),(1,1),(3,1)])],
'channels':[{'id':'ch','name':'Instagram','active':True}],
'orders':[{'id':'o','reference':'IG-1001','customer':'Örnek Müşteri','status':'reserved','shipping':'consolidate','allocations':[{'id':'a0','product_id':'p','location_id':'0','quantity':2,'state':'reserved'},{'id':'a3','product_id':'p','location_id':'3','quantity':2,'state':'reserved'}]}]}
class Client:
 def snapshot(self):return DATA
 def status(self):return {'plan':'duo','devices_used':2,'device_limit':3,'valid_until':'2026-11-07','allowed':True,'role':'owner','enabled':True}
 def read(self,*a):return [{'name':'Merkez Bilgisayarı','active':True,'code':'DPQ-TEST'}]

def test_five_shortcuts_and_small_sidebar(window):
 assert len(window.quick_shortcuts)==5
 labels=[b.text() for b in window.menu_kaydir.findChildren(ui.QPushButton)]
 assert len(labels)==9
 assert not any('Hızlı Komut' in x for x in labels)
 assert 'Paketim ve Abonelik' in labels
 assert [x.key().toString() for x in window.quick_shortcuts]==[x[0] for x in SHORTCUTS]

def test_real_settings_has_five_clickable_commands(application,window):
 d=ui.AyarlarPenceresi(window.vt,window.cloud_client,window.yenile,window)
 tabs=d.findChild(ui.QTabWidget);index=next(i for i in range(tabs.count()) if tabs.tabText(i)=='Gizli Komutlar')
 tabs.setCurrentIndex(index)
 assert len(tabs.widget(index).findChildren(ui.QPushButton))==5
 d.show();application.processEvents()
 out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
 assert d.grab().save(str(out/'settings-shortcuts.png'));d.close()

def test_commerce_screen_layouts(application,window,monkeypatch):
 # Layout fixtures only, deliberately bypass networking; backend behavior tested separately.
 monkeypatch.setattr(ServerDialog,'run',lambda self,fn,done=None:done(fn()) if done else fn())
 client=Client();out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
 for name,d in [('plans',PlansDialog(client,window)),('orders',OrdersDialog(client,window)),('stock',StockDialog(client,'catalog',window)),('support',SupportDialog(client,window))]:
  d.show();application.processEvents()
  if name=='orders':d.orders.selectRow(0);application.processEvents();assert d.allocations.rowCount()==2
  if name=='stock':assert d.grid.rowCount()==4
  assert d.grab().save(str(out/(name+'.png')));d.close()
 window.show();application.processEvents();assert window.grab().save(str(out/'main-menu.png'))

def test_login_has_quiet_package_link(application,window):
 d=ui.GirisPenceresi(window.vt)
 labels=[b.text() for b in d.findChildren(ui.QPushButton)]
 assert 'Giriş Yap' in labels
 assert '30 gün ücretsiz deneyin · Paketleri incele' in labels
 d.show();application.processEvents();assert d.grab().save(str(Path(__file__).resolve().parents[1]/'test-results'/'login.png'));d.close()

def test_username_login_cannot_borrow_shared_owner_cloud_token(application,window,monkeypatch):
 errors=[];refreshed=[]
 class Cloud:
  def __init__(self,*a):pass
  def yapilandir(self,*a):pass
  def oturumu_yenile(self,token):refreshed.append(token)
 monkeypatch.setattr(ui,'cloud_yapilandirmasi_oku',lambda:('https://test.supabase.co','public-key-long-enough'))
 monkeypatch.setattr(ui,'ayarlari_oku',lambda:{'cloud_refresh_token_dpapi':'shared-owner-token','cihaz_kimligi':'device'})
 monkeypatch.setattr(ui,'windows_sifre_coz',lambda x:x)
 monkeypatch.setattr(ui,'DeporiaQCloud',Cloud)
 monkeypatch.setattr(ui.QMessageBox,'critical',lambda *args:errors.append(args[-1]))
 d=ui.GirisPenceresi(window.vt);d.kullanici.setText('TEST_ADMIN');d.parola.setText('Fixture!Password2026');d.giris()
 assert not refreshed
 assert errors and 'E-posta' in errors[0]
 d.close()

def test_bound_refresh_token_must_match_cloud_user(application,window,monkeypatch):
 errors=[];uid=str(window.kullanici['id'])
 class Cloud:
  def __init__(self,*a):self.user_id='wrong-cloud-user'
  def yapilandir(self,*a):pass
  def oturumu_yenile(self,*a):pass
 monkeypatch.setattr(ui,'cloud_yapilandirmasi_oku',lambda:('https://test.supabase.co','public-key-long-enough'))
 monkeypatch.setattr(ui,'ayarlari_oku',lambda:{'cihaz_kimligi':'device','cloud_accounts':{uid:{'user_id':'expected','refresh_token_dpapi':'token'}}})
 monkeypatch.setattr(ui,'windows_sifre_coz',lambda x:x)
 monkeypatch.setattr(ui,'DeporiaQCloud',Cloud)
 monkeypatch.setattr(ui.QMessageBox,'critical',lambda *args:errors.append(args[-1]))
 d=ui.GirisPenceresi(window.vt);d.kullanici.setText('TEST_ADMIN');d.parola.setText('Fixture!Password2026');d.giris()
 assert errors and 'bu yerel kullanıcıya ait değil' in errors[0]
 d.close()
