"""Render the actual Quick 3D scene on a Windows RHI, not a mock drawing."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deporiaq_fur import register_fur
register_fur()
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QUrl,qInstallMessageHandler
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def message(kind,context,text):
    print(text,flush=True)
    if any(x in text for x in ('is not a type','Cannot assign','ReferenceError','Error creating','Failed to create','Failed to initialize')):errors.append(text)
qInstallMessageHandler(message)
app=QApplication([]);view=QQuickWidget();view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
view.setClearColor(Qt.GlobalColor.transparent);view.resize(440,472)
view.setSource(QUrl.fromLocalFile(str(ROOT/'companion/Cat.qml')));view.show();QTest.qWait(1500)
assert view.status()==QQuickWidget.Status.Ready,[e.toString() for e in view.errors()]
out=ROOT/'test-results'/'companion';out.mkdir(parents=True,exist_ok=True)
for mode in ('idle','wave','walk','happy','sleep','hungry','eat','startle','peek'):
    root=view.rootObject();root.setProperty('mood',mode);root.setProperty('phase',1.3);root.setProperty('facing',-12 if mode=='walk' else 0)
    QTest.qWait(500);frame=view.grabFramebuffer();assert not frame.isNull()
    colored=sum(frame.pixelColor(x,y).alpha()>10 for x in range(0,frame.width(),5) for y in range(0,frame.height(),5))
    assert colored>150,(mode,colored)
    assert frame.save(str(out/f'{mode}.png'))
assert not errors,errors
view.close();print('PASS: nine 3D poses rendered with a real graphics backend',flush=True)
