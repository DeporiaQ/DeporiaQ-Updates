"""Offline in-application guide. No external AI service or API key is used."""
from PySide6.QtCore import Qt,QTimer,QEvent
from PySide6.QtWidgets import QDockWidget,QScrollArea,QVBoxLayout,QHBoxLayout,QFrame,QSizePolicy,QLayout
from deporiaq_i18n import T,render,Localized,QLabel,QPlainTextEdit,QPushButton,QWidget,QComboBox
from deporiaq_translations import EN
from deporiaq_assistant_guide import TOPICS,BY_KEY,lookup,fold,FOLLOW_UP,GREETINGS

for topic in TOPICS:
    EN[topic.title]=topic.title_en
    EN[topic.body]=topic.body_en

# Explicit navigation allowlist. Questions can never supply a method or command.
ACTIONS={
 'catalog':(T('Ürünler ve Stokları Aç'),'urun_yonetimi_ac'),
 'stock_menu':(T('Stok ve Ürünleri Aç'),'stok_merkezi_ac'),
 'receive':(T('Stok Girişini Aç'),'stok_girisi_ac'),
 'transfer':(T('Stok Transferini Aç'),'transfer_ac'),
 'count':(T('Stok Sayımını Aç'),'araclar_ac'),
 'sales':(T('Satışlar Menüsünü Aç'),'satis_merkezi_ac'),
 'branch_sale':(T('Şube Satış / Rezervasyonu Aç'),'satis_ac'),
 'management':(T('Yönetim Menüsünü Aç'),'yonetim_merkezi_ac'),
 'reports':(T('Raporlar Menüsünü Aç'),'rapor_merkezi_ac'),
 'operations':(T('Operasyon Merkezini Aç'),'operasyon_ac'),
 'backup':(T('Yedekleme Ekranını Aç'),'yedek_al'),
 'settings':(T('Ayarları Aç'),'ayarlar_ac'),
 'plans':(T('Paketim ve Aboneliği Aç'),'paket_ac'),
 'support':(T('Destek Talebi Ekranını Aç'),'destek_ac'),
 'help':(T('Kullanım Rehberini Aç'),'yardim_ac'),
 'search':(T('Üst Arama Alanını Aç'),'global_search_open'),
 'notifications':(T('Bildirimleri Aç'),'notification_history'),
 'shortcuts':(T('Kısayolları Aç'),'kisayollar_ac'),
 'updates':(T('Güncellemeleri Denetle'),'guncelleme_denetle'),
 'panels':(T('Panelleri Aç'),'panels_open'),
 'orders':(T('İnternet Siparişlerini Aç'),'internet_ac'),
}
ADMIN_ACTIONS={'management','operations','backup'}
BUSINESS_ACTIONS={'catalog','stock_menu','receive','transfer','count','sales','branch_sale','management','reports','operations','backup','orders'}
WRITE_SCREENS={'receive','transfer','count','sales','branch_sale','orders'}

class AssistantPanel(Localized,QDockWidget):
    MAX_MESSAGES=24
    def __init__(self,window):
        super().__init__(window);self.setWindowTitle(T('DeporiaQ Asistan'));self.window=window;self.job=None;self.history=[];self.ready=True;self.last_topic=None
        self.setObjectName('assistantDock');self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable);self.setMinimumWidth(345);self.setMaximumWidth(460)
        root=QWidget();layout=QVBoxLayout(root);layout.setContentsMargins(16,14,16,14);layout.setSpacing(10)
        heading=QLabel(T('DeporiaQ Asistan'));heading.setObjectName('sayfaBaslik');layout.addWidget(heading)
        self.status=QLabel(T('DeporiaQ kullanımında yanınızdayım.'));self.status.setWordWrap(True);layout.addWidget(self.status)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.messages=QWidget();self.messages_layout=QVBoxLayout(self.messages);self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize);self.scroll.setWidget(self.messages);layout.addWidget(self.scroll,1)
        self.input=QPlainTextEdit();self.input.setPlaceholderText(T('Örneğin: Şubeler arası transfer nasıl yapılır?'));self.input.setAccessibleName(T('Kullanım sorunuzu yazın'));self.input.setMaximumHeight(86);self.input.installEventFilter(self);layout.addWidget(self.input)
        self.input.textChanged.connect(self.input_changed)
        bar=QHBoxLayout();self.send=QPushButton(T('Gönder'));self.send.setObjectName('birincil');self.send.clicked.connect(self.submit);bar.addWidget(self.send)
        self.clear=QPushButton(T('Yeni sohbet'));self.clear.clicked.connect(self.reset);bar.addWidget(self.clear);layout.addLayout(bar)
        self.setStyleSheet("QDockWidget#assistantDock{background:#101b2c;border:1px solid #344d69;border-radius:16px;}");self.setWidget(root);self.resize(410,500);self.reset()

    def position_in_window(self):
        w=self.window;self.resize(min(430,max(345,w.width()-40)),min(530,max(350,w.height()-180)))
        self.move(max(10,w.width()-self.width()-24),max(100,w.height()-self.height()-76))

    def check(self):
        # Kept as a local availability hook for the main window; no network check.
        self.ready=True;self.status.setText(T('DeporiaQ kullanımında yanınızdayım.'))

    def input_changed(self):
        length=len(self.input.toPlainText().strip());self.send.setEnabled(0<length<=2000)
        if length>2000:self.status.setText(T('Sorunuzu en fazla 2000 karakterle yazın.'))
        else:self.status.setText(T('DeporiaQ kullanımında yanınızdayım.'))

    def eventFilter(self,obj,event):
        if obj is self.input and event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if not event.isAutoRepeat():self.submit()
            return True
        return super().eventFilter(obj,event)

    def unavailable(self,action):
        if action not in ACTIONS:return T('Bu ekran rehberden açılamıyor.')
        role=self.window.kullanici['rol']
        if action in ADMIN_ACTIONS and role!='ANA_YONETICI':return T('Bu ekran için ana yönetici yetkisi gerekir.')
        if action in BUSINESS_ACTIONS and getattr(self.window,'lisans_kilitli',False):return T('Bu ekran için etkin abonelik gerekir.')
        cloud_role=getattr(getattr(self.window,'cloud_client',None),'role','')
        if action in WRITE_SCREENS and (role=='GORUNTULEYICI' or cloud_role=='viewer'):return T('Görüntüleyici hesabı bu işlem ekranını açamaz.')
        return None

    def navigate(self,action):
        reason=self.unavailable(action)
        if reason:self.status.setText(reason);return
        method=getattr(self.window,ACTIONS[action][1],None)
        if not callable(method):self.status.setText(T('Bu ekran rehberden açılamıyor.'));return
        # This only opens an existing, permission-checked screen. Never submit it.
        method()

    def append(self,name,text,actions=(),choices=()):
        frame=QFrame();frame.setObjectName('assistantMessage');frame.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Minimum);box=QVBoxLayout(frame)
        label=QLabel(name);label.setObjectName('soluk');box.addWidget(label)
        content=QLabel(text);content.setTextFormat(Qt.TextFormat.PlainText);content.setWordWrap(True);content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Minimum)
        content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);box.addWidget(content)
        for key in choices:
            button=QPushButton(T(BY_KEY[key].title));button.setMinimumHeight(38);button.setProperty('topic_id',key);button.clicked.connect(lambda checked=False,k=key:self.show_topic(k));box.addWidget(button)
        for action in actions:
            button=QPushButton(ACTIONS[action][0]);button.setMinimumHeight(38);button.setProperty('guide_action',action)
            reason=self.unavailable(action)
            if reason:button.setEnabled(False);button.setToolTip(reason)
            button.clicked.connect(lambda checked=False,a=action:self.navigate(a));box.addWidget(button)
        self.messages_layout.addWidget(frame)
        while self.messages_layout.count()>self.MAX_MESSAGES:
            old=self.messages_layout.takeAt(0).widget();old.hide();old.deleteLater()
        QTimer.singleShot(0,self,lambda:self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def show_topic(self,key):
        topic=BY_KEY[key];self.last_topic=key
        self.append(T(topic.title),T(topic.body),topic.actions)
        self.status.setText(T('DeporiaQ kullanımında yanınızdayım.'))

    def submit(self):
        text=self.input.toPlainText().strip()
        if not 1<=len(text)<=2000:self.status.setText(T('Sorunuzu 1–2000 karakter arasında yazın.'));return
        self.append(T('Siz'),text);self.history=(self.history+[text])[-12:];self.input.clear()
        normalized=fold(text)
        if normalized in GREETINGS:
            self.append(T('DeporiaQ Asistan'),T('Merhaba! Size nasıl yardımcı olabilirim?'));return
        keys=(self.last_topic,) if normalized in FOLLOW_UP and self.last_topic else lookup(text)
        if len(keys)==1:self.show_topic(keys[0])
        elif keys:
            self.last_topic=None
            self.append(T('Konu seçimi'),T('Sorunuz birden fazla konuyla eşleşti. Hangisini açalım?'),choices=keys)
        else:
            self.last_topic=None
            self.append(T('DeporiaQ Asistan'),T('Hangi ekranda ne yapmak istediğinizi biraz daha ayrıntılı yazar mısınız? Bir hata görüyorsanız hata metnini de ekleyebilirsiniz.'),actions=('support',))

    def reset(self):
        self.history=[];self.last_topic=None;self.input.clear()
        while self.messages_layout.count():
            item=self.messages_layout.takeAt(0);item.widget().hide();item.widget().deleteLater()
        self.append(T('DeporiaQ Asistan'),T('Merhaba! Size nasıl yardımcı olabilirim?'))
        self.check();self.input_changed()
