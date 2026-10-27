"""Native Qt Quick 3D evidence with synthetic data; external services disabled."""
import os,sys,tempfile,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ.setdefault('QT_QPA_PLATFORM','windows' if sys.platform=='win32' else 'xcb')
sandbox=tempfile.TemporaryDirectory(prefix='dpq-native-0280-');os.environ['LOCALAPPDATA']=sandbox.name
import deporiaq_qt as ui
from PySide6.QtCore import Qt,QPoint,QRect,qInstallMessageHandler
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest
from retail_fixture import fixture
from deporiaq_warehouse import WarehouseView
from deporiaq_i18n import set_language
errors=[];sys.excepthook=lambda *args:errors.append(''.join(traceback.format_exception(*args)))
def message(kind,context,text):
 if any(s in text for s in ('is not a type','Cannot assign','ReferenceError','Error creating','Failed to create','Failed to initialize','not defined')):errors.append(text)
qInstallMessageHandler(message)
app=ui.QApplication([]);app.setStyleSheet(ui.STIL)
data=fixture();out=ROOT/'test-results/native-0281';out.mkdir(parents=True,exist_ok=True)
db=ui.Veritabani(Path(sandbox.name)/'fixture.db');db.ilk_kurulumu_tamamla('ÖRNEK KİTABEVİ · TEST VERİSİ','Kitabevi','Merkez Depo','TL','NATIVE_TEST','Fixture!Password2026');db.ayar_kaydet('ui_animation','0');db.baglanti.commit()
user=db.baglanti.execute('select * from kullanicilar limit 1').fetchone()
for method in ('cloud_oturumunu_yenile','kurlari_yenile','guncelleme_denetle'):setattr(ui.AnaPencere,method,lambda *args:None)
ui.GuncellemeKontrolu.run=lambda self:None
window=ui.AnaPencere(db,user,None);window.retail_hub.accept(data);window.resize(1366,900);window.show();QTest.qWait(800)
for mode in ('dark','light'):
 db.ayar_kaydet('ui_mode',mode);ui.apply_appearance(window);QTest.qWait(300);window.grab().save(str(out/('dashboard-'+mode+'.png')))
from deporiaq_positions import PositionsDialog
from deporiaq_retail_ui import OffersDialog
window.retail_hub.refresh=lambda:None
window.retail_hub.client.read=lambda action,payload=None:data
window.retail_hub.data['positions']=[dict(id='position',version=1,product_id=data['products'][0]['id'],location_id=data['locations'][0]['id'],floor='2. Kat',area='L koridoru',shelf='Polisiye A',compartment='Üst göz',note='Merdivenin solu')]
positions=PositionsDialog(window.retail_hub,window);positions.show();positions.query.setText(data['products'][0]['barcode']);QTest.qWait(300)
assert positions.grid.rowCount()==1 and not positions.findChildren(QQuickWidget)
positions.grab().save(str(out/'product-locations.png'));positions.close()
assert window.pet_dock.isHidden()
canvas=window.panel_canvas
for key in canvas.panels:canvas.set_visible(key,False)
canvas.set_visible('retail_pos',True);pos=window.retail_hub.panels['pos'];canvas.place(canvas.panels['retail_pos'],QRect(0,0,800,650));canvas.remember(canvas.panels['retail_pos']);window.kaydir.verticalScrollBar().setValue(0)
QTest.qWait(400);window.grab().save(str(out/'checkout-panel.png'))
for timer in (window.canli_zamanlayici,window.senkron_zamanlayici,window.kur_zamanlayici):timer.stop()
window.close();db.kapat();assert not errors,'\n'.join(errors)
print('PASS text-only product positions, hidden pet dock, checkout and both themes')
