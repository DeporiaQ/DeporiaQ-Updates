"""DeporiaQ 0.20.0 - Kompakt panel, dahili finans tarayıcısı ve sosyal merkez."""
import csv
import json
import os
import secrets
import subprocess
import sys
import shutil
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QTimer, Signal, QRectF, QUrl
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QIcon, QIntValidator,
                           QKeySequence, QPainter, QPen, QShortcut, QTextDocument)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEB_MOTORU_VAR = True
except ImportError:
    QWebEngineView = None
    WEB_MOTORU_VAR = False

from stok_programi_v2 import (
    PROGRAM_ADI, VERITABANI_YOLU, DeporiaQCloud, Veritabani, ayarlari_oku,
    eski_veritabanini_tasi, veritabani_butunlugunu_kurtar,
    parola_guclu_mu, veritabani_yedegi_al, yerel_ayari_kaydet,
)

SURUM = "0.20.0"


def kaynak_yolu(ad):
    return str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / ad)


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
            if not adres.startswith("https://"): raise ValueError("Güncelleme adresi güvenli değil.")
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
            sonuc = {"tarih": kok.attrib.get("Tarih", "")}
            for kod in ("USD", "EUR", "GBP"):
                para_birimi = kok.find(f"Currency[@CurrencyCode='{kod}']")
                if para_birimi is not None:
                    alis = para_birimi.findtext("ForexBuying", "").strip()
                    satis = para_birimi.findtext("ForexSelling", "").strip()
                    if alis and satis:
                        sonuc[kod] = (float(alis), float(satis))
            if len(sonuc) == 1:
                raise ValueError("Kur bilgisi bulunamadı.")
            self.tamamlandi.emit(sonuc)
        except Exception as hata:
            self.hata.emit(str(hata))


class HalkaGrafik(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.kritik = 0; self.saglikli = 0; self.setMinimumHeight(145)

    def veri_ayarla(self, kritik, saglikli):
        self.kritik, self.saglikli = max(0, int(kritik)), max(0, int(saglikli)); self.update()

    def paintEvent(self, olay):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        toplam = self.kritik + self.saglikli
        alan = QRectF(18, 18, min(self.width() * .48, 150), min(self.height() - 36, 150))
        kalem = QPen(QColor("#334155"), 18); kalem.setCapStyle(Qt.PenCapStyle.RoundCap); p.setPen(kalem)
        p.drawArc(alan, 0, 360 * 16)
        if toplam:
            aci = int(360 * 16 * self.saglikli / toplam)
            kalem.setColor(QColor("#10B981")); p.setPen(kalem); p.drawArc(alan, 90 * 16, -aci)
            kalem.setColor(QColor("#F59E0B")); p.setPen(kalem); p.drawArc(alan, (90 * 16) - aci, -(360 * 16 - aci))
        p.setPen(QColor("#F8FAFC")); p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(alan, Qt.AlignmentFlag.AlignCenter, str(toplam))
        x = int(alan.right() + 28); p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor("#10B981")); p.drawText(x, 68, f"● Sağlıklı: {self.saglikli}")
        p.setPen(QColor("#F59E0B")); p.drawText(x, 101, f"● Kritik: {self.kritik}")


class CubukGrafik(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.veriler = []; self.setMinimumHeight(145)

    def veri_ayarla(self, veriler):
        self.veriler = list(veriler)[:5]; self.update()

    def paintEvent(self, olay):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.veriler:
            p.setPen(QColor("#94A3B8")); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Henüz stok verisi yok")
            return
        en_buyuk = max(float(v) for _, v in self.veriler) or 1
        sol, ust, gen = 100, 4, max(50, self.width() - 120)
        for i, (ad, deger) in enumerate(self.veriler):
            y = ust + i * 27; oran = float(deger) / en_buyuk
            p.setPen(QColor("#CBD5E1")); p.drawText(QRectF(4, y, sol - 12, 22), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(ad)[:15])
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#263449")); p.drawRoundedRect(QRectF(sol, y + 3, gen, 16), 5, 5)
            p.setBrush(QColor("#38BDF8")); p.drawRoundedRect(QRectF(sol, y + 3, max(4, gen * oran), 16), 5, 5)


class FinansTarayicisi(QDialog):
    SAYFALAR = (
        ("Borsa İstanbul", "https://www.borsaistanbul.com/"),
        ("KAP", "https://www.kap.org.tr/"),
        ("Finans Haberleri", "https://www.bloomberght.com/"),
    )

    def __init__(self, parent=None, secili=0):
        super().__init__(parent); self.setWindowTitle("DeporiaQ Finans Merkezi"); self.resize(1250, 780)
        ana = QVBoxLayout(self); araclar = QHBoxLayout()
        geri = QPushButton("← Geri"); ileri = QPushButton("İleri →"); yenile = QPushButton("↻ Yenile")
        self.adres = QLineEdit(); self.adres.setReadOnly(True)
        araclar.addWidget(geri); araclar.addWidget(ileri); araclar.addWidget(yenile); araclar.addWidget(self.adres, 1)
        ana.addLayout(araclar); self.sekmeler = QTabWidget(); ana.addWidget(self.sekmeler, 1); self.gorunumler = []
        if not WEB_MOTORU_VAR:
            bilgi = QLabel("Dahili internet görüntüleyicisi bu kurulumda bulunamadı.\nSayfaları varsayılan tarayıcıda açabilirsiniz.")
            bilgi.setAlignment(Qt.AlignmentFlag.AlignCenter); ana.addWidget(bilgi)
            for ad, url in self.SAYFALAR:
                b = QPushButton(f"{ad} sayfasını aç"); b.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u))); ana.addWidget(b)
            return
        for ad, url in self.SAYFALAR:
            web = QWebEngineView(); web.setUrl(QUrl(url)); self.gorunumler.append(web); self.sekmeler.addTab(web, ad)
            web.urlChanged.connect(lambda u, w=web: self.adres.setText(u.toString()) if w is self.aktif_web() else None)
        self.sekmeler.currentChanged.connect(self.sekme_degisti); self.sekmeler.setCurrentIndex(max(0, min(secili, len(self.SAYFALAR)-1)))
        geri.clicked.connect(lambda: self.aktif_web().back() if self.aktif_web() else None)
        ileri.clicked.connect(lambda: self.aktif_web().forward() if self.aktif_web() else None)
        yenile.clicked.connect(lambda: self.aktif_web().reload() if self.aktif_web() else None); self.sekme_degisti()

    def aktif_web(self):
        return self.gorunumler[self.sekmeler.currentIndex()] if self.gorunumler and self.sekmeler.currentIndex() >= 0 else None

    def sekme_degisti(self, _=None):
        web = self.aktif_web()
        if web: self.adres.setText(web.url().toString())


def para(deger):
    return f"{float(deger):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


class GirisPenceresi(QWidget):
    def __init__(self, vt):
        super().__init__()
        self.vt = vt
        self.ana = None
        self.ayarlar = ayarlari_oku()
        self.setWindowTitle(f"{PROGRAM_ADI} {SURUM} • Giriş")
        self.setMinimumSize(440, 410)
        kutu = QVBoxLayout(self)
        kutu.setContentsMargins(55, 45, 55, 45)
        marka = QLabel("DeporiaQ")
        marka.setObjectName("marka")
        marka.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kutu.addWidget(marka)
        alt = QLabel(f"v{SURUM} • PySide6/Qt")
        alt.setObjectName("soluk")
        alt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kutu.addWidget(alt)
        kutu.addSpacing(28)
        self.kullanici = QLineEdit()
        self.kullanici.setPlaceholderText("Kullanıcı adı")
        self.kullanici.setText(str(self.ayarlar.get("hatirlanan_kullanici", "")))
        self.parola = QLineEdit()
        self.parola.setPlaceholderText("Parola")
        self.parola.setEchoMode(QLineEdit.EchoMode.Password)
        self.parola.returnPressed.connect(self.giris)
        kutu.addWidget(self.kullanici)
        kutu.addWidget(self.parola)
        secenekler = QHBoxLayout()
        self.hatirla = QCheckBox("Beni Hatırla")
        self.hatirla.setChecked(bool(self.kullanici.text()))
        self.goster = QCheckBox("Parolayı Göster")
        self.goster.toggled.connect(
            lambda acik: self.parola.setEchoMode(
                QLineEdit.EchoMode.Normal if acik else QLineEdit.EchoMode.Password
            )
        )
        secenekler.addWidget(self.hatirla); secenekler.addStretch(); secenekler.addWidget(self.goster)
        kutu.addLayout(secenekler)
        dugme = QPushButton("Giriş Yap")
        dugme.setObjectName("birincil")
        dugme.clicked.connect(self.giris)
        kutu.addWidget(dugme)
        alt_dugmeler = QHBoxLayout()
        unuttum = QPushButton("Şifremi Unuttum")
        unuttum.setObjectName("metinDugme")
        unuttum.clicked.connect(self.parola_yardimi)
        kapat = QPushButton("Programı Kapat")
        kapat.setObjectName("metinDugme")
        kapat.clicked.connect(QApplication.quit)
        alt_dugmeler.addWidget(unuttum); alt_dugmeler.addStretch(); alt_dugmeler.addWidget(kapat)
        kutu.addLayout(alt_dugmeler)
        kutu.addStretch()
        telif = QLabel("© 2026 DeporiaQ. Tüm hakları saklıdır.")
        telif.setObjectName("soluk")
        telif.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kutu.addWidget(telif)

    def giris(self):
        kayit = self.vt.kimlik_dogrula(self.kullanici.text(), self.parola.text())
        if not kayit:
            QMessageBox.warning(self, "Giriş başarısız", "Kullanıcı adı veya parola hatalı.")
            self.parola.clear()
            return
        self.vt.aktif_kullanici_id = kayit["id"]
        yerel_ayari_kaydet(
            "hatirlanan_kullanici", self.kullanici.text().strip() if self.hatirla.isChecked() else ""
        )
        self.ana = AnaPencere(self.vt, dict(kayit), self)
        self.ana.showMaximized()
        self.hide()

    def parola_yardimi(self):
        QMessageBox.information(
            self, "Parola yardımı",
            "Parolalar güvenlik nedeniyle açık biçimde saklanmaz. "
            "Parolanızı hatırlamıyorsanız 0.13.4 sürümündeki Kullanıcılar ve Güvenlik ekranından "
            "yetkili yönetici hesabıyla parolayı yenileyin."
        )


class TransferPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent)
        self.vt, self.yenile = vt, yenile
        self.setWindowTitle("Stok Transferi")
        self.setMinimumSize(590, 390)
        ana = QVBoxLayout(self)
        baslik = QLabel("Barkodlu Stok Transferi")
        baslik.setObjectName("sayfaBaslik")
        ana.addWidget(baslik)
        form = QFormLayout()
        self.kaynak = QComboBox(); self.hedef = QComboBox()
        self.barkod = QLineEdit(); self.barkod.setPlaceholderText("Barkodu okutun veya yazın")
        self.miktar = QLineEdit("1"); self.miktar.setValidator(QIntValidator(1, 1_000_000, self))
        self.bilgi = QLabel("Kaynak ve hedef seçerek barkodu girin.")
        self.bilgi.setObjectName("soluk")
        form.addRow("Kaynak:", self.kaynak); form.addRow("Hedef:", self.hedef)
        form.addRow("Barkod:", self.barkod); form.addRow("Miktar:", self.miktar)
        ana.addLayout(form); ana.addWidget(self.bilgi)
        aktar = QPushButton("Transferi Tamamla")
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
            f"{urun['ad']} • Kaynak stok: {urun['miktar']}" if urun else "Ürün kaynak konumda bulunamadı."
        )

    def aktar(self):
        urun = self.vt.barkodla_urun_bul(self.barkod.text().strip(), self.kaynak.currentData())
        if not urun or self.hedef.currentData() is None:
            QMessageBox.warning(self, "Eksik bilgi", "Geçerli barkod, kaynak ve hedef seçin.")
            return
        try:
            kaynak, hedef = self.vt.stok_transferi(
                urun["id"], self.kaynak.currentData(), self.hedef.currentData(), pozitif_sayi_al(self.miktar)
            )
            self.vt.denetim_ekle(
                "STOK_TRANSFERI", f"{kaynak} → {hedef} • {urun['ad']} • {pozitif_sayi_al(self.miktar)} adet"
            )
        except ValueError as hata:
            QMessageBox.warning(self, "Transfer yapılamadı", str(hata)); return
        QMessageBox.information(self, "Transfer tamamlandı", f"{kaynak} → {hedef} aktarımı kaydedildi.")
        self.barkod.clear(); self.miktar.setText("1"); self.yenile()


class StokGirisPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent); self.vt, self.yenile = vt, yenile
        self.setWindowTitle("Barkodla Stok Girişi"); self.setMinimumWidth(540)
        d = QVBoxLayout(self); b = QLabel("Merkez Depoya Stok Girişi"); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        form = QFormLayout(); self.barkod = QLineEdit(); self.miktar = QLineEdit("1"); self.miktar.setValidator(QIntValidator(1,1_000_000,self))
        self.bilgi = QLabel("Barkodu okutun."); self.bilgi.setObjectName("soluk")
        form.addRow("Barkod:",self.barkod); form.addRow("Miktar:",self.miktar); d.addLayout(form); d.addWidget(self.bilgi)
        self.barkod.returnPressed.connect(self.bul)
        kaydet=QPushButton("Stoğa Ekle"); kaydet.setObjectName("basari"); kaydet.clicked.connect(self.ekle); d.addWidget(kaydet)
    def bul(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip())
        self.bilgi.setText(f"{u['ad']} • Mevcut: {u['miktar']}" if u else "Ürün bulunamadı.")
    def ekle(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip())
        if not u: QMessageBox.warning(self,"Ürün bulunamadı","Önce geçerli bir barkod girin."); return
        miktar=pozitif_sayi_al(self.miktar)
        if not miktar: QMessageBox.warning(self,"Geçersiz miktar","Miktar en az 1 olmalıdır."); return
        self.vt.merkeze_stok_girisi(u["id"],miktar)
        self.vt.denetim_ekle("STOK_GIRISI",f"{u['ad']} • Merkez Depo • {miktar} adet")
        QMessageBox.information(self,"Stok güncellendi",f"{u['ad']} ürününe {miktar} adet eklendi.")
        self.barkod.clear(); self.miktar.setText("1"); self.yenile()


class UrunYonetimiPenceresi(QDialog):
    def __init__(self,vt,yenile,parent=None):
        super().__init__(parent); self.vt,self.yenile_ana=vt,yenile; self.setWindowTitle("Ürün Yönetimi"); self.resize(1000,650)
        d=QVBoxLayout(self); b=QLabel("Ürün Yönetimi"); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels(["ID","Barkod","Ürün","Satış","Alış","Kritik"]); tablo_standardi(self.t,36); d.addWidget(self.t)
        a=QHBoxLayout()
        for ad,fn,stil in (("Yeni Ürün",self.ekle,"basari"),("Fiyat Güncelle",self.fiyat,""),("Ürünü Kaldır",self.sil,"tehlike")):
            q=QPushButton(ad); q.setObjectName(stil); q.clicked.connect(fn); a.addWidget(q)
        a.addStretch(); d.addLayout(a); self.yenile()
    def yenile(self):
        rows=self.vt.tum_aktif_urunleri_getir(); self.t.setRowCount(len(rows))
        for r,u in enumerate(rows):
            for c,v in enumerate((u['id'],u['barkod'],u['ad'],para(u['fiyat']),para(u['alis_fiyati']),u['kritik_stok'])): self.t.setItem(r,c,QTableWidgetItem(str(v)))
        self.yenile_ana()
    def secili_id(self):
        r=self.t.currentRow()
        if r<0: QMessageBox.warning(self,"Seçim gerekli","Önce bir ürün seçin."); return None
        return int(self.t.item(r,0).text())
    def ekle(self):
        p=QDialog(self); p.setWindowTitle("Yeni Ürün"); f=QFormLayout(p)
        barkod=QLineEdit(); ad=QLineEdit(); fiyat=QDoubleSpinBox(); fiyat.setMaximum(10_000_000); fiyat.setDecimals(2)
        alis=QDoubleSpinBox(); alis.setMaximum(10_000_000); alis.setDecimals(2); kritik=QSpinBox(); kritik.setMaximum(1_000_000)
        for x,w in (("Barkod:",barkod),("Ürün adı:",ad),("Satış fiyatı:",fiyat),("Alış fiyatı:",alis),("Kritik stok:",kritik)): f.addRow(x,w)
        ok=QPushButton("Ürünü Kaydet"); ok.setObjectName("basari"); f.addRow(ok); ok.clicked.connect(p.accept)
        if not p.exec(): return
        try: self.vt.urun_ekle(barkod.text(),ad.text(),fiyat.value(),alis.value(),kritik.value())
        except ValueError as e: QMessageBox.warning(self,"Kaydedilemedi",str(e)); return
        self.yenile()
    def fiyat(self):
        uid=self.secili_id()
        if uid is None:return
        deger,ok=QInputDialog.getDouble(self,"Fiyat Güncelle","Yeni satış fiyatı:",0,0.01,10_000_000,2)
        if ok:self.vt.urun_fiyati_guncelle(uid,deger);self.yenile()
    def sil(self):
        uid=self.secili_id()
        if uid is None:return
        if QMessageBox.question(self,"Ürünü kaldır","Seçili ürünü kaldırmak istiyor musunuz?")!=QMessageBox.StandardButton.Yes:return
        try:self.vt.urunu_pasiflestir(uid)
        except ValueError as e:QMessageBox.warning(self,"Kaldırılamadı",str(e));return
        self.yenile()


class KonumYonetimiPenceresi(QDialog):
    def __init__(self,vt,yenile,parent=None):
        super().__init__(parent);self.vt,self.yenile_ana=vt,yenile;self.setWindowTitle("Depo ve Şubeler");self.resize(760,520)
        d=QVBoxLayout(self);b=QLabel("Depo ve Şube Yönetimi");b.setObjectName("sayfaBaslik");d.addWidget(b)
        self.t=QTableWidget(0,3);self.t.setHorizontalHeaderLabels(["ID","Konum","Tür"]);tablo_standardi(self.t);d.addWidget(self.t)
        a=QHBoxLayout()
        for ad,fn,stil in (("Yeni Depo",lambda:self.ekle("DEPO"),""),("Yeni Şube",lambda:self.ekle("SUBE"),"basari"),("Adını Güncelle",self.guncelle,""),("Kaldır",self.sil,"tehlike")):
            q=QPushButton(ad);q.setObjectName(stil);q.clicked.connect(fn);a.addWidget(q)
        d.addLayout(a);self.yenile()
    def yenile(self):
        rows=self.vt.konumlari_getir();self.t.setRowCount(len(rows))
        for r,k in enumerate(rows):
            for c,v in enumerate((k['id'],k['ad'],k['tur'])):self.t.setItem(r,c,QTableWidgetItem(str(v)))
        self.yenile_ana()
    def secili(self):
        r=self.t.currentRow();return int(self.t.item(r,0).text()) if r>=0 else None
    def ekle(self,tur):
        ad,ok=QInputDialog.getText(self,"Yeni konum",("Depo" if tur=="DEPO" else "Şube")+" adı:")
        if not ok:return
        try:self.vt.konum_ekle(ad,tur)
        except ValueError as e:QMessageBox.warning(self,"Eklenemedi",str(e));return
        self.yenile()
    def guncelle(self):
        kid=self.secili()
        if kid is None:return
        ad,ok=QInputDialog.getText(self,"Konum adı","Yeni ad:")
        if ok:
            try:self.vt.konum_guncelle(kid,ad)
            except ValueError as e:QMessageBox.warning(self,"Güncellenemedi",str(e));return
            self.yenile()
    def sil(self):
        kid=self.secili()
        if kid is None:return
        try:self.vt.konumu_pasiflestir(kid)
        except ValueError as e:QMessageBox.warning(self,"Kaldırılamadı",str(e));return
        self.yenile()


class KullaniciYonetimiPenceresi(QDialog):
    ROLLER={"Ana Yönetici":"ANA_YONETICI","Depo Personeli":"DEPO_PERSONELI","Şube Personeli":"SUBE_PERSONELI","Görüntüleyici":"GORUNTULEYICI"}
    def __init__(self,vt,aktif,parent=None):
        super().__init__(parent);self.vt,self.aktif=vt,aktif;self.setWindowTitle("Kullanıcı ve Yetki Yönetimi");self.resize(950,600)
        d=QVBoxLayout(self);b=QLabel("Kullanıcı ve Yetki Yönetimi");b.setObjectName("sayfaBaslik");d.addWidget(b)
        self.t=QTableWidget(0,6);self.t.setHorizontalHeaderLabels(["ID","Kullanıcı","Rol","Konum","Durum","Konum ID"]);tablo_standardi(self.t);d.addWidget(self.t)
        a=QHBoxLayout()
        for ad,fn,stil in (("Kullanıcı Oluştur",self.ekle,"basari"),("Aktif/Pasif Yap",self.durum,""),("Parolayı Yenile",self.parola,""),("Kullanıcıyı Kaldır",self.sil,"tehlike")):
            q=QPushButton(ad);q.setObjectName(stil);q.clicked.connect(fn);a.addWidget(q)
        d.addLayout(a);self.yenile()
    def yenile(self):
        rows=self.vt.kullanicilari_getir();self.t.setRowCount(len(rows))
        adlar={v:k for k,v in self.ROLLER.items()}
        for r,k in enumerate(rows):
            vals=(k['id'],k['kullanici_adi'],adlar.get(k['rol'],k['rol']),k['konum_adi'],"Aktif" if k['aktif'] else "Pasif",k['konum_id'] if k['konum_id'] is not None else "")
            for c,v in enumerate(vals):self.t.setItem(r,c,QTableWidgetItem(str(v)))
        self.t.setColumnHidden(5,True)
    def secili(self):
        r=self.t.currentRow()
        if r<0:QMessageBox.warning(self,"Seçim gerekli","Önce bir kullanıcı seçin.");return None
        return r,int(self.t.item(r,0).text())
    def onay(self):
        pw,ok=QInputDialog.getText(self,"Yönetici onayı","Mevcut yönetici parolanız:",QLineEdit.EchoMode.Password)
        return bool(ok and self.vt.kimlik_dogrula(self.aktif['kullanici_adi'],pw))
    def ekle(self):
        p=QDialog(self);p.setWindowTitle("Yeni Kullanıcı");f=QFormLayout(p)
        ad=QLineEdit();pw=QLineEdit();pw.setEchoMode(QLineEdit.EchoMode.Password);rol=QComboBox();rol.addItems(self.ROLLER);kon=QComboBox();kon.addItem("Atanmamış",None)
        for k in self.vt.konumlari_getir():kon.addItem(f"{k['ad']} ({k['tur']})",k['id'])
        f.addRow("Kullanıcı adı:",ad);f.addRow("Geçici parola:",pw);f.addRow("Rol:",rol);f.addRow("Konum:",kon)
        okb=QPushButton("Kullanıcıyı Kaydet");okb.setObjectName("basari");okb.clicked.connect(p.accept);f.addRow(okb)
        if not p.exec():return
        guclu,hata=parola_guclu_mu(pw.text())
        if not guclu:QMessageBox.warning(self,"Zayıf parola",hata);return
        if not self.onay():QMessageBox.warning(self,"Onay başarısız","Yönetici parolası doğrulanamadı.");return
        try:self.vt.kullanici_ekle(ad.text().strip(),pw.text(),self.ROLLER[rol.currentText()],kon.currentData())
        except ValueError as e:QMessageBox.warning(self,"Eklenemedi",str(e));return
        self.yenile()
    def durum(self):
        sec=self.secili()
        if not sec or not self.onay():return
        r,uid=sec
        if uid==self.aktif['id']:QMessageBox.warning(self,"İşlem engellendi","Kendi aktif hesabınızı kapatamazsınız.");return
        self.vt.kullanici_durumunu_degistir(uid,self.t.item(r,4).text()!="Aktif");self.yenile()
    def parola(self):
        sec=self.secili()
        if not sec:return
        pw,ok=QInputDialog.getText(self,"Parolayı yenile","Yeni güçlü parola:",QLineEdit.EchoMode.Password)
        if not ok:return
        guclu,hata=parola_guclu_mu(pw)
        if not guclu:QMessageBox.warning(self,"Zayıf parola",hata);return
        if not self.onay():return
        self.vt.kullanici_parolasi_degistir(sec[1],pw);QMessageBox.information(self,"Tamamlandı","Kullanıcı parolası yenilendi.")
    def sil(self):
        sec=self.secili()
        if not sec or not self.onay():return
        try:self.vt.kullanici_sil(sec[1])
        except ValueError as e:QMessageBox.warning(self,"Kaldırılamadı",str(e));return
        self.yenile()


class SubeSatisPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent); self.vt,self.yenile=vt,yenile
        self.setWindowTitle("Şubede Satış"); self.setMinimumWidth(560)
        d=QVBoxLayout(self); b=QLabel("Barkodlu Şube Satışı"); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        f=QFormLayout(); self.sube=QComboBox()
        for k in vt.konumlari_getir():
            if k["tur"]=="SUBE": self.sube.addItem(k["ad"],k["id"])
        self.barkod=QLineEdit(); self.barkod.setPlaceholderText("Barkodu okutun")
        self.miktar=QLineEdit("1"); self.miktar.setValidator(QIntValidator(1,1_000_000,self))
        self.bilgi=QLabel("Ürün bilgisi barkod okutulduğunda görünür."); self.bilgi.setObjectName("soluk")
        f.addRow("Şube:",self.sube); f.addRow("Barkod:",self.barkod); f.addRow("Miktar:",self.miktar)
        d.addLayout(f); d.addWidget(self.bilgi)
        self.barkod.returnPressed.connect(self.bul)
        q=QPushButton("Satışı Tamamla"); q.setObjectName("basari"); q.clicked.connect(self.sat); d.addWidget(q)
    def bul(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip(),self.sube.currentData())
        self.bilgi.setText(f"{u['ad']} • Stok: {u['miktar']} • {para(u['fiyat'])}" if u else "Ürün bu şubede bulunamadı.")
    def sat(self):
        u=self.vt.barkodla_urun_bul(self.barkod.text().strip(),self.sube.currentData()); m=pozitif_sayi_al(self.miktar)
        if not u or not m: QMessageBox.warning(self,"Eksik bilgi","Geçerli barkod ve miktar girin."); return
        try: ad,sube,fiyat,toplam=self.vt.subede_satis_yap(u["id"],self.sube.currentData(),m)
        except ValueError as e: QMessageBox.warning(self,"Satış yapılamadı",str(e)); return
        QMessageBox.information(self,"Satış tamamlandı",f"{sube}\n{ad} • {m} adet\nToplam: {para(toplam)}")
        self.barkod.clear(); self.miktar.setText("1"); self.yenile()


class AraclarPenceresi(QDialog):
    def __init__(self, vt, yenile, parent=None):
        super().__init__(parent); self.vt,self.yenile=vt,yenile
        self.setWindowTitle("Profesyonel Araçlar"); self.resize(760,500)
        d=QVBoxLayout(self); b=QLabel("Profesyonel Araçlar"); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        sek=QTabWidget(); d.addWidget(sek)
        katalog=QWidget(); k=QFormLayout(katalog); self.kategori=QLineEdit(); self.tedarikci=QLineEdit(); self.tel=QLineEdit(); self.eposta=QLineEdit()
        kb=QPushButton("Kategori Ekle"); kb.clicked.connect(self.kategori_ekle); tb=QPushButton("Tedarikçi Ekle"); tb.clicked.connect(self.tedarikci_ekle)
        k.addRow("Yeni kategori:",self.kategori); k.addRow(kb); k.addRow("Tedarikçi:",self.tedarikci); k.addRow("Telefon:",self.tel); k.addRow("E-posta:",self.eposta); k.addRow(tb)
        sek.addTab(katalog,"Katalog")
        sayim=QWidget(); s=QFormLayout(sayim); self.konum=QComboBox(); self.urun=QComboBox(); self.sayim=QLineEdit(); self.sayim.setValidator(QIntValidator(0,1_000_000,self)); self.not_alan=QLineEdit()
        for x in vt.konumlari_getir(): self.konum.addItem(x["ad"],x["id"])
        for x in vt.tum_aktif_urunleri_getir(): self.urun.addItem(f"{x['barkod']} • {x['ad']}",x["id"])
        sb=QPushButton("Sayım Sonucunu Uygula"); sb.setObjectName("basari"); sb.clicked.connect(self.sayim_uygula)
        s.addRow("Konum:",self.konum); s.addRow("Ürün:",self.urun); s.addRow("Fiziksel miktar:",self.sayim); s.addRow("Açıklama:",self.not_alan); s.addRow(sb)
        sek.addTab(sayim,"Stok Sayımı")
    def kategori_ekle(self):
        try:self.vt.kategori_ekle(self.kategori.text());self.kategori.clear();QMessageBox.information(self,"Tamamlandı","Kategori eklendi.")
        except ValueError as e:QMessageBox.warning(self,"Eklenemedi",str(e))
    def tedarikci_ekle(self):
        try:self.vt.tedarikci_ekle(self.tedarikci.text(),self.tel.text(),self.eposta.text());QMessageBox.information(self,"Tamamlandı","Tedarikçi eklendi.")
        except ValueError as e:QMessageBox.warning(self,"Eklenemedi",str(e))
    def sayim_uygula(self):
        try:onceki,fark=self.vt.stok_sayim_duzelt(self.urun.currentData(),self.konum.currentData(),int(self.sayim.text() or 0),self.not_alan.text())
        except ValueError as e:QMessageBox.warning(self,"Uygulanamadı",str(e));return
        self.yenile();QMessageBox.information(self,"Sayım uygulandı",f"Önceki: {onceki} • Fark: {fark:+d}")


class AyarlarPenceresi(QDialog):
    def __init__(self, vt, cloud, cloud_yenile, parent=None):
        super().__init__(parent); self.vt,self.cloud,self.cloud_yenile=vt,cloud,cloud_yenile
        self.setWindowTitle("Ayarlar Merkezi"); self.resize(820,540)
        d=QVBoxLayout(self); b=QLabel("Ayarlar Merkezi"); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        sek=QTabWidget(); d.addWidget(sek)
        genel=QWidget(); g=QFormLayout(genel); self.isletme=QLineEdit(vt.ayar_getir("isletme_adi","")); gb=QPushButton("İşletme Bilgisini Kaydet"); gb.clicked.connect(self.genel_kaydet); g.addRow("İşletme adı:",self.isletme); g.addRow(gb); sek.addTab(genel,"Genel")
        bulut=QWidget(); c=QFormLayout(bulut); a=ayarlari_oku(); self.url=QLineEdit(a.get("cloud_url","")); self.key=QLineEdit(a.get("cloud_publishable_key","")); self.key.setEchoMode(QLineEdit.EchoMode.Password); self.email=QLineEdit(a.get("cloud_email","")); self.pw=QLineEdit(); self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        cb=QPushButton("Cloud Giriş ve Senkronizasyon"); cb.setObjectName("birincil"); cb.clicked.connect(self.cloud_giris)
        c.addRow("Project URL:",self.url); c.addRow("Publishable / anon key:",self.key); c.addRow("Cloud e-posta:",self.email); c.addRow("Cloud parola:",self.pw); c.addRow(cb); sek.addTab(bulut,"Cloud ve Senkronizasyon")
        guv=QWidget(); q=QFormLayout(guv); self.kilit=QComboBox(); self.kilit.addItems(["0","5","10","15","30","60"]); self.kilit.setCurrentText(vt.ayar_getir("otomatik_kilit_dakika","30")); qb=QPushButton("Güvenlik Ayarını Kaydet"); qb.clicked.connect(self.guvenlik_kaydet); q.addRow("Otomatik kilit (dakika):",self.kilit);q.addRow(qb);sek.addTab(guv,"Güvenlik")
        bild=QWidget(); n=QFormLayout(bild); self.kritik=QCheckBox("Kritik stok uyarılarını göster"); self.kritik.setChecked(vt.ayar_getir("kritik_bildirim","1")=="1"); nb=QPushButton("Bildirim Ayarını Kaydet"); nb.clicked.connect(self.bildirim_kaydet); n.addRow(self.kritik);n.addRow(nb);sek.addTab(bild,"Bildirimler")
    def genel_kaydet(self):self.vt.ayar_kaydet("isletme_adi",self.isletme.text().strip());self.vt.baglanti.commit();QMessageBox.information(self,"Kaydedildi","İşletme bilgisi kaydedildi.")
    def guvenlik_kaydet(self):self.vt.ayar_kaydet("otomatik_kilit_dakika",self.kilit.currentText());self.vt.baglanti.commit();QMessageBox.information(self,"Kaydedildi","Güvenlik ayarı kaydedildi.")
    def bildirim_kaydet(self):self.vt.ayar_kaydet("kritik_bildirim","1" if self.kritik.isChecked() else "0");self.vt.baglanti.commit();QMessageBox.information(self,"Kaydedildi","Bildirim ayarı kaydedildi.")
    def cloud_giris(self):
        try:
            self.cloud.yapilandir(self.url.text(),self.key.text()); ad=self.cloud.giris_yap(self.email.text(),self.pw.text()); sonuc,_=self.cloud.akilli_senkronize()
            yerel_ayari_kaydet("cloud_url",self.url.text().strip());yerel_ayari_kaydet("cloud_publishable_key",self.key.text().strip());yerel_ayari_kaydet("cloud_email",self.email.text().strip())
            self.vt.ayar_kaydet("cloud_etkin","1");self.vt.baglanti.commit();self.cloud_yenile();QMessageBox.information(self,"Cloud bağlı",f"{ad}\nSenkronizasyon: {sonuc}")
        except Exception as e:QMessageBox.warning(self,"Cloud bağlantısı kurulamadı",str(e))


class YardimMerkezi(QDialog):
    KONULAR={
        "Hızlı Başlangıç":"""DeporiaQ'ya Hoş Geldiniz\n\n1. Ürün Yönetimi'nden ürün kartlarını oluşturun.\n2. Stok Girişi ile merkez depoya mal kabul edin.\n3. Depo ve Şubeler bölümünden çalışma noktalarını yönetin.\n4. Stok Transferi ile ürünleri konumlar arasında aktarın.\n5. Gösterge Paneli ve raporlardan işletmenizi takip edin.\n\nBarkod alanına tıklayıp USB okuyucu veya el terminaliyle barkodu okutabilirsiniz.""",
        "Stok İşlemleri":"""STOK GİRİŞİ\nMerkez depoya gelen ürünün barkodunu okutun ve miktarı girin.\n\nTRANSFER\nKaynak ve hedef konumu seçin. Ürün ve miktar doğrulandıktan sonra işlem hareket geçmişine kaydedilir.\n\nŞUBEDE SATIŞ\nSatış yapılan şubeyi seçin, barkodu okutun ve miktarı girin. Stok otomatik düşer ve ciro/kâr raporuna işlenir.\n\nSTOK SAYIMI\nProfesyonel Araçlar > Stok Sayımı ile sistem miktarını fiziksel sayımla eşitleyin.""",
        "Cloud ve Kullanıcılar":"""Cloud hesabı, yerel kullanıcı hesabından ayrıdır.\n\nCloud e-posta/parolası işletmenin bulut verilerine erişir. Yerel Kullanıcılar ekranındaki hesaplar ise bu bilgisayarda programa giriş ve yetki kontrolü içindir.\n\nAyarlar > Cloud ve Senkronizasyon bölümünden giriş yapabilirsiniz. Parola açık biçimde kaydedilmez. Durum göstergesindeki yeşil nokta verilerin güncel olduğunu belirtir.""",
        "Raporlar ve Yazdır":"""Raporlar ve Yazdır bölümünde genel stok, kritik stok, kâr, denetim ve oturum kayıtları bulunur.\n\nYazdır düğmesi Windows yazıcı ekranını açar. CSV Dışa Aktar seçeneği raporu Excel ile açılabilecek biçimde kaydeder.\n\nSipariş Önerileri, kritik seviyedeki ürünler için hedef stoğu kritik seviyenin iki katına tamamlayacak öneri üretir.""",
        "Kısayollar":"""F5 — Ekranı ve stokları yenile\nCtrl+T — Stok Transferi ekranını aç\nEnter — Barkod alanlarında ürünü sorgula veya sonraki adıma geç\nEsc — Açık pencereyi kapat""",
        "Sorun Giderme":"""ÜRÜN BULUNAMADI\nDoğru konumun seçili olduğunu ve ürünün o konumda stok kaydı bulunduğunu kontrol edin.\n\nCLOUD BAĞLI DEĞİL\nİnternet bağlantısını, Project URL'yi ve publishable/anon anahtarını kontrol edin. Cloud parolası güvenlik nedeniyle her zaman ekranda tutulmaz.\n\nGÜNCELLEME GELMİYOR\nAyarlar dosyasındaki manifest adresini, internet bağlantısını ve DeporiaQUpdate.exe dosyasının kurulum klasöründe bulunduğunu kontrol edin.\n\nVERİ SORUNU\nÖnce Veri ve Yedekleme ile yedek alın. Ardından VERITABANI_ONAR aracını kullanın.""",
    }
    def __init__(self,vt,parent=None):
        super().__init__(parent);self.vt=vt;self.setWindowTitle("DeporiaQ Yardım Merkezi");self.resize(900,650)
        d=QVBoxLayout(self);b=QLabel("Yardım Merkezi");b.setObjectName("sayfaBaslik");d.addWidget(b)
        alt=QLabel(f"DeporiaQ {SURUM} • Kullanım rehberi, sorun giderme ve destek");alt.setObjectName("soluk");d.addWidget(alt)
        sek=QTabWidget();d.addWidget(sek,1)
        for ad,metin in self.KONULAR.items():
            alan=QPlainTextEdit(metin);alan.setReadOnly(True);sek.addTab(alan,ad)
        destek=QWidget();f=QFormLayout(destek);self.tur=QComboBox();self.tur.addItems(["Teknik Sorun","Kullanım Sorusu","Öneri","Cloud Sorunu"]);self.konu=QLineEdit();self.mesaj=QPlainTextEdit();self.iletisim=QLineEdit()
        g=QPushButton("Destek Kaydı Oluştur");g.setObjectName("birincil");g.clicked.connect(self.gonder)
        f.addRow("Talep türü:",self.tur);f.addRow("Konu:",self.konu);f.addRow("Açıklama:",self.mesaj);f.addRow("İletişim:",self.iletisim);f.addRow(g);sek.addTab(destek,"Destek")
        a=QHBoxLayout();surum=QLabel(f"Sürüm {SURUM} • © 2026 DeporiaQ");surum.setObjectName("soluk");k=QPushButton("Kapat");k.clicked.connect(self.accept);a.addWidget(surum);a.addStretch();a.addWidget(k);d.addLayout(a)
    def gonder(self):
        try:no=self.vt.destek_talebi_olustur(self.tur.currentText(),self.konu.text(),self.mesaj.toPlainText(),self.iletisim.text())
        except ValueError as e:QMessageBox.warning(self,"Eksik bilgi",str(e));return
        QMessageBox.information(self,"Destek kaydı oluşturuldu",f"Takip numaranız: {no}\nKayıt bu bilgisayarda güvenle saklandı.");self.konu.clear();self.mesaj.clear()


class SiparisOnerileriPenceresi(QDialog):
    def __init__(self, vt, parent=None):
        super().__init__(parent); self.vt=vt
        self.setWindowTitle("Akıllı Sipariş Önerileri"); self.resize(980,620)
        d=QVBoxLayout(self); b=QLabel("Akıllı Sipariş Önerileri"); b.setObjectName("sayfaBaslik"); d.addWidget(b)
        aciklama=QLabel("Kritik ürünler için hedef stok, kritik seviyenin iki katı olarak hesaplanır."); aciklama.setObjectName("soluk"); d.addWidget(aciklama)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels(["Konum","Barkod","Ürün","Mevcut","Hedef","Önerilen Sipariş"]); tablo_standardi(self.t,36); d.addWidget(self.t,1)
        a=QHBoxLayout(); yenile=QPushButton("Listeyi Yenile"); yenile.clicked.connect(self.yenile); aktar=QPushButton("CSV Dışa Aktar"); aktar.setObjectName("birincil"); aktar.clicked.connect(self.csv_aktar); kapat=QPushButton("Kapat"); kapat.clicked.connect(self.accept)
        a.addWidget(yenile); a.addWidget(aktar); a.addStretch(); a.addWidget(kapat); d.addLayout(a); self.yenile()
    def yenile(self):
        self.satirlar=[]
        for x in self.vt.kritik_stoklari_getir():
            mevcut=int(x["miktar"] or 0); kritik=int(x["kritik_stok"] or 0); hedef=max(kritik*2,1); onerilen=max(hedef-mevcut,1)
            self.satirlar.append((x["konum"],x["barkod"],x["urun"],mevcut,hedef,onerilen))
        self.t.setRowCount(len(self.satirlar))
        for r,satir in enumerate(self.satirlar):
            for c,v in enumerate(satir):self.t.setItem(r,c,QTableWidgetItem(str(v)))
    def csv_aktar(self):
        yol,_=QFileDialog.getSaveFileName(self,"Sipariş önerilerini kaydet","DeporiaQ_Siparis_Onerileri.csv","CSV (*.csv)")
        if not yol:return
        with open(yol,"w",newline="",encoding="utf-8-sig") as f:
            y=csv.writer(f,delimiter=";");y.writerow(["Konum","Barkod","Ürün","Mevcut","Hedef","Önerilen Sipariş"]);y.writerows(self.satirlar)
        QMessageBox.information(self,"Dışa aktarıldı",f"Sipariş önerileri kaydedildi:\n{yol}")


class AnaPencere(QMainWindow):
    def __init__(self, vt, kullanici, giris):
        super().__init__()
        self.vt, self.kullanici, self.giris = vt, kullanici, giris
        ayarlar=ayarlari_oku(); cihaz=str(ayarlar.get("cihaz_kimligi","")).strip()
        if not cihaz:
            cihaz="DPQ-"+secrets.token_hex(6).upper(); yerel_ayari_kaydet("cihaz_kimligi",cihaz)
        self.cloud_client=DeporiaQCloud(vt,cihaz)
        self.setWindowTitle(f"{PROGRAM_ADI} {SURUM}")
        self.setMinimumSize(900, 650)
        govde = QWidget(); self.setCentralWidget(govde)
        ana = QVBoxLayout(govde); ana.setContentsMargins(0, 0, 0, 0); ana.setSpacing(0)
        ana.addWidget(self.ust_cubuk())
        orta = QHBoxLayout(); orta.setContentsMargins(0, 0, 0, 0); orta.setSpacing(0)
        orta.addWidget(self.yan_menu())
        kaydir = QScrollArea(); kaydir.setWidgetResizable(True)
        self.icerik = QWidget(); self.icerik.setMinimumWidth(720)
        kaydir.setWidget(self.icerik); orta.addWidget(kaydir, 1)
        ana.addLayout(orta, 1)
        ana.addWidget(self.alt_cubuk())
        self.dashboard_kur()
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.transfer_ac)
        QShortcut(QKeySequence("F5"), self, activated=self.yenile)
        QTimer.singleShot(50, self.yenile)
        QTimer.singleShot(4000, lambda:self.guncelleme_denetle(True))

    def ust_cubuk(self):
        cubuk = QFrame(); cubuk.setObjectName("ustCubuk")
        d = QHBoxLayout(cubuk); d.setContentsMargins(24, 12, 24, 12); d.setSpacing(10)
        marka = QLabel("DeporiaQ"); marka.setObjectName("markaKucuk")
        surum = QLabel(f"v{SURUM}"); surum.setObjectName("surum")
        d.addWidget(marka); d.addWidget(surum); d.addSpacing(18)
        profil = QVBoxLayout(); profil.setSpacing(1)
        isletme = QLabel(self.vt.ayar_getir("isletme_adi", "DeporiaQ İşletmesi")); isletme.setObjectName("isletme")
        roller = {"ANA_YONETICI":"Ana Yönetici","DEPO_PERSONELI":"Depo Personeli","SUBE_PERSONELI":"Şube Personeli","GORUNTULEYICI":"Görüntüleyici"}
        kullanici = QLabel(f"{self.kullanici['kullanici_adi']}  •  {roller.get(self.kullanici['rol'], self.kullanici['rol'])}")
        kullanici.setObjectName("profil")
        profil.addWidget(isletme); profil.addWidget(kullanici); d.addLayout(profil)
        d.addStretch()
        self.cloud = QLabel('<span style="color:#94A3B8">●</span> <span style="color:#FFFFFF">Yerel çalışma</span>')
        self.cloud.setObjectName("cloud")
        d.addWidget(self.cloud)
        return cubuk

    def yan_menu(self):
        menu = QFrame(); menu.setObjectName("yanMenu"); menu.setFixedWidth(190)
        d = QVBoxLayout(menu); d.setContentsMargins(10, 14, 10, 12); d.setSpacing(5)
        d.addWidget(QLabel("MENÜ"))
        for ad, komut in (
            ("Gösterge Paneli", self.yenile), ("Stok Girişi", self.stok_girisi_ac),
            ("Ürün Yönetimi", self.urun_yonetimi_ac), ("Şubede Satış", self.satis_ac),
            ("Stok Transferi", self.transfer_ac),
            ("Depo ve Şubeler", self.konum_yonetimi_ac), ("Kritik Stoklar", self.kritikleri_ac),
            ("Sipariş Önerileri", self.siparis_onerileri_ac),
            ("Hareket Geçmişi", self.hareketleri_ac), ("Raporlar ve Yazdır", self.raporlar_ac),
            ("Profesyonel Araçlar", self.araclar_ac), ("Kullanıcılar", self.kullanicilar_ac),
            ("Veri ve Yedekleme", self.yedek_al), ("Ayarlar", self.ayarlar_ac),
            ("Güncellemeleri Denetle", lambda:self.guncelleme_denetle(False)), ("Yardım Merkezi", self.yardim_ac),
        ):
            b = QPushButton(ad); b.clicked.connect(komut); d.addWidget(b)
        d.addStretch()
        d.addWidget(QLabel("DeporiaQ Modern\nGüvenli • Hızlı • Bulut"))
        telif = QLabel("© 2026 DeporiaQ.\nTüm hakları saklıdır."); telif.setObjectName("soluk")
        d.addWidget(telif)
        return menu

    def alt_cubuk(self):
        alt = QFrame(); alt.setObjectName("altCubuk")
        d = QHBoxLayout(alt); d.setContentsMargins(18, 8, 18, 8)
        durum = QLabel("Sistem hazır"); durum.setObjectName("durum")
        d.addWidget(durum); d.addStretch()
        cikis = QPushButton("Çıkış Yap"); cikis.clicked.connect(self.cikis_yap)
        kapat = QPushButton("Programı Kapat"); kapat.setObjectName("tehlike"); kapat.clicked.connect(QApplication.quit)
        d.addWidget(cikis); d.addWidget(kapat)
        return alt

    def dashboard_kur(self):
        d = QVBoxLayout(self.icerik); d.setContentsMargins(14, 10, 14, 10); d.setSpacing(8)
        ust = QHBoxLayout(); baslik = QLabel("İşletme Özeti"); baslik.setObjectName("sayfaBaslik"); ust.addWidget(baslik)
        ust.addSpacing(18); self.konum = QComboBox(); self.konum.setMinimumWidth(320); self.konum.setMaximumWidth(460)
        self.konum.currentIndexChanged.connect(self.yenile); ust.addWidget(self.konum)
        yenile = QPushButton("↻ Yenile"); yenile.clicked.connect(self.yenile); ust.addWidget(yenile); ust.addStretch(); d.addLayout(ust)
        kartlar = QHBoxLayout(); self.kartlar = []
        for bas in ("Ürün çeşidi", "Seçili konum stoğu", "Toplam stok değeri", "Kritik stok"):
            k = QFrame(); k.setObjectName("kart"); kd = QVBoxLayout(k); kd.setContentsMargins(10,6,10,7); kd.setSpacing(2)
            kd.addWidget(QLabel(bas)); deger = QLabel("0"); deger.setObjectName("kartDeger"); kd.addWidget(deger)
            kartlar.addWidget(k); self.kartlar.append(deger)
        d.addLayout(kartlar)
        grafikler = QHBoxLayout(); grafikler.setSpacing(8)
        stok_karti = QFrame(); stok_karti.setObjectName("panel"); sk = QVBoxLayout(stok_karti)
        sk.addWidget(QLabel("Stok Sağlığı")); self.halka_grafik = HalkaGrafik(); sk.addWidget(self.halka_grafik)
        deger_karti = QFrame(); deger_karti.setObjectName("panel"); dk = QVBoxLayout(deger_karti)
        dk.addWidget(QLabel("En Değerli 5 Ürün")); self.cubuk_grafik = CubukGrafik(); dk.addWidget(self.cubuk_grafik)
        hareket_grafik_karti = QFrame(); hareket_grafik_karti.setObjectName("panel"); hg = QVBoxLayout(hareket_grafik_karti)
        hg.addWidget(QLabel("Hareket Dağılımı")); self.hareket_grafik = CubukGrafik(); hg.addWidget(self.hareket_grafik)
        grafikler.addWidget(stok_karti, 1); grafikler.addWidget(deger_karti, 1); grafikler.addWidget(hareket_grafik_karti, 1); d.addLayout(grafikler)

        alt = QHBoxLayout()
        hareket_karti = QFrame(); hareket_karti.setObjectName("panel"); hk = QVBoxLayout(hareket_karti)
        hk.addWidget(QLabel("Son Stok Hareketleri")); self.hareket_tablosu = QTableWidget(0, 3)
        self.hareket_tablosu.setHorizontalHeaderLabels(["Tarih", "İşlem", "Miktar"]); tablo_standardi(self.hareket_tablosu, 27)
        self.hareket_tablosu.setMaximumHeight(190); hk.addWidget(self.hareket_tablosu)
        alt.addWidget(hareket_karti, 2)
        finans = QFrame(); finans.setObjectName("panel"); fk = QVBoxLayout(finans)
        fb = QHBoxLayout(); fb.addWidget(QLabel("Finans Merkezi")); fb.addStretch()
        kur_yenile = QPushButton("Kurları Yenile"); kur_yenile.clicked.connect(self.kurlari_yenile); fb.addWidget(kur_yenile); fk.addLayout(fb)
        self.kur_bilgileri = QLabel("TCMB kurları yükleniyor…"); self.kur_bilgileri.setObjectName("kurBilgisi"); fk.addWidget(self.kur_bilgileri)
        self.kur_durumu = QLabel("Resmî TCMB gösterge kurları"); self.kur_durumu.setObjectName("soluk"); fk.addWidget(self.kur_durumu)
        baglantilar = QHBoxLayout()
        altin = QPushButton("Altın ve Kurlar"); altin.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/Doviz+Kurlari"))); baglantilar.addWidget(altin)
        for sira, ad in enumerate(("Borsa İstanbul", "KAP", "Finans Haberleri")):
            b = QPushButton(ad); b.clicked.connect(lambda _, i=sira: self.finans_merkezi_ac(i)); baglantilar.addWidget(b)
        fk.addLayout(baglantilar); alt.addWidget(finans, 2)
        sosyal = QFrame(); sosyal.setObjectName("panel"); sd = QVBoxLayout(sosyal); sd.addWidget(QLabel("DeporiaQ Sosyal"))
        sosyal_bilgi = QLabel("Yeni özellikler, eğitim videoları ve duyurular yakında."); sosyal_bilgi.setWordWrap(True); sosyal_bilgi.setObjectName("soluk"); sd.addWidget(sosyal_bilgi)
        youtube = QPushButton("▶ YouTube  •  Yakında"); instagram = QPushButton("◎ Instagram  •  Yakında")
        youtube.clicked.connect(lambda: self.sosyal_yakinda("YouTube")); instagram.clicked.connect(lambda: self.sosyal_yakinda("Instagram"))
        sd.addWidget(youtube); sd.addWidget(instagram); sd.addStretch(); alt.addWidget(sosyal, 1); d.addLayout(alt)
        hizli = QHBoxLayout()
        for ad, komut in (("Stok Girişi", self.stok_girisi_ac), ("Ürünler", self.urun_yonetimi_ac),
                          ("Kritik Stoklar", self.kritikleri_ac), ("Sipariş Önerileri", self.siparis_onerileri_ac),
                          ("Stok Transferi", self.transfer_ac)):
            b = QPushButton(ad); b.clicked.connect(komut); hizli.addWidget(b)
        d.addLayout(hizli)
        self.ara = QLineEdit()
        QTimer.singleShot(700, self.kurlari_yenile)

    def konumlari_yenile(self):
        onceki = self.konum.currentData(); self.konum.blockSignals(True); self.konum.clear()
        for k in self.vt.konumlari_getir(): self.konum.addItem(f"{k['ad']} ({k['tur']})", k["id"])
        if onceki is not None:
            i = self.konum.findData(onceki)
            if i >= 0: self.konum.setCurrentIndex(i)
        self.konum.blockSignals(False)

    def yenile(self):
        self.konumlari_yenile(); self.tablo_yenile()
        etkin = self.vt.ayar_getir("cloud_etkin", "0") == "1"
        bekleyen = self.vt.baglanti.execute("SELECT COUNT(*) FROM senkron_kuyrugu WHERE gonderildi=0").fetchone()[0]
        if etkin and bekleyen:
            nokta, metin = "#FBBF24", f"{bekleyen} işlem bekliyor"
        elif etkin:
            nokta, metin = "#4ADE80", "Cloud güncel"
        else:
            nokta, metin = "#94A3B8", "Yerel çalışma"
        self.cloud.setText(f'<span style="color:{nokta}">●</span> <span style="color:#FFFFFF">{metin}</span>')

    def tablo_yenile(self):
        konum = self.konum.currentData()
        if konum is None: return
        urunler = self.vt.urunleri_getir("", konum)
        ozet = self.vt.ozet_getir(konum); kritik = len(self.vt.kritik_stoklari_getir())
        for w, v in zip(self.kartlar, (ozet["urun_sayisi"], ozet["toplam_stok"], para(ozet["toplam_deger"]), kritik)):
            w.setText(str(v))
        kritik_konum = sum(1 for u in urunler if int(u["miktar"] or 0) <= int(u["kritik_stok"] or 0))
        self.halka_grafik.veri_ayarla(kritik_konum, max(0, len(urunler) - kritik_konum))
        en_degerli = sorted(((u["ad"], float(u["miktar"] or 0) * float(u["fiyat"] or 0)) for u in urunler), key=lambda x:x[1], reverse=True)[:5]
        self.cubuk_grafik.veri_ayarla(en_degerli)
        hareket_ozeti = self.vt.baglanti.execute(
            "SELECT hareket_turu,COUNT(*) adet FROM stok_hareketleri "
            "WHERE kaynak_konum_id=? OR hedef_konum_id=? GROUP BY hareket_turu ORDER BY adet DESC LIMIT 5", (konum, konum)
        ).fetchall()
        self.hareket_grafik.veri_ayarla([(str(h["hareket_turu"]).replace("_", " ").title(), h["adet"]) for h in hareket_ozeti])
        hareketler = self.vt.baglanti.execute(
            "SELECT tarih_saat,hareket_turu,miktar FROM stok_hareketleri "
            "WHERE kaynak_konum_id=? OR hedef_konum_id=? ORDER BY id DESC LIMIT 5", (konum, konum)
        ).fetchall()
        self.hareket_tablosu.setRowCount(len(hareketler))
        for r, h in enumerate(hareketler):
            for c, v in enumerate((h["tarih_saat"], str(h["hareket_turu"]).replace("_", " ").title(), h["miktar"])):
                self.hareket_tablosu.setItem(r, c, QTableWidgetItem(str(v)))

    def kurlari_yenile(self):
        if hasattr(self, "kur_iscisi") and self.kur_iscisi.isRunning(): return
        self.kur_bilgileri.setText("TCMB kurları yükleniyor…")
        self.kur_iscisi = KurKontrolu(self)
        self.kur_iscisi.tamamlandi.connect(self.kur_sonucu)
        self.kur_iscisi.hata.connect(lambda _: self.kur_hatasi())
        self.kur_iscisi.start()

    def kur_sonucu(self, sonuc):
        satirlar = []
        for kod in ("USD", "EUR", "GBP"):
            if kod in sonuc:
                alis, satis = sonuc[kod]; satirlar.append(f"{kod}   Alış {alis:.4f}  •  Satış {satis:.4f}")
        self.kur_bilgileri.setText("\n".join(satirlar))
        self.kur_durumu.setText(f"TCMB gösterge kurları • {sonuc.get('tarih', 'güncel')}")

    def kur_hatasi(self):
        self.kur_bilgileri.setText("Kur bilgisi şu anda alınamadı.")
        self.kur_durumu.setText("İnternet bağlantınızı kontrol edip yeniden deneyin.")

    def finans_merkezi_ac(self, secili=0):
        FinansTarayicisi(self, secili).exec()

    def sosyal_yakinda(self, platform):
        QMessageBox.information(self, f"DeporiaQ {platform}", f"DeporiaQ {platform} hesabı henüz açılmadı.\nHesap açıldığında bağlantı bu düğmeye eklenecek.")

    def transfer_ac(self):
        if self.kullanici["rol"] not in ("ANA_YONETICI", "DEPO_PERSONELI"):
            QMessageBox.warning(self, "Yetki gerekli", "Bu hesabın stok transferi yetkisi bulunmuyor.")
            return
        TransferPenceresi(self.vt, self.yenile, self).exec()

    def stok_girisi_ac(self):
        if self.kullanici["rol"] != "ANA_YONETICI":
            QMessageBox.warning(self,"Yetki gerekli","Bu işlem için Ana Yönetici yetkisi gerekir.");return
        StokGirisPenceresi(self.vt,self.yenile,self).exec()

    def urun_yonetimi_ac(self):
        if self.kullanici["rol"] != "ANA_YONETICI":
            QMessageBox.warning(self,"Yetki gerekli","Bu işlem için Ana Yönetici yetkisi gerekir.");return
        UrunYonetimiPenceresi(self.vt,self.yenile,self).exec()

    def konum_yonetimi_ac(self):
        if self.kullanici["rol"] != "ANA_YONETICI":
            QMessageBox.warning(self,"Yetki gerekli","Bu işlem için Ana Yönetici yetkisi gerekir.");return
        KonumYonetimiPenceresi(self.vt,self.yenile,self).exec()

    def satis_ac(self):
        if self.kullanici["rol"] not in ("ANA_YONETICI","SUBE_PERSONELI"):
            QMessageBox.warning(self,"Yetki gerekli","Bu hesabın satış yetkisi bulunmuyor.");return
        SubeSatisPenceresi(self.vt,self.yenile,self).exec()

    def araclar_ac(self):
        if self.kullanici["rol"]!="ANA_YONETICI":QMessageBox.warning(self,"Yetki gerekli","Bu işlem için Ana Yönetici yetkisi gerekir.");return
        AraclarPenceresi(self.vt,self.yenile,self).exec()

    def ayarlar_ac(self):
        if self.kullanici["rol"]!="ANA_YONETICI":QMessageBox.warning(self,"Yetki gerekli","Bu işlem için Ana Yönetici yetkisi gerekir.");return
        AyarlarPenceresi(self.vt,self.cloud_client,self.yenile,self).exec();self.yenile()

    def yardim_ac(self):
        YardimMerkezi(self.vt,self).exec()

    def guncelleme_denetle(self,sessiz=False):
        if hasattr(self,"guncelleme_isci") and self.guncelleme_isci.isRunning():return
        self.guncelleme_sessiz=sessiz;self.guncelleme_isci=GuncellemeKontrolu(self)
        self.guncelleme_isci.tamamlandi.connect(self.guncelleme_sonucu)
        self.guncelleme_isci.hata.connect(lambda h:None if self.guncelleme_sessiz else QMessageBox.warning(self,"Güncelleme denetlenemedi",h))
        self.guncelleme_isci.start()

    def guncelleme_sonucu(self,manifest):
        yeni=str(manifest.get("version","0"))
        if surum_parcalari(yeni)<=surum_parcalari(SURUM):
            if not self.guncelleme_sessiz:QMessageBox.information(self,"DeporiaQ güncel",f"En güncel sürümü kullanıyorsunuz: {SURUM}")
            return
        notlar=str(manifest.get("notes","")).strip();mesaj=f"DeporiaQ {yeni} hazır.\n\n{notlar[:500]}\n\nGüvenli güncelleme aracını şimdi açalım mı?"
        if QMessageBox.question(self,"Yeni güncelleme hazır",mesaj)!=QMessageBox.StandardButton.Yes:return
        arac=Path(sys.executable).resolve().parent/"DeporiaQUpdate.exe" if getattr(sys,"frozen",False) else Path(__file__).resolve().parent/"DeporiaQUpdate.exe"
        if not arac.exists():QMessageBox.warning(self,"Güncelleme aracı bulunamadı","DeporiaQUpdate.exe kurulum klasöründe bulunamadı.");return
        subprocess.Popen([str(arac)],close_fds=True)

    def yedek_al(self):
        if self.kullanici["rol"] != "ANA_YONETICI":
            QMessageBox.warning(self,"Yetki gerekli","Bu işlem için Ana Yönetici yetkisi gerekir.");return
        varsayilan=f"DeporiaQ_Yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        yol,_=QFileDialog.getSaveFileName(self,"Veritabanı yedeğini kaydet",varsayilan,"DeporiaQ Veritabanı (*.db)")
        if not yol:return
        try:self.vt.baglanti.commit();shutil.copy2(VERITABANI_YOLU,yol)
        except OSError as e:QMessageBox.warning(self,"Yedek alınamadı",str(e));return
        QMessageBox.information(self,"Yedek tamamlandı",f"Veritabanı yedeği kaydedildi:\n{yol}")

    def kullanicilar_ac(self):
        if self.kullanici["rol"] != "ANA_YONETICI":
            QMessageBox.warning(self,"Yetki gerekli","Bu işlem için Ana Yönetici yetkisi gerekir.");return
        KullaniciYonetimiPenceresi(self.vt,self.kullanici,self).exec()

    def kritikleri_ac(self):
        self.liste_dialog("Kritik Stoklar", ["Konum", "Barkod", "Ürün", "Mevcut", "Kritik"], self.vt.kritik_stoklari_getir(), ["konum","barkod","urun","miktar","kritik_stok"])

    def siparis_onerileri_ac(self):
        SiparisOnerileriPenceresi(self.vt,self).exec()

    def hareketleri_ac(self):
        satirlar = self.vt.baglanti.execute("""SELECT tarih_saat,hareket_turu,miktar,aciklama FROM stok_hareketleri ORDER BY id DESC LIMIT 250""").fetchall()
        self.liste_dialog("Hareket Geçmişi", ["Tarih", "Hareket", "Miktar", "Açıklama"], satirlar, ["tarih_saat","hareket_turu","miktar","aciklama"])

    def raporlar_ac(self):
        p=QDialog(self);p.setWindowTitle("Raporlar ve Yazdır");p.resize(1050,680);d=QVBoxLayout(p)
        b=QLabel("Raporlar ve Yazdır");b.setObjectName("sayfaBaslik");d.addWidget(b)
        sec=QHBoxLayout(); tur=QComboBox();tur.addItems(["Genel Stok Raporu","Kritik Stok Raporu","Kâr Raporu","Denetim Kayıtları","Oturum Kayıtları"]);sec.addWidget(tur)
        t=QTableWidget();tablo_standardi(t);d.addLayout(sec);d.addWidget(t,1)
        def doldur():
            ad=tur.currentText()
            if ad=="Genel Stok Raporu": cols,rows,fields=["Barkod","Ürün","Stok","Fiyat"],self.vt.urunleri_getir("",self.konum.currentData()),["barkod","ad","miktar","fiyat"]
            elif ad=="Kritik Stok Raporu": cols,rows,fields=["Konum","Barkod","Ürün","Mevcut","Kritik"],self.vt.kritik_stoklari_getir(),["konum","barkod","urun","miktar","kritik_stok"]
            elif ad=="Kâr Raporu": cols,rows,fields=["Tarih","Ürün","Miktar","Ciro","Brüt kâr"],self.vt.kar_raporu_getir(),["tarih_saat","urun","miktar","ciro","brut_kar"]
            elif ad=="Denetim Kayıtları": cols,rows,fields=["Tarih","Kullanıcı","İşlem","Açıklama"],self.vt.denetim_kayitlari_getir(),["tarih_saat","kullanici","islem","aciklama"]
            else: cols,rows,fields=["Giriş","Çıkış","Kullanıcı"],self.vt.oturum_kayitlari_getir(),["giris_zamani","cikis_zamani","kullanici"]
            t.setColumnCount(len(cols));t.setHorizontalHeaderLabels(cols);t.setRowCount(len(rows));tablo_standardi(t)
            for r,x in enumerate(rows):
                for c,f in enumerate(fields):t.setItem(r,c,QTableWidgetItem(str(x[f] if x[f] is not None else "")))
        tur.currentIndexChanged.connect(doldur);doldur()
        a=QHBoxLayout(); yaz=QPushButton("Yazdır"); yaz.clicked.connect(lambda:self.tablo_yazdir(t,tur.currentText(),p)); csvb=QPushButton("CSV Dışa Aktar");csvb.clicked.connect(lambda:self.tablo_csv(t,tur.currentText(),p));kapat=QPushButton("Kapat");kapat.clicked.connect(p.accept)
        a.addWidget(yaz);a.addWidget(csvb);a.addStretch();a.addWidget(kapat);d.addLayout(a);p.exec()

    def tablo_yazdir(self,t,baslik,parent):
        html=f"<h1>{baslik}</h1><table border='1' cellspacing='0' cellpadding='5'><tr>"+"".join(f"<th>{t.horizontalHeaderItem(c).text()}</th>" for c in range(t.columnCount()))+"</tr>"
        for r in range(t.rowCount()):html+="<tr>"+"".join(f"<td>{t.item(r,c).text() if t.item(r,c) else ''}</td>" for c in range(t.columnCount()))+"</tr>"
        belge=QTextDocument();belge.setHtml(html+"</table>");yazici=QPrinter(QPrinter.PrinterMode.HighResolution);dlg=QPrintDialog(yazici,parent)
        if dlg.exec():belge.print_(yazici)

    def tablo_csv(self,t,baslik,parent):
        yol,_=QFileDialog.getSaveFileName(parent,"Raporu kaydet",baslik.replace(" ","_")+".csv","CSV (*.csv)")
        if not yol:return
        with open(yol,"w",newline="",encoding="utf-8-sig") as f:
            y=csv.writer(f,delimiter=";");y.writerow([t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]);y.writerows([[t.item(r,c).text() if t.item(r,c) else "" for c in range(t.columnCount())] for r in range(t.rowCount())])
        QMessageBox.information(parent,"Dışa aktarıldı",f"Rapor kaydedildi:\n{yol}")

    def liste_dialog(self, baslik, kolonlar, satirlar, alanlar):
        p = QDialog(self); p.setWindowTitle(baslik); p.resize(900, 600); d = QVBoxLayout(p)
        t = QTableWidget(len(satirlar), len(kolonlar)); t.setHorizontalHeaderLabels(kolonlar)
        tablo_standardi(t,36)
        for r, s in enumerate(satirlar):
            for c, a in enumerate(alanlar): t.setItem(r,c,QTableWidgetItem(str(s[a] if s[a] is not None else "")))
        d.addWidget(t); p.exec()

    def cikis_yap(self):
        self.vt.aktif_kullanici_id = None
        self.close(); self.giris.parola.clear(); self.giris.show(); self.giris.raise_()


STIL = """
QWidget { background:#131A26; color:#F8FAFC; font-family:'Segoe UI'; font-size:14px; }
QLineEdit,QComboBox,QSpinBox { background:#1E2635; border:1px solid #3B4B63; padding:8px; min-height:20px; }
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
QLabel#durum { color:#8FA6BF; }
QFrame#kart { background:#1E2635; border:1px solid #38516E; border-radius:7px; }
QFrame#kart QLabel { background:transparent; border:0; }
QLabel#kartDeger { font-size:22px; font-weight:800; color:#38BDF8; }
QFrame#panel { background:#192334; border:1px solid #38516E; border-radius:8px; }
QFrame#panel QLabel { background:transparent; border:0; font-weight:650; }
QLabel#kurBilgisi { color:#E2E8F0; font-family:'Consolas'; font-size:13px; line-height:1.5; }
QHeaderView::section { background:#314C6B; padding:8px; font-weight:700; }
"""


def main():
    eski_veritabanini_tasi(); veritabani_butunlugunu_kurtar(); veritabani_yedegi_al()
    vt = Veritabani(VERITABANI_YOLU)
    app = QApplication(sys.argv); app.setApplicationName(PROGRAM_ADI); app.setApplicationVersion(SURUM)
    app.setWindowIcon(QIcon(kaynak_yolu("deporiaq_icon.svg"))); app.setStyleSheet(STIL); app.setFont(QFont("Segoe UI", 10))
    if vt.ilk_kurulum_gerekli():
        QMessageBox.critical(None, "Kurulum gerekli", "Önce DeporiaQ 0.13.4 ile ilk işletme kurulumunu tamamlayın.")
        return 1
    giris = GirisPenceresi(vt); giris.show()
    sonuc = app.exec(); vt.kapat(); return sonuc


if __name__ == "__main__":
    raise SystemExit(main())
