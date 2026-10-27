"""DeporiaQ 0.23.0 - güvenli abonelik, doğru roller ve yenilenen görünüm."""
import csv
import uuid
import time
import json
import os
import secrets
import subprocess
import sys
import shutil
import sqlite3
import webbrowser
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from deporiaq_workspace_ui import BasketDialog, RecordsDialog, ProductDetailsDialog, CollectionDialog, DamageDialog, BulkPricesDialog, ImportDialog, ApprovalDialog
from deporiaq_visuals import NotificationButton,play_brand
from deporiaq_runtime import clean_environment, acknowledge_startup, startup_error
sys.excepthook = startup_error
from deporiaq_analiz_ui import AnalysisWindow, CommandPalette
from deporiaq_commerce import CommerceClient, SHORTCUTS
from deporiaq_preferences import apply_appearance,extend_settings,save_notifications,SessionGuard
from deporiaq_commerce_ui import PlansDialog, StockDialog, OrdersDialog, SupportDialog, SaleDialog, SubscriptionClock,Job

from PySide6.QtCore import QThread, Qt, QTimer, Signal, QRectF
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QIntValidator,
                           QKeySequence, QPainter, QPen, QPixmap, QShortcut, QTextDocument)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QBoxLayout, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QCompleter,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter

from stok_programi_v2 import (
    PROGRAM_ADI, VERITABANI_YOLU, DeporiaQCloud, Veritabani, ayarlari_oku,
    eski_veritabanini_tasi, veritabani_butunlugunu_kurtar,
    parola_guclu_mu, veritabani_yedegi_al, yerel_ayari_kaydet,
    windows_sifrele, windows_sifre_coz,
)

from deporiaq_visuals import WorkspaceDialog as QDialog
from deporiaq_i18n import T,render,language,set_language,join_text
from deporiaq_experience import ExperienceHeader,FlagButton,SearchController
from deporiaq_assistant import AssistantPanel
from deporiaq_panels import PanelCanvas,PanelsDialog
from deporiaq_companion import CompanionController,PetDock,companion_settings
from deporiaq_i18n import T, render, Text ,QCheckBox,QComboBox,QFileDialog,QFormLayout,QInputDialog,QLabel,QLineEdit,QMainWindow,QMessageBox,QPlainTextEdit,QPushButton,QTabWidget,QTableWidget,QTableWidgetItem,QWidget

SURUM = "0.28.1"


def kaynak_yolu(ad):
    return str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / ad)


def cloud_yapilandirmasi_oku():
    """Yayın paketine gömülen güvenli istemci yapılandırmasını döndürür."""
    try:
        veri = json.loads(Path(kaynak_yolu("deporiaq_cloud.json")).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, AttributeError):
        veri = {}
    yerel = ayarlari_oku()
    url = str(veri.get("project_url") or yerel.get("cloud_url") or "").strip()
    anahtar = str(veri.get("publishable_key") or yerel.get("cloud_publishable_key") or "").strip()
    if "SUPABASE_" in url or "SUPABASE_" in anahtar:
        url = anahtar = ""
    return url, anahtar


def tablo_standardi(tablo, satir_yuksekligi=34):
    tablo.verticalHeader().hide()
    tablo.verticalHeader().setDefaultSectionSize(satir_yuksekligi)
    tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tablo.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tablo.setAlternatingRowColors(True)
    tablo.setShowGrid(False)


def pozitif_sayi_al(alan):
    metin = alan.text().strip()
    return int(metin) if metin.isdigit() and int(metin) > 0 else 0


def surum_parcalari(surum):
    try: return tuple(int(x) for x in str(surum).split("."))
    except ValueError: return (0,)


class GuncellemeKontrolu(QThread):
    tamamlandi=Signal(object); hata=Signal(str)
    def run(self):
        try:
            adres=str(ayarlari_oku().get("guncelleme_manifest_url","")).strip()
            if not adres.startswith("https://"): raise ValueError(T('Güncelleme adresi güvenli değil.'))
            req=urllib.request.Request(adres,headers={"User-Agent":f"DeporiaQ/{SURUM}"})
            with urllib.request.urlopen(req,timeout=8) as cevap: veri=json.loads(cevap.read(65536).decode("utf-8"))
            self.tamamlandi.emit(veri)
        except Exception as e:self.hata.emit(str(e))


class KurKontrolu(QThread):
    tamamlandi = Signal(dict)
    hata = Signal(str)

    def run(self):
        try:
            istek = urllib.request.Request(
                "https://www.tcmb.gov.tr/kurlar/today.xml",
                headers={"User-Agent": f"DeporiaQ/{SURUM}"},
            )
            with urllib.request.urlopen(istek, timeout=8) as cevap:
                kok = ET.fromstring(cevap.read(250_000))
            sonuc = {"tarih": kok.attrib.get(T('Tarih'), "")}
            for kod in ("USD", "EUR", "GBP"):
                para_birimi = kok.find(f"Currency[@CurrencyCode='{kod}']")
                if para_birimi is not None:
                    alis = para_birimi.findtext("ForexBuying", "").strip()
                    satis = para_birimi.findtext("ForexSelling", "").strip()
                    if alis and satis:
                        sonuc[kod] = (float(alis), float(satis))
            try:
                for sembol,anahtar in (("GC=F","ALTIN"),("SI=F","GUMUS"),("XU100.IS","BIST")):
                    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sembol,safe='')}?range=2d&interval=1d"
                    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 DeporiaQ"})
                    with urllib.request.urlopen(req,timeout=6) as cevap: piyasa=json.loads(cevap.read(300000).decode("utf-8"))
                    sonuclar=piyasa["chart"]["result"][0]; meta=sonuclar["meta"]; simdiki=float(meta.get("regularMarketPrice") or 0); onceki=float(meta.get("chartPreviousClose") or meta.get("previousClose") or simdiki)
                    sonuc[anahtar]=(simdiki,((simdiki-onceki)/onceki*100) if onceki else 0)
            except Exception:
                pass
            if len(sonuc) == 1:
                raise ValueError(T('Kur bilgisi bulunamadı.'))
            self.tamamlandi.emit(sonuc)
        except Exception as hata:
            self.hata.emit(str(hata))


class CloudKontrolu(QThread):
    tamamlandi=Signal(object,str); hata=Signal(str)
    def __init__(self,cloud,refresh_token="",parent=None): super().__init__(parent);self.cloud=cloud;self.refresh_token=refresh_token
    def run(self):
        try:
            if self.refresh_token and not self.cloud.bagli:self.cloud.oturumu_yenile(self.refresh_token)
            if not self.cloud.bagli:raise RuntimeError(T('Cloud oturumu gerekli'))
            self.cloud.lisans_dogrula()
            self.cloud._cihazi_kaydet()
            # Device inventory is optional; a listing failure cannot revoke a verified session.
            try: devices=self.cloud.cihazlari_getir()
            except Exception: devices=[]
            self.tamamlandi.emit(devices,self.cloud.refresh_token)
        except Exception as e:self.hata.emit(str(e))


class PresenceWorker(QThread):
    received=Signal(object);failed=Signal(str)
    def __init__(self,cloud,session,name,leave=False,parent=None):
        super().__init__(parent);self.cloud=cloud;self.session=session;self.name=name;self.leave=leave
    def run(self):
        try:self.received.emit(self.cloud._istek('/rest/v1/rpc/dpq_presence','POST',{'p_device':self.cloud.cihaz_kimligi,'p_session':self.session,'p_name':self.name,'p_leave':self.leave}))
        except Exception as e:self.failed.emit(str(e))

class CloudSenkronIsci(QThread):
    tamamlandi=Signal(str); hata=Signal(str)
    def __init__(self,cloud,parent=None):super().__init__(parent);self.cloud=cloud
    def run(self):
        yeni_vt=None
        try:
            yeni_vt=Veritabani(self.cloud.vt.yol); kopya=DeporiaQCloud(yeni_vt,self.cloud.cihaz_kimligi)
            for alan in ("url","anahtar","access_token","refresh_token","user_id","company_id","company_name","role","local_username","location_name"):setattr(kopya,alan,getattr(self.cloud,alan,""))
            kopya._istek = self.cloud._istek  # shared, locked session; independent SQLite connection
            durum,_=kopya.akilli_senkronize();self.tamamlandi.emit(durum)
        except Exception as e:self.hata.emit(str(e))
        finally:
            if yeni_vt:yeni_vt.kapat()


class HalkaGrafik(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.kritik = 0; self.saglikli = 0; self.setMinimumHeight(190)

    def veri_ayarla(self, kritik, saglikli):
        self.kritik, self.saglikli = max(0, int(kritik)), max(0, int(saglikli)); self.update()

    def paintEvent(self, olay):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        toplam = self.kritik + self.saglikli
        cap = min(self.height() - 32, self.width() * .35, 148)
        alan = QRectF(20, 16, cap, cap)
        kalem = QPen(QColor("#334155"), 20); kalem.setCapStyle(Qt.PenCapStyle.RoundCap); p.setPen(kalem)
        p.drawArc(alan, 0, 360 * 16)
        if toplam:
            aci = int(360 * 16 * self.saglikli / toplam)
            kalem.setColor(QColor("#10B981")); p.setPen(kalem); p.drawArc(alan, 90 * 16, -aci)
            kalem.setColor(QColor("#F59E0B")); p.setPen(kalem); p.drawArc(alan, (90 * 16) - aci, -(360 * 16 - aci))
        p.setPen(self.palette().windowText().color()); p.setFont(QFont("Segoe UI", 21, QFont.Weight.Bold))
        p.drawText(alan, Qt.AlignmentFlag.AlignCenter, render(str(toplam)))
        x = int(alan.right() + 18); p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.setPen(QColor("#34D399")); p.drawText(x, 76, render(T('●  Sağlıklı: {count}', count=self.saglikli)))
        p.setPen(QColor("#FBBF24")); p.drawText(x, 116, render(T('●  Kritik: {count}',count=self.kritik)))
        oran = int(round(self.saglikli / toplam * 100)) if toplam else 0
        p.setPen(self.palette().windowText().color()); p.setFont(QFont("Segoe UI", 9))
        p.drawText(x, 154, render(T('Stok sağlık oranı  %{v0}', v0=oran)))


class CubukGrafik(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.veriler = []; self.setMinimumHeight(145)

    def veri_ayarla(self, veriler):
        self.veriler = list(veriler)[:5]; self.update()

    def paintEvent(self, olay):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.veriler:
            p.setPen(self.palette().windowText().color()); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, render(T('Henüz stok verisi yok')))
            return
        en_buyuk = max(float(v) for _, v in self.veriler) or 1
        sol, ust, gen = 122, 4, max(50, self.width() - 136)
        olcer = QFontMetrics(p.font())
        for i, (ad, deger) in enumerate(self.veriler):
            y = ust + i * 27; oran = float(deger) / en_buyuk
            etiket = olcer.elidedText(str(ad), Qt.TextElideMode.ElideRight, sol - 12)
            p.setPen(self.palette().windowText().color()); p.drawText(QRectF(4, y, sol - 12, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, render(etiket))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#263449")); p.drawRoundedRect(QRectF(sol, y + 3, gen, 16), 5, 5)
            p.setBrush(QColor("#38BDF8")); p.drawRoundedRect(QRectF(sol, y + 3, max(4, gen * oran), 16), 5, 5)


class SutunGrafik(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.veriler=[]; self.setMinimumHeight(190)
    def veri_ayarla(self, veriler): self.veriler=list(veriler)[:4]; self.update()
    def paintEvent(self, olay):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.veriler:
            p.setPen(self.palette().windowText().color()); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,render(T('Henüz hareket yok'))); return
        en_buyuk=max(float(v) for _,v in self.veriler) or 1; taban=self.height()-32
        gen=max(24,(self.width()-30)//len(self.veriler)-14)
        for i,(ad,deger) in enumerate(self.veriler):
            x=18+i*(gen+14); h=max(5,(self.height()-62)*float(deger)/en_buyuk)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(("#38BDF8","#10B981","#F59E0B","#A78BFA")[i%4]))
            p.drawRoundedRect(QRectF(x,taban-h,gen,h),5,5); p.setPen(self.palette().windowText().color()); p.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
            p.drawText(QRectF(x,taban-h-23,gen,21),Qt.AlignmentFlag.AlignCenter,render(str(deger)))
            p.setPen(self.palette().windowText().color()); p.drawText(QRectF(x,taban+3,gen,24),Qt.AlignmentFlag.AlignCenter,render(str(ad)[:10]))


class DashboardArkaPlan(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.gorsel = QPixmap(kaynak_yolu("dashboard_background.jpg"));self.background_enabled=True;self.overlay=85

    def paintEvent(self, olay):
        p = QPainter(self)
        if self.background_enabled and not self.gorsel.isNull():
            kapla = self.gorsel.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
            x = max(0, (kapla.width() - self.width()) // 2); y = max(0, (kapla.height() - self.height()) // 2)
            p.drawPixmap(QRectF(self.rect()), kapla, QRectF(x, y, self.width(), self.height()))
        # Görsel belirgin kalır; koyu katman metinlerin okunabilirliğini korur.
        p.fillRect(self.rect(), QColor(211,222,234,max(150,self.overlay) if self.background_enabled else 255) if getattr(self,'light_mode',False) else QColor(7, 15, 28, self.overlay if self.background_enabled else 255))


class FinansOzetGrafik(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.deger=0.0; self.ortalama=0.0; self.kritik=0; self.oran=0; self.setMinimumHeight(170)
    def veri_ayarla(self, deger, urun_sayisi, kritik):
        self.deger=float(deger or 0); self.ortalama=self.deger/max(1,int(urun_sayisi or 0)); self.kritik=int(kritik or 0)
        self.oran=max(0,min(100,100-round(self.kritik/max(1,int(urun_sayisi or 0))*100))); self.update()
    def paintEvent(self, olay):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        text=self.palette().windowText().color();w=self.width()
        values=((T('Stok sermayesi'),para(self.deger),'#38BDF8'),(T('Ürün başına değer'),para(self.ortalama),'#A78BFA'),(T('Kritik ürün'),str(self.kritik),'#F59E0B'))
        for i,(label,value,color) in enumerate(values):
            y=8+i*29;p.setPen(text);p.setFont(QFont('Segoe UI',10))
            p.drawText(QRectF(10,y,w*.52,24),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,render(label))
            p.setPen(QColor(color));p.setFont(QFont('Segoe UI',12,QFont.Weight.Bold))
            p.drawText(QRectF(w*.52,y,w*.48-10,24),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,value)
        p.setPen(text);p.setFont(QFont('Segoe UI',9));p.drawText(QRectF(10,104,w-75,22),Qt.AlignmentFlag.AlignLeft,render(T('Stok sağlık oranı')))
        p.drawText(QRectF(w-60,104,50,22),Qt.AlignmentFlag.AlignRight,str(self.oran)+'%')
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(126,155,185,60));p.drawRoundedRect(QRectF(10,133,w-20,10),5,5)
        p.setBrush(QColor('#10B981' if self.oran>=75 else '#FBBF24' if self.oran>=50 else '#F45B76'));p.drawRoundedRect(QRectF(10,133,max(4,(w-20)*self.oran/100),10),5,5)


def para(deger):
    if language()=='en':return f'{float(deger):,.2f} TRY'
    return f"{float(deger):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


class IlkKurulumPenceresi(QDialog):
    """Temiz bilgisayarı kullanıcı hesabıyla Cloud işletmesine bağlar."""
    def __init__(self, vt, parent=None):
        super().__init__(parent)
        self.vt = vt
        self.job=None
        self.setWindowTitle(T('{v0} {v1} • İşletmeye Bağlan', v0=PROGRAM_ADI, v1=SURUM))
        self.setMinimumSize(520, 500)
        ana = QVBoxLayout(self)
        ana.setContentsMargins(48,38,48,38);ana.setSpacing(14)
        baslik = QLabel(T('DeporiaQ Cloud Girişi'))
        baslik.setObjectName("sayfaBaslik")
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ana.addWidget(baslik)
        aciklama = QLabel(
            T('Yöneticinizin size verdiği e-posta ve parolayla giriş yapın. İşletmeniz, yetkiniz, ürünleriniz ve stoklarınız otomatik olarak indirilecektir.')
        )
        aciklama.setWordWrap(True);aciklama.setAlignment(Qt.AlignmentFlag.AlignCenter);aciklama.setObjectName("soluk");ana.addWidget(aciklama)
        ana.addSpacing(12);a=ayarlari_oku()
        self.m_email=QLineEdit(str(a.get("cloud_email","")));self.m_email.setPlaceholderText(T('E-posta adresiniz'))
        self.m_cloud_pw=QLineEdit();self.m_cloud_pw.setPlaceholderText(T('Cloud parolanız'));self.m_cloud_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.m_cloud_pw.returnPressed.connect(self.mevcut_isletme)
        ana.addWidget(self.m_email);ana.addWidget(self.m_cloud_pw)
        secenekler=QHBoxLayout();self.m_hatirla=QCheckBox(T('Beni hatırla'));self.m_hatirla.setChecked(True)
        goster=QCheckBox(T('Parolayı göster'));goster.toggled.connect(lambda acik:self.m_cloud_pw.setEchoMode(QLineEdit.EchoMode.Normal if acik else QLineEdit.EchoMode.Password))
        secenekler.addWidget(self.m_hatirla);secenekler.addStretch();secenekler.addWidget(goster);ana.addLayout(secenekler)
        self.durum=QLabel(T('İlk girişte verileriniz güvenli biçimde bu bilgisayara hazırlanır.'));self.durum.setWordWrap(True);self.durum.setObjectName("soluk");ana.addWidget(self.durum)
        self.m_tamam=QPushButton(T('Giriş Yap ve İşletmeyi Hazırla'));self.m_tamam.setObjectName("birincil");self.m_tamam.clicked.connect(self.mevcut_isletme);ana.addWidget(self.m_tamam)
        self.new_business=QPushButton(T('Yeni İşletme Oluştur · 30 Gün Dene'));self.new_business.clicked.connect(self.yeni_isletme);ana.addWidget(self.new_business)
        ana.addStretch()

    def yeni_isletme(self):
        from deporiaq_onboarding import RegistrationDialog
        url,key=cloud_yapilandirmasi_oku()
        if not url or not key:self.durum.setText(T('Cloud yapılandırması eksik'));return
        cloud=DeporiaQCloud(self.vt,'');cloud.yapilandir(url,key)
        dialog=RegistrationDialog(cloud,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.m_email.setText(dialog.email.text().strip());self.m_cloud_pw.setText(dialog.password.text());self.mevcut_isletme()

    def closeEvent(self,event):
        if self.job is not None:event.ignore()
        else:super().closeEvent(event)

    def reject(self):
        if self.job is None:super().reject()

    def mevcut_isletme(self):
        if self.job is not None:return
        email=self.m_email.text().strip();parola=self.m_cloud_pw.text()
        if not email or not parola:
            QMessageBox.warning(self,T('Eksik bilgi'),T('E-posta adresinizi ve parolanızı yazın.'));return
        url,anahtar=cloud_yapilandirmasi_oku()
        if not url or not anahtar:
            QMessageBox.warning(self,T('Cloud yapılandırması eksik'),T('Bu DeporiaQ paketinde Cloud bağlantısı yapılandırılmamış. İşletme yöneticinizle iletişime geçin.'));return
        a=ayarlari_oku(); cihaz=str(a.get("cihaz_kimligi","")).strip()
        if not cihaz:
            cihaz="DPQ-"+secrets.token_hex(6).upper(); yerel_ayari_kaydet("cihaz_kimligi",cihaz)
        kullanici="".join(c for c in email.split("@",1)[0].upper() if c.isalnum() or c in "_-") or "DEPORIAQ"
        remember=self.m_hatirla.isChecked();path=self.vt.yol
        self.m_tamam.setEnabled(False);self.new_business.setEnabled(False);self.durum.setText(T('Cloud hesabı doğrulanıyor ve işletme verileri indiriliyor…'))
        def prepare():
            # Each thread owns its SQLite connection; the first-run UI stays responsive.
            local=Veritabani(path)
            try:
                cloud=DeporiaQCloud(local,cihaz);cloud.local_username=kullanici;cloud.yapilandir(url,anahtar)
                sirket=cloud.giris_yap(email,parola);urun,konum,stok=cloud.mevcut_isletmeyi_bu_cihaza_kur(kullanici,parola)
                yerel_ayari_kaydet('cloud_url',url);yerel_ayari_kaydet('cloud_publishable_key',anahtar);yerel_ayari_kaydet('cloud_email',email if remember else '')
                yerel_ayari_kaydet('hatirlanan_kullanici',kullanici if remember else '')
                yerel_ayari_kaydet('cloud_refresh_token_dpapi',windows_sifrele(cloud.refresh_token) if remember else '')
                return sirket,urun,konum,stok
            finally:local.kapat()
        self.job=Job(prepare,self)
        def finished():
            job=self.job;self.job=None;self.m_tamam.setEnabled(True);self.new_business.setEnabled(True)
            if job.error:
                self.durum.setText(T('Bağlantı kurulamadı. Bilgilerinizi kontrol edip yeniden deneyin.'));QMessageBox.warning(self,T('İşletmeye bağlanılamadı'),job.error)
            else:
                sirket,urun,konum,stok=job.result
                QMessageBox.information(self,T('Bağlantı tamamlandı'),T('{v0} bu bilgisayara bağlandı.\n{v1} konum, {v2} ürün ve {v3} stok kaydı indirildi.\n\nSonraki girişlerde kullanıcı adınız: {v4}', v0=sirket, v1=konum, v2=urun, v3=stok, v4=kullanici));self.accept()
            job.deleteLater()
        self.job.finished.connect(finished);self.job.start()


class GirisPenceresi(QWidget):
    def __init__(self, vt):
        super().__init__()
        self.vt = vt
        self.ana = None
        self.ayarlar = ayarlari_oku()
        self.setWindowTitle(T('{v0} {v1} • Giriş', v0=PROGRAM_ADI, v1=SURUM))
        self.setMinimumSize(440, 410)
        kutu = QVBoxLayout(self)
        kutu.setContentsMargins(55, 45, 55, 45)
        marka = QLabel("DeporiaQ")
        marka.setObjectName("marka")
        marka.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kutu.addWidget(marka)
        alt = QLabel(T('v{v0} • Stok ve Depo Yönetimi', v0=SURUM))
        alt.setObjectName("soluk")
        alt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kutu.addWidget(alt)
        kutu.addSpacing(28)
        self.kullanici = QLineEdit()
        self.kullanici.setPlaceholderText(T('Kullanıcı adı veya Cloud e-posta'))
        self.kullanici.setText(str(self.ayarlar.get("hatirlanan_kullanici", "")))
        self.parola = QLineEdit()
        self.parola.setPlaceholderText(T('Parola'))
        self.parola.setEchoMode(QLineEdit.EchoMode.Password)
        self.parola.returnPressed.connect(self.giris)
        kutu.addWidget(self.kullanici)
        kutu.addWidget(self.parola)
        secenekler = QHBoxLayout()
        self.hatirla = QCheckBox(T('Beni Hatırla'))
        self.hatirla.setChecked(bool(self.kullanici.text()))
        self.goster = QCheckBox(T('Parolayı Göster'))
        self.goster.toggled.connect(
            lambda acik: self.parola.setEchoMode(
                QLineEdit.EchoMode.Normal if acik else QLineEdit.EchoMode.Password
            )
        )
        secenekler.addWidget(self.hatirla); secenekler.addStretch(); secenekler.addWidget(self.goster)
        kutu.addLayout(secenekler)
        dugme = QPushButton(T('Giriş Yap'))
        dugme.setObjectName("birincil")
        dugme.clicked.connect(self.giris)
        kutu.addWidget(dugme)
        alt_dugmeler = QHBoxLayout()
        unuttum = QPushButton(T('Şifremi Unuttum'))
        unuttum.setObjectName("metinDugme")
        unuttum.clicked.connect(self.parola_yardimi)
        kapat = QPushButton(T('Programı Kapat'))
        kapat.setObjectName("metinDugme")
        kapat.clicked.connect(self.close)
        alt_dugmeler.addWidget(unuttum); alt_dugmeler.addStretch(); alt_dugmeler.addWidget(kapat)
        kutu.addLayout(alt_dugmeler)
        paket = QPushButton(T('30 gün ücretsiz deneyin · Paketleri incele'))
        paket.setObjectName("metinDugme")
        paket.clicked.connect(lambda:PlansDialog(None,self).exec())
        kutu.addWidget(paket)
        kutu.addStretch()
        telif = QLabel(T('© 2026 DeporiaQ. Tüm hakları saklıdır.'))
        telif.setObjectName("soluk")
        telif.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kutu.addWidget(telif)
        # Kullanıcı oturum açmadan da yeni sürümü görebilsin.
        QTimer.singleShot(1400, self.guncelleme_denetle)

    def guncelleme_denetle(self):
        if not self.isVisible() or self.vt.ayar_getir("notify_update","1")!="1":return
        if hasattr(self, "guncelleme_isci") and self.guncelleme_isci.isRunning():
            return
        self.guncelleme_isci = GuncellemeKontrolu(self)
        self.guncelleme_isci.tamamlandi.connect(self.guncelleme_sonucu)
        self.guncelleme_isci.start()

    def guncelleme_sonucu(self, manifest):
        yeni = str(manifest.get("version", "0"))
        if surum_parcalari(yeni) <= surum_parcalari(SURUM):
            return
        arac = (Path(sys.executable).resolve().parent / "DeporiaQUpdate.exe"
                if getattr(sys, "frozen", False)
                else Path(__file__).resolve().parent / "DeporiaQUpdate.exe")
        if arac.exists():
            subprocess.Popen([str(arac), "--notify"], close_fds=True, env=clean_environment())

    def giris(self):
        girilen = self.kullanici.text().strip()
        yerel_ad = ("".join(c for c in girilen.split("@",1)[0].upper() if c.isalnum() or c in "_-")
                    if "@" in girilen else girilen)
        url, anahtar = cloud_yapilandirmasi_oku()
        cloud_bagli = bool(url and anahtar)
        if not cloud_bagli:
            QMessageBox.warning(self,T('Sunucu gerekli'),T('Bu sürümde stok ve lisans işlemleri için Cloud yapılandırması gereklidir.')); return
        # E-postayla girişte Cloud hesabı doğrudan kimliktir; kullanıcı adıyla girişte yerel parola doğrulanır.
        kayit = self.vt.kullanici_bul(yerel_ad) if (cloud_bagli and "@" in girilen) else self.vt.kimlik_dogrula(yerel_ad, self.parola.text())
        if not kayit:
            QMessageBox.warning(self, T('Giriş başarısız'), T('Kullanıcı adı/e-posta veya parola hatalı.'))
            self.parola.clear(); return
        # Cloud bağlantılı kurulumlarda üyelik, rol ve abonelik her açılışta sunucudan doğrulanır.
        if cloud_bagli:
            cihaz = str(ayarlari_oku().get("cihaz_kimligi", ""))
            if not cihaz:
                cihaz="DPQ-"+secrets.token_hex(16); yerel_ayari_kaydet("cihaz_kimligi",cihaz)
            cloud = DeporiaQCloud(self.vt, cihaz)
            cloud.local_username = yerel_ad
            try:
                cloud.yapilandir(url, anahtar)
                if "@" in girilen:
                    cloud.giris_yap(girilen, self.parola.text())
                else:
                    saved=ayarlari_oku().get('cloud_accounts',{}).get(str(kayit['id']),{})
                    token=windows_sifre_coz(str(saved.get('refresh_token_dpapi','')))
                    if not token:
                        raise RuntimeError(T('Güvenli Cloud oturumu bulunamadı. E-posta adresiniz ve Cloud parolanızla giriş yapın.'))
                    cloud.oturumu_yenile(token)
                    if cloud.user_id!=saved.get('user_id'):
                        raise RuntimeError(T('Cloud oturumu bu yerel kullanıcıya ait değil. E-postanızla giriş yapın.'))
                accounts=ayarlari_oku().get('cloud_accounts',{})
                accounts[str(kayit['id'])]={'user_id':cloud.user_id,'refresh_token_dpapi':windows_sifrele(cloud.refresh_token)}
                yerel_ayari_kaydet('cloud_accounts',accounts)
                yerel_rol = cloud.yerel_rol_kodu(cloud.role)
                self.vt.baglanti.execute("UPDATE kullanicilar SET rol=? WHERE id=?", (yerel_rol, kayit["id"]))
                self.vt.baglanti.commit()
                kayit = self.vt.baglanti.execute(
                    "SELECT * FROM kullanicilar WHERE id=?", (kayit["id"],)
                ).fetchone()
                yerel_ayari_kaydet("cloud_refresh_token_dpapi", windows_sifrele(cloud.refresh_token))
                if "@" in girilen: yerel_ayari_kaydet("cloud_email", girilen)
            except Exception as e:
                QMessageBox.critical(self, T('Cloud ve lisans doğrulanamadı'), str(e))
                return
        if not cloud.entitlement.get('allowed'):
            QMessageBox.information(self,T('Abonelik etkin değil'),T('İşletme işlemleri kapalı. Paket ve destek ekranlarını kullanabilirsiniz.'))
            PlansDialog(CommerceClient(cloud),self).exec();return
        bound=self.vt.ayar_getir('dpq_company_id','')
        if bound and bound!=cloud.company_id:
            QMessageBox.critical(self,T('İşletme uyuşmazlığı'),T('Bu yerel veritabanı başka bir işletmeye bağlı. Ayrı kurulum gerekir.'));return
        if not bound and self.vt.ayar_getir('isletme_adi','').strip().casefold()!=cloud.company_name.strip().casefold():
            QMessageBox.warning(self,T('Geçiş doğrulaması gerekli'),T('Yerel işletme adı ile Cloud işletmesi uyuşmuyor. Veriler uzlaştırılmadan giriş yapılmaz.'));return
        self.vt.ayar_kaydet('dpq_company_id',cloud.company_id);self.vt.baglanti.commit()
        self.auth_cloud = cloud
        self.vt.aktif_kullanici_id = kayit["id"]
        yerel_ayari_kaydet(
            "hatirlanan_kullanici", yerel_ad if self.hatirla.isChecked() else ""
        )
        self.ana = AnaPencere(self.vt, dict(kayit), self)
        self.ana.showMaximized()
        self.hide()

    def parola_yardimi(self):
        QMessageBox.information(
            self, T('Parola yardımı'),
            T('Cloud giriş parolanız için hesap yöneticinizle iletişime geçin. Bu bilgisayardaki yerel kilit parolası, yetkili yönetici tarafından Kullanıcı Yetkileri bölümünden yenilenebilir. Parolalar açık biçimde saklanmaz.')
        )


class TransferPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent)
        self.vt, self.yenile = vt, yenile
        self.setWindowTitle(T('Stok Transferi'))
        self.setMinimumSize(590, 390)
        ana = QVBoxLayout(self)
        baslik = QLabel(T('Barkodlu Stok Transferi'))
        baslik.setObjectName("sayfaBaslik")
        ana.addWidget(baslik)
        form = QFormLayout()
        self.kaynak = QComboBox(); self.hedef = QComboBox()
        self.barkod = QLineEdit(); self.barkod.setPlaceholderText(T('Barkodu okutun veya yazın'))
        self.miktar = QLineEdit("1"); self.miktar.setValidator(QIntValidator(1, 1_000_000, self))
        self.bilgi = QLabel(T('Kaynak ve hedef seçerek barkodu girin.'))
        self.bilgi.setObjectName("soluk")
        form.addRow(T('Kaynak:'), self.kaynak); form.addRow(T('Hedef:'), self.hedef)
        form.addRow(T('Barkod:'), self.barkod); form.addRow(T('Miktar:'), self.miktar)
        ana.addLayout(form); ana.addWidget(self.bilgi)
        aktar = QPushButton(T('Transferi Tamamla'))
        aktar.setObjectName("basari")
        aktar.clicked.connect(self.aktar)
        ana.addWidget(aktar); ana.addStretch()
        self.kaynak.currentIndexChanged.connect(self.hedefleri_yenile)
        self.barkod.returnPressed.connect(self.urunu_goster)
        self.kaynaklari_yenile()

    def kaynaklari_yenile(self):
        self.kaynak.clear()
        for k in self.vt.konumlari_getir():
            if k["tur"] in ("MERKEZ", "DEPO"):
                self.kaynak.addItem(k["ad"], k["id"])
        self.hedefleri_yenile()

    def hedefleri_yenile(self):
        self.hedef.clear()
        kaynak_id = self.kaynak.currentData()
        if kaynak_id is None:
            return
        for k in self.vt.hedef_konumlari_getir(kaynak_id):
            self.hedef.addItem(k["ad"], k["id"])

    def urunu_goster(self):
        urun = self.vt.barkodla_urun_bul(self.barkod.text().strip(), self.kaynak.currentData())
        self.bilgi.setText(
            f"{urun['ad']} • Kaynak stok: {urun['miktar']}" if urun else T('Ürün kaynak konumda bulunamadı.')
        )

    def aktar(self):
        urun = self.vt.barkodla_urun_bul(self.barkod.text().strip(), self.kaynak.currentData())
        if not urun or self.hedef.currentData() is None:
            QMessageBox.warning(self, T('Eksik bilgi'), T('Geçerli barkod, kaynak ve hedef seçin.'))
            return
        try:
            kaynak, hedef = self.vt.stok_transferi(
                urun["id"], self.kaynak.currentData(), self.hedef.currentData(), pozitif_sayi_al(self.miktar)
            )
            self.vt.denetim_ekle(
                "STOK_TRANSFERI", f"{kaynak} → {hedef} • {urun['ad']} • {pozitif_sayi_al(self.miktar)} adet"
            )
        except ValueError as hata:
            QMessageBox.warning(self, T('Transfer yapılamadı'), str(hata)); return
        QMessageBox.information(self, T('Transfer tamamlandı'), T('{v0} → {v1} aktarımı kaydedildi.', v0=kaynak, v1=hedef))
        self.barkod.clear(); self.miktar.setText("1"); self.yenile()


class StokGirisPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent); self.vt, self.yenile = vt, yenile
        self.setWindowTitle(T('Barkodla Stok Girişi')); self.setMinimumWidth(540)
        d = QVBoxLayout(self); b = QLabel(T('Merkez Depoya Stok Girişi')); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        form = QFormLayout(); self.barkod = QLineEdit(); self.miktar = QLineEdit("1"); self.miktar.setValidator(QIntValidator(1,1_000_000,self))
        self.bilgi = QLabel(T('Barkodu okutun.')); self.bilgi.setObjectName("soluk")
        form.addRow(T('Barkod:'),self.barkod); form.addRow(T('Miktar:'),self.miktar); d.addLayout(form); d.addWidget(self.bilgi)
        self.barkod.returnPressed.connect(self.bul)
        kaydet=QPushButton(T('Stoğa Ekle')); kaydet.setObjectName("basari"); kaydet.clicked.connect(self.ekle); d.addWidget(kaydet)
    def bul(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip())
        self.bilgi.setText(f"{u['ad']} • Mevcut: {u['miktar']}" if u else T('Ürün bulunamadı.'))
    def ekle(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip())
        if not u: QMessageBox.warning(self,T('Ürün bulunamadı'),T('Önce geçerli bir barkod girin.')); return
        miktar=pozitif_sayi_al(self.miktar)
        if not miktar: QMessageBox.warning(self,T('Geçersiz miktar'),T('Miktar en az 1 olmalıdır.')); return
        self.vt.merkeze_stok_girisi(u["id"],miktar)
        self.vt.denetim_ekle("STOK_GIRISI",f"{u['ad']} • Merkez Depo • {miktar} adet")
        QMessageBox.information(self,T('Stok güncellendi'),T('{v0} ürününe {v1} adet eklendi.', v0=u['ad'], v1=miktar))
        self.barkod.clear(); self.miktar.setText("1"); self.yenile()


class UrunYonetimiPenceresi(QDialog):
    def __init__(self,vt,yenile,parent=None):
        super().__init__(parent); self.vt,self.yenile_ana=vt,yenile; self.setWindowTitle(T('Ürün Yönetimi')); self.resize(1000,650)
        d=QVBoxLayout(self); b=QLabel(T('Ürün Yönetimi')); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels(["ID",T('Barkod'),T('Ürün'),T('Satış'),T('Alış'),T('Kritik')]); tablo_standardi(self.t,36); d.addWidget(self.t)
        a=QHBoxLayout()
        for ad,fn,stil in ((T('Yeni Ürün'),self.ekle,"basari"),(T('Fiyat Güncelle'),self.fiyat,""),(T('Ürünü Kaldır'),self.sil,"tehlike")):
            q=QPushButton(ad); q.setObjectName(stil); q.clicked.connect(fn); a.addWidget(q)
        a.addStretch(); d.addLayout(a); self.yenile()
    def yenile(self):
        rows=self.vt.tum_aktif_urunleri_getir(); self.t.setRowCount(len(rows))
        for r,u in enumerate(rows):
            for c,v in enumerate((u['id'],u['barkod'],u['ad'],para(u['fiyat']),para(u['alis_fiyati']),u['kritik_stok'])): self.t.setItem(r,c,QTableWidgetItem(v if isinstance(v,Text) else str(v)))
        self.yenile_ana()
    def secili_id(self):
        r=self.t.currentRow()
        if r<0: QMessageBox.warning(self,T('Seçim gerekli'),T('Önce bir ürün seçin.')); return None
        return int(self.t.item(r,0).text())
    def ekle(self):
        p=QDialog(self); p.setWindowTitle(T('Yeni Ürün')); f=QFormLayout(p)
        barkod=QLineEdit(); ad=QLineEdit(); fiyat=QDoubleSpinBox(); fiyat.setMaximum(10_000_000); fiyat.setDecimals(2)
        alis=QDoubleSpinBox(); alis.setMaximum(10_000_000); alis.setDecimals(2); kritik=QSpinBox(); kritik.setMaximum(1_000_000)
        for x,w in ((T('Barkod:'),barkod),(T('Ürün adı:'),ad),(T('Satış fiyatı:'),fiyat),(T('Alış fiyatı:'),alis),(T('Kritik stok:'),kritik)): f.addRow(x,w)
        ok=QPushButton(T('Ürünü Kaydet')); ok.setObjectName("basari"); f.addRow(ok); ok.clicked.connect(p.accept)
        if not p.exec(): return
        try: self.vt.urun_ekle(barkod.text(),ad.text(),fiyat.value(),alis.value(),kritik.value())
        except ValueError as e: QMessageBox.warning(self,T('Kaydedilemedi'),str(e)); return
        self.yenile()
    def fiyat(self):
        uid=self.secili_id()
        if uid is None:return
        deger,ok=QInputDialog.getDouble(self,T('Fiyat Güncelle'),T('Yeni satış fiyatı:'),0,0.01,10_000_000,2)
        if ok:self.vt.urun_fiyati_guncelle(uid,deger);self.yenile()
    def sil(self):
        uid=self.secili_id()
        if uid is None:return
        if QMessageBox.question(self,T('Ürünü kaldır'),T('Seçili ürünü kaldırmak istiyor musunuz?'))!=QMessageBox.StandardButton.Yes:return
        try:self.vt.urunu_pasiflestir(uid)
        except ValueError as e:QMessageBox.warning(self,T('Kaldırılamadı'),str(e));return
        self.yenile()


class KonumYonetimiPenceresi(QDialog):
    def __init__(self,vt,yenile,parent=None):
        super().__init__(parent);self.vt,self.yenile_ana=vt,yenile;self.setWindowTitle(T('Depo ve Şubeler'));self.resize(760,520)
        d=QVBoxLayout(self);b=QLabel(T('Depo ve Şube Yönetimi'));b.setObjectName("sayfaBaslik");d.addWidget(b)
        self.t=QTableWidget(0,3);self.t.setHorizontalHeaderLabels(["ID",T('Konum'),T('Tür')]);tablo_standardi(self.t);d.addWidget(self.t)
        a=QHBoxLayout()
        for ad,fn,stil in ((T('Yeni Depo'),lambda:self.ekle("DEPO"),""),(T('Yeni Şube'),lambda:self.ekle("SUBE"),"basari"),(T('Adını Güncelle'),self.guncelle,""),(T('Kaldır'),self.sil,"tehlike")):
            q=QPushButton(ad);q.setObjectName(stil);q.clicked.connect(fn);a.addWidget(q)
        d.addLayout(a);self.yenile()
    def yenile(self):
        rows=self.vt.konumlari_getir();self.t.setRowCount(len(rows))
        for r,k in enumerate(rows):
            for c,v in enumerate((k['id'],k['ad'],k['tur'])):self.t.setItem(r,c,QTableWidgetItem(v if isinstance(v,Text) else str(v)))
        self.yenile_ana()
    def secili(self):
        r=self.t.currentRow();return int(self.t.item(r,0).text()) if r>=0 else None
    def ekle(self,tur):
        ad,ok=QInputDialog.getText(self,T('Yeni konum'),(T('Depo') if tur=="DEPO" else T('Şube'))+T(' adı:'))
        if not ok:return
        try:self.vt.konum_ekle(ad,tur)
        except ValueError as e:QMessageBox.warning(self,T('Eklenemedi'),str(e));return
        self.yenile()
    def guncelle(self):
        kid=self.secili()
        if kid is None:return
        ad,ok=QInputDialog.getText(self,T('Konum adı'),T('Yeni ad:'))
        if ok:
            try:self.vt.konum_guncelle(kid,ad)
            except ValueError as e:QMessageBox.warning(self,T('Güncellenemedi'),str(e));return
            self.yenile()
    def sil(self):
        kid=self.secili()
        if kid is None:return
        try:self.vt.konumu_pasiflestir(kid)
        except ValueError as e:QMessageBox.warning(self,T('Kaldırılamadı'),str(e));return
        self.yenile()


class KullaniciYonetimiPenceresi(QDialog):
    ROLLER={T('Ana Yönetici'):"ANA_YONETICI",T('Depo Personeli'):"DEPO_PERSONELI",T('Şube Personeli'):"SUBE_PERSONELI",T('Görüntüleyici'):"GORUNTULEYICI"}
    def __init__(self,vt,aktif,parent=None):
        super().__init__(parent);self.vt,self.aktif=vt,aktif;self.setWindowTitle(T('Kullanıcı ve Yetki Yönetimi'));self.resize(950,600)
        d=QVBoxLayout(self);b=QLabel(T('Kullanıcı ve Yetki Yönetimi'));b.setObjectName("sayfaBaslik");d.addWidget(b)
        self.t=QTableWidget(0,6);self.t.setHorizontalHeaderLabels(["ID",T('Kullanıcı'),T('Rol'),T('Konum'),T('Durum'),T('Konum ID')]);tablo_standardi(self.t);d.addWidget(self.t)
        a=QHBoxLayout()
        for ad,fn,stil in ((T('Kullanıcı Oluştur'),self.ekle,"basari"),(T('Aktif/Pasif Yap'),self.durum,""),(T('Parolayı Yenile'),self.parola,""),(T('Kullanıcıyı Kaldır'),self.sil,"tehlike")):
            q=QPushButton(ad);q.setObjectName(stil);q.clicked.connect(fn);a.addWidget(q)
        d.addLayout(a);self.yenile()
    def yenile(self):
        rows=self.vt.kullanicilari_getir();self.t.setRowCount(len(rows))
        adlar={v:k for k,v in self.ROLLER.items()}
        for r,k in enumerate(rows):
            vals=(k['id'],k['kullanici_adi'],adlar.get(k['rol'],k['rol']),k['konum_adi'],T('Aktif') if k['aktif'] else T('Pasif'),k['konum_id'] if k['konum_id'] is not None else "")
            for c,v in enumerate(vals):self.t.setItem(r,c,QTableWidgetItem(v if isinstance(v,Text) else str(v)))
        self.t.setColumnHidden(5,True)
    def secili(self):
        r=self.t.currentRow()
        if r<0:QMessageBox.warning(self,T('Seçim gerekli'),T('Önce bir kullanıcı seçin.'));return None
        return r,int(self.t.item(r,0).text())
    def onay(self):
        pw,ok=QInputDialog.getText(self,T('Yönetici onayı'),T('Mevcut yönetici parolanız:'),QLineEdit.EchoMode.Password)
        return bool(ok and self.vt.kimlik_dogrula(self.aktif['kullanici_adi'],pw))
    def ekle(self):
        p=QDialog(self);p.setWindowTitle(T('Yeni Kullanıcı'));f=QFormLayout(p)
        ad=QLineEdit();pw=QLineEdit();pw.setEchoMode(QLineEdit.EchoMode.Password);rol=QComboBox();rol.addItems(self.ROLLER);kon=QComboBox();kon.addItem(T('Atanmamış'),None)
        pw_goster=QCheckBox(T('Geçici parolayı göster')); pw_goster.toggled.connect(lambda acik:pw.setEchoMode(QLineEdit.EchoMode.Normal if acik else QLineEdit.EchoMode.Password))
        for k in self.vt.konumlari_getir():kon.addItem(f"{k['ad']} ({k['tur']})",k['id'])
        f.addRow(T('Kullanıcı adı:'),ad);f.addRow(T('Geçici parola:'),pw);f.addRow(pw_goster);f.addRow(T('Rol:'),rol);f.addRow(T('Konum:'),kon)
        okb=QPushButton(T('Kullanıcıyı Kaydet'));okb.setObjectName("basari");okb.clicked.connect(p.accept);f.addRow(okb)
        if not p.exec():return
        guclu,hata=parola_guclu_mu(pw.text())
        if not guclu:QMessageBox.warning(self,T('Zayıf parola'),hata);return
        if not self.onay():QMessageBox.warning(self,T('Onay başarısız'),T('Yönetici parolası doğrulanamadı.'));return
        try:self.vt.kullanici_ekle(ad.text().strip(),pw.text(),self.ROLLER[rol.currentText()],kon.currentData())
        except ValueError as e:QMessageBox.warning(self,T('Eklenemedi'),str(e));return
        self.yenile()
    def durum(self):
        sec=self.secili()
        if not sec or not self.onay():return
        r,uid=sec
        if uid==self.aktif['id']:QMessageBox.warning(self,T('İşlem engellendi'),T('Kendi aktif hesabınızı kapatamazsınız.'));return
        self.vt.kullanici_durumunu_degistir(uid,self.t.item(r,4).text()!=T('Aktif'));self.yenile()
    def parola(self):
        sec=self.secili()
        if not sec:return
        pw,ok=QInputDialog.getText(self,T('Parolayı yenile'),T('Yeni güçlü parola:'),QLineEdit.EchoMode.Password)
        if not ok:return
        guclu,hata=parola_guclu_mu(pw)
        if not guclu:QMessageBox.warning(self,T('Zayıf parola'),hata);return
        if not self.onay():return
        self.vt.kullanici_parolasi_degistir(sec[1],pw);QMessageBox.information(self,T('Tamamlandı'),T('Kullanıcı parolası yenilendi.'))
    def sil(self):
        sec=self.secili()
        if not sec or not self.onay():return
        try:self.vt.kullanici_sil(sec[1])
        except ValueError as e:QMessageBox.warning(self,T('Kaldırılamadı'),str(e));return
        self.yenile()


class SubeSatisPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent); self.vt,self.yenile=vt,yenile
        self.setWindowTitle(T('Şubede Satış')); self.setMinimumWidth(560)
        d=QVBoxLayout(self); b=QLabel(T('Barkodlu Şube Satışı')); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        f=QFormLayout(); self.sube=QComboBox()
        for k in vt.konumlari_getir():
            if k["tur"]=="SUBE": self.sube.addItem(k["ad"],k["id"])
        self.barkod=QLineEdit(); self.barkod.setPlaceholderText(T('Barkodu okutun'))
        self.miktar=QLineEdit("1"); self.miktar.setValidator(QIntValidator(1,1_000_000,self))
        self.bilgi=QLabel(T('Ürün bilgisi barkod okutulduğunda görünür.')); self.bilgi.setObjectName("soluk")
        f.addRow(T('Şube:'),self.sube); f.addRow(T('Barkod:'),self.barkod); f.addRow(T('Miktar:'),self.miktar)
        d.addLayout(f); d.addWidget(self.bilgi)
        self.barkod.returnPressed.connect(self.bul)
        q=QPushButton(T('Satışı Tamamla')); q.setObjectName("basari"); q.clicked.connect(self.sat); d.addWidget(q)
    def bul(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip(),self.sube.currentData())
        self.bilgi.setText(f"{u['ad']} • Stok: {u['miktar']} • {para(u['fiyat'])}" if u else T('Ürün bu şubede bulunamadı.'))
    def sat(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip(),self.sube.currentData()); m=pozitif_sayi_al(self.miktar)
        if not u or not m: QMessageBox.warning(self,T('Eksik bilgi'),T('Geçerli barkod ve miktar girin.')); return
        try: ad,sube,fiyat,toplam=self.vt.subede_satis_yap(u["id"],self.sube.currentData(),m)
        except ValueError as e: QMessageBox.warning(self,T('Satış yapılamadı'),str(e)); return
        QMessageBox.information(self,T('Satış tamamlandı'),f"{sube}\n{ad} • {m} adet\nToplam: {para(toplam)}")
        self.barkod.clear(); self.miktar.setText("1"); self.yenile()


class AraclarPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent); self.vt,self.yenile=vt,yenile
        self.setWindowTitle(T('Profesyonel Araçlar')); self.resize(760,500)
        d=QVBoxLayout(self); b=QLabel(T('Profesyonel Araçlar')); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        sek=QTabWidget(); d.addWidget(sek)
        katalog=QWidget(); k=QFormLayout(katalog); self.kategori=QLineEdit(); self.tedarikci=QLineEdit(); self.tel=QLineEdit(); self.eposta=QLineEdit()
        kb=QPushButton(T('Kategori Ekle')); kb.clicked.connect(self.kategori_ekle); tb=QPushButton(T('Tedarikçi Ekle')); tb.clicked.connect(self.tedarikci_ekle)
        k.addRow(T('Yeni kategori:'),self.kategori); k.addRow(kb); k.addRow(T('Tedarikçi:'),self.tedarikci); k.addRow(T('Telefon:'),self.tel); k.addRow(T('E-posta:'),self.eposta); k.addRow(tb)
        sek.addTab(katalog,T('Katalog'))
        sayim=QWidget(); s=QFormLayout(sayim); self.konum=QComboBox(); self.urun=QComboBox(); self.sayim=QLineEdit(); self.sayim.setValidator(QIntValidator(0,1_000_000,self)); self.not_alan=QLineEdit()
        for x in vt.konumlari_getir(): self.konum.addItem(x["ad"],x["id"])
        for x in vt.tum_aktif_urunleri_getir(): self.urun.addItem(f"{x['barkod']} • {x['ad']}",x["id"])
        sb=QPushButton(T('Sayım Sonucunu Uygula')); sb.setObjectName("basari"); sb.clicked.connect(self.sayim_uygula)
        s.addRow(T('Konum:'),self.konum); s.addRow(T('Ürün:'),self.urun); s.addRow(T('Fiziksel miktar:'),self.sayim); s.addRow(T('Açıklama:'),self.not_alan); s.addRow(sb)
        sek.addTab(sayim,T('Stok Sayımı'))
    def kategori_ekle(self):
        try:self.vt.kategori_ekle(self.kategori.text());self.kategori.clear();QMessageBox.information(self,T('Tamamlandı'),T('Kategori eklendi.'))
        except ValueError as e:QMessageBox.warning(self,T('Eklenemedi'),str(e))
    def tedarikci_ekle(self):
        try:self.vt.tedarikci_ekle(self.tedarikci.text(),self.tel.text(),self.eposta.text());QMessageBox.information(self,T('Tamamlandı'),T('Tedarikçi eklendi.'))
        except ValueError as e:QMessageBox.warning(self,T('Eklenemedi'),str(e))
    def sayim_uygula(self):
        try:onceki,fark=self.vt.stok_sayim_duzelt(self.urun.currentData(),self.konum.currentData(),int(self.sayim.text() or 0),self.not_alan.text())
        except ValueError as e:QMessageBox.warning(self,T('Uygulanamadı'),str(e));return
        self.yenile();QMessageBox.information(self,T('Sayım uygulandı'),T('Önceki: {v0} • Fark: {v1:+d}', v0=onceki, v1=fark))


class AyarlarPenceresi(QDialog):
    def __init__(self, vt, cloud, cloud_yenile, parent=None):
        super().__init__(parent); self.vt,self.cloud,self.cloud_yenile=vt,cloud,cloud_yenile
        self.setWindowTitle(T('Ayarlar Merkezi')); self.resize(820,540)
        d=QVBoxLayout(self); b=QLabel(T('Ayarlar Merkezi')); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        sek=QTabWidget(); d.addWidget(sek)
        genel=QWidget(); g=QFormLayout(genel)
        self.expected_company_name=cloud.company_name or vt.ayar_getir('isletme_adi','')
        self.isletme=QLineEdit(self.expected_company_name);self.isletme.setMaxLength(120)
        self.company_save=QPushButton(T('İşletme Bilgisini Kaydet'));self.company_save.clicked.connect(self.genel_kaydet)
        owner=cloud.bagli and cloud.role=='owner';self.isletme.setReadOnly(not owner);self.company_save.setEnabled(owner)
        g.addRow(T('İşletme adı:'),self.isletme);g.addRow(self.company_save)
        self.company_status=QLabel(T('İşletme adını yalnızca ana hesap sahibi değiştirebilir.'));self.company_status.setWordWrap(True);g.addRow(self.company_status)
        sek.addTab(genel,T('Genel'));self.job=None
        bulut=QWidget(); c=QFormLayout(bulut); a=ayarlari_oku(); config_url,config_key=cloud_yapilandirmasi_oku(); self.url=QLineEdit(cloud.url or config_url); self.key=QLineEdit(cloud.anahtar or config_key); self.key.setEchoMode(QLineEdit.EchoMode.Password); self.email=QLineEdit(a.get("cloud_email","")); self.pw=QLineEdit(); self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.cloud_hatirla=QCheckBox(T('Bu cihazdaki Cloud oturumunu hatırla')); self.cloud_hatirla.setChecked(bool(a.get("cloud_refresh_token_dpapi","")))
        self.cloud_goster=QCheckBox(T('Cloud parolasını göster')); self.cloud_goster.toggled.connect(lambda acik:self.pw.setEchoMode(QLineEdit.EchoMode.Normal if acik else QLineEdit.EchoMode.Password))
        cb=QPushButton(T('Bağlantıyı Doğrula') if cloud.bagli and not getattr(cloud,"auth_required",False) else T('Cloud Giriş ve Senkronizasyon')); cb.setObjectName("birincil"); cb.clicked.connect(self.cloud_giris)
        self.connection_label=QLabel(T('Cloud bağlı · Uygulama girişiniz kullanılıyor; tekrar parola girmeniz gerekmez.') if cloud.bagli else T('Cloud oturumu kapalı')); c.addRow(self.connection_label)
        c.addRow("Project URL:",self.url); c.addRow("Publishable / anon key:",self.key); c.addRow(T('Cloud e-posta:'),self.email); c.addRow(T('Cloud parola:'),self.pw); c.addRow(self.cloud_goster); c.addRow(self.cloud_hatirla); c.addRow(cb); sek.addTab(bulut,T('Cloud ve Senkronizasyon'))
        if cloud.bagli and not getattr(cloud,"auth_required",False):
            for field in (self.url,self.key,self.email,self.pw,self.cloud_goster,self.cloud_hatirla):field.setEnabled(False)
            self.pw.setPlaceholderText(T('Açık oturum otomatik yenilenir'))
        guv=QWidget(); q=QFormLayout(guv); self.kilit=QComboBox(); self.kilit.addItems(["0","5","10","15","30","60"]); self.kilit.setCurrentText(vt.ayar_getir("otomatik_kilit_dakika","30")); qb=QPushButton(T('Güvenlik Ayarını Kaydet')); qb.clicked.connect(self.guvenlik_kaydet); q.addRow(T('Otomatik kilit (dakika):'),self.kilit);q.addRow(qb);sek.addTab(guv,T('Güvenlik'))
        bild=QWidget(); n=QFormLayout(bild); self.kritik=QCheckBox(T('Kritik stok uyarılarını göster')); self.kritik.setChecked(vt.ayar_getir("kritik_bildirim","1")=="1"); nb=QPushButton(T('Bildirim Ayarını Kaydet')); nb.clicked.connect(self.bildirim_kaydet); n.addRow(self.kritik);n.addRow(nb);sek.addTab(bild,T('Bildirimler'))
        gizli=QWidget();gl=QVBoxLayout(gizli)
        gl.addWidget(QLabel(T('Beş hızlı geçiş. Açık işlem penceresini kapatmadan ekran değiştirmez.')))
        for key,label,method in SHORTCUTS:
            button=QPushButton(key+" · "+label)
            def navigate(checked=False,method=method):
                if QMessageBox.question(self,T('Hızlı geçiş'),T('Kaydetmediğiniz ayarlar varsa önce kaydedin. Bu ekrandan ayrılsın mı?'))!=QMessageBox.StandardButton.Yes:return
                self.accept()
                if parent:QTimer.singleShot(0,getattr(parent,method))
            button.clicked.connect(navigate);gl.addWidget(button)
        gl.addStretch();sek.addTab(gizli,T('Gizli Komutlar'))
        extend_settings(self,g,q,n)
        if parent and hasattr(parent,"companion"):companion_settings(parent.companion,sek)
    def genel_kaydet(self):
        if self.job is not None:return
        if not self.cloud.bagli or self.cloud.role!='owner':self.company_status.setText(T('İşletme adını yalnızca ana hesap sahibi değiştirebilir.'));return
        name=self.isletme.text().strip()
        if not 2<=len(name)<=120 or any(ord(c)<32 for c in name):self.company_status.setText(T('İşletme adı 2–120 karakter olmalıdır.'));return
        from deporiaq_commerce_ui import Job
        self.company_save.setEnabled(False);self.isletme.setReadOnly(True);self.company_status.setText(T('Kaydediliyor…'))
        payload={'p_device':self.cloud.cihaz_kimligi,'p_name':name,'p_expected_name':self.expected_company_name}
        self.job=Job(lambda:self.cloud._istek('/rest/v1/rpc/dpq_company_profile','POST',payload),self)
        self.job.finished.connect(self.company_saved);self.job.start()
    def company_saved(self):
        job=self.job;self.job=None;self.company_save.setEnabled(self.cloud.role=='owner');self.isletme.setReadOnly(self.cloud.role!='owner')
        if job.error:self.company_status.setText(job.error)
        else:
            self.expected_company_name=job.result['name'];self.cloud.company_name=job.result['name']
            self.vt.ayar_kaydet('isletme_adi',job.result['name']);self.vt.baglanti.commit()
            parent=self.parentWidget()
            if parent and hasattr(parent,'company_label'):
                parent.company_profile_epoch=getattr(parent,'company_profile_epoch',0)+1
                parent.company_label.setText(job.result['name']);parent.company_label.setToolTip(job.result['name'])
            self.company_status.setText(T('İşletme adı Cloud ve başlıkta güncellendi.'))
        job.deleteLater()
    def reject(self):
        if self.job is None:super().reject()
    def closeEvent(self,event):
        if self.job is not None:event.ignore()
        else:super().closeEvent(event)
    def guvenlik_kaydet(self):self.vt.ayar_kaydet("otomatik_kilit_dakika",self.kilit.currentText());self.vt.baglanti.commit();QMessageBox.information(self,T('Kaydedildi'),T('Güvenlik ayarı kaydedildi.'))
    def bildirim_kaydet(self):save_notifications(self);self.vt.ayar_kaydet("kritik_bildirim","1" if self.kritik.isChecked() else "0");self.vt.baglanti.commit();QMessageBox.information(self,T('Kaydedildi'),T('Bildirim ayarı kaydedildi.'))
    def cloud_giris(self):
        if self.cloud.bagli and not getattr(self.cloud,"auth_required",False):
            try:
                self.cloud.lisans_dogrula()
                self.connection_label.setText(T('Cloud bağlı · Oturumunuz doğrulandı.'))
                self.cloud_yenile()
            except Exception as e:
                self.connection_label.setText(T('Bağlantı doğrulanamadı; oturum korunuyor. ')+str(e))
            return
        try:
            candidate=DeporiaQCloud(self.vt,self.cloud.cihaz_kimligi)
            candidate.yapilandir(self.url.text(),self.key.text())
            if self.cloud.bagli and candidate.url != self.cloud.url:
                raise ValueError(T('Açık oturumda işletme sunucusu değiştirilemez.'))
            ad=candidate.giris_yap(self.email.text(),self.pw.text())
            if self.cloud.bagli and (candidate.user_id!=self.cloud.user_id or candidate.company_id!=self.cloud.company_id):
                raise ValueError(T('Ayarlar üzerinden kullanıcı veya işletme değiştirilemez. Çıkış yapıp giriş ekranını kullanın.'))
            with self.cloud._session_lock:
                for field in ('url','anahtar','access_token','refresh_token','user_id','company_id','company_name','role','entitlement','auth_required'):
                    setattr(self.cloud,field,getattr(candidate,field))
                if self.cloud.on_token_rotated:self.cloud.on_token_rotated(self.cloud)
            sonuc,_=self.cloud.akilli_senkronize()
            self.pw.clear();self.connection_label.setText(T('Cloud oturumu açık'))
            yerel_ayari_kaydet("cloud_url",self.url.text().strip());yerel_ayari_kaydet("cloud_publishable_key",self.key.text().strip());yerel_ayari_kaydet("cloud_email",self.email.text().strip())
            if self.cloud.refresh_token and self.cloud_hatirla.isChecked(): yerel_ayari_kaydet("cloud_refresh_token_dpapi",windows_sifrele(self.cloud.refresh_token))
            else: yerel_ayari_kaydet("cloud_refresh_token_dpapi","")
            self.vt.ayar_kaydet("cloud_etkin","1");self.vt.baglanti.commit();self.cloud_yenile();QMessageBox.information(self,T('Cloud bağlı'),f"{ad}\nSenkronizasyon: {sonuc}")
        except Exception as e:QMessageBox.warning(self,T('Cloud bağlantısı kurulamadı'),str(e))


class UrunOzellestirmePenceresi(QDialog):
    def __init__(self,vt,kullanici,cloud,yenile,parent=None):
        super().__init__(parent); self.vt,self.kullanici,self.cloud,self.yenile=vt,kullanici,cloud,yenile; self.urunler=[]
        self.setWindowTitle(T('Ürün Özelleştirmeleri')); self.resize(820,610); d=QVBoxLayout(self)
        b=QLabel(T('Ürün Özelleştirmeleri')); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        self.arama=QLineEdit(); self.arama.setPlaceholderText(T('Ürün adı veya barkodun bir kısmını yazın'))
        self.urunler=[dict(x) for x in vt.tum_aktif_urunleri_getir()]
        self.tamamlayici=QCompleter([f"{u['barkod']} • {u['ad']}" for u in self.urunler],self); self.tamamlayici.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive); self.tamamlayici.setFilterMode(Qt.MatchFlag.MatchContains)
        self.arama.setCompleter(self.tamamlayici); self.arama.textChanged.connect(self.urun_bul); d.addWidget(self.arama)
        f=QFormLayout(); self.yeni_ad=QLineEdit(); self.yeni_barkod=QLineEdit(); f.addRow(T('Yeni ürün adı:'),self.yeni_ad); f.addRow(T('Yeni barkod:'),self.yeni_barkod); d.addLayout(f)
        self.secili_id=None; gonder=QPushButton(T('Ürün Özelleştirme Talebi Gönder')); gonder.setObjectName("birincil"); gonder.clicked.connect(self.talep_gonder); d.addWidget(gonder)
        self.durum=QLabel(""); self.durum.setObjectName("soluk"); d.addWidget(self.durum)
        self.tablo=QTableWidget(0,5); self.tablo.setHorizontalHeaderLabels([T('Ürün'),T('Yeni ad'),T('Yeni barkod'),T('Talep eden'),T('Durum')]); tablo_standardi(self.tablo,30); d.addWidget(self.tablo,1)
        if kullanici["rol"]=="ANA_YONETICI":
            a=QHBoxLayout(); kabul=QPushButton(T('Talebi Kabul Et')); kabul.setObjectName("basari"); kabul.clicked.connect(lambda:self.karar("KABUL")); red=QPushButton(T('Talebi Reddet')); red.setObjectName("tehlike"); red.clicked.connect(lambda:self.karar("RED")); a.addWidget(kabul);a.addWidget(red);d.addLayout(a)
        self.liste_yenile()
    def urun_bul(self,metin):
        m=metin.casefold().strip()
        if " • " in m:m=m.split(" • ",1)[0].strip()
        eslesen=next((u for u in self.urunler if m and (m in str(u['ad']).casefold() or m in str(u['barkod']).casefold())),None)
        if eslesen: self.secili_id=eslesen['id']; self.yeni_ad.setText(eslesen['ad']); self.yeni_barkod.setText(eslesen['barkod'])
    def talep_gonder(self):
        if not self.secili_id or not self.yeni_ad.text().strip() or not self.yeni_barkod.text().strip(): QMessageBox.warning(self,T('Eksik bilgi'),T('Listeden bir ürün seçip yeni ad ve barkodu doldurun.'));return
        u=next(x for x in self.urunler if x['id']==self.secili_id)
        try:
            self.vt.baglanti.execute("INSERT INTO urun_ozellestirme_talepleri(urun_id,eski_ad,eski_barkod,yeni_ad,yeni_barkod,talep_eden_id,tarih_saat) VALUES(?,?,?,?,?,?,?)",(u['id'],u['ad'],u['barkod'],self.yeni_ad.text().strip(),self.yeni_barkod.text().strip(),self.kullanici['id'],datetime.now().strftime('%d.%m.%Y %H:%M:%S')));self.vt.baglanti.commit()
            if self.cloud.bagli:self.cloud.urun_talebi_gonder({"old_name":u['ad'],"old_barcode":u['barkod'],"new_name":self.yeni_ad.text().strip(),"new_barcode":self.yeni_barkod.text().strip(),"requester_name":self.kullanici['kullanici_adi']})
            self.durum.setText(T('Talep ana yönetici onayına gönderildi.'));self.liste_yenile()
        except Exception as e: QMessageBox.warning(self,T('Talep gönderilemedi'),str(e))
    def liste_yenile(self):
        satirlar=[dict(x) for x in self.vt.baglanti.execute("SELECT t.*,COALESCE(k.kullanici_adi,'—') talep_eden FROM urun_ozellestirme_talepleri t LEFT JOIN kullanicilar k ON k.id=t.talep_eden_id ORDER BY t.id DESC LIMIT 100").fetchall()]
        if self.cloud.bagli:
            try:
                satirlar=[{"id":x['id'],"remote":True,"urun_id":None,"eski_ad":x['old_name'],"eski_barkod":x['old_barcode'],"yeni_ad":x['new_name'],"yeni_barkod":x['new_barcode'],"talep_eden":x.get('requester_name','—'),"durum":{'approved':'KABUL','rejected':'RED','pending':'BEKLIYOR'}.get(x.get('status'),x.get('status'))} for x in self.cloud.urun_talepleri_getir()]
            except Exception:pass
        self.tablo.setRowCount(len(satirlar));self.kayitlar=[]
        for r,x in enumerate(satirlar):
            self.kayitlar.append(dict(x)); durum={'KABUL':T('Talep kabul edildi.'),'RED':T('Talep reddedildi!'),'BEKLIYOR':T('Onay bekliyor')}.get(x['durum'],x['durum'])
            for c,v in enumerate((x['eski_ad'],x['yeni_ad'],x['yeni_barkod'],x['talep_eden'],durum)):self.tablo.setItem(r,c,QTableWidgetItem(v if isinstance(v,Text) else str(v)))
    def karar(self,karar):
        r=self.tablo.currentRow()
        if r<0: QMessageBox.warning(self,T('Seçim gerekli'),T('Bir talep seçin.'));return
        x=self.kayitlar[r]
        if x['durum']!='BEKLIYOR': QMessageBox.information(self,T('İşlem yapılmış'),T('Bu talep daha önce karara bağlanmış.'));return
        try:
            urun_id=x.get('urun_id')
            if not urun_id: 
                urun=self.vt.baglanti.execute("SELECT id FROM urunler WHERE barkod=?",(x['eski_barkod'],)).fetchone();urun_id=urun['id'] if urun else None
            if karar=='KABUL' and urun_id:self.vt.baglanti.execute("UPDATE urunler SET ad=?,barkod=? WHERE id=?",(x['yeni_ad'],x['yeni_barkod'],urun_id))
            if x.get('remote'):self.cloud.urun_talebi_karar(x['id'],'approved' if karar=='KABUL' else 'rejected')
            else:self.vt.baglanti.execute("UPDATE urun_ozellestirme_talepleri SET durum=?,karar_tarihi=?,karar_veren_id=? WHERE id=?",(karar,datetime.now().strftime('%d.%m.%Y %H:%M:%S'),self.kullanici['id'],x['id']))
            self.vt.baglanti.commit();self.durum.setText(T('Talep kabul edildi.') if karar=='KABUL' else T('Talep reddedildi!'));self.liste_yenile();self.yenile()
        except Exception as e:self.vt.baglanti.rollback();QMessageBox.warning(self,T('İşlem başarısız'),str(e))


from deporiaq_help import HELP

class YardimMerkezi(QDialog):
    KONULAR={
        T('Hızlı Başlangıç'):T("DeporiaQ'ya Hoş Geldiniz\n\n1. Ürün Yönetimi'nden ürün kartlarını oluşturun.\n2. Stok Girişi ile merkez depoya mal kabul edin.\n3. Depo ve Şubeler bölümünden çalışma noktalarını yönetin.\n4. Stok Transferi ile ürünleri konumlar arasında aktarın.\n5. Gösterge Paneli ve raporlardan işletmenizi takip edin.\n\nBarkod alanına tıklayıp USB okuyucu veya el terminaliyle barkodu okutabilirsiniz."),
        T('Stok İşlemleri'):T('STOK GİRİŞİ\nMerkez depoya gelen ürünün barkodunu okutun ve miktarı girin.\n\nTRANSFER\nKaynak ve hedef konumu seçin. Ürün ve miktar doğrulandıktan sonra işlem hareket geçmişine kaydedilir.\n\nŞUBEDE SATIŞ\nSatış yapılan şubeyi seçin, barkodu okutun ve miktarı girin. Stok otomatik düşer ve ciro/kâr raporuna işlenir.\n\nSTOK SAYIMI\nProfesyonel Araçlar > Stok Sayımı ile sistem miktarını fiziksel sayımla eşitleyin.'),
        T('Cloud ve Kullanıcılar'):T('Cloud hesabı, yerel kullanıcı hesabından ayrıdır.\n\nCloud e-posta/parolası işletmenin bulut verilerine erişir. Yerel Kullanıcılar ekranındaki hesaplar ise bu bilgisayarda programa giriş ve yetki kontrolü içindir.\n\nAyarlar > Cloud ve Senkronizasyon bölümünden giriş yapabilirsiniz. Parola açık biçimde kaydedilmez. Durum göstergesindeki yeşil nokta verilerin güncel olduğunu belirtir.'),
        T('Raporlar ve Yazdır'):T('Raporlar ve Yazdır bölümünde genel stok, kritik stok, kâr, denetim ve oturum kayıtları bulunur.\n\nYazdır düğmesi Windows yazıcı ekranını açar. CSV Dışa Aktar seçeneği raporu Excel ile açılabilecek biçimde kaydeder.\n\nSipariş Önerileri, kritik seviyedeki ürünler için hedef stoğu kritik seviyenin iki katına tamamlayacak öneri üretir.'),
        T('Operasyon Merkezi'):T('Ana Yönetici için 9 analiz ekranı: tüm depolarda arama, tükenme, ABC, hareketsiz stok, transfer önerisi, satın alma planı, konum karşılaştırması, günlük satış ve sayım listesi.\n\nSonuçlar yerel veriye dayanır. Cloud eşitlemesi tamamlandıktan sonra Verileri Yenile düğmesini kullanın. Öneriler otomatik stok değişikliği yapmaz.\n\nDestek: deporiaq@gmail.com\nInstagram: @deporiaq\nYouTube: @DeporiaQ'),
        T('Kısayollar'):join_text("\n",[key+" — "+label for key,label,_ in SHORTCUTS]),
        T('Sorun Giderme'):T("ÜRÜN BULUNAMADI\nDoğru konumun seçili olduğunu ve ürünün o konumda stok kaydı bulunduğunu kontrol edin.\n\nCLOUD BAĞLI DEĞİL\nİnternet bağlantısını, Project URL'yi ve publishable/anon anahtarını kontrol edin. Cloud parolası güvenlik nedeniyle her zaman ekranda tutulmaz.\n\nGÜNCELLEME GELMİYOR\nAyarlar dosyasındaki manifest adresini, internet bağlantısını ve DeporiaQUpdate.exe dosyasının kurulum klasöründe bulunduğunu kontrol edin.\n\nVERİ SORUNU\nÖnce Veri ve Yedekleme ile yedek alın. Ardından VERITABANI_ONAR aracını kullanın."),
    }
    KONULAR.update(HELP)
    def __init__(self,vt,parent=None):
        super().__init__(parent);self.vt=vt;self.setWindowTitle(T('DeporiaQ Yardım Merkezi'));self.resize(900,650)
        d=QVBoxLayout(self);b=QLabel(T('Yardım Merkezi'));b.setObjectName("sayfaBaslik");d.addWidget(b)
        alt=QLabel(T('DeporiaQ {v0} • Kullanım rehberi, sorun giderme ve destek', v0=SURUM));alt.setObjectName("soluk");d.addWidget(alt)
        sek=QTabWidget();d.addWidget(sek,1)
        for ad,metin in self.KONULAR.items():
            alan=QPlainTextEdit(metin);alan.setReadOnly(True);sek.addTab(alan,ad)
        destek=QWidget();f=QVBoxLayout(destek)
        f.addWidget(QLabel(T('Müşteri desteği: deporiaq@gmail.com')))
        g=QPushButton(T('Sunucuya Destek Talebi Gönder'))
        g.clicked.connect(lambda:SupportDialog(parent.commerce,self).exec() if parent else None)
        f.addWidget(g);sek.addTab(destek,T('Destek'))
        a=QHBoxLayout();surum=QLabel(T('Sürüm {v0} • © 2026 DeporiaQ', v0=SURUM));surum.setObjectName("soluk");k=QPushButton(T('Kapat'));k.clicked.connect(self.accept);a.addWidget(surum);a.addStretch();a.addWidget(k);d.addLayout(a)
    def gonder(self):
        try:no=self.vt.destek_talebi_olustur(self.tur.currentText(),self.konu.text(),self.mesaj.toPlainText(),self.iletisim.text())
        except ValueError as e:QMessageBox.warning(self,T('Eksik bilgi'),str(e));return
        QMessageBox.information(self,T('Destek kaydı oluşturuldu'),T('Takip numaranız: {v0}\nKayıt bu bilgisayarda güvenle saklandı.', v0=no));self.konu.clear();self.mesaj.clear()


class SiparisOnerileriPenceresi(QDialog):
    def __init__(self, vt, parent=None):
        super().__init__(parent); self.vt=vt
        self.setWindowTitle(T('Akıllı Sipariş Önerileri')); self.resize(980,620)
        d=QVBoxLayout(self); b=QLabel(T('Akıllı Sipariş Önerileri')); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        aciklama=QLabel(T('Kritik ürünler için hedef stok, kritik seviyenin iki katı olarak hesaplanır.')); aciklama.setObjectName("soluk"); d.addWidget(aciklama)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels([T('Konum'),T('Barkod'),T('Ürün'),T('Mevcut'),T('Hedef'),T('Önerilen Sipariş')]); tablo_standardi(self.t,36); d.addWidget(self.t,1)
        a=QHBoxLayout(); yenile=QPushButton(T('Listeyi Yenile')); yenile.clicked.connect(self.yenile); aktar=QPushButton(T('CSV Dışa Aktar')); aktar.setObjectName("birincil"); aktar.clicked.connect(self.csv_aktar); kapat=QPushButton(T('Kapat')); kapat.clicked.connect(self.accept)
        a.addWidget(yenile); a.addWidget(aktar); a.addStretch(); a.addWidget(kapat); d.addLayout(a); self.yenile()
    def yenile(self):
        self.satirlar=[]
        for x in self.vt.kritik_stoklari_getir():
            mevcut=int(x["miktar"] or 0); kritik=int(x["kritik_stok"] or 0); hedef=max(kritik*2,1); onerilen=max(hedef-mevcut,1)
            self.satirlar.append((x["konum"],x["barkod"],x["urun"],mevcut,hedef,onerilen))
        self.t.setRowCount(len(self.satirlar))
        for r,satir in enumerate(self.satirlar):
            for c,v in enumerate(satir):self.t.setItem(r,c,QTableWidgetItem(v if isinstance(v,Text) else str(v)))
    def csv_aktar(self):
        yol,_=QFileDialog.getSaveFileName(self,T('Sipariş önerilerini kaydet'),"DeporiaQ_Siparis_Onerileri.csv","CSV (*.csv)")
        if not yol:return
        with open(yol,"w",newline="",encoding="utf-8-sig") as f:
            y=csv.writer(f,delimiter=";");y.writerow([T('Konum'),T('Barkod'),T('Ürün'),T('Mevcut'),T('Hedef'),T('Önerilen Sipariş')]);y.writerows(self.satirlar)
        QMessageBox.information(self,T('Dışa aktarıldı'),T('Sipariş önerileri kaydedildi:\n{v0}', v0=yol))


class AnaPencere(QMainWindow):
    def __init__(self, vt, kullanici, giris):
        super().__init__()
        self.vt, self.kullanici, self.giris = vt, kullanici, giris
        set_language(vt.ayar_getir('ui_language','tr'))
        ayarlar=ayarlari_oku(); cihaz=str(ayarlar.get("cihaz_kimligi","")).strip()
        if not cihaz:
            cihaz="DPQ-"+secrets.token_hex(6).upper(); yerel_ayari_kaydet("cihaz_kimligi",cihaz)
        self.cloud_client=getattr(giris,"auth_cloud",None) or DeporiaQCloud(vt,cihaz)
        self.cloud_client.on_token_rotated=self.cloud_tokenini_kaydet
        self.commerce=CommerceClient(self.cloud_client)
        self.cloud_client.local_username=str(kullanici["kullanici_adi"])
        try:
            konum=vt.baglanti.execute("SELECT ad FROM konumlar WHERE id=?",(kullanici["konum_id"],)).fetchone()
            self.cloud_client.location_name=konum["ad"] if konum else T('Merkez')
        except Exception:self.cloud_client.location_name=T('Merkez')
        self.setWindowTitle(f"{PROGRAM_ADI} {SURUM}")
        self.setMinimumSize(760, 560)
        govde = QWidget(); self.setCentralWidget(govde)
        ana = QVBoxLayout(govde); ana.setContentsMargins(0, 0, 0, 0); ana.setSpacing(0)
        ana.addWidget(self.ust_cubuk())
        orta = QHBoxLayout(); orta.setContentsMargins(0, 0, 0, 0); orta.setSpacing(0)
        orta.addWidget(self.yan_menu())
        self.kaydir = QScrollArea(); self.kaydir.setWidgetResizable(True)
        self.kaydir.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.icerik = DashboardArkaPlan(); self.icerik.setObjectName("dashboardArkaPlan"); self.icerik.setMinimumWidth(0)
        self.kaydir.setWidget(self.icerik); orta.addWidget(self.kaydir, 1)
        ana.addLayout(orta, 1)
        ana.addWidget(self.alt_cubuk())
        self.dashboard_kur()
        from deporiaq_retail import RetailHub
        self.retail_hub=RetailHub(self)
        self.retail_hub.install(self.panel_canvas)
        self.companion=CompanionController(self,self.pet_dock)
        self.notification_storage_key='notification_history_'+str(self.kullanici['id'])
        try:self.notifications=json.loads(self.vt.ayar_getir(self.notification_storage_key,'[]'))[-100:]
        except (ValueError,TypeError):self.notifications=[]
        self.notification_keys={tuple(row[1:]) for row in self.notifications};self.session_guard=SessionGuard(self)
        self.notification_button.setCount(0)
        self.search_controller=SearchController(self,self.header.search)
        self.refresh_profile_text()
        apply_appearance(self)
        self.quick_shortcuts=[]
        for key,label,method in SHORTCUTS:
            shortcut=QShortcut(QKeySequence(key),self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(getattr(self,method));self.quick_shortcuts.append(shortcut)
        self.startup_timers=[]
        self.schedule(50,self.yenile)
        self.canli_zamanlayici=QTimer(self);self.canli_zamanlayici.timeout.connect(self.canli_yenile);self.canli_zamanlayici.start(15000)
        self.senkron_zamanlayici=QTimer(self);self.senkron_zamanlayici.timeout.connect(self.cloud_senkronize);self.senkron_zamanlayici.start(30000)
        self.kur_zamanlayici=QTimer(self);self.kur_zamanlayici.timeout.connect(self.kurlari_yenile);self.kur_zamanlayici.start(300000)
        self.lisans_kilitli=False
        self.license_timer=QTimer(self);self.license_timer.timeout.connect(self.cloud_oturumunu_yenile);self.license_timer.start(1800000)
        self.presence_session=str(uuid.uuid4());self.presence_seen=0
        self.presence_timer=QTimer(self);self.presence_timer.timeout.connect(self.refresh_presence);self.presence_timer.start(10000)
        self.schedule(900,self.cloud_oturumunu_yenile)
        self.schedule(1200,self.cloud_senkronize)
        if self.vt.ayar_getir("notify_update","1")=="1":self.schedule(2000,lambda:self.guncelleme_denetle(True))
        self.schedule(0,self.duyarli_yerlesimi_guncelle)

    def schedule(self,delay,fn):
        timer=QTimer(self);timer.setSingleShot(True);timer.timeout.connect(fn);timer.start(delay);self.startup_timers.append(timer)

    def closeEvent(self,event):
        if hasattr(self,'retail_hub'):
            self.retail_hub.timer.stop()
            from deporiaq_commerce_ui import Job
            if any(job.isRunning() for job in self.retail_hub.findChildren(Job)) or any(job.isRunning() for job in self.panel_canvas.findChildren(Job)):
                event.ignore();QTimer.singleShot(300,self.close);return
        panels=[w for w in self.findChildren(QDialog) if w.isVisible()]
        if any(getattr(w,'job',None) is not None for w in panels):
            event.ignore();self.cloud.setText(T('İşlem tamamlanınca kapanacak…'));QTimer.singleShot(300,self.close);return
        for panel in panels:
            if not panel.close():event.ignore();self._logout_requested=False;return
        timers=self.startup_timers+[self.canli_zamanlayici,self.senkron_zamanlayici,self.kur_zamanlayici,self.presence_timer,self.license_timer]
        for timer in timers:timer.stop()
        workers=[getattr(self,name,None) for name in ('cloud_iscisi','senkron_iscisi','kur_iscisi','guncelleme_isci','presence_worker','company_worker')]
        workers += [getattr(getattr(self,name,None),'job',None) for name in ('search_controller','assistant_panel')]
        if any(worker is not None and worker.isRunning() for worker in workers):
            event.ignore();self.cloud.setText(T('Bağlantı tamamlanıyor…'));QTimer.singleShot(300,self.close);return
        if self.cloud_client.bagli and not getattr(self,'_presence_left',False):
            self._presence_left=True;event.ignore()
            self.presence_worker=PresenceWorker(self.cloud_client,self.presence_session,self.kullanici['kullanici_adi'],True,self)
            self.presence_worker.finished.connect(self.close);self.presence_worker.start();return
        if hasattr(self,'session_guard'):self.session_guard.timer.stop();QApplication.instance().removeEventFilter(self.session_guard)
        if hasattr(self,'companion'):self.companion.stop()
        if self.vt.ayar_getir('ui_animation','1')=='1':play_brand(kaynak_yolu('deporiaq_icon.svg'),True)
        if getattr(self,'_logout_requested',False):
            self.vt.aktif_kullanici_id=None;self.cloud_client.cikis_yap();self.giris.auth_cloud=None
            self.giris.parola.clear();self.giris.show();self.giris.raise_()
        super().closeEvent(event)

    def home(self):
        active=QApplication.activeModalWidget() or next((w for w in self.findChildren(QDialog) if w.isVisible()),None)
        if active and active is not self:
            if getattr(active,'job',None) is not None:return
            if QMessageBox.question(active,T('Ana Sayfaya Dön'),T('Açık pencere kapatılacak. Kaydedilmemiş girişlerden vazgeçilsin mi?'))!=QMessageBox.StandardButton.Yes:return
            self.return_home=True
            active.reject()
            if active.isVisible():return
        self.kaydir.verticalScrollBar().setValue(0);self.yenile();self.konum.setFocus()

    def notify(self,title,message,key=None,force=False):
        if not hasattr(self,'notifications'):return
        if key and self.vt.ayar_getir(key,'1')!='1':return
        identity=(title,message)
        if identity in self.notification_keys and not force:return
        self.notification_keys.add(identity)
        self.notifications.append((datetime.now().strftime('%d.%m.%Y %H:%M'),title,message))
        self.notifications=self.notifications[-100:]
        self.notification_button.setCount(self.notification_button.unread+1)
        self.vt.ayar_kaydet(self.notification_storage_key,json.dumps(self.notifications,ensure_ascii=False));self.vt.baglanti.commit()
        self.notification_button.setToolTip(title+' · '+message)
        if self.vt.ayar_getir('notify_sound','0')=='1':QApplication.beep()

    def notification_history(self):
        self.notification_button.setCount(0)
        d=QDialog(self);d.setWindowTitle(T('Bildirimler'));d.resize(560,520);layout=QVBoxLayout(d)
        title=QLabel(T('Bildirimler'));title.setObjectName('sayfaBaslik');layout.addWidget(title)
        scroll=QScrollArea();scroll.setWidgetResizable(True);root=QWidget();cards=QVBoxLayout(root);cards.setAlignment(Qt.AlignmentFlag.AlignTop);scroll.setWidget(root);layout.addWidget(scroll,1)
        for when,title,message in reversed(self.notifications):
            card=QFrame();card.setObjectName('notificationCard');box=QVBoxLayout(card)
            top=QLabel(title+'  ·  '+when);top.setTextFormat(Qt.TextFormat.PlainText);top.setWordWrap(True);box.addWidget(top)
            content=QLabel(message);content.setTextFormat(Qt.TextFormat.PlainText);content.setWordWrap(True);box.addWidget(content);cards.addWidget(card)
        if not self.notifications:cards.addWidget(QLabel(T('Henüz bildirim yok.')))
        clear=QPushButton(T('Geçmişi Temizle'))
        def reset():
            self.notifications.clear();self.notification_keys.clear();self.notification_button.setCount(0)
            self.vt.ayar_kaydet(self.notification_storage_key,'[]');self.vt.baglanti.commit();d.accept()
        clear.clicked.connect(reset);layout.addWidget(clear);d.exec()

    def grup_ac(self,title,entries):
        self.return_home=False
        d=QDialog(self);d.setWindowTitle(title);d.setMinimumWidth(360);v=QVBoxLayout(d)
        for label,callback in entries:
            b=QPushButton(label)
            def selected(checked=False,fn=callback):
                d.hide()
                try:fn()
                finally:
                    if getattr(self,"return_home",False):d.reject()
                    else:d.show();d.raise_();d.activateWindow()
            b.clicked.connect(selected);v.addWidget(b)
        d.exec()

    def stok_merkezi_ac(self):
        self.grup_ac(T('Stok ve Ürünler'), [(T('Ürünler ve Stoklar'),self.urun_yonetimi_ac),(T('Stok Girişi'),self.stok_girisi_ac),(T('Stok Sayımı'),self.araclar_ac),(T('Ürün Ayrıntıları'),lambda:ProductDetailsDialog(self.commerce,self).exec()),(T('Hasarlı Ürün Ayır'),lambda:DamageDialog(self.commerce,self).exec()),(T('Parti ve Son Kullanma'),lambda:RecordsDialog(self.commerce,'batch',self).exec())])

    def satis_merkezi_ac(self):
        self.grup_ac(T('Satışlar'),[(T('Satış Kasası'),lambda:self.retail_hub.open('pos')),(T('Kayıtlı Eski Sepetler'),lambda:BasketDialog(self.commerce,self).exec()),(T('Şube Satış / Rezervasyon'),self.satis_ac),(T('İnternet Siparişleri'),self.internet_ac)])

    def depo_merkezi_ac(self):
        self.grup_ac(T('Depolar ve Transferler'),[(T('Konumlar'),self.konum_yonetimi_ac),(T('Stok Transferi'),self.transfer_ac)])

    def rapor_merkezi_ac(self):
        self.grup_ac(T('Raporlar'),[(T('Operasyon Merkezi'),self.operasyon_ac),(T('Raporlar ve Yazdır'),self.raporlar_ac),(T('Kritik Stoklar'),self.kritikleri_ac),(T('Sipariş Önerileri'),self.siparis_onerileri_ac),(T('Hareket Geçmişi'),self.hareketleri_ac)])

    def yonetim_merkezi_ac(self):
        self.grup_ac(T('Yönetim'),[(T('Kullanıcı Yetkileri'),self.kullanicilar_ac),(T('Veri ve Yedekleme'),self.yedek_al),(T('Tedarikçiler'),lambda:RecordsDialog(self.commerce,'supplier',self).exec()),(T('Satın Alma Siparişleri'),lambda:CollectionDialog(self.commerce,'purchase',self).exec()),(T('Set ve Paketler'),lambda:self.retail_hub.open('bundles')),(T('Eski Paket Kayıtları'),lambda:CollectionDialog(self.commerce,'bundle',self).exec()),(T('Excel Ürün İçe Aktarma'),lambda:ImportDialog(self.commerce,self).exec()),(T('Toplu Fiyat Güncelle'),lambda:BulkPricesDialog(self.commerce,self).exec()),(T('Personel İndirim Sınırı'),self.discount_policy),(T('İndirim Onayları'),lambda:ApprovalDialog(self.commerce,self).exec())])

    def destek_merkezi_ac(self):
        self.grup_ac(T('Yardım ve Destek'),[(T('Kullanım Rehberi'),self.yardim_ac),(T('Destek Talebi Gönder'),self.destek_ac)])

    def discount_policy(self):
        value,ok=QInputDialog.getDouble(self,T('Personel İndirim Sınırı'),T('Yönetici olmayan satış personeli için azami indirim (%):'),0,0,100,2)
        if not ok:return
        from deporiaq_commerce_ui import ServerDialog
        d=ServerDialog(self.commerce,T('İndirim Yetkisi'),self)
        d.run(lambda:self.commerce.mutate('workspace_discount_policy',{'limit':value}),lambda r:d.status_label.setText(T('Personel indirim sınırı: %')+str(r['limit'])))
        d.exec()

    def internet_ac(self):
        OrdersDialog(self.commerce,self).exec()

    def paket_ac(self):
        PlansDialog(self.commerce,self).exec()

    def destek_ac(self):
        SupportDialog(self.commerce,self).exec()

    def kisayollar_ac(self):
        self.grup_ac(T('Ayarlar · Gizli Komutlar'),[(key+' · '+label,getattr(self,method)) for key,label,method in SHORTCUTS])

    def ust_cubuk(self):
        self.header=ExperienceHeader(self,SURUM)
        return self.header

    def refresh_profile_text(self):
        roles={'owner':T('Ana Yönetici'),'admin':T('Yönetici'),'manager':T('Yönetici'),'warehouse':T('Depo Personeli'),'employee':T('Personel'),'branch':T('Şube Personeli'),'viewer':T('Görüntüleyici')}
        role=roles.get(self.cloud_client.role,T('Ana Yönetici') if self.kullanici['rol']=='ANA_YONETICI' else T('Personel'))
        self.user_label.setText(T('{user}  ·  {role}',user=self.kullanici['kullanici_adi'],role=role))

    def change_language(self,code):
        self.vt.ayar_kaydet('ui_language',code);self.vt.baglanti.commit();yerel_ayari_kaydet('ui_language',code)
        set_language(code)
        for key,button in self.language_flags.items():button.setChecked(key==code)
        self.refresh_profile_text();self.cloud_gostergesini_yenile();self.tablo_yenile()
        if hasattr(self,'search_controller'):self.search_controller.hide()
        self.header.reflow()

    def toggle_mode(self):
        mode='light' if self.vt.ayar_getir('ui_mode','dark')=='dark' else 'dark'
        self.vt.ayar_kaydet('ui_mode',mode);self.vt.baglanti.commit()
        self.header.dark.kind='sun' if mode=='dark' else 'moon';apply_appearance(self)

    def global_search_open(self):
        if not hasattr(self,'search_controller'):return
        self.header.search.setFocus();self.header.search.selectAll();self.search_controller.changed(self.header.search.text())

    def assistant_open(self):
        if not hasattr(self,'assistant_panel'):
            self.assistant_panel=AssistantPanel(self)
            self.assistant_panel.check()
        self.assistant_panel.position_in_window();self.assistant_panel.show();self.assistant_panel.raise_();self.assistant_panel.input.setFocus()

    def refresh_company(self):
        if not self.cloud_client.bagli or time.monotonic()-getattr(self,'company_checked',0)<30:return
        if getattr(self,'company_worker',None) is not None and self.company_worker.isRunning():return
        from deporiaq_commerce_ui import Job
        self.company_checked=time.monotonic()
        self.company_worker=Job(lambda:self.cloud_client._istek('/rest/v1/rpc/dpq_company_profile','POST',{'p_device':self.cloud_client.cihaz_kimligi}),self)
        self.company_worker.profile_epoch=getattr(self,'company_profile_epoch',0)
        self.company_worker.finished.connect(self.company_refreshed);self.company_worker.start()

    def company_refreshed(self):
        job=self.company_worker
        if not job.error and job.profile_epoch==getattr(self,'company_profile_epoch',0):
            name=job.result['name'];self.cloud_client.company_name=name
            self.company_label.setText(name);self.company_label.setToolTip(name)
            self.vt.ayar_kaydet('isletme_adi',name);self.vt.baglanti.commit()

    def yan_menu(self):
        menu = QFrame(); menu.setObjectName("yanMenu")
        menu.setFixedWidth(218)
        d = QVBoxLayout(menu); d.setContentsMargins(10, 14, 10, 12); d.setSpacing(5)
        d.addWidget(QLabel(T('MENÜ')))
        navigation=QWidget();navigation.setObjectName('menuNavigation')
        nav=QVBoxLayout(navigation);nav.setContentsMargins(0,0,0,0);nav.setSpacing(5)
        entries=[(T('Ana Sayfa'),self.home),(T('Stok ve Ürünler'),self.stok_merkezi_ac),
                 (T('Satışlar'),self.satis_merkezi_ac),(T('Depolar ve Transferler'),self.depo_merkezi_ac),
                 (T('Raporlar'),self.rapor_merkezi_ac)]
        entries.append((T('Yönetim'),self.yonetim_merkezi_ac))
        entries += [(T('Paneller'),self.panels_open),(T('Paketim ve Abonelik'),self.paket_ac),(T('Ayarlar'),self.ayarlar_ac),(T('Yardım ve Destek'),self.destek_merkezi_ac)]
        for ad,komut in entries:
            b=QPushButton(ad);b.clicked.connect(komut);nav.addWidget(b)
            if komut==self.yonetim_merkezi_ac:self.management_button=b;b.setVisible(self.kullanici["rol"]=="ANA_YONETICI")
        nav.addStretch()
        kaydir=QScrollArea();kaydir.setObjectName('yanMenuKaydirma');kaydir.setWidgetResizable(True)
        kaydir.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        kaydir.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        kaydir.setFrameShape(QFrame.Shape.NoFrame);kaydir.setMinimumHeight(80)
        kaydir.setStyleSheet('QScrollArea#yanMenuKaydirma,QWidget#menuNavigation {background:transparent;border:0;}')
        kaydir.setWidget(navigation);self.menu_kaydir=kaydir;d.addWidget(kaydir,1)
        flags=QHBoxLayout();flags.setSpacing(8);self.language_flags={}
        flags.addStretch()
        for code in ('tr','en'):
            flag=FlagButton(code);flag.setChecked(language()==code);flag.clicked.connect(lambda checked=False,c=code:self.change_language(c));self.language_flags[code]=flag;flags.addWidget(flag)
        flags.addStretch();d.addSpacing(4);d.addLayout(flags)
        self.companion_host=QWidget();self.companion_host.setObjectName("companionHome")
        self.companion_host.setFixedHeight(210);self.companion_host.setMinimumWidth(0)
        d.addWidget(self.companion_host)
        self.cloud=QLabel(T('Cloud oturumu kapalı'));self.cloud.setObjectName('cloud');self.cloud.setWordWrap(True);d.addWidget(self.cloud)
        self.support_mail=QLabel("deporiaq@gmail.com");d.addWidget(self.support_mail)
        telif = QLabel(T('© 2026 DeporiaQ.\nTüm hakları saklıdır.')); telif.setObjectName("soluk")
        d.addWidget(telif)
        for label in menu.findChildren(QLabel):
            label.setWordWrap(True);label.setMinimumWidth(0);label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        for button in menu.findChildren(QPushButton):
            button.setMinimumWidth(0);button.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        return menu

    def alt_cubuk(self):
        alt = QFrame(); alt.setObjectName("altCubuk")
        d = QHBoxLayout(alt); d.setContentsMargins(18, 8, 18, 8)
        durum = QLabel(T('{version} • Özetler yerel önbellektir',version=SURUM)); durum.setObjectName("durum")
        d.addWidget(durum)
        self.pet_dock=PetDock(self);self.pet_dock.hide()
        d.addStretch()
        guncelle=QPushButton(T('Güncellemeleri Denetle'));guncelle.clicked.connect(lambda:self.guncelleme_denetle(False));d.addWidget(guncelle)
        cikis = QPushButton(T('Çıkış Yap')); cikis.clicked.connect(self.cikis_yap)
        kapat = QPushButton(T('Programı Kapat')); kapat.setObjectName("tehlike"); kapat.clicked.connect(self.close)
        d.addWidget(cikis); d.addWidget(kapat)
        return alt

    def panels_open(self):
        PanelsDialog(self.panel_canvas,self).exec()

    def dashboard_kur(self):
        d = QVBoxLayout(self.icerik); d.setContentsMargins(14, 10, 14, 10); d.setSpacing(8)
        self.ust_yerlesim = QGridLayout(); self.ust_yerlesim.setSpacing(8)
        self.baslik = QLabel(T('İşletme Özeti')); self.baslik.setObjectName("sayfaBaslik")
        self.konum = QComboBox(); self.konum.setMinimumWidth(200); self.konum.setMaximumWidth(820)
        self.konum.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.konum.currentIndexChanged.connect(self.yenile)
        self.yenile_dugmesi = QPushButton(T('Yenile')); self.yenile_dugmesi.clicked.connect(self.yenile)
        self.sosyal = QWidget(); self.sosyal.setObjectName("dashboardSosyal"); sosyal = QHBoxLayout(self.sosyal); sosyal.setContentsMargins(0,0,0,0); sosyal.setSpacing(8)
        youtube=QPushButton(QIcon(kaynak_yolu("youtube_icon.svg")),"DeporiaQ"); youtube.setToolTip(T('DeporiaQ YouTube • Yakında'))
        instagram=QPushButton(QIcon(kaynak_yolu("instagram_icon.svg")),"DeporiaQ"); instagram.setToolTip(T('DeporiaQ Instagram • Yakında'))
        youtube.clicked.connect(lambda:self.sosyal_yakinda("YouTube")); instagram.clicked.connect(lambda:self.sosyal_yakinda("Instagram"))
        sosyal.addWidget(youtube); sosyal.addWidget(instagram)
        for name in ('WhatsApp','X'):
            button=QPushButton(QIcon(kaynak_yolu(name.lower()+'_icon.svg')),'' if name=='X' else name);button.setAccessibleName(name);button.setToolTip(name+T(' hesabı henüz tanımlanmadı'));button.clicked.connect(lambda checked=False,name=name:self.sosyal_yakinda(name));sosyal.addWidget(button)
        self.x_button=button
        for social_button in self.sosyal.findChildren(QPushButton):social_button.setFixedSize(112,42)
        d.addLayout(self.ust_yerlesim)
        self.kart_yerlesim = QGridLayout(); self.kart_yerlesim.setSpacing(8); self.kartlar = []; self.kart_widgetlari=[]
        for bas in (T('Ürün çeşidi'), T('Seçili konum stoğu'), T('Toplam stok değeri'), T('Kritik stok')):
            k = QFrame(); k.setObjectName("kart"); kd = QHBoxLayout(k); kd.setContentsMargins(15,8,15,8); kd.setSpacing(12)
            baslik=QLabel(bas);baslik.setObjectName("kartBaslik");baslik.setWordWrap(True);kd.addWidget(baslik);kd.addStretch()
            deger = QLabel("0"); deger.setObjectName("kartDeger");deger.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter);kd.addWidget(deger)
            k.setMinimumHeight(66)
            self.kart_widgetlari.append(k); self.kartlar.append(deger)

        self.grafik_yerlesim = QGridLayout(); self.grafik_yerlesim.setSpacing(8)
        stok_karti = QFrame(); stok_karti.setObjectName("panel"); sk = QVBoxLayout(stok_karti)
        sk.addWidget(QLabel(T('Stok Sağlığı'))); stok_grafikleri=QHBoxLayout(); self.stok_grafikleri=stok_grafikleri; self.halka_grafik = HalkaGrafik(); self.stok_sutun_grafik=SutunGrafik()
        stok_grafikleri.addWidget(self.halka_grafik,1); stok_grafikleri.addWidget(self.stok_sutun_grafik,1); sk.addLayout(stok_grafikleri)
        deger_karti = QFrame(); deger_karti.setObjectName("panel"); dk = QVBoxLayout(deger_karti)
        dk.addWidget(QLabel(T('En Değerli 5 Ürün'))); self.cubuk_grafik = CubukGrafik(); dk.addWidget(self.cubuk_grafik)
        hareket_grafik_karti = QFrame(); hareket_grafik_karti.setObjectName("panel"); hg = QVBoxLayout(hareket_grafik_karti)
        hg.addWidget(QLabel(T('Hareket Dağılımı'))); self.hareket_grafik = CubukGrafik(); hg.addWidget(self.hareket_grafik)
        self.grafik_widgetlari=[stok_karti,deger_karti,hareket_grafik_karti]

        self.alt_yerlesim = QGridLayout(); self.alt_yerlesim.setSpacing(8)
        hareket_karti = QFrame(); hareket_karti.setObjectName("panel"); hk = QVBoxLayout(hareket_karti)
        hk.addWidget(QLabel(T('Son Stok Hareketleri'))); self.hareket_tablosu = QTableWidget(0, 3)
        self.hareket_tablosu.setHorizontalHeaderLabels([T('Tarih'), T('İşlem'), T('Miktar')]); tablo_standardi(self.hareket_tablosu, 27)
        self.hareket_tablosu.setMinimumHeight(80); hk.addWidget(self.hareket_tablosu,1)
        finans = QFrame(); finans.setObjectName("panel"); fk = QVBoxLayout(finans)
        fb = QHBoxLayout(); fb.addWidget(QLabel(T('Finans Merkezi'))); fb.addStretch(); fk.addLayout(fb)
        self.kur_bilgileri = QLabel(T('TCMB kurları yükleniyor…')); self.kur_bilgileri.setObjectName("kurBilgisi"); fk.addWidget(self.kur_bilgileri)
        self.piyasa_bilgileri=QLabel(T('ALTIN  —     GÜMÜŞ  —\nBİST ARTAN  —     BİST AZALAN  —')); self.piyasa_bilgileri.setObjectName("kurBilgisi"); self.piyasa_bilgileri.setAlignment(Qt.AlignmentFlag.AlignCenter); fk.addWidget(self.piyasa_bilgileri)
        self.finans_ozet=FinansOzetGrafik();fk.addWidget(self.finans_ozet,1)
        self.kur_durumu = QLabel(T('Resmî TCMB gösterge kurları')); self.kur_durumu.setObjectName("soluk"); fk.addWidget(self.kur_durumu)
        aktif = QFrame(); aktif.setObjectName("panel"); ad = QVBoxLayout(aktif); ad.addWidget(QLabel(T('Aktif Kullanıcılar')))
        self.aktif_kullanicilar=QLabel(T('Cloud bağlantısı bekleniyor…')); self.aktif_kullanicilar.setObjectName("soluk"); self.aktif_kullanicilar.setAlignment(Qt.AlignmentFlag.AlignTop); self.aktif_kullanicilar.setWordWrap(True)
        ad.addWidget(self.aktif_kullanicilar,1); self.alt_widgetlari=[hareket_karti,finans,aktif]
        self.panel_canvas=PanelCanvas(self);d.addWidget(self.panel_canvas,1)
        titles=[T('Ürün çeşidi'),T('Seçili konum stoğu'),T('Toplam stok değeri'),T('Kritik stok')]
        for i,(key,widget,title) in enumerate(zip(('products','stock','value','critical'),self.kart_widgetlari,titles)):
            widget.findChildren(QLabel)[0].hide()
            self.panel_canvas.add(key,title,widget,(i*402,0,394,100),(200,90))
        for key,title,widget,rect in [
            ('health',T('Stok Sağlığı'),stok_karti,(0,110,796,290)),
            ('top',T('En Değerli 5 Ürün'),deger_karti,(806,110,394,290)),
            ('movements_chart',T('Hareket Dağılımı'),hareket_grafik_karti,(1210,110,390,290)),
            ('movements',T('Son Stok Hareketleri'),hareket_karti,(0,410,636,490)),
            ('finance',T('Finans Merkezi'),finans,(646,410,636,490)),
            ('users',T('Aktif Kullanıcılar'),aktif,(1292,410,308,490))]:
            widget.findChildren(QLabel)[0].hide()
            self.panel_canvas.add(key,title,widget,rect,(180,150))
        self.hizli_yerlesim = QGridLayout(); self.hizli_yerlesim.setSpacing(8); self.hizli_dugmeler=[]
        for ad, komut in ((T('Ürün Özelleştirmeleri'), self.urun_ozellestirmeleri_ac), (T('Ürünler'), self.urun_yonetimi_ac),
                          (T('Kritik Stoklar'), self.kritikleri_ac), (T('Sipariş Önerileri'), self.siparis_onerileri_ac),
                          (T('Stok Transferi'), self.transfer_ac)):
            b = QPushButton(ad); b.clicked.connect(komut); self.hizli_dugmeler.append(b)
        d.addLayout(self.hizli_yerlesim)
        self.ara = QLineEdit()
        self.duyarli_mod = None; self.duyarli_yerlesimi_guncelle()
        QTimer.singleShot(700, self.kurlari_yenile)

    @staticmethod
    def yerlesimi_bosalt(yerlesim):
        while yerlesim.count(): yerlesim.takeAt(0)

    def resizeEvent(self, olay):
        super().resizeEvent(olay)
        self.schedule(0,self.duyarli_yerlesimi_guncelle)
        if hasattr(self,'assistant_panel'):self.assistant_panel.position_in_window()

    def duyarli_yerlesimi_guncelle(self):
        if not hasattr(self, "kaydir") or not hasattr(self, "ust_yerlesim"): return
        genislik = self.kaydir.viewport().width()
        mod = "genis" if genislik >= 1400 else "orta" if genislik >= 760 else "dar"
        if mod == self.duyarli_mod: return
        self.duyarli_mod = mod
        for yerlesim in (self.ust_yerlesim,self.hizli_yerlesim):
            self.yerlesimi_bosalt(yerlesim)
        # Clear stretches left behind by the previous window width.
        for yerlesim in (self.ust_yerlesim,self.hizli_yerlesim):
            for sutun in range(5): yerlesim.setColumnStretch(sutun,0)
        self.stok_grafikleri.setDirection(QBoxLayout.Direction.TopToBottom if mod == "dar" else QBoxLayout.Direction.LeftToRight)
        if mod == "genis":
            self.ust_yerlesim.addWidget(self.baslik,0,0); self.ust_yerlesim.addWidget(self.konum,0,1)
            self.ust_yerlesim.addWidget(self.yenile_dugmesi,0,2); self.ust_yerlesim.setColumnStretch(1,3); self.ust_yerlesim.setColumnStretch(3,1)
            self.ust_yerlesim.addWidget(self.sosyal,0,4); kart_sutun,grafik_sutun=4,3
        elif mod == "orta":
            self.ust_yerlesim.addWidget(self.baslik,0,0); self.ust_yerlesim.addWidget(self.konum,0,1)
            self.ust_yerlesim.addWidget(self.yenile_dugmesi,0,2); self.ust_yerlesim.addWidget(self.sosyal,1,0,1,3,Qt.AlignmentFlag.AlignRight)
            kart_sutun,grafik_sutun=2,2
        else:
            self.ust_yerlesim.addWidget(self.baslik,0,0,1,2); self.ust_yerlesim.addWidget(self.konum,1,0)
            self.ust_yerlesim.addWidget(self.yenile_dugmesi,1,1); self.ust_yerlesim.addWidget(self.sosyal,2,0,1,2,Qt.AlignmentFlag.AlignLeft)
            kart_sutun,grafik_sutun=2,1
        hizli_sutun=5 if mod=='genis' else 3 if mod=='orta' else 2
        for i,w in enumerate(self.hizli_dugmeler): self.hizli_yerlesim.addWidget(w,i//hizli_sutun,i%hizli_sutun)

    def konumlari_yenile(self):
        onceki = self.konum.currentData(); self.konum.blockSignals(True); self.konum.clear()
        for k in self.vt.konumlari_getir(): self.konum.addItem(f"{k['ad']} ({k['tur']})", k["id"])
        if onceki is not None:
            i = self.konum.findData(onceki)
            if i >= 0: self.konum.setCurrentIndex(i)
        self.konum.blockSignals(False)

    def yenile(self):
        self.konumlari_yenile(); self.tablo_yenile()
        self.cloud_gostergesini_yenile()

    def cloud_gostergesini_yenile(self):
        state=getattr(self,'cloud_connection_state','connected' if self.cloud_client.bagli else 'offline')
        if state=='auth_required':
            nokta,metin='#F45B76',T('Cloud giriş gerekli')
        elif state=='retry':
            nokta,metin='#FBBF24',T('Cloud bağlanıyor')
        elif self.cloud_client.bagli:
            nokta,metin='#4ADE80',T('Cloud bağlı')
        else:
            nokta,metin='#94A3B8',T('Cloud oturumu kapalı')
        self.cloud.setText(f'<span style="color:{nokta}">●</span> {metin}')

    def canli_yenile(self):
        self.refresh_company()
        self.tablo_yenile()
        if not self.cloud_client.bagli or getattr(self,'cloud_connection_state','') in ('retry','auth_required'):self.cloud_oturumunu_yenile()

    def cloud_oturumunu_yenile(self):
        if hasattr(self,"cloud_iscisi") and self.cloud_iscisi.isRunning():return
        a=ayarlari_oku(); url,key=cloud_yapilandirmasi_oku()
        if not self.cloud_client.bagli and (not url or not key):
            self.cloud_connection_state='offline';self.cloud_gostergesini_yenile();return
        try:
            if not self.cloud_client.bagli:self.cloud_client.yapilandir(url,key)
        except Exception:return
        token=""
        try:token=windows_sifre_coz(str(a.get('cloud_accounts',{}).get(str(self.kullanici['id']),{}).get('refresh_token_dpapi','')))
        except Exception:pass
        self.cloud_iscisi=CloudKontrolu(self.cloud_client,token,self);self.cloud_iscisi.tamamlandi.connect(self.cloud_sonucu);self.cloud_iscisi.hata.connect(self.cloud_hatasi);self.cloud_iscisi.start()

    def refresh_presence(self):
        if time.monotonic()-self.presence_seen>=30:self.aktif_kullanicilar.setText(T('Aktif kullanıcı bilgisi doğrulanamıyor.'))
        if not self.cloud_client.bagli:return
        if getattr(self,'presence_worker',None) is not None and self.presence_worker.isRunning():return
        self.presence_worker=PresenceWorker(self.cloud_client,self.presence_session,self.kullanici['kullanici_adi'],parent=self)
        self.presence_worker.received.connect(self.presence_result);self.presence_worker.start()

    def presence_result(self,users):
        self.presence_seen=time.monotonic()
        self.aktif_kullanicilar.setText('\n'.join(x['name'] for x in users) or T('Aktif kullanıcı yok.'))

    def cloud_tokenini_kaydet(self,cloud):
        if getattr(self,"remember_disabled",False):return
        accounts=ayarlari_oku().get('cloud_accounts',{})
        accounts[str(self.kullanici['id'])]={'user_id':cloud.user_id,'refresh_token_dpapi':windows_sifrele(cloud.refresh_token)}
        yerel_ayari_kaydet('cloud_accounts',accounts)

    def cloud_sonucu(self,cihazlar,yeni_token):
        if yeni_token:self.cloud_tokenini_kaydet(self.cloud_client)
        self.lisans_kilitli=not bool(getattr(self.cloud_client,'entitlement',{}).get('allowed'))
        self.refresh_presence();self.refresh_company()
        self.cloud_connection_state='connected'
        self.subscription_label.setText(T('Abonelik aktif değil') if self.lisans_kilitli else T('Abonelik aktif'))
        self.subscription_label.setStyleSheet('color:'+('#F45B76' if self.lisans_kilitli else '#4ADE80'))
        self.cloud_gostergesini_yenile()
        self.cloud.setToolTip('')
        status=getattr(self.cloud_client,'entitlement',{})
        remaining=SubscriptionClock(status).seconds()
        if remaining is not None and remaining<=int(self.vt.ayar_getir('notify_expiry_days','7'))*86400:
            self.notify(T('Paket süresi'),T('Paket bitişi yaklaşıyor. Kalan süreyi Paketim ve Abonelik ekranından kontrol edin.'),'notify_expiry')

    def cloud_hatasi(self,hata):
        if 'DPQ_LICENSE' in str(hata):
            self.lisans_kilitli=True;self.subscription_label.setText(T('Abonelik aktif değil'));self.subscription_label.setStyleSheet('color:#F45B76')
            self.cloud_connection_state='connected';self.cloud_gostergesini_yenile();return
        # Preserve credentials on temporary network failures. Server RPCs still authorize every operation.
        self.cloud_connection_state='retry'
        self.subscription_label.setText(T('Abonelik doğrulanamıyor'));self.subscription_label.setStyleSheet('color:#FBBF24')
        self.notify(T('Cloud bağlantısı'),T('Bağlantı geçici olarak doğrulanamadı. Yeniden denenecek.'),"notify_cloud")
        self.cloud.setToolTip(str(hata))
        if getattr(self.cloud_client,'auth_required',False) or '(401)' in str(hata):
            self.lisans_kilitli=True
            self.cloud_connection_state='auth_required'
        self.cloud_gostergesini_yenile()

    def cloud_senkron_hatasi(self,hata):
        # Local cache errors are not authentication or subscription failures.
        if getattr(self.cloud_client,'auth_required',False):
            self.cloud_hatasi(hata)
        else:self.cloud.setToolTip(T('Özetler henüz güncellenemedi: ')+str(hata))

    def cloud_senkronize(self):
        if not self.cloud_client.bagli or (hasattr(self,"senkron_iscisi") and self.senkron_iscisi.isRunning()):return
        self.senkron_iscisi=CloudSenkronIsci(self.cloud_client,self);self.senkron_iscisi.tamamlandi.connect(lambda _:self.tablo_yenile());self.senkron_iscisi.hata.connect(self.cloud_senkron_hatasi);self.senkron_iscisi.start()

    def tablo_yenile(self):
        konum = self.konum.currentData()
        if konum is None: return
        urunler = self.vt.urunleri_getir("", konum)
        ozet = self.vt.ozet_getir(konum); kritik = len(self.vt.kritik_stoklari_getir())
        for w, v in zip(self.kartlar, (ozet["urun_sayisi"], ozet["toplam_stok"], para(ozet["toplam_deger"]), kritik)):
            w.setText(str(v))
        if kritik:self.notify(T('Kritik stok'),T('{v0} ürün/konum kaydı kritik stok seviyesinde.', v0=kritik),"kritik_bildirim")
        kritik_konum = sum(1 for u in urunler if int(u["miktar"] or 0) <= int(u["kritik_stok"] or 0))
        self.halka_grafik.veri_ayarla(kritik_konum, max(0, len(urunler) - kritik_konum))
        en_degerli = sorted(((u["ad"], float(u["miktar"] or 0) * float(u["fiyat"] or 0)) for u in urunler), key=lambda x:x[1], reverse=True)[:5]
        self.cubuk_grafik.veri_ayarla(en_degerli)
        hareket_ozeti = self.vt.baglanti.execute(
            "SELECT hareket_turu,COUNT(*) adet FROM stok_hareketleri "
            "WHERE kaynak_konum_id=? OR hedef_konum_id=? GROUP BY hareket_turu ORDER BY adet DESC LIMIT 5", (konum, konum)
        ).fetchall()
        self.hareket_grafik.veri_ayarla([(T(str(h["hareket_turu"]).replace("_", " ").title()), h["adet"]) for h in hareket_ozeti])
        self.stok_sutun_grafik.veri_ayarla([(T('Kritik'),kritik_konum),(T('Sağlıklı'),max(0,len(urunler)-kritik_konum)),(T('Stok'),sum(int(u["miktar"] or 0) for u in urunler))])
        self.finans_ozet.veri_ayarla(ozet["toplam_deger"],ozet["urun_sayisi"],kritik_konum)
        hareketler = self.vt.baglanti.execute(
            "SELECT tarih_saat,hareket_turu,miktar FROM stok_hareketleri "
            "WHERE kaynak_konum_id=? OR hedef_konum_id=? ORDER BY id DESC LIMIT 9", (konum, konum)
        ).fetchall()
        self.hareket_tablosu.setRowCount(len(hareketler))
        for r, h in enumerate(hareketler):
            for c, v in enumerate((h["tarih_saat"], T(str(h["hareket_turu"]).replace("_", " ").title()), h["miktar"])):
                self.hareket_tablosu.setItem(r, c, QTableWidgetItem(v if isinstance(v,Text) else str(v)))

    def kurlari_yenile(self):
        if hasattr(self, "kur_iscisi") and self.kur_iscisi.isRunning(): return
        self.kur_bilgileri.setText(T('TCMB kurları yükleniyor…'))
        self.kur_iscisi = KurKontrolu(self)
        self.kur_iscisi.tamamlandi.connect(self.kur_sonucu)
        self.kur_iscisi.hata.connect(lambda _: self.kur_hatasi())
        self.kur_iscisi.start()

    def kur_sonucu(self, sonuc):
        satirlar = []
        for kod in ("USD", "EUR", "GBP"):
            if kod in sonuc:
                alis, satis = sonuc[kod]; satirlar.append(T('{v0}   Alış {v1:.4f}  •  Satış {v2:.4f}', v0=kod, v1=alis, v2=satis))
        self.kur_bilgileri.setText("\n".join(satirlar))
        altin=sonuc.get("ALTIN");gumus=sonuc.get("GUMUS");bist=sonuc.get("BIST")
        def piyasa_satiri(ad,deger):return f"{ad}  {deger[0]:,.2f}  ({deger[1]:+.2f}%)" if deger else f"{ad}  veri bekleniyor"
        artan=bist if bist and bist[1]>=0 else None;azalan=bist if bist and bist[1]<0 else None
        self.piyasa_bilgileri.setText(f"{piyasa_satiri('ALTIN',altin)}     {piyasa_satiri(T('GÜMÜŞ'),gumus)}\n{piyasa_satiri(T('BİST ARTAN'),artan)}     {piyasa_satiri(T('BİST AZALAN'),azalan)}")
        self.kur_durumu.setText(T('TCMB gösterge kurları • {v0}', v0=sonuc.get('tarih', 'güncel')))

    def kur_hatasi(self):
        self.kur_bilgileri.setText(T('Kur bilgisi şu anda alınamadı.'))
        self.kur_durumu.setText(T('İnternet bağlantınızı kontrol edip yeniden deneyin.'))

    def sosyal_yakinda(self, platform):
        adres = {"Instagram": "https://www.instagram.com/deporiaq/", "YouTube": "https://www.youtube.com/@DeporiaQ"}.get(platform)
        if adres: webbrowser.open(adres)

    def operasyon_ac(self, initial="search"):
        if self.kullanici["rol"] != "ANA_YONETICI" or self.lisans_kilitli:
            QMessageBox.warning(self,T('Yetki gerekli'),T('Operasyon Merkezi için aktif Ana Yönetici oturumu gerekir.'))
            return
        AnalysisWindow(self.vt,self,initial if isinstance(initial,str) else "search").exec()

    def komut_paleti_ac(self):
        self.global_search_open()

    def transfer_ac(self):
        StockDialog(self.commerce,'transfer',self).exec()

    def stok_girisi_ac(self):
        StockDialog(self.commerce,'receive',self).exec()

    def urun_yonetimi_ac(self):
        StockDialog(self.commerce,'catalog',self).exec()

    def urun_ozellestirmeleri_ac(self):
        self.urun_yonetimi_ac()

    def konum_yonetimi_ac(self):
        StockDialog(self.commerce,'catalog',self).exec()

    def satis_ac(self):
        selected=self.vt.baglanti.execute('SELECT ad FROM konumlar WHERE id=?',(self.konum.currentData(),)).fetchone()
        SaleDialog(self.commerce,selected['ad'] if selected else '',self).exec()
        self.cloud_senkronize()

    def araclar_ac(self):
        StockDialog(self.commerce,'count',self).exec()

    def ayarlar_ac(self):
        AyarlarPenceresi(self.vt,self.cloud_client,self.yenile,self).exec()

    def yardim_ac(self):
        YardimMerkezi(self.vt,self).exec()

    def guncelleme_denetle(self,sessiz=False):
        if hasattr(self,"guncelleme_isci") and self.guncelleme_isci.isRunning():return
        self.guncelleme_sessiz=sessiz;self.guncelleme_isci=GuncellemeKontrolu(self)
        self.guncelleme_isci.tamamlandi.connect(self.guncelleme_sonucu)
        self.guncelleme_isci.hata.connect(lambda h:None if self.guncelleme_sessiz else QMessageBox.warning(self,T('Güncelleme denetlenemedi'),h))
        self.guncelleme_isci.start()

    def guncelleme_sonucu(self,manifest):
        yeni=str(manifest.get("version","0"))
        if surum_parcalari(yeni)<=surum_parcalari(SURUM):
            if not self.guncelleme_sessiz:QMessageBox.information(self,T('DeporiaQ güncel'),T('En güncel sürümü kullanıyorsunuz: {v0}', v0=SURUM))
            return
        notlar=str(manifest.get("notes","")).strip();mesaj=T('DeporiaQ {v0} hazır.\n\n{v1}\n\nGüvenli güncelleme aracını şimdi açalım mı?', v0=yeni, v1=notlar[:500])
        arac=Path(sys.executable).resolve().parent/"DeporiaQUpdate.exe" if getattr(sys,"frozen",False) else Path(__file__).resolve().parent/"DeporiaQUpdate.exe"
        if not arac.exists():QMessageBox.warning(self,T('Güncelleme aracı bulunamadı'),T('DeporiaQUpdate.exe kurulum klasöründe bulunamadı.'));return
        subprocess.Popen([str(arac),"--notify"],close_fds=True,env=clean_environment())

    def yedek_al(self):
        if self.kullanici["rol"] != "ANA_YONETICI":
            QMessageBox.warning(self,T('Yetki gerekli'),T('Bu işlem için Ana Yönetici yetkisi gerekir.'));return
        varsayilan=f"DeporiaQ_Yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        yol,_=QFileDialog.getSaveFileName(self,T('Veritabanı yedeğini kaydet'),varsayilan,T('DeporiaQ Veritabanı (*.db)'))
        if not yol:return
        try:
            if Path(yol).resolve() == Path(self.vt.yol).resolve():
                raise ValueError(T('Yedek için asıl veritabanından farklı bir dosya seçin.'))
            with sqlite3.connect(yol) as hedef:
                self.vt.baglanti.backup(hedef)
                if hedef.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError(T('Yedek bütünlük kontrolünden geçemedi.'))
        except (OSError,sqlite3.Error,ValueError) as e:QMessageBox.warning(self,T('Yedek alınamadı'),str(e));return
        QMessageBox.information(self,T('Yedek tamamlandı'),T('Veritabanı yedeği kaydedildi:\n{v0}', v0=yol))

    def kullanicilar_ac(self):
        from deporiaq_positions import AuthorityDialog
        AuthorityDialog(self.retail_hub,self).exec()

    def kritikleri_ac(self):
        self.liste_dialog(T('Kritik Stoklar'), [T('Konum'), T('Barkod'), T('Ürün'), T('Mevcut'), T('Kritik')], self.vt.kritik_stoklari_getir(), ["konum","barkod","urun","miktar","kritik_stok"])

    def siparis_onerileri_ac(self):
        SiparisOnerileriPenceresi(self.vt,self).exec()

    def hareketleri_ac(self):
        satirlar = self.vt.baglanti.execute("""SELECT tarih_saat,hareket_turu,miktar,aciklama FROM stok_hareketleri ORDER BY id DESC LIMIT 250""").fetchall()
        self.liste_dialog(T('Hareket Geçmişi'), [T('Tarih'), T('Hareket'), T('Miktar'), T('Açıklama')], satirlar, ["tarih_saat","hareket_turu","miktar","aciklama"])

    def raporlar_ac(self):
        p=QDialog(self);p.setWindowTitle(T('Raporlar ve Yazdır'));p.resize(1050,680);d=QVBoxLayout(p)
        b=QLabel(T('Raporlar ve Yazdır'));b.setObjectName("sayfaBaslik");d.addWidget(b)
        sec=QHBoxLayout(); tur=QComboBox();tur.addItems([T('Genel Stok Raporu'),T('Kritik Stok Raporu'),T('Kâr Raporu'),T('Denetim Kayıtları'),T('Oturum Kayıtları')]);sec.addWidget(tur)
        t=QTableWidget();tablo_standardi(t);d.addLayout(sec);d.addWidget(t,1)
        def doldur():
            ad=tur.currentText()
            if ad==T('Genel Stok Raporu'): cols,rows,fields=[T('Barkod'),T('Ürün'),T('Stok'),T('Fiyat')],self.vt.urunleri_getir("",self.konum.currentData()),["barkod","ad","miktar","fiyat"]
            elif ad==T('Kritik Stok Raporu'): cols,rows,fields=[T('Konum'),T('Barkod'),T('Ürün'),T('Mevcut'),T('Kritik')],self.vt.kritik_stoklari_getir(),["konum","barkod","urun","miktar","kritik_stok"]
            elif ad==T('Kâr Raporu'): cols,rows,fields=[T('Tarih'),T('Ürün'),T('Miktar'),T('Ciro'),T('Brüt kâr')],self.vt.kar_raporu_getir(),["tarih_saat","urun","miktar","ciro","brut_kar"]
            elif ad==T('Denetim Kayıtları'): cols,rows,fields=[T('Tarih'),T('Kullanıcı'),T('İşlem'),T('Açıklama')],self.vt.denetim_kayitlari_getir(),["tarih_saat","kullanici","islem","aciklama"]
            else: cols,rows,fields=[T('Giriş'),T('Çıkış'),T('Kullanıcı')],self.vt.oturum_kayitlari_getir(),["giris_zamani","cikis_zamani","kullanici"]
            t.setColumnCount(len(cols));t.setHorizontalHeaderLabels(cols);t.setRowCount(len(rows));tablo_standardi(t)
            for r,x in enumerate(rows):
                for c,f in enumerate(fields):t.setItem(r,c,QTableWidgetItem(str(x[f] if x[f] is not None else "")))
        tur.currentIndexChanged.connect(doldur);doldur()
        a=QHBoxLayout(); yaz=QPushButton(T('Yazdır')); yaz.clicked.connect(lambda:self.tablo_yazdir(t,tur.currentText(),p)); csvb=QPushButton(T('CSV Dışa Aktar'));csvb.clicked.connect(lambda:self.tablo_csv(t,tur.currentText(),p));kapat=QPushButton(T('Kapat'));kapat.clicked.connect(p.accept)
        a.addWidget(yaz);a.addWidget(csvb);a.addStretch();a.addWidget(kapat);d.addLayout(a);p.exec()

    def tablo_yazdir(self,t,baslik,parent):
        html=f"<h1>{baslik}</h1><table border='1' cellspacing='0' cellpadding='5'><tr>"+"".join(f"<th>{t.horizontalHeaderItem(c).text()}</th>" for c in range(t.columnCount()))+"</tr>"
        for r in range(t.rowCount()):html+="<tr>"+"".join(f"<td>{t.item(r,c).text() if t.item(r,c) else ''}</td>" for c in range(t.columnCount()))+"</tr>"
        belge=QTextDocument();belge.setHtml(html+"</table>");yazici=QPrinter(QPrinter.PrinterMode.HighResolution);dlg=QPrintDialog(yazici,parent)
        if dlg.exec():belge.print_(yazici)

    def tablo_csv(self,t,baslik,parent):
        yol,_=QFileDialog.getSaveFileName(parent,T('Raporu kaydet'),baslik.replace(" ","_")+".csv","CSV (*.csv)")
        if not yol:return
        with open(yol,"w",newline="",encoding="utf-8-sig") as f:
            y=csv.writer(f,delimiter=";");y.writerow([t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]);y.writerows([[t.item(r,c).text() if t.item(r,c) else "" for c in range(t.columnCount())] for r in range(t.rowCount())])
        QMessageBox.information(parent,T('Dışa aktarıldı'),f"Rapor kaydedildi:\n{yol}")

    def liste_dialog(self, baslik, kolonlar, satirlar, alanlar):
        p = QDialog(self); p.setWindowTitle(baslik); p.resize(900, 600); d = QVBoxLayout(p)
        t = QTableWidget(len(satirlar), len(kolonlar)); t.setHorizontalHeaderLabels(kolonlar)
        tablo_standardi(t,36)
        for r, s in enumerate(satirlar):
            for c, a in enumerate(alanlar): t.setItem(r,c,QTableWidgetItem(str(s[a] if s[a] is not None else "")))
        d.addWidget(t); p.exec()

    def cikis_yap(self):
        self._logout_requested=True
        self.close()


STIL = """
QWidget { background:#131A26; color:#F8FAFC; font-family:'Segoe UI'; font-size:14px; }
QWidget#dashboardArkaPlan, QWidget#dashboardSosyal { background:transparent; }
HalkaGrafik, CubukGrafik, SutunGrafik, FinansOzetGrafik { background:transparent; }
QLabel { background:transparent; }
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit { background:#1E2635; border:1px solid #3B4B63; padding:8px; min-height:20px; }
QComboBox {padding-right:30px;}
QComboBox::drop-down {subcontrol-origin:padding;subcontrol-position:top right;width:28px;border:0;}
QComboBox::down-arrow {image:url(__CHEVRON__);width:12px;height:8px;}
QSpinBox::up-button,QDoubleSpinBox::up-button {subcontrol-origin:border;subcontrol-position:top right;width:24px;border:0;}
QSpinBox::down-button,QDoubleSpinBox::down-button {subcontrol-origin:border;subcontrol-position:bottom right;width:24px;border:0;}
QSpinBox::up-arrow,QDoubleSpinBox::up-arrow {image:url(__CHEVRON_UP__);width:12px;height:8px;}
QSpinBox::down-arrow,QDoubleSpinBox::down-arrow {image:url(__CHEVRON__);width:12px;height:8px;}
QTableWidget { background:#1E2635; border:1px solid #3B4B63; alternate-background-color:#293344; }
QTableWidget::item { padding:6px 8px; border:0; }
QTableWidget::item:selected { background:#2563EB; color:#FFFFFF; }
QPushButton { background:#2C3E55; border:1px solid #46617F; border-radius:5px; padding:10px 14px; font-weight:600; }
QPushButton:hover { background:#365578; } QPushButton#birincil { background:#2563EB; }
QPushButton#basari { background:#059669; } QPushButton#tehlike { background:#B91C1C; }
QPushButton#metinDugme { background:transparent; border:0; color:#94A3B8; padding:7px 2px; }
QPushButton#metinDugme:hover { color:#38BDF8; }
QFrame#ustCubuk { background:#263B53; border-bottom:1px solid #38516E; }
QFrame#altCubuk { background:#1B2A3C; border-top:1px solid #38516E; }
QFrame#yanMenu { background:#21354D; border-right:1px solid #38516E; }
QFrame#ustCubuk QLabel,QFrame#altCubuk QLabel,QFrame#yanMenu QLabel { background:transparent; border:0; }
QLabel#marka { font-size:38px; font-weight:800; color:#38BDF8; }
QLabel#markaKucuk { font-size:29px; font-weight:800; color:#FFFFFF; }
QLabel#surum { color:#8FB3D9; font-size:14px; padding-top:5px; }
QLabel#isletme { color:#FFFFFF; font-size:14px; font-weight:650; }
QLabel#profil { color:#B7C7DA; font-size:12px; }
QLabel#sayfaBaslik { font-size:24px; font-weight:750; } QLabel#soluk { color:#94A3B8; }
QLabel#cloud { color:#FFFFFF; background:#17243A; border:1px solid #31537A; border-radius:14px; padding:7px 12px; font-weight:700; }
QLabel#online { color:#FFFFFF; background:transparent; border:0; padding:7px 5px; font-weight:700; }
QLabel#durum { color:#8FA6BF; }
QFrame#kart { background:rgba(24,34,49,170); border:1px solid rgba(111,163,211,185); border-radius:10px; }
QFrame#kart QLabel { background:transparent; border:0; }
QLabel#kartBaslik { font-size:15px; font-weight:650; color:#E2E8F0; }
QLabel#kartDeger { font-size:24px; font-weight:800; color:#38BDF8; }
QFrame#panel { background:rgba(13,27,44,170); border:1px solid rgba(111,163,211,175); border-radius:10px; }
QFrame#panel QLabel { background:transparent; border:0; font-weight:650; }
QLabel#kurBilgisi { color:#E2E8F0; font-family:'Consolas'; font-size:13px; line-height:1.5; }
QHeaderView::section { background:#314C6B; padding:8px; font-weight:700; }
QScrollBar:vertical { background:#111827; width:10px; margin:3px 2px; border:0; border-radius:5px; }
QScrollBar::handle:vertical { background:#46617F; min-height:38px; border-radius:4px; }
QScrollBar::handle:vertical:hover { background:#38BDF8; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; background:transparent; border:0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:transparent; }
QScrollBar:horizontal { background:#111827; height:10px; margin:2px 3px; border:0; border-radius:5px; }
QScrollBar::handle:horizontal { background:#46617F; min-width:38px; border-radius:4px; }
QScrollBar::handle:horizontal:hover { background:#38BDF8; }
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal { width:0; background:transparent; border:0; }
QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal { background:transparent; }
"""


STIL=STIL.replace("__CHEVRON__",kaynak_yolu("chevron.svg").replace("\\","/"))

STIL=STIL.replace("__CHEVRON_UP__",kaynak_yolu("chevron_up.svg").replace("\\","/"))

def main():
    eski_veritabanini_tasi(); veritabani_butunlugunu_kurtar(); veritabani_yedegi_al()
    vt = Veritabani(VERITABANI_YOLU)
    app = QApplication(sys.argv); app.setApplicationName(PROGRAM_ADI); app.setApplicationVersion(SURUM)
    set_language(vt.ayar_getir('ui_language','tr'))
    app.setWindowIcon(QIcon(kaynak_yolu("deporiaq_icon.svg"))); app.setStyleSheet(STIL); app.setFont(QFont("Segoe UI", 10))
    if vt.ayar_getir('ui_animation','1')=='1':play_brand(kaynak_yolu('deporiaq_icon.svg'))
    if vt.ilk_kurulum_gerekli():
        kurulum = IlkKurulumPenceresi(vt)
        QTimer.singleShot(250, lambda: acknowledge_startup(SURUM) if kurulum.isVisible() else None)
        if not kurulum.exec():
            vt.kapat(); return 0
    giris = GirisPenceresi(vt); giris.show()
    QTimer.singleShot(250, lambda: acknowledge_startup(SURUM) if giris.isVisible() else None)
    sonuc = app.exec(); vt.kapat(); return sonuc


if __name__ == "__main__":
    raise SystemExit(main())
