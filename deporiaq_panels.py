"""Persistent free-position dashboard panels; hiding never destroys a data widget."""
import json
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QScrollArea, QSizePolicy
from deporiaq_i18n import T, QLabel, QPushButton, QWidget, QCheckBox
from deporiaq_visuals import WorkspaceDialog

class DragBar(QWidget):
    def __init__(self, panel, title):
        super().__init__(panel); self.panel=panel; self.start=None
        self.setCursor(Qt.CursorShape.SizeAllCursor); self.setFixedHeight(30)
        row=QHBoxLayout(self);row.setContentsMargins(9,0,4,0)
        label=QLabel(title);label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents);row.addWidget(label,1)
        self.close=QPushButton('×');self.close.setFixedSize(24,24);self.close.setAccessibleName(T('Paneli gizle'))
        self.close.setToolTip(T('Paneli gizle'));self.close.setStyleSheet('QPushButton{background:transparent;border:0;color:rgba(180,200,220,150);padding:0;font-size:19px;} QPushButton:hover{color:#f8fafc;background:#39465b;border-radius:6px;}')
        self.close.clicked.connect(lambda:self.panel.canvas.set_visible(self.panel.key,False));row.addWidget(self.close)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.start=(event.globalPosition().toPoint(),self.panel.geometry());self.panel.raise_();event.accept()
    def mouseMoveEvent(self,event):
        if self.start and not self.panel.canvas.locked:
            delta=event.globalPosition().toPoint()-self.start[0];rect=QRect(self.start[1]);rect.moveTopLeft(rect.topLeft()+delta)
            self.panel.canvas.place(self.panel,rect);event.accept()
    def mouseReleaseEvent(self,event):
        if self.start:self.start=None;self.panel.canvas.remember(self.panel)

class ResizeCorner(QWidget):
    def __init__(self,panel):
        super().__init__(panel);self.panel=panel;self.start=None;self.setFixedSize(17,17);self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip(T('Boyutlandırmak için sürükleyin'))
    def paintEvent(self,event):
        from PySide6.QtGui import QPainter,QPen,QColor
        p=QPainter(self);p.setPen(QPen(QColor(156,180,206,120),1.2))
        for n in (4,8,12):p.drawLine(15-n,15,15,15-n)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.start=(event.globalPosition().toPoint(),self.panel.geometry());self.panel.raise_()
    def mouseMoveEvent(self,event):
        if self.start and not self.panel.canvas.locked:
            delta=event.globalPosition().toPoint()-self.start[0];rect=QRect(self.start[1]);rect.setWidth(rect.width()+delta.x());rect.setHeight(rect.height()+delta.y());self.panel.canvas.place(self.panel,rect)
    def mouseReleaseEvent(self,event):
        if self.start:self.start=None;self.panel.canvas.remember(self.panel)

class DashboardPanel(QFrame):
    def __init__(self,canvas,key,title,content,minimum):
        super().__init__(canvas);self.canvas=canvas;self.key=key;self.title=title;self.minimum=minimum
        self.setObjectName('panel');self.setMinimumSize(*minimum)
        content.setObjectName('freePanelContent');content.setStyleSheet('QFrame#freePanelContent{background:transparent;border:0;}')
        content.setMinimumSize(0,0);content.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored)
        layout=QVBoxLayout(self);layout.setContentsMargins(3,0,3,12);layout.setSpacing(0)
        self.bar=DragBar(self,title);layout.addWidget(self.bar);layout.addWidget(content,1);self.content=content
        self.corner=ResizeCorner(self)
    def resizeEvent(self,event):
        super().resizeEvent(event);self.corner.move(self.width()-19,self.height()-19);self.corner.raise_()

class PanelCanvas(QWidget):
    changed=Signal()
    def __init__(self,window):
        super().__init__();self.window=window;self.panels={};self.defaults={};self.restoring=False
        self.key='panel_layout_v1_'+str(window.kullanici['id']);self.locked=False
        try:
            raw=json.loads(window.vt.ayar_getir(self.key,'{}'));self.saved=raw if isinstance(raw,dict) else {}
        except (ValueError,TypeError):self.saved={}
        self.locked=bool(self.saved.get('_locked',False));self.setMinimumSize(1000,740)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def add(self,key,title,content,rect,minimum=(210,160)):
        self.defaults[key]=rect;panel=DashboardPanel(self,key,title,content,minimum);self.panels[key]=panel
        self.restore_panel(panel);return panel
    def state(self,key):
        state=self.saved.get(key,{})
        if not isinstance(state,dict):state={}
        rect=state.get('rect',self.defaults[key])
        if not isinstance(rect,list) and not isinstance(rect,tuple):rect=self.defaults[key]
        if len(rect)!=4 or any(not isinstance(n,(float,int)) or not 0<=n<=2000 for n in rect):rect=self.defaults[key]
        return rect,bool(state.get('visible',True))
    def place(self,panel,rect):
        w=max(panel.minimum[0],min(rect.width(),self.width()));h=max(panel.minimum[1],min(rect.height(),self.height()))
        x=max(0,min(rect.x(),self.width()-w));y=max(0,min(rect.y(),self.height()-h));panel.setGeometry(x,y,w,h)
    def restore_panel(self,panel):
        rect,visible=self.state(panel.key);sx=self.width()/1600;sy=self.height()/900
        self.place(panel,QRect(round(rect[0]*sx),round(rect[1]*sy),round(rect[2]*sx),round(rect[3]*sy)))
        panel.setVisible(visible);panel.corner.setVisible(not self.locked)
        panel.bar.setCursor(Qt.CursorShape.ArrowCursor if self.locked else Qt.CursorShape.SizeAllCursor)
    def remember(self,panel):
        rect=panel.geometry();sx=1600/max(1,self.width());sy=900/max(1,self.height())
        self.saved[panel.key]={'rect':[round(rect.x()*sx,2),round(rect.y()*sy,2),round(rect.width()*sx,2),round(rect.height()*sy,2)],'visible':not panel.isHidden()};self.save()
    def save(self):
        self.saved['_locked']=self.locked;self.window.vt.ayar_kaydet(self.key,json.dumps(self.saved));self.window.vt.baglanti.commit();self.changed.emit()
    def set_visible(self,key,visible):
        panel=self.panels[key];panel.setVisible(visible);self.remember(panel)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        for panel in self.panels.values():self.restore_panel(panel)
    def reset(self):
        self.saved={};self.locked=False
        for panel in self.panels.values():self.restore_panel(panel)
        self.save()
    def set_locked(self,locked):
        self.locked=locked
        for panel in self.panels.values():self.restore_panel(panel)
        self.save()

class PanelsDialog(WorkspaceDialog):
    def __init__(self,canvas,parent):
        super().__init__(parent);self.setWindowTitle(T('Paneller'));self.resize(430,520);self.canvas=canvas
        layout=QVBoxLayout(self);title=QLabel(T('Çalışma alanınız'));title.setObjectName('sayfaBaslik');layout.addWidget(title)
        note=QLabel(T('Başlığından sürükleyerek taşıyın, sağ alt köşeden boyutlandırın. Gizlenen panellerin yeri boş kalır; veriler güncellenmeye devam eder.'));note.setWordWrap(True);layout.addWidget(note)
        self.checks={}
        for key,panel in canvas.panels.items():
            check=QCheckBox(panel.title);check.setChecked(not panel.isHidden());check.toggled.connect(lambda on,k=key:canvas.set_visible(k,on));layout.addWidget(check);self.checks[key]=check
        self.lock=QCheckBox(T('Panel konumlarını ve boyutlarını kilitle'));self.lock.setChecked(canvas.locked);self.lock.toggled.connect(canvas.set_locked);layout.addWidget(self.lock)
        reset=QPushButton(T('Varsayılan yerleşime dön'));reset.clicked.connect(self.reset);layout.addWidget(reset)
        done=QPushButton(T('Tamam'));done.clicked.connect(self.accept);layout.addWidget(done);layout.addStretch()
    def reset(self):
        self.canvas.reset()
        for check in self.checks.values():check.blockSignals(True);check.setChecked(True);check.blockSignals(False)
        self.lock.blockSignals(True);self.lock.setChecked(False);self.lock.blockSignals(False)
