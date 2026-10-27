"""Native Windows integration: real 3D, panel input and assistant interaction.
All records are synthetic and all external services are disabled in this test.
"""
import os,sys,tempfile,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','windows' if sys.platform=='win32' else 'xcb')
sandbox=tempfile.TemporaryDirectory(prefix='dpq-native-0271-');os.environ['LOCALAPPDATA']=sandbox.name
import deporiaq_qt as ui
from PySide6.QtCore import Qt,QPoint,QRect,qInstallMessageHandler
from deporiaq_i18n import render
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
out=ROOT/'test-results/native-0271';out.mkdir(parents=True,exist_ok=True)
def shot(name):
    QTest.qWait(350);assert window.grab().save(str(out/(name+'.png')))
def cat_fully_visible():
    rect=QRect(pet.view.mapTo(window,QPoint(0,0)),pet.view.size())
    assert window.rect().contains(rect),('Cat clipped by window',rect,window.rect())
    assert pet.view.parentWidget().rect().contains(pet.view.geometry()),'Cat clipped by sidebar home'
    for widget in (pet.view,window.language_flags['tr'],window.support_mail):
        assert not widget.visibleRegion().isEmpty(),('Sidebar control clipped',widget.objectName())
frame=pet.view.grabFramebuffer();assert not frame.isNull()
assert sum(frame.pixelColor(x,y).alpha()>10 for x in range(0,frame.width(),3) for y in range(0,frame.height(),3))>150
cat_fully_visible();shot('dashboard-cat')
# Fixed seated scene, readable signs and pointer-following gaze.
root=pet.view.rootObject();position=pet.view.pos()
for mode in ('idle','hungry','eat','happy'):
    pet.mode=mode;root.setProperty('mood',mode);root.setProperty('messageText',render(pet.message()));root.setProperty('phase',1.3)
    QTest.qWait(400);frame=pet.view.grabFramebuffer()
    assert frame.save(str(out/('pose-'+mode+'.png')))
    assert frame.pixelColor(0,0).alpha()<10
for point in (QPoint(300,120),QPoint(1200,680)):
    QCursor.setPos(window.mapToGlobal(point));pet.tick();QTest.qWait(350)
    assert pet.view.pos()==position,'The seated cat must not roam'
    assert abs(root.property('lookX'))>0
root.setProperty('mood','idle')
QTest.mouseClick(pet.view,Qt.MouseButton.LeftButton,pos=pet.view.rect().center());app.processEvents();pet.tick()
assert window.assistant_panel.isVisible() and not pet.view.isVisible(),'Assistant must remain above the companion'
shot('assistant')
window.assistant_panel.input.setPlainText('Paneli büyütmek istiyorum');window.assistant_panel.submit();shot('assistant-answer')
def answer_visible():
    panel=window.assistant_panel;frame=panel.messages_layout.itemAt(panel.messages_layout.count()-1).widget()
    body=frame.findChild(ui.QLabel,'assistantAnswer');viewport=panel.scroll.viewport()
    top=body.mapTo(viewport,QPoint(0,0)).y()
    assert 0<=top<viewport.height()-20,('Answer scrolled out of view',top,viewport.height())
    bottom=frame.y()+frame.height()+panel.messages_layout.contentsMargins().bottom()
    assert panel.messages.height()<=max(viewport.height(),bottom)+2,'Trailing blank space after answer'
answer_visible();window.toggle_mode();shot('assistant-light');answer_visible();window.toggle_mode()
window.assistant_panel.close();pet.tick();assert pet.view.isVisible()
# Feeding never starts a walk or sleep animation.
pet.state.last_fed=0;assert pet.state.hungry();pet.state.motion=False
assert pet.dock.isHidden();pet.feed();assert pet.state.food and pet.mode=='eat'
pet.mode_until=0;pet.tick();assert not pet.state.food and not pet.state.hungry() and pet.mode=='happy'
pet.mode_until=0;pet.tick();assert pet.mode=='idle';assert pet.view.pos()==position;shot('seated-after-feeding')
pet.state.motion=True
pet.set_enabled(False);assert pet.view.isHidden() and window.header.assistant.isVisible()
QTest.mouseClick(window.header.assistant,Qt.MouseButton.LeftButton);assert window.assistant_panel.isVisible();window.assistant_panel.close()
# Hidden panels keep their data widget; neighbouring geometry must not move.
canvas=window.panel_canvas;key=next(iter(canvas.panels));others={k:p.geometry() for k,p in canvas.panels.items() if k!=key}
canvas.set_visible(key,False);window.yenile();app.processEvents()
assert others=={k:p.geometry() for k,p in canvas.panels.items() if k!=key};assert canvas.panels[key].isHidden()
shot('hidden-panel');canvas.reset();pet.set_enabled(True)
window.resize(1000,720);QTest.qWait(250);pet.home();pet.tick();shot('small-window')
cat_fully_visible()
window.change_language('en');pet.mode='idle';pet.message_index=1;pet.message_until=pet.next_message=10**12;pet.tick()
assert root.property('messageText')=='You can rename me in Settings.'
shot('english-sign');cat_fully_visible()
for timer in (window.canli_zamanlayici,window.senkron_zamanlayici,window.kur_zamanlayici):timer.stop()
window.close();db.kapat();assert not errors,errors
print('PASS: native 3D display, clickable cat, assistant layering, feed/hunger, seated feeding and gaze, fallback, hidden-panel stability and small window')
