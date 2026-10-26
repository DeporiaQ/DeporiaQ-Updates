"""Persistent dashboard grid. Hidden panels keep their data and reserved layout."""
import json
import math
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
        self.close.setToolTip(T('Paneli gizle'));self.close.setStyleSheet('QPushButton{background:transparent;border:0;padding:0;font-size:19px;} QPushButton:hover{background:rgba(120,145,170,45);border-radius:6px;}')
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
        p=QPainter(self);p.setPen(QPen(self.palette().windowText().color(),1.2))
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
    COLUMNS=24
    GAP=12
    ROW=52
    def __init__(self,window):
        super().__init__();self.window=window;self.panels={};self.defaults={};self.restoring=False
        self.key='panel_layout_v2_'+str(window.kullanici['id']);self.locked=False
        try:
            raw=json.loads(window.vt.ayar_getir(self.key,'{}'));self.saved=raw if isinstance(raw,dict) else {}
        except (ValueError,TypeError):self.saved={}
        if not self.saved:
            try:
                legacy=json.loads(window.vt.ayar_getir('panel_layout_v1_'+str(window.kullanici['id']),'{}'))
                for k,state in legacy.items():
                    if isinstance(state,dict) and isinstance(state.get('rect'),list) and len(state['rect'])==4:
                        x,y,w,h=state['rect']
                        self.saved[k]={'grid':[max(0,round(x/1600*24)),max(0,round(y/900*15)),max(1,round(w/1600*24)),max(1,round(h/900*15))],'visible':bool(state.get('visible',True))}
                self.saved['_locked']=bool(legacy.get('_locked',False))
            except (ValueError,TypeError,AttributeError):self.saved={}
        self.default_visibility={};self.openers={};self.grid={};self._laying_out=False
        self.locked=bool(self.saved.get('_locked',False));self.setMinimumSize(1000,780)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def add(self,key,title,content,rect,minimum=(210,160),visible=True,opener=None):
        self.defaults[key]=rect;panel=DashboardPanel(self,key,title,content,minimum);self.panels[key]=panel
        self.default_visibility[key]=visible;self.openers[key]=opener
        self.restore_panel(panel);return panel
    def state(self,key):
        state=self.saved.get(key,{})
        if not isinstance(state,dict):state={}
        rect=state.get('grid')
        if not isinstance(rect,(list,tuple)) or len(rect)!=4 or any(type(n) is not int or not 0<=n<=2000 for n in rect):
            x,y,w,h=self.defaults[key]
            rect=[round(x/1600*24),round(y/900*15),max(1,round(w/1600*24)),max(1,round(h/900*15))]
        return rect,bool(state.get('visible',self.default_visibility[key]))
    def bounds(self,cell):
        col,row,cols,rows=cell;pitch=(self.width()+self.GAP)/self.COLUMNS
        x=round(col*pitch);right=round((col+cols)*pitch)-self.GAP
        return QRect(x,row*self.ROW,right-x,rows*self.ROW-self.GAP)
    @staticmethod
    def intersects(a,b):
        return a[0]<b[0]+b[2] and a[0]+a[2]>b[0] and a[1]<b[1]+b[3] and a[1]+a[3]>b[1]
    def fit(self,panel,cell):
        pitch=(self.width()+self.GAP)/self.COLUMNS
        cols=min(24,max(math.ceil((panel.minimum[0]+self.GAP)/pitch),cell[2]))
        rows=max(math.ceil((panel.minimum[1]+self.GAP)/self.ROW),cell[3])
        col=max(0,min(cell[0],24-cols));row=max(0,min(cell[1],500))
        other=[v for k,v in self.grid.items() if k!=panel.key and not self.panels[k].isHidden()]
        if not any(self.intersects((col,row,cols,rows),v) for v in other):return [col,row,cols,rows]
        # Only move the dragged panel. Closing one never compacts its neighbours.
        bottom=max([v[1]+v[3] for v in other]+[row])+rows
        candidates=sorted(((c,r) for r in range(bottom+1) for c in range(25-cols)),
                          key=lambda p:((p[0]-col)**2+(p[1]-row)**2,p[1],p[0]))
        for c,r in candidates:
            found=[c,r,cols,rows]
            if not any(self.intersects(found,v) for v in other):return found
        return [0,bottom,cols,rows]
    def place(self,panel,rect):
        pitch=(self.width()+self.GAP)/24
        cell=[round(rect.x()/pitch),round(rect.y()/self.ROW),round((rect.width()+self.GAP)/pitch),round((rect.height()+self.GAP)/self.ROW)]
        self.grid[panel.key]=self.fit(panel,cell);panel.setGeometry(self.bounds(self.grid[panel.key]));self.grow()
    def grow(self):
        bottom=max([c[1]+c[3] for k,c in self.grid.items() if not self.panels[k].isHidden()]+[15])
        height=bottom*self.ROW-self.GAP
        if self.minimumHeight()!=height:self.setMinimumHeight(height)
    def restore_panel(self,panel):
        rect,visible=self.state(panel.key)
        panel.setVisible(visible);panel.corner.setVisible(not self.locked)
        self.grid[panel.key]=self.fit(panel,rect) if visible else rect
        panel.setGeometry(self.bounds(self.grid[panel.key]));self.grow()
        panel.bar.setCursor(Qt.CursorShape.ArrowCursor if self.locked else Qt.CursorShape.SizeAllCursor)
    def remember(self,panel):
        self.saved[panel.key]={'grid':list(self.grid[panel.key]),'visible':not panel.isHidden()};self.save()
    def save(self):
        self.saved['_locked']=self.locked;self.window.vt.ayar_kaydet(self.key,json.dumps(self.saved));self.window.vt.baglanti.commit();self.changed.emit()
    def set_visible(self,key,visible):
        panel=self.panels[key];panel.setVisible(visible)
        if visible:self.grid[key]=self.fit(panel,self.grid[key]);panel.setGeometry(self.bounds(self.grid[key]))
        self.grow();self.remember(panel)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self._laying_out:return
        self._laying_out=True
        try:
            # Horizontal scaling keeps the pixel gap constant; vertical cells do not stretch.
            for panel in self.panels.values():
                if panel.key in self.grid:
                    self.grid[panel.key]=self.fit(panel,self.grid[panel.key]) if not panel.isHidden() else self.grid[panel.key]
                    panel.setGeometry(self.bounds(self.grid[panel.key]))
            self.grow()
        finally:self._laying_out=False
    def reset(self):
        self.saved={};self.grid={};self.locked=False
        for panel in self.panels.values():self.restore_panel(panel)
        self.save()
    def set_locked(self,locked):
        self.locked=locked
        for panel in self.panels.values():
            panel.corner.setVisible(not locked)
            panel.bar.setCursor(Qt.CursorShape.ArrowCursor if locked else Qt.CursorShape.SizeAllCursor)
        self.save()
    def open_panel(self,key):
        if self.openers.get(key):return self.openers[key]()
        panel=self.panels[key];dialog=WorkspaceDialog(self.window);dialog.setWindowTitle(panel.title);dialog.resize(900,620)
        layout=QVBoxLayout(dialog);layout.addWidget(panel.content);panel.content.show()
        try:dialog.exec()
        finally:panel.layout().addWidget(panel.content,1);panel.content.show();dialog.deleteLater()

class PanelsDialog(WorkspaceDialog):
    def __init__(self,canvas,parent):
        super().__init__(parent);self.setWindowTitle(T('Paneller'));self.resize(640,700);self.canvas=canvas
        layout=QVBoxLayout(self);title=QLabel(T('Çalışma alanınız'));title.setObjectName('sayfaBaslik');layout.addWidget(title)
        note=QLabel(T('İşaretlenen paneller ana sayfada görünür. Aç düğmesi, paneli ana sayfaya eklemeden açar. Taşıma ve boyutlandırma sabit aralıklı düzene oturur; gizlenen panelin yeri boş kalır.'));note.setWordWrap(True);layout.addWidget(note)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();items=QVBoxLayout(body);scroll.setWidget(body);layout.addWidget(scroll,1)
        self.checks={}
        for key,panel in canvas.panels.items():
            row=QHBoxLayout();check=QCheckBox(panel.title);check.setChecked(not panel.isHidden());check.toggled.connect(lambda on,k=key:canvas.set_visible(k,on));row.addWidget(check,1);self.checks[key]=check
            button=QPushButton(T('Aç'));button.clicked.connect(lambda checked=False,k=key:canvas.open_panel(k));row.addWidget(button);items.addLayout(row)
        self.lock=QCheckBox(T('Panel konumlarını ve boyutlarını kilitle'));self.lock.setChecked(canvas.locked);self.lock.toggled.connect(canvas.set_locked);layout.addWidget(self.lock)
        reset=QPushButton(T('Varsayılan yerleşime dön'));reset.clicked.connect(self.reset);layout.addWidget(reset)
        done=QPushButton(T('Tamam'));done.clicked.connect(self.accept);layout.addWidget(done);layout.addStretch()
    def reset(self):
        self.canvas.reset()
        for key,check in self.checks.items():check.blockSignals(True);check.setChecked(self.canvas.default_visibility[key]);check.blockSignals(False)
        self.lock.blockSignals(True);self.lock.setChecked(False);self.lock.blockSignals(False)
