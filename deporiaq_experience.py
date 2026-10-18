"""Responsive header, accessible vector controls and in-app discovery."""
import math
import unicodedata
from PySide6.QtCore import Qt,QRectF,QPointF,QTimer,QSize,QEvent
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen,QIcon,QPixmap,QPolygonF,QFont
from PySide6.QtWidgets import QAbstractButton,QFrame,QHBoxLayout,QVBoxLayout,QListWidget,QListWidgetItem,QApplication
from deporiaq_i18n import T,render,language,Localized,QLabel,QLineEdit,QPushButton
from deporiaq_commerce_ui import Job,StockDialog

def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(value).replace('ı','i').replace('İ','i').casefold()) if not unicodedata.combining(c))

class IconButton(Localized,QAbstractButton):
    def __init__(self,kind,label,parent=None):
        super().__init__(parent);self.kind=kind;self.label=label;self.unread=0
        self.setFixedSize(42,42);self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.setToolTip(label);self.setAccessibleName(label)
    def setCount(self,count):
        self.unread=max(0,int(count));self.update()
        self.setToolTip(T('Bildirimler · {count} okunmamış',count=self.unread));self.setAccessibleName(T('Bildirimler · {count} okunmamış',count=self.unread))
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color=self.palette().windowText().color();color.setAlpha(255 if self.underMouse() or self.hasFocus() else 210)
        p.setPen(QPen(color,1.8,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));p.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind=='settings':
            polygon=QPolygonF()
            for i in range(32):
                angle=i*math.pi/16;r=11 if i%4 in (0,3) else 8.3
                polygon.append(QPointF(21+math.cos(angle)*r,21+math.sin(angle)*r))
            p.drawPolygon(polygon);p.drawEllipse(QPointF(21,21),3.4,3.4)
        elif self.kind=='moon':
            outer=QPainterPath();outer.addEllipse(QRectF(10,10,22,22));cut=QPainterPath();cut.addEllipse(QRectF(18,5,22,22));p.drawPath(outer.subtracted(cut))
        elif self.kind=='sun':
            p.drawEllipse(QPointF(21,21),6,6)
            for i in range(8):
                a=i*math.pi/4;p.drawLine(QPointF(21+9*math.cos(a),21+9*math.sin(a)),QPointF(21+12*math.cos(a),21+12*math.sin(a)))
        elif self.kind=='bell':
            path=QPainterPath(QPointF(11,27));path.lineTo(14,23);path.lineTo(14,18);path.cubicTo(14,8,28,8,28,18);path.lineTo(28,23);path.lineTo(31,27);path.closeSubpath();p.drawPath(path);p.drawArc(QRectF(18,26,6,7),180*16,180*16)
            if self.unread:
                p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#FBBF24'));p.drawEllipse(QRectF(25,1,17,17));p.setPen(QColor('#152036'));p.setFont(QFont('Segoe UI',8,QFont.Weight.Bold));p.drawText(QRectF(25,1,17,17),Qt.AlignmentFlag.AlignCenter,str(self.unread) if self.unread<100 else '99+')
        if self.hasFocus():
            p.setPen(QPen(QColor('#38BDF8'),1,Qt.PenStyle.DotLine));p.drawEllipse(QRectF(2,2,38,38))

class FlagButton(QAbstractButton):
    def __init__(self,code,parent=None):
        super().__init__(parent);self.code=code;self.setFixedSize(62,42);self.setCheckable(True)
        self.setToolTip('Türkçe' if code=='tr' else 'English');self.setAccessibleName(self.toolTip());self.setCursor(Qt.CursorShape.PointingHandCursor)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        area=QRectF(8,7,46,28);clip=QPainterPath();clip.addRoundedRect(area,3,3);p.setClipPath(clip)
        if self.code=='tr':
            p.fillRect(area,QColor('#E30A17'));p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('white'));p.drawEllipse(QRectF(20,11,20,20));p.setBrush(QColor('#E30A17'));p.drawEllipse(QRectF(24,11,17,20))
            star=QPolygonF()
            for i in range(10):
                angle=i*math.pi/5-math.pi/2;r=6 if i%2==0 else 2.5;star.append(QPointF(40+math.cos(angle)*r,21+math.sin(angle)*r))
            p.setBrush(QColor('white'));p.drawPolygon(star)
        else:
            p.fillRect(area,QColor('#012169'))
            for col,width in [('white',8),('#C8102E',3)]:
                p.setPen(QPen(QColor(col),width));p.drawLine(QPointF(8,7),QPointF(54,35));p.drawLine(QPointF(54,7),QPointF(8,35))
            for col,width in [('white',10),('#C8102E',6)]:
                p.setPen(QPen(QColor(col),width));p.drawLine(QPointF(31,7),QPointF(31,35));p.drawLine(QPointF(8,21),QPointF(54,21))
        p.setClipping(False)
        if self.isChecked() or self.hasFocus():p.setPen(QPen(QColor('#38BDF8'),2));p.drawLine(QPointF(15,40),QPointF(47,40))

def search_icon():
    pix=QPixmap(28,28);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(130,151,176,210),2.2,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));p.drawEllipse(QRectF(5,4,12,12));p.drawLine(QPointF(15,15),QPointF(23,23));p.end();return QIcon(pix)

class ExperienceHeader(QFrame):
    def __init__(self,window,version):
        super().__init__();self.window=window;self.setObjectName('ustCubuk')
        self.brand=QLabel('DeporiaQ',self);self.brand.setObjectName('markaKucuk')
        self.version=QLabel('v'+version,self);self.version.setObjectName('surum')
        self.profile=QFrame(self);self.profile.setObjectName("headerProfile");pv=QVBoxLayout(self.profile);pv.setContentsMargins(0,0,0,0);pv.setSpacing(5)
        window.company_label=QLabel(window.cloud_client.company_name or window.vt.ayar_getir('isletme_adi','DeporiaQ'));window.company_label.setObjectName('isletme');window.company_label.setTextFormat(Qt.TextFormat.PlainText);pv.addWidget(window.company_label)
        window.user_label=QLabel();window.user_label.setObjectName('profil');window.user_label.setTextFormat(Qt.TextFormat.PlainText);pv.addWidget(window.user_label)
        window.subscription_label=QLabel(T('Abonelik doğrulanıyor'));window.subscription_label.setObjectName('profil');pv.addWidget(window.subscription_label)
        self.search=QLineEdit(self);self.search.setObjectName('globalSearch');self.search.setPlaceholderText(T('Ürün, barkod veya menü ara…'));self.search.setAccessibleName(T('Uygulamada ara'))
        self.search.setMaxLength(120);self.search.addAction(search_icon(),QLineEdit.ActionPosition.TrailingPosition).triggered.connect(window.global_search_open)
        self.assistant=QPushButton(T('Asistan'),self);self.assistant.setObjectName('assistantEntry');self.assistant.setStyleSheet('QPushButton{font-family:Segoe UI;font-size:16px;font-weight:600;color:#74d8ff;background:transparent;border:0;padding:4px;} QPushButton:hover{color:#b8eeff;}');self.assistant.clicked.connect(window.assistant_open)
        self.controls=QFrame(self);self.controls.setObjectName("headerActions");bar=QHBoxLayout(self.controls);bar.setContentsMargins(0,0,0,0);bar.setSpacing(4)
        self.settings=IconButton('settings',T('Ayarlar'));self.settings.clicked.connect(window.ayarlar_ac)
        window.notification_button=IconButton('bell',T('Bildirimler'));window.notification_button.clicked.connect(window.notification_history)
        self.dark=IconButton('sun' if window.vt.ayar_getir('ui_mode','dark')=='dark' else 'moon',T('Açık / karanlık mod'));self.dark.clicked.connect(window.toggle_mode)
        for button in (self.settings,window.notification_button,self.dark):bar.addWidget(button)
        self.setMinimumWidth(0);self.reflow()
    def reflow(self):
        w=self.width();wide=w>=1320;self.setFixedHeight(96 if wide else 148)
        self.brand.setGeometry(20,12,170,38);self.version.setGeometry(22,52,160,24)
        profile_width=max(160,min(300,w-380));self.profile.setGeometry(205,10,profile_width,76)
        self.controls.setGeometry(w-156,22,138,44)
        if wide:
            width=min(560,w-2*(205+profile_width+20));width=max(240,width);y=26
        else:width=min(560,w-280);y=96
        self.search.setGeometry((w-width)//2,y,width,44)
        self.assistant.setGeometry((w+width)//2+10,y,110,44)
    def resizeEvent(self,event):super().resizeEvent(event);self.reflow()

class SearchController(QFrame):
    def __init__(self,window,entry):
        super().__init__(window);self.window=window;self.entry=entry;self.job=None;self.query='';self.generation=0;self.records=[]
        self.setObjectName('searchResults');layout=QVBoxLayout(self);layout.setContentsMargins(10,10,10,10)
        self.hint=QLabel(T('Menüye veya ürüne geçmek için seçin.'));layout.addWidget(self.hint)
        self.list=QListWidget();self.list.setMinimumHeight(190);layout.addWidget(self.list)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(300);self.timer.timeout.connect(self.lookup)
        entry.textChanged.connect(self.changed);entry.returnPressed.connect(self.open_selected);entry.installEventFilter(self);self.list.installEventFilter(self)
        self.list.itemActivated.connect(self.open_selected);self.list.itemClicked.connect(self.open_selected);self.hide()
    def commands(self):
        w=self.window
        entries=[(T('Ana Sayfa'),w.home),(T('Paneller'),w.panels_open),(T('Stok ve Ürünler'),w.stok_merkezi_ac),(T('Satışlar'),w.satis_merkezi_ac),(T('Depolar ve Transferler'),w.depo_merkezi_ac),(T('Raporlar'),w.rapor_merkezi_ac),(T('Ayarlar'),w.ayarlar_ac),(T('Paketim ve Abonelik'),w.paket_ac),(T('Yardım ve Destek'),w.destek_merkezi_ac),(T('DeporiaQ Asistan'),w.assistant_open)]
        if w.kullanici['rol']=='ANA_YONETICI':entries.append((T('Yönetim'),w.yonetim_merkezi_ac))
        return [{'kind':'menu','title':label,'subtitle':T('Menü'),'action':action} for label,action in entries if not self.query or fold(self.query) in fold(label) or fold(self.query) in fold(label.source)]
    def position(self):
        origin=self.entry.mapTo(self.window,self.entry.rect().bottomLeft());self.setGeometry(origin.x(),origin.y()+6,max(390,self.entry.width()),290)
    def changed(self,text):
        self.query=text.strip();self.generation+=1;self.records=self.commands();self.render();self.position();self.show();self.raise_()
        self.timer.start()
    def lookup(self):
        if self.job is not None or len(self.query)<2:return
        if not self.window.cloud_client.bagli:self.hint.setText(T('Ürün araması için Cloud bağlantısı gerekli.'));return
        generation=self.generation;query=self.query
        self.hint.setText(T('Ürün ve konumlar aranıyor…'))
        self.job=Job(lambda:self.window.cloud_client._istek('/rest/v1/rpc/dpq_search','POST',{'p_query':query,'p_device':self.window.cloud_client.cihaz_kimligi}),self)
        self.job.finished.connect(lambda:self.complete(generation));self.job.start()
    def complete(self,generation):
        job=self.job;self.job=None
        if generation==self.generation:
            if job.error:self.hint.setText(T('Cloud araması tamamlanamadı. Tekrar deneyin.'))
            else:self.records=self.commands()+list(job.result or []);self.render()
        else:self.timer.start()
        job.deleteLater()
    def render(self):
        self.list.clear()
        for record in self.records:
            title=render(record['title']);subtitle=render(record.get('subtitle',''))
            item=QListWidgetItem(title+'\n'+subtitle);item.setSizeHint(QSize(200,52));self.list.addItem(item)
        self.list.setCurrentRow(0)
        self.hint.setText(T('Sonuç bulunamadı.') if not self.records else T('Menüye veya ürüne geçmek için seçin.'))
    def open_selected(self,*_):
        if not self.isVisible():return
        index=self.list.currentRow()
        if not 0<=index<len(self.records):return
        row=self.records[index];self.hide();self.entry.clearFocus()
        if row['kind']=='menu':QTimer.singleShot(0,row['action']);return
        window=self.window
        class FoundStock(StockDialog):
            def populate(self,data):
                super().populate(data)
                if row['kind']=='product':self.search.setText(row['subtitle'])
                else:self.filter_location.setCurrentIndex(max(0,self.filter_location.findData(row['id'])))
        FoundStock(window.commerce,'catalog',window).exec()
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.KeyPress:
            if event.key()==Qt.Key.Key_Escape:self.hide();return True
            if obj is self.entry and event.key()==Qt.Key.Key_Down:self.list.setFocus();return True
        if event.type()==QEvent.Type.FocusOut:
            QTimer.singleShot(0,self,self.hide_when_blurred)
        return False

    def hide_when_blurred(self):
        if not (self.entry.hasFocus() or self.list.hasFocus()):self.hide()
