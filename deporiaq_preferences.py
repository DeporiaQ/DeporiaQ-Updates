"""Local appearance, notifications and workstation locking. No subscription writes."""
import json
import time
from pathlib import Path
from PySide6.QtCore import QObject, QEvent, QTimer, Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices, QPainter, QColor, QIcon
from PySide6.QtWidgets import (QApplication,QDialog,QVBoxLayout,QLabel,QLineEdit,QPushButton,
    QComboBox,QCheckBox,QSpinBox,QFileDialog,QMessageBox,QPlainTextEdit)
from deporiaq_i18n import T, render, Text ,QCheckBox,QComboBox,QFileDialog,QLabel,QLineEdit,QMessageBox,QPlainTextEdit,QPushButton

def apply_appearance(window):
    from deporiaq_qt import STIL, kaynak_yolu
    vt=window.vt
    theme=vt.ayar_getir('ui_theme',T('Gece Mavisi'))
    style=STIL
    if theme==T('Grafit'):
        for a,b in {'#131A26':'#191919','#1E2635':'#272727','#263B53':'#303030',
                    '#21354D':'#242424','#2C3E55':'#383838','#314C6B':'#444444'}.items():style=style.replace(a,b)
    elif theme==T('Yüksek Kontrast'):
        style+='\nQWidget {color:#FFFFFF;} QFrame#panel,QFrame#kart {background:#080D15;border:2px solid #CBD5E1;} QPushButton {border:2px solid #CBD5E1;} QLabel#soluk {color:#E2E8F0;}'
    mode=vt.ayar_getir('ui_mode','dark')
    if mode=='light':
        style+='''
        QWidget {color:#182D43;background:#F3F6FA;}
        QDialog,QMainWindow {background:#F3F6FA;}
        QLabel {background:transparent;}
        QFrame#ustCubuk,QFrame#yanMenu,QFrame#altCubuk {background:#ECF1F7;border-color:#CCD7E5;}
        QFrame#panel,QFrame#kart {background:rgba(250,253,255,225);border-color:#B2C6D9;}
        QLabel#markaKucuk,QLabel#isletme,QLabel#cloud,QLabel#kartBaslik {color:#1B334A;}
        QLabel#profil,QLabel#soluk,QLabel#durum {color:#526981;}
        QLabel#kartDeger {color:#057AB4;}
        QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit,QListWidget,QTableWidget {background:#FFFFFF;color:#182D43;border-color:#B2C6D9;alternate-background-color:#EEF3F9;}
        QPushButton {background:#E2EBF5;color:#1A3955;border-color:#BDCDDD;}
        QPushButton:hover {background:#CFDFEF;}
        QPushButton#birincil,QPushButton#tehlike,QPushButton#basari {color:#FFFFFF;}
        QHeaderView::section {background:#DAE5F0;color:#243B53;}
        QTabBar::tab {background:#E2EBF5;color:#243B53;padding:8px;}
        QTabBar::tab:selected {background:#FFFFFF;}
        '''
    style+='''
    QFrame#headerProfile,QFrame#headerActions {background:transparent;border:0;}
    QWidget#dashboardSosyal {background:transparent;}
    QWidget#dashboardSosyal QPushButton {padding:5px 4px;font-size:13px;}
    QFrame#yanMenu QPushButton {padding:9px 7px;font-size:13px;}
    QLineEdit#globalSearch {background:rgba(125,150,180,24);border:1px solid rgba(126,155,185,95);border-radius:10px;padding:10px 12px;}
    QLineEdit#globalSearch:focus {border:1px solid #38BDF8;}
    QPushButton#assistantEntry {background:transparent;border:0;padding:7px;color:#38BDF8;}
    QFrame#searchResults {background:#1E2B3D;border:1px solid #506C88;border-radius:10px;}
    QFrame#notificationCard,QFrame#assistantMessage {background:rgba(125,150,180,18);border:1px solid rgba(126,155,185,70);border-radius:9px;}
    QFrame#assistantSurface {background:#142237;border:1px solid #47627F;border-radius:14px;}
    QScrollArea#assistantScroll,QWidget#assistantMessages {background:#142237;border:0;}
    QPushButton#assistantClose {background:transparent;border:0;padding:0;font-size:22px;}
    QPushButton#assistantClose:hover {background:rgba(126,155,185,45);}
    QLabel#cloud {background:transparent;border:0;padding:7px 0;font-size:12px;}
    '''
    if mode=='light':style+='QFrame#searchResults {background:#FFFFFF;} QPushButton#assistantEntry {color:#006BA6;} QFrame#assistantSurface {background:#F3F6FA;border-color:#AFC3D8;} QScrollArea#assistantScroll,QWidget#assistantMessages {background:#F3F6FA;}'
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
    window.icerik.light_mode=mode=='light'
    window.icerik.update()
    if hasattr(window,'x_button'):
        pix=QPixmap(kaynak_yolu('x_icon.svg'))
        if mode=='light':
            painter=QPainter(pix);painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn);painter.fillRect(pix.rect(),QColor('#182D43'));painter.end()
        window.x_button.setIcon(QIcon(pix))

def extend_settings(dialog,general,security,notifications):
    from deporiaq_commerce_ui import quantity_control
    vt=dialog.vt; parent=dialog.parentWidget()
    dialog.theme=QComboBox();dialog.theme.addItems([T('Gece Mavisi'),T('Grafit'),T('Yüksek Kontrast')]);dialog.theme.setCurrentText(vt.ayar_getir('ui_theme',T('Gece Mavisi')))
    dialog.font_size=QSpinBox();dialog.font_size.setRange(12,18);dialog.font_size.setValue(int(vt.ayar_getir('ui_font_size','14')))
    dialog.background_enabled=QCheckBox(T('Arka plan görselini göster'));dialog.background_enabled.setChecked(vt.ayar_getir('ui_background_enabled','1')=='1')
    dialog.overlay=QSpinBox();dialog.overlay.setRange(50,230);dialog.overlay.setValue(int(vt.ayar_getir('ui_overlay','85')))
    dialog.background_path=vt.ayar_getir('ui_background','')
    catalog=QComboBox()
    for key,label in [('modern_depo',T('Modern Depo')),('kitabevi',T('Kitabevi')),('lojistik',T('Lojistik Merkezi')),('lacivert',T('Sade Lacivert')),('antrasit',T('Antrasit Geometrik'))]:catalog.addItem(label,'builtin:'+key)
    catalog.setCurrentIndex(catalog.findData(dialog.background_path))
    catalog.activated.connect(lambda:setattr(dialog,'background_path',catalog.currentData()))
    general.addRow(T('Standart arka plan:'),catalog)
    animation=QCheckBox(T('Açılış ve kapanış logo animasyonu'));animation.setChecked(vt.ayar_getir('ui_animation','1')=='1');general.addRow(animation)
    background=QPushButton(T('Arka Plan Görseli Seç…'))
    def choose():
        path,_=QFileDialog.getOpenFileName(dialog,T('Arka plan seç'),'',T('Görseller (*.png *.jpg *.jpeg)'))
        if not path:return
        pix=QPixmap(path)
        if pix.isNull():QMessageBox.warning(dialog,T('Görsel açılamadı'),T('Geçerli bir PNG veya JPEG seçin.'));return
        target=Path(vt.yol).parent/'appearance'/'background.png';target.parent.mkdir(exist_ok=True)
        pix=pix.scaled(2560,1440,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
        if not pix.save(str(target),'PNG'):QMessageBox.warning(dialog,T('Kaydedilemedi'),T('Görsel kaydedilemedi.'));return
        dialog.background_path=str(target);background.setText(T('Görsel seçildi · Kaydet ile uygula'))
    background.clicked.connect(choose)
    reset=QPushButton(T('Varsayılan Arka Plan'));reset.clicked.connect(lambda:setattr(dialog,'background_path',''))
    save=QPushButton(T('Görünümü Uygula'))
    def save_appearance():
        values={'ui_animation':str(int(animation.isChecked())),'ui_theme':dialog.theme.currentText(),'ui_font_size':str(dialog.font_size.value()),
            'ui_background':dialog.background_path,'ui_background_enabled':str(int(dialog.background_enabled.isChecked())),
            'ui_overlay':str(dialog.overlay.value())}
        for k,v in values.items():vt.ayar_kaydet(k,v)
        vt.baglanti.commit()
        if parent:apply_appearance(parent)
    save.clicked.connect(save_appearance)
    for label,widget in [(T('Tema:'),dialog.theme),(T('Yazı boyutu:'),quantity_control(dialog.font_size)[0]),(T('Karartma (50–230):'),quantity_control(dialog.overlay)[0])]:general.addRow(label,widget)
    for widget in (dialog.background_enabled,background,reset,save):general.addRow(widget)
    lock=QPushButton(T('Ekranı Şimdi Kilitle'));lock.clicked.connect(lambda:parent.session_guard.lock() if parent else None);security.addRow(lock)
    note=QLabel(T('Kilit, bu bilgisayardaki kullanıcı parolanızla açılır. Cloud oturumu korunur. 0 dakika otomatik kilidi kapatır.'));note.setWordWrap(True);security.addRow(note)
    forget=QPushButton(T('Bu Cihazdaki Hatırlanan Girişi Sil'))
    def forget_login():
        from stok_programi_v2 import ayarlari_oku,yerel_ayari_kaydet
        if QMessageBox.question(dialog,T('Hatırlanan giriş'),T('Bir sonraki girişte parola istenecek. Devam edilsin mi?'))!=QMessageBox.StandardButton.Yes:return
        accounts=ayarlari_oku().get('cloud_accounts',{});accounts.pop(str(parent.kullanici['id']),None)
        yerel_ayari_kaydet('cloud_accounts',accounts);yerel_ayari_kaydet('cloud_refresh_token_dpapi','')
        parent.remember_disabled=True
        QMessageBox.information(dialog,T('Kaydedildi'),T('Hatırlanan giriş silindi. Mevcut çalışma oturumu açık kalır.'))
    forget.clicked.connect(forget_login);security.addRow(forget)
    backup=QPushButton(T('Yerel Yedek Al'));backup.clicked.connect(lambda:parent.yedek_al());security.addRow(backup)
    diagnostic=QPushButton(T('Destek İçin Tanılama Raporu Kaydet'));diagnostic.clicked.connect(lambda:export_diagnostics(parent,dialog));security.addRow(diagnostic)
    dialog.notification_options={}
    for key,label in [('notify_cloud',T('Bağlantı sorunlarını bildir')),('notify_expiry',T('Paket bitişi yaklaşınca bildir')),('notify_update',T('Açılışta güncellemeleri denetle')),('notify_sound',T('Yeni bildirimde ses çal'))]:
        check=QCheckBox(label);check.setChecked(vt.ayar_getir(key,'0' if key=='notify_sound' else '1')=='1');notifications.addRow(check);dialog.notification_options[key]=check
    dialog.expiry_days=QSpinBox();dialog.expiry_days.setRange(1,90);dialog.expiry_days.setValue(int(vt.ayar_getir('notify_expiry_days','7')));notifications.addRow(T('Bitişten kaç gün önce:'),quantity_control(dialog.expiry_days)[0])
    test=QPushButton(T('Bildirim Sesi ve Görünümünü Dene'));test.clicked.connect(lambda:parent.notify(T('Bildirim ayarları'),T('Test bildirimi başarıyla oluşturuldu.'),force=True));notifications.addRow(test)
    history=QPushButton(T('Bildirim Geçmişini Aç'));history.clicked.connect(lambda:parent.notification_history());notifications.addRow(history)

def save_notifications(dialog):
    for key,check in dialog.notification_options.items():dialog.vt.ayar_kaydet(key,str(int(check.isChecked())))
    dialog.vt.ayar_kaydet('notify_expiry_days',str(dialog.expiry_days.value()));dialog.vt.baglanti.commit()

def export_diagnostics(window,parent):
    from deporiaq_qt import SURUM
    path,_=QFileDialog.getSaveFileName(parent,T('Tanılama raporu'),'DeporiaQ_Tanilama.json','JSON (*.json)')
    if not path:return
    # Explicit allowlist: no tokens, credentials, customer records or personal file paths.
    report={'version':SURUM,'cloud_connected':bool(window.cloud_client.bagli),
        'connection_state':getattr(window,'cloud_connection_state','offline'),
        'pending_operations':0,'local_database_check':window.vt.baglanti.execute('PRAGMA quick_check').fetchone()[0]}
    with window.commerce._db() as db:
        report['pending_operations']=db.execute("SELECT count(*) FROM requests WHERE state='pending'").fetchone()[0]
    try:Path(path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    except OSError as e:QMessageBox.warning(parent,T('Kaydedilemedi'),str(e));return
    QMessageBox.information(parent,T('Tanılama kaydedildi'),T('Rapor kaydedildi. Parola, anahtar ve ürün kayıtları içermez.'))

class LockDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.setWindowTitle(T('DeporiaQ · Ekran Kilitli'))
        self.setWindowModality(Qt.WindowModality.ApplicationModal);self.setMinimumWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint,False)
        layout=QVBoxLayout(self);layout.addWidget(QLabel(T('Yerel kullanıcı: ')+window.kullanici['kullanici_adi']))
        self.password=QLineEdit();self.password.setEchoMode(QLineEdit.EchoMode.Password);self.password.setPlaceholderText(T('Bu bilgisayardaki kullanıcı parolanız'));layout.addWidget(self.password)
        self.message=QLabel(T('Cloud bağlantınız ve açık işlemleriniz korunuyor.'));self.message.setWordWrap(True);layout.addWidget(self.message)
        self.unlock_button=QPushButton(T('Kilidi Aç'));self.unlock_button.clicked.connect(self.unlock);layout.addWidget(self.unlock_button);self.password.returnPressed.connect(self.unlock)
        self.retry_at=0
    def unlock(self):
        if time.monotonic()<self.retry_at:return
        user=self.window.vt.kimlik_dogrula(self.window.kullanici['kullanici_adi'],self.password.text());self.password.clear()
        if user and user['id']==self.window.kullanici['id']:self.accept()
        else:self.retry_at=time.monotonic()+2;self.message.setText(T('Parola yanlış. 2 saniye sonra tekrar deneyin.'))
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
