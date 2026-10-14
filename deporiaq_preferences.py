"""Local appearance, notifications and workstation locking. No subscription writes."""
import json
import time
from pathlib import Path
from PySide6.QtCore import QObject, QEvent, QTimer, Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import (QApplication,QDialog,QVBoxLayout,QLabel,QLineEdit,QPushButton,
    QComboBox,QCheckBox,QSpinBox,QFileDialog,QMessageBox,QPlainTextEdit)

def apply_appearance(window):
    from deporiaq_qt import STIL, kaynak_yolu
    vt=window.vt
    theme=vt.ayar_getir('ui_theme','Gece Mavisi')
    style=STIL
    if theme=='Grafit':
        for a,b in {'#131A26':'#191919','#1E2635':'#272727','#263B53':'#303030',
                    '#21354D':'#242424','#2C3E55':'#383838','#314C6B':'#444444'}.items():style=style.replace(a,b)
    elif theme=='Yüksek Kontrast':
        style+='\nQWidget {color:#FFFFFF;} QFrame#panel,QFrame#kart {background:#080D15;border:2px solid #CBD5E1;} QPushButton {border:2px solid #CBD5E1;} QLabel#soluk {color:#E2E8F0;}'
    size=int(vt.ayar_getir('ui_font_size','14'))
    style+=f'\nQWidget {{font-size:{max(12,min(size,18))}px;}}'
    app=QApplication.instance()
    if app.styleSheet()!=style:
        # Collect detached Python wrappers before Qt traverses all live widgets.
        # Keep live wrappers referenced during global repolishing.
        import gc
        gc.collect()
        live_widgets=app.allWidgets()
        app.setStyleSheet(style)
        del live_widgets
    path=vt.ayar_getir('ui_background','')
    if path.startswith('builtin:'):path=kaynak_yolu('backgrounds/'+path[8:]+'.svg')
    window.icerik.gorsel=QPixmap(path if path and Path(path).is_file() else kaynak_yolu('dashboard_background.jpg'))
    window.icerik.background_enabled=vt.ayar_getir('ui_background_enabled','1')=='1'
    window.icerik.overlay=int(vt.ayar_getir('ui_overlay','85'))
    window.icerik.update()

def extend_settings(dialog,general,security,notifications):
    from deporiaq_commerce_ui import quantity_control
    vt=dialog.vt; parent=dialog.parentWidget()
    dialog.theme=QComboBox();dialog.theme.addItems(['Gece Mavisi','Grafit','Yüksek Kontrast']);dialog.theme.setCurrentText(vt.ayar_getir('ui_theme','Gece Mavisi'))
    dialog.font_size=QSpinBox();dialog.font_size.setRange(12,18);dialog.font_size.setValue(int(vt.ayar_getir('ui_font_size','14')))
    dialog.background_enabled=QCheckBox('Arka plan görselini göster');dialog.background_enabled.setChecked(vt.ayar_getir('ui_background_enabled','1')=='1')
    dialog.overlay=QSpinBox();dialog.overlay.setRange(50,230);dialog.overlay.setValue(int(vt.ayar_getir('ui_overlay','85')))
    dialog.background_path=vt.ayar_getir('ui_background','')
    catalog=QComboBox()
    for key,label in [('modern_depo','Modern Depo'),('kitabevi','Kitabevi'),('lojistik','Lojistik Merkezi'),('lacivert','Sade Lacivert'),('antrasit','Antrasit Geometrik')]:catalog.addItem(label,'builtin:'+key)
    catalog.setCurrentIndex(catalog.findData(dialog.background_path))
    catalog.activated.connect(lambda:setattr(dialog,'background_path',catalog.currentData()))
    general.addRow('Standart arka plan:',catalog)
    animation=QCheckBox('Açılış ve kapanış logo animasyonu');animation.setChecked(vt.ayar_getir('ui_animation','1')=='1');general.addRow(animation)
    background=QPushButton('Arka Plan Görseli Seç…')
    def choose():
        path,_=QFileDialog.getOpenFileName(dialog,'Arka plan seç','','Görseller (*.png *.jpg *.jpeg)')
        if not path:return
        pix=QPixmap(path)
        if pix.isNull():QMessageBox.warning(dialog,'Görsel açılamadı','Geçerli bir PNG veya JPEG seçin.');return
        target=Path(vt.yol).parent/'appearance'/'background.png';target.parent.mkdir(exist_ok=True)
        pix=pix.scaled(2560,1440,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
        if not pix.save(str(target),'PNG'):QMessageBox.warning(dialog,'Kaydedilemedi','Görsel kaydedilemedi.');return
        dialog.background_path=str(target);background.setText('Görsel seçildi · Kaydet ile uygula')
    background.clicked.connect(choose)
    reset=QPushButton('Varsayılan Arka Plan');reset.clicked.connect(lambda:setattr(dialog,'background_path',''))
    save=QPushButton('Görünümü Uygula')
    def save_appearance():
        values={'ui_animation':str(int(animation.isChecked())),'ui_theme':dialog.theme.currentText(),'ui_font_size':str(dialog.font_size.value()),
            'ui_background':dialog.background_path,'ui_background_enabled':str(int(dialog.background_enabled.isChecked())),
            'ui_overlay':str(dialog.overlay.value())}
        for k,v in values.items():vt.ayar_kaydet(k,v)
        vt.baglanti.commit()
        if parent:apply_appearance(parent)
    save.clicked.connect(save_appearance)
    for label,widget in [('Tema:',dialog.theme),('Yazı boyutu:',quantity_control(dialog.font_size)[0]),('Karartma (50–230):',quantity_control(dialog.overlay)[0])]:general.addRow(label,widget)
    for widget in (dialog.background_enabled,background,reset,save):general.addRow(widget)
    order=QComboBox();order.addItems(['Ürün · Stok · Değer · Kritik','Kritik · Stok · Ürün · Değer','Değer · Stok · Kritik · Ürün']);order.setCurrentIndex(int(vt.ayar_getir('dashboard_order','0')))
    general.addRow('Ana sayfa kart sırası:',order)
    card_options=[]
    for i,label in enumerate(['Ürün çeşidi','Seçili konum stoğu','Toplam stok değeri','Kritik stok']):
        check=QCheckBox(label+' kartını göster');check.setChecked(vt.ayar_getir('dashboard_card_'+str(i),'1')=='1');general.addRow(check);card_options.append(check)
    layout_save=QPushButton('Ana Sayfa Düzenini Uygula')
    def save_layout():
        vt.ayar_kaydet('dashboard_order',str(order.currentIndex()))
        for i,check in enumerate(card_options):vt.ayar_kaydet('dashboard_card_'+str(i),str(int(check.isChecked())))
        vt.baglanti.commit()
        if parent:parent.duyarli_mod=None;parent.duyarli_yerlesimi_guncelle()
    layout_save.clicked.connect(save_layout);general.addRow(layout_save)

    lock=QPushButton('Ekranı Şimdi Kilitle');lock.clicked.connect(lambda:parent.session_guard.lock() if parent else None);security.addRow(lock)
    note=QLabel('Kilit, bu bilgisayardaki kullanıcı parolanızla açılır. Cloud oturumu korunur. 0 dakika otomatik kilidi kapatır.');note.setWordWrap(True);security.addRow(note)
    forget=QPushButton('Bu Cihazdaki Hatırlanan Girişi Sil')
    def forget_login():
        from stok_programi_v2 import ayarlari_oku,yerel_ayari_kaydet
        if QMessageBox.question(dialog,'Hatırlanan giriş','Bir sonraki girişte parola istenecek. Devam edilsin mi?')!=QMessageBox.StandardButton.Yes:return
        accounts=ayarlari_oku().get('cloud_accounts',{});accounts.pop(str(parent.kullanici['id']),None)
        yerel_ayari_kaydet('cloud_accounts',accounts);yerel_ayari_kaydet('cloud_refresh_token_dpapi','')
        parent.remember_disabled=True
        QMessageBox.information(dialog,'Kaydedildi','Hatırlanan giriş silindi. Mevcut çalışma oturumu açık kalır.')
    forget.clicked.connect(forget_login);security.addRow(forget)
    backup=QPushButton('Yerel Yedek Al');backup.clicked.connect(lambda:parent.yedek_al());security.addRow(backup)
    diagnostic=QPushButton('Destek İçin Tanılama Raporu Kaydet');diagnostic.clicked.connect(lambda:export_diagnostics(parent,dialog));security.addRow(diagnostic)
    dialog.notification_options={}
    for key,label in [('notify_cloud','Bağlantı sorunlarını bildir'),('notify_expiry','Paket bitişi yaklaşınca bildir'),('notify_update','Açılışta güncellemeleri denetle'),('notify_sound','Yeni bildirimde ses çal')]:
        check=QCheckBox(label);check.setChecked(vt.ayar_getir(key,'0' if key=='notify_sound' else '1')=='1');notifications.addRow(check);dialog.notification_options[key]=check
    dialog.expiry_days=QSpinBox();dialog.expiry_days.setRange(1,90);dialog.expiry_days.setValue(int(vt.ayar_getir('notify_expiry_days','7')));notifications.addRow('Bitişten kaç gün önce:',quantity_control(dialog.expiry_days)[0])
    test=QPushButton('Bildirim Sesi ve Görünümünü Dene');test.clicked.connect(lambda:parent.notify('Bildirim ayarları','Test bildirimi başarıyla oluşturuldu.',force=True));notifications.addRow(test)
    history=QPushButton('Bildirim Geçmişini Aç');history.clicked.connect(lambda:parent.notification_history());notifications.addRow(history)

def save_notifications(dialog):
    for key,check in dialog.notification_options.items():dialog.vt.ayar_kaydet(key,str(int(check.isChecked())))
    dialog.vt.ayar_kaydet('notify_expiry_days',str(dialog.expiry_days.value()));dialog.vt.baglanti.commit()

def export_diagnostics(window,parent):
    from deporiaq_qt import SURUM
    path,_=QFileDialog.getSaveFileName(parent,'Tanılama raporu','DeporiaQ_Tanilama.json','JSON (*.json)')
    if not path:return
    # Explicit allowlist: no tokens, credentials, customer records or personal file paths.
    report={'version':SURUM,'cloud_connected':bool(window.cloud_client.bagli),
        'connection_state':getattr(window,'cloud_connection_state','offline'),
        'pending_operations':0,'local_database_check':window.vt.baglanti.execute('PRAGMA quick_check').fetchone()[0]}
    with window.commerce._db() as db:
        report['pending_operations']=db.execute("SELECT count(*) FROM requests WHERE state='pending'").fetchone()[0]
    try:Path(path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    except OSError as e:QMessageBox.warning(parent,'Kaydedilemedi',str(e));return
    QMessageBox.information(parent,'Tanılama kaydedildi','Rapor kaydedildi. Parola, anahtar ve ürün kayıtları içermez.')

class LockDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.setWindowTitle('DeporiaQ · Ekran Kilitli')
        self.setWindowModality(Qt.WindowModality.ApplicationModal);self.setMinimumWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint,False)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Yerel kullanıcı: '+window.kullanici['kullanici_adi']))
        self.password=QLineEdit();self.password.setEchoMode(QLineEdit.EchoMode.Password);self.password.setPlaceholderText('Bu bilgisayardaki kullanıcı parolanız');layout.addWidget(self.password)
        self.message=QLabel('Cloud bağlantınız ve açık işlemleriniz korunuyor.');self.message.setWordWrap(True);layout.addWidget(self.message)
        self.unlock_button=QPushButton('Kilidi Aç');self.unlock_button.clicked.connect(self.unlock);layout.addWidget(self.unlock_button);self.password.returnPressed.connect(self.unlock)
        self.retry_at=0
    def unlock(self):
        if time.monotonic()<self.retry_at:return
        user=self.window.vt.kimlik_dogrula(self.window.kullanici['kullanici_adi'],self.password.text());self.password.clear()
        if user and user['id']==self.window.kullanici['id']:self.accept()
        else:self.retry_at=time.monotonic()+2;self.message.setText('Parola yanlış. 2 saniye sonra tekrar deneyin.')
    def reject(self):pass
    def closeEvent(self,event):event.ignore()

class SessionGuard(QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.last_activity=time.monotonic();self.dialog=None
        QApplication.instance().installEventFilter(self)
        self.timer=QTimer(self);self.timer.timeout.connect(self.check);self.timer.start(1000)
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.KeyPress,QEvent.Type.MouseButtonPress,QEvent.Type.MouseMove,QEvent.Type.Wheel):self.last_activity=time.monotonic()
        # Ctrl+1 works inside dialogs too; busy jobs must finish and edits require confirmation.
        if event.type()==QEvent.Type.KeyPress and event.key()==Qt.Key.Key_1 and event.modifiers()==Qt.KeyboardModifier.ControlModifier and self.window.isVisible():
            if self.dialog is None:self.window.home()
            return True
        return False
    def check(self):
        if not self.window.isVisible():return
        minutes=int(self.window.vt.ayar_getir('otomatik_kilit_dakika','30'))
        if minutes>0 and time.monotonic()-self.last_activity>=minutes*60:self.lock()
    def lock(self):
        if self.dialog is not None:self.dialog.raise_();return
        self.dialog=LockDialog(self.window);self.dialog.finished.connect(self.unlocked);self.dialog.show();self.dialog.password.setFocus()
    def unlocked(self):
        self.last_activity=time.monotonic();self.dialog.deleteLater();self.dialog=None
