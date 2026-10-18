"""Optional, local 3D desktop companion. It never reads business data."""
import json,math,random,time,sys
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,Qt,QUrl,QPoint,QEvent,QRect
from PySide6.QtGui import QColor,QPainter,QPen,QBrush,QCursor,QFont,QRegion,QPolygon
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QFormLayout,QHBoxLayout,QSpinBox
from deporiaq_i18n import T,QLabel,QCheckBox,QLineEdit,QPushButton

class PetState:
    def __init__(self,saved=None,now=None):
        saved=saved or {};now=time.time() if now is None else now
        self.name=str(saved.get('name','Mırmır'))[:32] or 'Mırmır'
        self.enabled=bool(saved.get('enabled',True));self.motion=bool(saved.get('motion',True))
        last_fed=float(saved.get('last_fed',now));self.last_fed=min(now,last_fed) if math.isfinite(last_fed) else now
        self.food=bool(saved.get('food',False))
        self.size=max(140,min(240,int(saved.get('size',180))))
    def hungry(self,now=None):return (time.time() if now is None else now)-self.last_fed>=3600
    def eat(self,now=None):
        if not self.food:return False
        self.food=False;self.last_fed=time.time() if now is None else now;return True
    def export(self):return dict(name=self.name,enabled=self.enabled,motion=self.motion,last_fed=self.last_fed,food=self.food,size=self.size)

class PetDock(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.controller=None;self.setFixedSize(162,40);self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(T('Mama kabını doldur'));self.setAccessibleName(T('Mama kabı ve minder'))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    def mousePressEvent(self,event):
        if self.controller and event.button()==Qt.MouseButton.LeftButton:self.controller.feed()
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Space,Qt.Key.Key_Return) and self.controller:self.controller.feed()
        else:super().keyPressEvent(event)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#6685b0'),1));p.setBrush(QColor('#526585'));p.drawEllipse(68,18,85,20)
        p.setBrush(QColor('#778aab'));p.drawEllipse(71,16,79,18);p.setPen(QPen(QColor('#9cacc5'),1));p.drawEllipse(78,20,65,11)
        p.setPen(QPen(QColor('#5c91ab'),1));p.setBrush(QColor('#1d5972'));p.drawRoundedRect(7,17,45,19,8,8)
        p.setBrush(QColor('#90c5da'));p.drawEllipse(7,13,45,13);p.setBrush(QColor('#163546'));p.drawEllipse(12,16,35,7)
        if self.controller and self.controller.state.food:
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#d9a85c'))
            for x,y in [(18,17),(27,16),(37,17),(22,21),(32,21),(42,20)]:p.drawEllipse(x,y,5,4)
        elif self.controller and self.controller.state.hungry():
            p.setPen(QColor('#ffd080'));p.setFont(QFont('Segoe UI',10));p.drawText(22,12,'♡')
        if self.hasFocus():p.setPen(QPen(QColor('#38bdf8'),1,Qt.PenStyle.DotLine));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),5,5)

class CompanionController(QObject):
    def __init__(self,window,dock):
        super().__init__(window);self.window=window;self.dock=dock;dock.controller=self
        self.key='companion_v1_'+str(window.kullanici['id'])
        try:self.state=PetState(json.loads(window.vt.ayar_getir(self.key,'{}')))
        except (TypeError,ValueError):self.state=PetState()
        self.view=None;self.failed=False;self.mode='idle';self.mode_until=0;self.next_action=time.monotonic()+12
        self.target=None;self.origin=time.monotonic();self.last=time.monotonic();self.previous_distance=500;self.startle_after=0
        self.rng=random.Random();self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(50)
        self.apply()
    def ensure_view(self):
        if self.view or self.failed:return
        # Unit tests use a headless raster surface; production/3D rendering tests use a real RHI.
        if QApplication.platformName()=='offscreen':return
        try:
            from PySide6.QtQuickWidgets import QQuickWidget
            import PySide6.QtQuick3D
            from deporiaq_fur import register_fur
            register_fur()
            view=QQuickWidget(self.window);view.setObjectName('companion3D');view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
            view.setClearColor(Qt.GlobalColor.transparent);view.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
            view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);view.setStyleSheet('background:transparent;border:0;')
            view.setCursor(Qt.CursorShape.PointingHandCursor);view.installEventFilter(self)
            view.setSource(QUrl.fromLocalFile(str(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'companion/Cat.qml')))
            if view.status()==QQuickWidget.Status.Error:
                self.failed=True;view.deleteLater();return
            self.view=view;self.resize();self.home()
        except (ImportError,RuntimeError):self.failed=True
    def eventFilter(self,obj,event):
        if obj is self.view and event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.target=None;self.set_mode('happy',3);self.window.assistant_open();return True
        return super().eventFilter(obj,event)
    def save(self):self.window.vt.ayar_kaydet(self.key,json.dumps(self.state.export(),ensure_ascii=False));self.window.vt.baglanti.commit()
    def resize(self):
        if self.view:
            self.view.resize(self.state.size,round(self.state.size*236/220));self.view.setToolTip(self.state.name+' · '+str(T('Asistanı aç')))
            # Keep clear corners clickable without cutting off ears, paws or a
            # turning head. The previous head-shaped mask clipped real 3D poses.
            w,h=self.view.width(),self.view.height()
            outline=[(.08,0),(.92,0),(1,.08),(1,.92),(.92,1),(.08,1),(0,.92),(0,.08)]
            self.view.setMask(QRegion(QPolygon([QPoint(round(w*x),round(h*y)) for x,y in outline])));self.clamp_position()
    def apply(self):
        if self.state.enabled:self.ensure_view()
        self.resize();self.dock.setVisible(self.state.enabled and self.view is not None and not self.failed)
        if self.view:self.view.setVisible(self.state.enabled and not self.failed)
        self.window.header.assistant.setVisible(not self.state.enabled or self.failed or self.view is None)
        self.dock.update()
    def home_point(self):
        # Align the visible paws with the bowl/cushion, not the transparent
        # bottom margin of the 3D viewport.
        width=self.view.width() if self.view else self.state.size
        height=self.view.height() if self.view else round(width*236/220)
        p=self.dock.mapTo(self.window,QPoint(29 if self.state.food else 112,20))
        return QPoint(max(0,p.x()-width//2),max(0,p.y()-round(height*.77)))
    def home(self):
        if self.view:self.view.move(self.home_point());self.view.raise_()
    def clamp_position(self):
        if self.view:
            # The viewport's empty lower margin may extend beyond the window;
            # the visible cat stays inside, including when resting on its bed.
            floor=self.window.height()-round(self.view.height()*.82)-8
            self.view.move(max(0,min(self.view.x(),self.window.width()-self.view.width())),max(self.window.header.height(),min(self.view.y(),floor)))
    def feed(self):
        self.state.food=True;self.save();self.dock.update()
        if self.state.motion:self.target=self.home_point();self.set_mode('walk',20)
        else:self.target=None;self.home();self.set_mode('eat',5)
    def set_mode(self,mode,seconds):
        self.mode=mode;self.mode_until=time.monotonic()+seconds
        if self.view and self.view.rootObject():self.view.rootObject().setProperty('mood',mode)
    def set_enabled(self,on):self.state.enabled=on;self.save();self.apply()
    def tick(self):
        now=time.monotonic();dt=min(.1,now-self.last);self.last=now
        if not self.view or not self.state.enabled:return
        assistant=getattr(self.window,'assistant_panel',None)
        visible=(self.window.isVisible() and not self.window.isMinimized() and self.window.isActiveWindow()
            and QApplication.activeModalWidget() is None and QApplication.activePopupWidget() is None
            and not (assistant and assistant.isVisible()))
        self.view.setVisible(visible)
        if not visible:return
        root=self.view.rootObject()
        if root is None:return
        root.setProperty('phase',(now-self.origin) if self.state.motion else 0)
        self.clamp_position()
        pointer=self.window.mapFromGlobal(QCursor.pos());center=self.view.geometry().center();delta=pointer-center;dist=math.hypot(delta.x(),delta.y())
        root.setProperty('lookX',max(-1,min(1,delta.x()/120)));root.setProperty('lookY',max(-1,min(1,delta.y()/100)))
        blink_phase=(now-self.origin)%4.7;root.setProperty('blink',.12 if 4.55<blink_phase<4.67 else 1.0)
        if self.state.motion and self.mode=='sleep' and self.previous_distance>90 and dist<90 and now>self.startle_after:
            self.set_mode('startle',1.2);self.startle_after=now+20
        self.previous_distance=dist
        # A saved full bowl is still eaten after reopening the application.
        if self.state.food and self.target is None and self.mode not in ('eat','happy','walk'):
            if self.state.motion:self.target=self.home_point();self.set_mode('walk',20)
            else:self.home();self.set_mode('eat',5)
        if self.mode=='chase' and self.target is not None and now<self.mode_until:
            left=self.window.menu_kaydir.width()+15;top=self.window.header.height()+30
            self.target=QPoint(max(left,min(self.window.width()-self.view.width()-20,pointer.x()-self.view.width()//2)),max(top,min(self.window.height()-self.view.height()-65,pointer.y()+18)))
        if self.mode=='chase' and now>=self.mode_until:self.target=None;self.set_mode('play',3)
        if self.target is not None:
            pos=self.view.pos();dx=self.target.x()-pos.x();dy=self.target.y()-pos.y();length=math.hypot(dx,dy)
            if length<6:
                self.view.move(self.target);self.target=None
                if self.state.food and (self.target is None):self.set_mode('eat',5)
                elif self.mode=='walk':self.set_mode('idle',5)
            else:
                step=min(length,dt*100);self.view.move(pos.x()+round(dx/length*step),pos.y()+round(dy/length*step));root.setProperty('facing',max(-25,min(25,dx/4)))
            return
        root.setProperty('facing',math.sin((now-self.origin)*.25)*7)
        if now<self.mode_until:return
        if self.mode=='eat':
            self.state.eat();self.save();self.dock.update();self.set_mode('happy',4);return
        if self.mode=='happy':self.home();self.set_mode('sleep',45);return
        if self.mode in ('startle','wave','play','chase','peek'):self.set_mode('idle',8);return
        if not self.state.motion:self.home();self.set_mode('hungry' if self.state.hungry() else 'idle',15);return
        if self.state.hungry():self.home();self.set_mode('hungry',20);self.dock.update();return
        # Pauses around user input, and never leaves this application window.
        if dist<100:self.set_mode('idle',5);return
        action=self.rng.choice(['sleep','wave','walk','peek','chase','play'])
        if action=='sleep':self.home();self.set_mode('sleep',35)
        elif action=='peek':
            panels=[p for p in self.window.panel_canvas.panels.values() if not p.isHidden()]
            if panels:
                panel=self.rng.choice(panels);p=panel.mapTo(self.window,QPoint(panel.width()-self.view.width()//2,0))
                self.view.move(max(220,min(self.window.width()-self.view.width()-10,p.x())),max(self.window.header.height(),p.y()-self.view.height()//2));self.set_mode('peek',4)
        elif action in ('walk','chase'):
            left=self.window.menu_kaydir.width()+15;top=self.window.header.height()+30
            right=max(left,self.window.width()-self.view.width()-20);bottom=max(top,self.window.height()-self.view.height()-65)
            x=max(left,min(right,pointer.x()-self.view.width()//2)) if action=='chase' else self.rng.randint(left,right)
            y=max(top,min(bottom,pointer.y()+18)) if action=='chase' else self.rng.randint(top,bottom)
            self.target=QPoint(x,y);self.set_mode(action,12)
        else:self.set_mode(action,4)
    def stop(self):
        self.timer.stop()
        if self.view:self.view.hide()

def companion_settings(controller,tabs):
    page=QWidget();form=QFormLayout(page)
    enabled=QCheckBox(T('3D kediyi göster'));enabled.setChecked(controller.state.enabled)
    name=QLineEdit(controller.state.name);name.setMaxLength(32)
    motion=QCheckBox(T('Gezinme, oyun ve fareye tepki'));motion.setChecked(controller.state.motion)
    size=QSpinBox();size.setRange(140,240);size.setValue(controller.state.size);size.setSuffix(' px')
    feed=QPushButton(T('Mama kabını doldur'));feed.clicked.connect(controller.feed)
    save=QPushButton(T('Kedi ayarlarını kaydet'))
    def commit():
        controller.state.name=name.text().strip() or 'Mırmır';controller.state.enabled=enabled.isChecked();controller.state.motion=motion.isChecked();controller.state.size=size.value();controller.save();controller.apply()
    save.clicked.connect(commit)
    form.addRow(enabled);form.addRow(T('Adı'),name);form.addRow(motion);form.addRow(T('Boyut'),size);form.addRow(feed);form.addRow(save)
    note=QLabel(T('Kedinize tıklayarak asistanı açın. Kedi gizlendiğinde üstteki Asistan düğmesini kullanabilirsiniz.'));note.setWordWrap(True);form.addRow(note)
    tabs.addTab(page,T('Kedim'))
