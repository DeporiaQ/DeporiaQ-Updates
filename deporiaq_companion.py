"""Optional, local 3D desktop companion. It never reads business data."""
import json,math,random,time,sys
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,Qt,QUrl,QPoint,QEvent,QRect
from PySide6.QtGui import QColor,QPainter,QPen,QBrush,QCursor,QFont,QRegion,QPolygon
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QFormLayout,QHBoxLayout,QSpinBox
from deporiaq_i18n import T,render,QLabel,QCheckBox,QLineEdit,QPushButton

class PetState:
    def __init__(self,saved=None,now=None):
        saved=saved or {};now=time.time() if now is None else now
        self.name=str(saved.get('name','Mırmır'))[:32] or 'Mırmır'
        self.enabled=bool(saved.get('enabled',True));self.motion=bool(saved.get('motion',True));self.messages=bool(saved.get('messages',True))
        last_fed=float(saved.get('last_fed',now));self.last_fed=min(now,last_fed) if math.isfinite(last_fed) else now
        self.food=bool(saved.get('food',False))
        self.size=max(140,min(240,int(saved.get('size',180))))
    def hungry(self,now=None):return (time.time() if now is None else now)-self.last_fed>=3600
    def eat(self,now=None):
        if not self.food:return False
        self.food=False;self.last_fed=time.time() if now is None else now;return True
    def export(self):return dict(name=self.name,enabled=self.enabled,motion=self.motion,last_fed=self.last_fed,food=self.food,size=self.size,messages=self.messages)

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
    """Seated companion anchored inside its sidebar home; pointer affects gaze only."""
    def __init__(self,window,dock):
        super().__init__(window);self.window=window;self.dock=dock;dock.controller=self
        self.key='companion_v1_'+str(window.kullanici['id'])
        try:self.state=PetState(json.loads(window.vt.ayar_getir(self.key,'{}')))
        except (TypeError,ValueError):self.state=PetState()
        self.view=None;self.failed=False;self.mode='idle';self.mode_until=0
        self.origin=time.monotonic();self.message_until=self.origin+9;self.next_message=self.origin+28;self.message_index=0
        window.companion_host.installEventFilter(self)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(50);self.apply()
    def ensure_view(self):
        if self.view or self.failed:return
        if QApplication.platformName()=='offscreen':return
        try:
            from PySide6.QtQuickWidgets import QQuickWidget
            import PySide6.QtQuick3D
            from deporiaq_fur import register_fur
            register_fur()
            view=QQuickWidget(self.window.companion_host);view.setObjectName('companion3D')
            view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
            view.setClearColor(Qt.GlobalColor.transparent);view.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
            view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);view.setStyleSheet('background:transparent;border:0;')
            view.setCursor(Qt.CursorShape.PointingHandCursor);view.installEventFilter(self)
            view.setSource(QUrl.fromLocalFile(str(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'companion/Cat.qml')))
            if view.status()==QQuickWidget.Status.Error:self.failed=True;view.deleteLater();return
            self.view=view;self.resize();self.home()
        except (ImportError,RuntimeError):self.failed=True
    def eventFilter(self,obj,event):
        if obj is self.window.companion_host and event.type()==QEvent.Type.Resize:self.resize()
        if obj is self.view and event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.window.assistant_open();return True
        return super().eventFilter(obj,event)
    def save(self):self.window.vt.ayar_kaydet(self.key,json.dumps(self.state.export(),ensure_ascii=False));self.window.vt.baglanti.commit()
    def resize(self):
        if self.view:
            host=self.window.companion_host;size=min(self.state.size,max(1,host.width()),200)
            self.view.resize(size,round(size*1.12));host.setFixedHeight(self.view.height()+4)
            self.view.setToolTip(self.state.name+' · '+str(T('Asistanı aç')));self.home()
    def apply(self):
        if self.state.enabled:self.ensure_view()
        self.resize();available=self.state.enabled and self.view is not None and not self.failed
        self.window.companion_host.setVisible(available);self.dock.setVisible(available)
        if self.view:self.view.setVisible(available)
        self.window.header.assistant.setVisible(not available);self.dock.update()
    def home_point(self):
        host=self.window.companion_host;width=self.view.width() if self.view else self.state.size
        return QPoint(max(0,(host.width()-width)//2),0)
    def home(self):
        if self.view:self.view.move(self.home_point())
    def clamp_position(self):self.home()
    def feed(self):
        self.state.food=True;self.save();self.dock.update();self.set_mode('eat',3)
        self.message_until=time.monotonic()+8
    def set_mode(self,mode,seconds):
        self.mode=mode if mode in ('idle','hungry','eat','happy') else 'idle'
        self.mode_until=time.monotonic()+seconds
        if self.view and self.view.rootObject():self.view.rootObject().setProperty('mood',self.mode)
    def set_enabled(self,on):self.state.enabled=on;self.save();self.apply()
    def message(self):
        if self.mode in ('eat','happy'):return T('Teşekkür ederim! Çok mutlu oldum.')
        if self.state.hungry():return T('Acıktım, bana mama verir misin?')
        messages=(T('Sana nasıl yardımcı olabilirim?'),T('İstersen ayarlardan ismimi değiştirebilirsin.'),T('Yardımcı kedin burada! Bana tıkla.'))
        return messages[self.message_index%len(messages)]
    def tick(self):
        now=time.monotonic()
        if self.state.food and self.mode not in ('eat','happy'):self.set_mode('eat',3)
        if now>=self.mode_until:
            if self.mode=='eat':self.state.eat();self.save();self.dock.update();self.set_mode('happy',5)
            else:self.set_mode('hungry' if self.state.hungry() else 'idle',10)
        if not self.view or not self.state.enabled:return
        assistant=getattr(self.window,'assistant_panel',None)
        visible=(self.window.isVisible() and not self.window.isMinimized() and self.window.isActiveWindow()
            and QApplication.activeModalWidget() is None and QApplication.activePopupWidget() is None
            and not (assistant and assistant.isVisible()))
        self.view.setVisible(visible)
        if not visible:return
        root=self.view.rootObject()
        if root is None:return
        self.home();root.setProperty('phase',(now-self.origin) if self.state.motion else 0)
        pointer=self.view.mapFromGlobal(QCursor.pos());delta=pointer-self.view.rect().center()
        root.setProperty('lookX',max(-1,min(1,delta.x()/200)) if self.state.motion else 0)
        root.setProperty('lookY',max(-1,min(1,delta.y()/180)) if self.state.motion else 0)
        blink_phase=(now-self.origin)%5.4;root.setProperty('blink',.16 if 5.22<blink_phase<5.34 and self.state.motion else 1.0)
        if now>=self.next_message:
            self.message_index+=1;self.message_until=now+9;self.next_message=now+32
        root.setProperty('messageText',render(self.message()) if self.state.messages and now<self.message_until else '')
    def stop(self):
        self.timer.stop()
        if self.view:self.view.hide()

def companion_settings(controller,tabs):
    page=QWidget();form=QFormLayout(page)
    enabled=QCheckBox(T('3D kediyi göster'));enabled.setChecked(controller.state.enabled)
    name=QLineEdit(controller.state.name);name.setMaxLength(32)
    messages=QCheckBox(T('Ara sıra yardım tabelası göster'));messages.setChecked(controller.state.messages)
    motion=QCheckBox(T('Fareyi bakışlarıyla takip et'));motion.setChecked(controller.state.motion)
    size=QSpinBox();size.setRange(140,240);size.setValue(controller.state.size);size.setSuffix(' px')
    feed=QPushButton(T('Mama kabını doldur'));feed.clicked.connect(controller.feed)
    save=QPushButton(T('Kedi ayarlarını kaydet'))
    def commit():
        controller.state.name=name.text().strip() or 'Mırmır';controller.state.enabled=enabled.isChecked();controller.state.motion=motion.isChecked();controller.state.messages=messages.isChecked();controller.state.size=size.value();controller.save();controller.apply()
    save.clicked.connect(commit)
    form.addRow(enabled);form.addRow(T('Adı'),name);form.addRow(motion);form.addRow(messages);form.addRow(T('Boyut'),size);form.addRow(feed);form.addRow(save)
    note=QLabel(T('Kedinize tıklayarak asistanı açın. Kedi gizlendiğinde üstteki Asistan düğmesini kullanabilirsiniz.'));note.setWordWrap(True);form.addRow(note)
    tabs.addTab(page,T('Kedim'))
