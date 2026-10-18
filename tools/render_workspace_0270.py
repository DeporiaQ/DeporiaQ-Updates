"""Native Windows integration: real 3D, panel input and assistant interaction.
All records are synthetic and all external services are disabled in this test.
"""
import os,sys,tempfile,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='windows'
sandbox=tempfile.TemporaryDirectory(prefix='dpq-native-0270-');os.environ['LOCALAPPDATA']=sandbox.name
import deporiaq_qt as ui
from PySide6.QtCore import Qt,QPoint,qInstallMessageHandler
from PySide6.QtGui import QCursor
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest
errors=[]
sys.excepthook=lambda *args:errors.append(''.join(traceback.format_exception(*args)))
def message(kind,context,text):
    if any(x in text for x in ('is not a type','Cannot assign','ReferenceError','Error creating','Failed to create','Failed to initialize')):errors.append(text)
qInstallMessageHandler(message)
app=ui.QApplication([]);app.setStyleSheet(ui.STIL);app.setFont(ui.QFont('Segoe UI',10))
db=ui.Veritabani(Path(sandbox.name)/'fixture.db');db.ilk_kurulumu_tamamla('ÖRNEK KİTABEVİ','Kitabevi','Merkez Depo','TL','NATIVE_TEST','Fixture!Password2026')
db.ayar_kaydet('ui_animation','0');db.baglanti.commit()
user=db.baglanti.execute('select * from kullanicilar limit 1').fetchone()
for method in ('cloud_oturumunu_yenile','kurlari_yenile','guncelleme_denetle'):setattr(ui.AnaPencere,method,lambda *args:None)
ui.GuncellemeKontrolu.run=lambda self:None
window=ui.AnaPencere(db,user,None);window.resize(1366,900);window.show();window.activateWindow();window.raise_();QTest.qWait(1600)
pet=window.companion;assert pet.view and not pet.failed,'3D renderer unavailable'
assert pet.view.status()==QQuickWidget.Status.Ready,[e.toString() for e in pet.view.errors()]
pet.timer.stop();pet.home();QCursor.setPos(window.mapToGlobal(QPoint(700,150)));pet.tick();QTest.qWait(300)
out=ROOT/'test-results/native-0270';out.mkdir(parents=True,exist_ok=True)
def shot(name):
    QTest.qWait(350);assert window.grab().save(str(out/(name+'.png')))
frame=pet.view.grabFramebuffer();assert not frame.isNull()
assert sum(frame.pixelColor(x,y).alpha()>10 for x in range(0,frame.width(),3) for y in range(0,frame.height(),3))>150
shot('dashboard-cat')
# Check the actual rendered alpha against the input mask in every major pose.
# A visually clipped ear can otherwise pass a generic "3D is visible" check.
root=pet.view.rootObject()
for mood in ('idle','wave','walk','happy','sleep','hungry','eat','startle','peek'):
    root.setProperty('mood',mood);root.setProperty('phase',1.3);root.setProperty('lookX',0);root.setProperty('lookY',0)
    QTest.qWait(500);frame=pet.view.grabFramebuffer();mask=pet.view.mask()
    clipped=[(x,y) for x in range(0,frame.width(),2) for y in range(0,frame.height(),2)
        if frame.pixelColor(x,y).alpha()>64 and not mask.contains(QPoint(round(x/frame.devicePixelRatio()),round(y/frame.devicePixelRatio())))]
    assert not clipped,(mood,'Opaque 3D pixels outside input mask',clipped[:8])
    assert frame.save(str(out/('pose-'+mood+'.png')))
root.setProperty('mood','idle');QTest.qWait(400)
QTest.mouseClick(pet.view,Qt.MouseButton.LeftButton,pos=pet.view.rect().center());app.processEvents();pet.tick()
assert window.assistant_panel.isVisible() and not pet.view.isVisible(),'Assistant must remain above the companion'
shot('assistant')
window.assistant_panel.input.setPlainText('Paneli büyütmek istiyorum');window.assistant_panel.submit();shot('assistant-answer')
window.toggle_mode();shot('assistant-light');window.toggle_mode()
window.assistant_panel.close();pet.tick();assert pet.view.isVisible()
# Keyboard/mouse access to feeding, hunger and the sleep/startle transition.
pet.state.last_fed=0;assert pet.state.hungry();pet.state.motion=False
QTest.mouseClick(pet.dock,Qt.MouseButton.LeftButton,pos=QPoint(28,24));assert pet.state.food and pet.mode=='eat'
pet.mode_until=0;pet.tick();assert not pet.state.food and not pet.state.hungry() and pet.mode=='happy'
pet.mode_until=0;pet.tick();assert pet.mode=='sleep';shot('sleep')
pet.state.motion=True;pet.previous_distance=500;pet.startle_after=0
QCursor.setPos(pet.view.mapToGlobal(pet.view.rect().center()));pet.tick();assert pet.mode=='startle';shot('startle')
pet.set_enabled(False);assert pet.view.isHidden() and window.header.assistant.isVisible()
QTest.mouseClick(window.header.assistant,Qt.MouseButton.LeftButton);assert window.assistant_panel.isVisible();window.assistant_panel.close()
# Hidden panels keep their data widget; neighbouring geometry must not move.
canvas=window.panel_canvas;key=next(iter(canvas.panels));others={k:p.geometry() for k,p in canvas.panels.items() if k!=key}
canvas.set_visible(key,False);window.yenile();app.processEvents()
assert others=={k:p.geometry() for k,p in canvas.panels.items() if k!=key};assert canvas.panels[key].isHidden()
shot('hidden-panel');canvas.reset();pet.set_enabled(True)
window.resize(1000,720);QTest.qWait(250);pet.home();pet.tick();shot('small-window')
for timer in (window.canli_zamanlayici,window.senkron_zamanlayici,window.kur_zamanlayici):timer.stop()
window.close();db.kapat();assert not errors,errors
print('PASS: native 3D display, clickable cat, assistant layering, feed/hunger, sleep/startle, fallback, hidden-panel stability and small window')
