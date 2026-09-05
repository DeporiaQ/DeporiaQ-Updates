import os
import csv
import base64
import ctypes
import html
import json
import hashlib
import shutil
import sqlite3
import sys
import secrets
import subprocess
import tkinter as tk
import threading
import tempfile
import time
import urllib.request
import urllib.error
import urllib.parse
import uuid
import zipfile
import xml.etree.ElementTree as ET
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, filedialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, CENTER, END, LEFT, RIGHT, X, Y


PROGRAM_ADI = "DeporiaQ"
PROGRAM_SURUMU = "0.21.2"
TELIF_METNI = "© 2026 DeporiaQ. Tüm hakları saklıdır."

RENK_ZEMIN = "#212121"
RENK_PANEL = "#292929"
RENK_METIN = "#F8FAFC"
RENK_SOLUK = "#94A3B8"
RENK_VURGU = "#38BDF8"
YAZI_TIPI = "Segoe UI Variable"


def tema_renklerini_ayarla(tema):
    """Tk tabanlı özel yüzeyleri ttk açık/koyu temasıyla aynı palete taşır."""
    global RENK_ZEMIN, RENK_PANEL, RENK_METIN, RENK_SOLUK, RENK_VURGU
    if str(tema).lower() == "acik":
        RENK_ZEMIN, RENK_PANEL = "#F4F7FB", "#FFFFFF"
        RENK_METIN, RENK_SOLUK, RENK_VURGU = "#172033", "#64748B", "#2563EB"
    else:
        RENK_ZEMIN, RENK_PANEL = "#151A24", "#1E2635"
        RENK_METIN, RENK_SOLUK, RENK_VURGU = "#F8FAFC", "#94A3B8", "#38BDF8"

ROL_ADLARI = {
    "ANA_YONETICI": "Ana Yönetici",
    "DEPO_PERSONELI": "Depo Personeli",
    "SUBE_PERSONELI": "Şube Personeli",
    "GORUNTULEYICI": "Görüntüleyici",
}

# Arayüz metinleri Türkçe kaynak metin üzerinden çevrilir. Veritabanındaki
# işletme, ürün ve kullanıcı adları hiçbir zaman çevrilmez veya değiştirilmez.
INGILIZCE_METINLER = {
    "Giriş Yap": "Sign In", "Programı Kapat": "Close Application",
    "Çıkış Yap": "Sign Out", "Şifremi Unuttum": "Forgot Password",
    "Kullanıcı adı:": "Username:", "Parola:": "Password:",
    "Parolayı göster": "Show password", "Parolaları Göster": "Show passwords",
    "Beni Hatırla": "Remember Me", "Güvenli oturum açma": "Secure sign-in",
    "Ürün Ekle": "Add Product", "Ürün Sil": "Delete Product",
    "Fiyat Güncelle": "Update Price", "Şubede Satış": "Branch Sale",
    "Genel Yönetici Raporu": "Executive Report", "Profesyonel Araçlar": "Professional Tools",
    "Operasyon Merkezi": "Operations Center", "Kullanıcılar": "Users",
    "Ayarlar": "Settings", "Yardım": "Help",
    "Veri ve Yedekleme": "Data and Backup", "Güncellemeleri Kontrol Et": "Check for Updates",
    "Depo / Şube Ekle": "Warehouse / Branch", "Stok Transferi": "Stock Transfer",
    "Hareket Geçmişi": "Activity History", "Kritik Stoklar": "Critical Stock",
    "Barkod:": "Barcode:", "Miktar:": "Quantity:", "Stoğa Ekle": "Add to Stock",
    "Konum seç:": "Select location:", "Ürün veya barkod ara:": "Search product or barcode:",
    "Ürün çeşidi": "Product types", "Seçili konum stoğu": "Selected location stock",
    "Toplam stok değeri": "Total stock value", "Barkod": "Barcode", "Ürün": "Product",
    "Stok miktarı": "Stock quantity", "Birim fiyat": "Unit price", "Stok değeri": "Stock value",
    "Kategori Ekle": "Add Category", "Kategoriyi Ata": "Assign Category",
    "Tedarikçi Ekle": "Add Supplier", "Mal Kabulü Tamamla": "Complete Goods Receipt",
    "Sayım Sonucunu Uygula": "Apply Stock Count", "Listeyi Yenile": "Refresh List",
    "Kategoriler": "Categories", "Tedarikçiler": "Suppliers", "Mal Kabul": "Goods Receipt",
    "Stok Sayımı": "Stock Count", "Kritik Stok": "Critical Stock",
    "Raporu Yazdır": "Print Report", "Yazdır": "Print",
    "Güvenlik Ayarları": "Security Settings", "İşletme bilgileri": "Business information",
    "İşletme adı:": "Business name:", "Otomatik kilit süresi:": "Auto-lock duration:",
    "Kilit Ayarını Kaydet": "Save Lock Settings", "Parolamı Değiştir": "Change Password",
    "İşletme Adını Kaydet": "Save Business Name", "Kapat": "Close",
    "Dil ve görünüm": "Language and appearance", "Uygulama dili:": "Application language:",
    "Dil Ayarını Kaydet": "Save Language", "Türkçe": "Turkish", "İngilizce": "English",
    "Yardım Merkezi": "Help Center", "Sıkça Sorulanlar": "Frequently Asked Questions",
    "Ticket At": "Submit Ticket", "Canlı Destek Talebi": "Live Support Request",
    "Talebi Kaydet": "Save Request", "Konu:": "Subject:", "Mesajınız:": "Your message:",
    "Ad soyad:": "Full name:", "Telefon / e-posta:": "Phone / email:",
    "Önceki sayfaya dön": "Go back", "Dış giriş": "External receipt",
    "Konum": "Location", "Tür": "Type", "Toplam stok": "Total stock",
    "Mevcut": "Current", "Kritik seviye": "Critical level", "Tarih": "Date",
    "Hareket": "Movement", "Kaynak": "Source", "Hedef": "Destination",
    "YARDIM MERKEZİ": "HELP CENTER", "GÜVENLİK AYARLARI": "SECURITY SETTINGS",
    "ÜRÜN YÖNETİMİ": "PRODUCT MANAGEMENT", "OPERASYON MERKEZİ": "OPERATIONS CENTER",
    "PROFESYONEL ARAÇLAR": "PROFESSIONAL TOOLS", "KRİTİK STOK RAPORU": "CRITICAL STOCK REPORT",
    "GENEL YÖNETİCİ STOK RAPORU": "EXECUTIVE STOCK REPORT",
    "SATIŞ VE BRÜT KÂR RAPORU": "SALES AND GROSS PROFIT REPORT",
    "STOK HAREKET GEÇMİŞİ": "STOCK MOVEMENT HISTORY",
    "DEPO VE ŞUBE YÖNETİMİ": "WAREHOUSE AND BRANCH MANAGEMENT",
    "KULLANICI VE YETKİ YÖNETİMİ": "USER AND PERMISSION MANAGEMENT",
    "Yeni kategori:": "New category:", "Ürün:": "Product:", "Kategori:": "Category:",
    "Tedarikçi:": "Supplier:", "Teslim alan konum:": "Receiving location:",
    "Birim alış maliyeti:": "Unit purchase cost:", "Fatura / irsaliye no:": "Invoice / delivery note:",
    "Fiziksel sayım miktarı:": "Physical count:", "Açıklama:": "Description:",
    "Tedarikçi unvanı": "Supplier name", "Telefon": "Phone", "E-posta": "Email",
    "Yeni Ürün Ekle": "Add New Product", "Ürünü Kaldır": "Remove Product",
    "Fiyatı Güncelle": "Update Price", "Transferi Tamamla": "Complete Transfer",
    "Satışı Tamamla": "Complete Sale", "Son Fişi Aç / Yazdır": "Open / Print Last Receipt",
    "Bugün": "Today", "Bu ay": "This month", "Tümü": "All",
    "Dönem:": "Period:", "Adet": "Quantity", "Alış": "Purchase",
    "Satış": "Sale", "Ciro": "Revenue", "Brüt kâr": "Gross profit",
    "Cloud e-posta:": "Cloud email:", "Cloud parola:": "Cloud password:",
    "Cloud Giriş": "Cloud Sign In",
    "Yerel Veriyi Buluta Gönder": "Upload Local Data to Cloud",
    "Buluttan Yenile": "Refresh from Cloud",
}


ISLETME_TURLERI = (
    "Akaryakıt İstasyonu", "Aktar", "Ambalaj Mağazası", "Anahtarcı",
    "Antikacı", "Ayakkabı Mağazası", "Av Bayisi", "Bakkal", "Balıkçı",
    "Baharatçı", "Bebek Mağazası", "Beyaz Eşya Mağazası", "Bijuteri",
    "Bilgisayarcı", "Bisiklet Mağazası", "Büfe", "Butik", "Çanta Mağazası",
    "Çiçekçi", "Çiftlik Ürünleri Mağazası", "Cep Telefonu Mağazası",
    "Eczane", "Elektrik Malzemeleri Mağazası", "Elektronik Mağazası",
    "Ev Tekstili Mağazası", "Fırın", "Fotoğrafçı", "Giyim Mağazası",
    "Gözlükçü", "Hırdavatçı", "Hobi Mağazası", "Hurdacı", "İnşaat Malzemeleri",
    "Kafe", "Kasap", "Kırtasiye", "Kitabevi", "Kozmetik Mağazası",
    "Kuruyemişçi", "Kuyumcu", "Manav", "Market", "Medikal Ürün Mağazası",
    "Mobilya Mağazası", "Motosiklet Bayisi", "Müzik Aletleri Mağazası",
    "Nalbur", "Oto Aksesuar Mağazası", "Oto Galeri", "Oto Yedek Parça",
    "Oyuncakçı", "Pastane", "Pet Shop", "Restoran", "Saatçi",
    "Sanayi Malzemeleri", "Spor Mağazası", "Süpermarket", "Şarküteri",
    "Tarım Ürünleri Bayisi", "Tekel Bayisi", "Tekstil Mağazası",
    "Temizlik Ürünleri Mağazası", "Toptancı", "Yapı Market", "Yem Bayisi",
    "Yöresel Ürünler Mağazası", "Züccaciye", "Diğer",
)


def uygulama_klasoru():
    """Python dosyasının veya oluşturulan EXE'nin bulunduğu klasörü verir."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


KURULUM_KLASORU = uygulama_klasoru()


def veri_klasoru():
    """Kullanıcı verilerini Windows'un güvenli LocalAppData alanında tutar."""
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / PROGRAM_ADI
    return Path.home() / ".local" / "share" / PROGRAM_ADI


VERI_KLASORU = veri_klasoru()
VERITABANI_YOLU = VERI_KLASORU / "deporiaq.db"
YEDEK_KLASORU = VERI_KLASORU / "yedekler"
AYARLAR_YOLU = VERI_KLASORU / "ayarlar.json"
TASIMA_ISARETI = VERI_KLASORU / "veritabani_tasima_0_3_1.tamam"


URUNLER = [
    ("Telefon", 15000.00),
    ("Dizüstü Bilgisayar", 32000.00),
    ("Masaüstü Bilgisayar", 28000.00),
    ("Yazıcı", 7500.00),
    ("Klavye", 850.00),
    ("Kablolu Mouse", 450.00),
    ("Bluetooth Mouse", 950.00),
    ("Gaming Mouse", 1450.00),
    ("Bluetooth Kulaklık", 1800.00),
    ("Gaming Kulaklık", 2400.00),
    ("Monitör", 6500.00),
    ("Gaming Monitör", 11500.00),
    ("Webcam", 1750.00),
    ("Mikrofon", 2200.00),
    ("Hoparlör", 1600.00),
    ("SSD", 2400.00),
    ("Harici SSD", 3900.00),
    ("Hard Disk", 2800.00),
    ("RAM", 2100.00),
    ("Ekran Kartı", 18500.00),
    ("Anakart", 7200.00),
    ("İşlemci", 9800.00),
    ("Güç Kaynağı", 3600.00),
    ("Bilgisayar Kasası", 4200.00),
    ("Modem", 1900.00),
    ("Router", 2600.00),
    ("Ağ Switchi", 3100.00),
    ("USB Bellek", 650.00),
    ("Tablet", 12000.00),
    ("Akıllı Saat", 5500.00),
]


def ean13_olustur(sira):
    """Test kullanımı için kontrol basamağı doğru bir EAN-13 üretir."""
    ilk_12_hane = f"869100000{sira:03d}"
    rakamlar = [int(rakam) for rakam in ilk_12_hane]
    toplam = sum(rakamlar[::2]) + sum(rakamlar[1::2]) * 3
    kontrol_hanesi = (10 - toplam % 10) % 10
    return ilk_12_hane + str(kontrol_hanesi)


def para_bicimlendir(tutar):
    bicimli = f"{tutar:,.2f}"
    bicimli = bicimli.replace(",", "X").replace(".", ",").replace("X", ".")
    return bicimli + " TL"


def ean13_svg(barkod, genislik=360, yukseklik=130):
    """13 haneli EAN barkodu bağımlılık olmadan yazdırılabilir SVG'ye çevirir."""
    if len(str(barkod)) != 13 or not str(barkod).isdigit():
        return ""
    l = {"0":"0001101","1":"0011001","2":"0010011","3":"0111101","4":"0100011","5":"0110001","6":"0101111","7":"0111011","8":"0110111","9":"0001011"}
    g = {"0":"0100111","1":"0110011","2":"0011011","3":"0100001","4":"0011101","5":"0111001","6":"0000101","7":"0010001","8":"0001001","9":"0010111"}
    r = {k: "".join("1" if c == "0" else "0" for c in v) for k, v in l.items()}
    parity = ("LLLLLL","LLGLGG","LLGGLG","LLGGGL","LGLLGG","LGGLLG","LGGGLL","LGLGLG","LGLGGL","LGGLGL")
    kod = "101"
    desen = parity[int(barkod[0])]
    for i, rakam in enumerate(barkod[1:7]):
        kod += (l if desen[i] == "L" else g)[rakam]
    kod += "01010"
    for rakam in barkod[7:]:
        kod += r[rakam]
    kod += "101"
    modul = genislik / 95
    cubuklar = []
    for i, bit in enumerate(kod):
        if bit == "1":
            cubuklar.append(
                f'<rect x="{i*modul:.2f}" y="0" width="{modul+0.2:.2f}" height="{yukseklik-24}"/>'
            )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{genislik}" height="{yukseklik}" '
        f'viewBox="0 0 {genislik} {yukseklik}"><g fill="#000">{"".join(cubuklar)}</g>'
        f'<text x="{genislik/2}" y="{yukseklik-4}" text-anchor="middle" '
        f'font-family="Arial" font-size="18">{barkod}</text></svg>'
    )


def urun_arama_eslesir(urun_adi, barkod, aranan):
    """Ürün adı/barkod aramasını yazım alışkanlıklarına toleranslı yapar."""
    aranan = aranan.strip().casefold()
    if not aranan:
        return True

    urun_metni = urun_adi.casefold()
    if aranan in urun_metni or aranan in str(barkod).casefold():
        return True

    # Türkiye'de sık kullanılan "mause" yazımıyla Mouse ürünlerini de bulur.
    return "mouse" in urun_metni and (
        aranan in "mause" or "mause".startswith(aranan)
    )


class Veritabani:
    def __init__(self, yol):
        self.yol = yol
        self.baglanti = sqlite3.connect(yol)
        self.baglanti.row_factory = sqlite3.Row
        self.baglanti.execute("PRAGMA foreign_keys = ON")
        self.tablolari_olustur()
        self.ilk_verileri_ekle()

    def tablolari_olustur(self):
        self.baglanti.executescript(
            """
            CREATE TABLE IF NOT EXISTS urunler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barkod TEXT NOT NULL UNIQUE,
                ad TEXT NOT NULL UNIQUE,
                fiyat REAL NOT NULL CHECK (fiyat >= 0),
                aktif INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS konumlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL UNIQUE,
                tur TEXT NOT NULL CHECK (tur IN ('MERKEZ', 'DEPO', 'SUBE')),
                aktif INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS stoklar (
                urun_id INTEGER NOT NULL,
                konum_id INTEGER NOT NULL,
                miktar INTEGER NOT NULL DEFAULT 0 CHECK (miktar >= 0),
                PRIMARY KEY (urun_id, konum_id),
                FOREIGN KEY (urun_id) REFERENCES urunler(id),
                FOREIGN KEY (konum_id) REFERENCES konumlar(id)
            );

            CREATE TABLE IF NOT EXISTS stok_hareketleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_id INTEGER NOT NULL,
                kaynak_konum_id INTEGER,
                hedef_konum_id INTEGER,
                miktar INTEGER NOT NULL CHECK (miktar > 0),
                hareket_turu TEXT NOT NULL,
                tarih_saat TEXT NOT NULL,
                aciklama TEXT,
                FOREIGN KEY (urun_id) REFERENCES urunler(id),
                FOREIGN KEY (kaynak_konum_id) REFERENCES konumlar(id),
                FOREIGN KEY (hedef_konum_id) REFERENCES konumlar(id)
            );

            CREATE TABLE IF NOT EXISTS kullanicilar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_adi TEXT NOT NULL UNIQUE,
                parola_ozeti TEXT NOT NULL,
                rol TEXT NOT NULL,
                konum_id INTEGER,
                aktif INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (konum_id) REFERENCES konumlar(id)
            );

            CREATE TABLE IF NOT EXISTS ayarlar (
                anahtar TEXT PRIMARY KEY,
                deger TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS denetim_kayitlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_id INTEGER,
                islem TEXT NOT NULL,
                aciklama TEXT,
                tarih_saat TEXT NOT NULL,
                FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS oturum_kayitlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_id INTEGER,
                giris_zamani TEXT NOT NULL,
                cikis_zamani TEXT,
                FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS kategoriler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL UNIQUE,
                aktif INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tedarikciler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unvan TEXT NOT NULL UNIQUE,
                telefon TEXT,
                eposta TEXT,
                aktif INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS mal_kabul_kayitlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tedarikci_id INTEGER,
                urun_id INTEGER NOT NULL,
                konum_id INTEGER NOT NULL,
                miktar INTEGER NOT NULL,
                birim_maliyet REAL NOT NULL,
                belge_no TEXT,
                tarih_saat TEXT NOT NULL,
                kullanici_id INTEGER,
                FOREIGN KEY (tedarikci_id) REFERENCES tedarikciler(id),
                FOREIGN KEY (urun_id) REFERENCES urunler(id),
                FOREIGN KEY (konum_id) REFERENCES konumlar(id)
            );

            CREATE TABLE IF NOT EXISTS stok_sayimlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_id INTEGER NOT NULL,
                konum_id INTEGER NOT NULL,
                onceki_miktar INTEGER NOT NULL,
                yeni_miktar INTEGER NOT NULL,
                aciklama TEXT,
                tarih_saat TEXT NOT NULL,
                kullanici_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS destek_talepleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                talep_turu TEXT NOT NULL,
                konu TEXT NOT NULL,
                mesaj TEXT NOT NULL,
                iletisim TEXT,
                durum TEXT NOT NULL DEFAULT 'BEKLIYOR',
                tarih_saat TEXT NOT NULL,
                kullanici_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS urun_ozellestirme_talepleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_id INTEGER NOT NULL,
                eski_ad TEXT NOT NULL,
                eski_barkod TEXT NOT NULL,
                yeni_ad TEXT NOT NULL,
                yeni_barkod TEXT NOT NULL,
                talep_eden_id INTEGER,
                durum TEXT NOT NULL DEFAULT 'BEKLIYOR',
                tarih_saat TEXT NOT NULL,
                karar_tarihi TEXT,
                karar_veren_id INTEGER,
                FOREIGN KEY (urun_id) REFERENCES urunler(id)
            );

            CREATE TABLE IF NOT EXISTS senkron_kuyrugu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                varlik TEXT NOT NULL,
                varlik_anahtari TEXT NOT NULL,
                islem TEXT NOT NULL,
                tarih_saat TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                gonderildi INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS cloud_sync_durumu (
                anahtar TEXT PRIMARY KEY,
                deger TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cloud_cakismalari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cakisma_kimligi TEXT NOT NULL UNIQUE,
                yerel_ozet TEXT NOT NULL,
                bulut_ozet TEXT NOT NULL,
                durum TEXT NOT NULL DEFAULT 'BEKLIYOR',
                tarih_saat TEXT NOT NULL,
                cozum TEXT
            );

            CREATE TABLE IF NOT EXISTS cloud_islem_kuyrugu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                islem_kimligi TEXT NOT NULL UNIQUE,
                islem_turu TEXT NOT NULL,
                veri_json TEXT NOT NULL,
                durum TEXT NOT NULL DEFAULT 'BEKLIYOR',
                deneme_sayisi INTEGER NOT NULL DEFAULT 0,
                son_hata TEXT,
                tarih_saat TEXT NOT NULL
            );

            CREATE TRIGGER IF NOT EXISTS cloud_urun_ekle AFTER INSERT ON urunler
            WHEN COALESCE((SELECT deger FROM ayarlar WHERE anahtar='cloud_etkin'),'0')='1'
            BEGIN INSERT INTO senkron_kuyrugu(varlik,varlik_anahtari,islem) VALUES('urun',NEW.id,'EKLE'); END;
            CREATE TRIGGER IF NOT EXISTS cloud_urun_guncelle AFTER UPDATE ON urunler
            WHEN COALESCE((SELECT deger FROM ayarlar WHERE anahtar='cloud_etkin'),'0')='1'
            BEGIN INSERT INTO senkron_kuyrugu(varlik,varlik_anahtari,islem) VALUES('urun',NEW.id,'GUNCELLE'); END;
            CREATE TRIGGER IF NOT EXISTS cloud_stok_guncelle AFTER UPDATE ON stoklar
            WHEN COALESCE((SELECT deger FROM ayarlar WHERE anahtar='cloud_etkin'),'0')='1'
            BEGIN INSERT INTO senkron_kuyrugu(varlik,varlik_anahtari,islem) VALUES('stok',NEW.urun_id||':'||NEW.konum_id,'GUNCELLE'); END;
            CREATE TRIGGER IF NOT EXISTS cloud_stok_ekle AFTER INSERT ON stoklar
            WHEN COALESCE((SELECT deger FROM ayarlar WHERE anahtar='cloud_etkin'),'0')='1'
            BEGIN INSERT INTO senkron_kuyrugu(varlik,varlik_anahtari,islem) VALUES('stok',NEW.urun_id||':'||NEW.konum_id,'EKLE'); END;
            CREATE TRIGGER IF NOT EXISTS cloud_konum_ekle AFTER INSERT ON konumlar
            WHEN COALESCE((SELECT deger FROM ayarlar WHERE anahtar='cloud_etkin'),'0')='1'
            BEGIN INSERT INTO senkron_kuyrugu(varlik,varlik_anahtari,islem) VALUES('konum',NEW.id,'EKLE'); END;
            """
        )

        urun_kolonlari = {
            kolon["name"] for kolon in self.baglanti.execute(
                "PRAGMA table_info(urunler)"
            ).fetchall()
        }
        if "alis_fiyati" not in urun_kolonlari:
            self.baglanti.execute(
                "ALTER TABLE urunler ADD COLUMN alis_fiyati REAL NOT NULL DEFAULT 0"
            )
        if "kritik_stok" not in urun_kolonlari:
            self.baglanti.execute(
                "ALTER TABLE urunler ADD COLUMN kritik_stok INTEGER NOT NULL DEFAULT 10"
            )
        if "kategori_id" not in urun_kolonlari:
            self.baglanti.execute("ALTER TABLE urunler ADD COLUMN kategori_id INTEGER")

        hareket_kolonlari = {
            kolon["name"]
            for kolon in self.baglanti.execute(
                "PRAGMA table_info(stok_hareketleri)"
            ).fetchall()
        }

        if "birim_fiyat" not in hareket_kolonlari:
            self.baglanti.execute(
                "ALTER TABLE stok_hareketleri ADD COLUMN birim_fiyat REAL"
            )

        if "toplam_tutar" not in hareket_kolonlari:
            self.baglanti.execute(
                "ALTER TABLE stok_hareketleri ADD COLUMN toplam_tutar REAL"
            )
        if "alis_fiyati" not in hareket_kolonlari:
            self.baglanti.execute(
                "ALTER TABLE stok_hareketleri ADD COLUMN alis_fiyati REAL"
            )
        if "kullanici_id" not in hareket_kolonlari:
            self.baglanti.execute(
                "ALTER TABLE stok_hareketleri ADD COLUMN kullanici_id INTEGER"
            )

        self.baglanti.commit()
        self.aktif_kullanici_id = None

    def denetim_ekle(self, islem, aciklama=""):
        self.baglanti.execute(
            "INSERT INTO denetim_kayitlari (kullanici_id, islem, aciklama, tarih_saat) VALUES (?, ?, ?, ?)",
            (self.aktif_kullanici_id, islem, aciklama, datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        )
        self.baglanti.commit()

    def oturum_baslat(self, kullanici_id):
        self.aktif_kullanici_id = kullanici_id
        imlec = self.baglanti.execute(
            "INSERT INTO oturum_kayitlari (kullanici_id, giris_zamani) VALUES (?, ?)",
            (kullanici_id, datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        )
        self.baglanti.commit()
        return imlec.lastrowid

    def oturum_bitir(self, oturum_id):
        if oturum_id:
            self.baglanti.execute(
                "UPDATE oturum_kayitlari SET cikis_zamani = ? WHERE id = ? AND cikis_zamani IS NULL",
                (datetime.now().strftime("%d.%m.%Y %H:%M:%S"), oturum_id)
            )
            self.baglanti.commit()
        self.aktif_kullanici_id = None

    def butunluk_kontrolu(self):
        return self.baglanti.execute("PRAGMA quick_check").fetchone()[0] == "ok"

    def kritik_stoklari_getir(self):
        return self.baglanti.execute(
            """
            SELECT k.ad AS konum, u.barkod, u.ad AS urun, s.miktar, u.kritik_stok
            FROM stoklar s JOIN urunler u ON u.id=s.urun_id
            JOIN konumlar k ON k.id=s.konum_id
            WHERE u.aktif=1 AND k.aktif=1 AND s.miktar <= u.kritik_stok
            ORDER BY s.miktar, k.ad, u.ad
            """
        ).fetchall()

    def kategorileri_getir(self):
        return self.baglanti.execute(
            "SELECT id, ad FROM kategoriler WHERE aktif=1 ORDER BY ad COLLATE NOCASE"
        ).fetchall()

    def kategori_ekle(self, ad):
        ad = ad.strip()
        if not ad:
            raise ValueError("Kategori adı boş bırakılamaz.")
        try:
            self.baglanti.execute("INSERT INTO kategoriler(ad) VALUES(?)", (ad,))
            self.baglanti.commit()
        except sqlite3.IntegrityError as hata:
            raise ValueError("Bu kategori zaten bulunuyor.") from hata

    def tedarikcileri_getir(self):
        return self.baglanti.execute(
            "SELECT id, unvan, telefon, eposta FROM tedarikciler WHERE aktif=1 ORDER BY unvan COLLATE NOCASE"
        ).fetchall()

    def tedarikci_ekle(self, unvan, telefon="", eposta=""):
        unvan = unvan.strip()
        if not unvan:
            raise ValueError("Tedarikçi unvanı boş bırakılamaz.")
        try:
            self.baglanti.execute(
                "INSERT INTO tedarikciler(unvan,telefon,eposta) VALUES(?,?,?)",
                (unvan, telefon.strip(), eposta.strip()),
            )
            self.baglanti.commit()
        except sqlite3.IntegrityError as hata:
            raise ValueError("Bu tedarikçi zaten bulunuyor.") from hata

    def urun_kategori_guncelle(self, urun_id, kategori_id):
        self.baglanti.execute(
            "UPDATE urunler SET kategori_id=? WHERE id=?", (kategori_id, urun_id)
        )
        self.baglanti.commit()

    def mal_kabul_yap(self, urun_id, konum_id, tedarikci_id, miktar, maliyet, belge_no=""):
        if miktar <= 0 or maliyet < 0:
            raise ValueError("Miktar pozitif, maliyet sıfır veya daha büyük olmalıdır.")
        tarih = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        try:
            self.baglanti.execute("BEGIN")
            self.baglanti.execute(
                """INSERT INTO stoklar(urun_id,konum_id,miktar) VALUES(?,?,?)
                ON CONFLICT(urun_id,konum_id) DO UPDATE SET miktar=miktar+excluded.miktar""",
                (urun_id, konum_id, miktar),
            )
            self.baglanti.execute("UPDATE urunler SET alis_fiyati=? WHERE id=?", (maliyet, urun_id))
            self.baglanti.execute(
                """INSERT INTO mal_kabul_kayitlari
                (tedarikci_id,urun_id,konum_id,miktar,birim_maliyet,belge_no,tarih_saat,kullanici_id)
                VALUES(?,?,?,?,?,?,?,?)""",
                (tedarikci_id,urun_id,konum_id,miktar,maliyet,belge_no.strip(),tarih,self.aktif_kullanici_id),
            )
            self.baglanti.execute(
                """INSERT INTO stok_hareketleri
                (urun_id,kaynak_konum_id,hedef_konum_id,miktar,hareket_turu,tarih_saat,aciklama,alis_fiyati,kullanici_id)
                VALUES(?,NULL,?,?,'TEDARIKCI_MAL_KABUL',?,?,?,?)""",
                (urun_id,konum_id,miktar,tarih,belge_no.strip() or "Tedarikçi mal kabul",maliyet,self.aktif_kullanici_id),
            )
            self.baglanti.commit()
        except Exception:
            self.baglanti.rollback(); raise

    def stok_sayim_duzelt(self, urun_id, konum_id, yeni_miktar, aciklama=""):
        if yeni_miktar < 0:
            raise ValueError("Sayım miktarı negatif olamaz.")
        onceki = self.baglanti.execute(
            "SELECT miktar FROM stoklar WHERE urun_id=? AND konum_id=?", (urun_id,konum_id)
        ).fetchone()
        if not onceki:
            raise ValueError("Stok kaydı bulunamadı.")
        tarih = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        fark = yeni_miktar - onceki["miktar"]
        try:
            self.baglanti.execute("BEGIN")
            self.baglanti.execute(
                "UPDATE stoklar SET miktar=? WHERE urun_id=? AND konum_id=?",
                (yeni_miktar,urun_id,konum_id),
            )
            self.baglanti.execute(
                """INSERT INTO stok_sayimlari
                (urun_id,konum_id,onceki_miktar,yeni_miktar,aciklama,tarih_saat,kullanici_id)
                VALUES(?,?,?,?,?,?,?)""",
                (urun_id,konum_id,onceki["miktar"],yeni_miktar,aciklama.strip(),tarih,self.aktif_kullanici_id),
            )
            if fark:
                self.baglanti.execute(
                    """INSERT INTO stok_hareketleri
                    (urun_id,kaynak_konum_id,hedef_konum_id,miktar,hareket_turu,tarih_saat,aciklama,kullanici_id)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (urun_id, konum_id if fark < 0 else None, konum_id if fark > 0 else None,
                     abs(fark), "SAYIM_DUZELTME", tarih, aciklama.strip() or "Fiziksel stok sayımı", self.aktif_kullanici_id),
                )
            self.baglanti.commit()
            return onceki["miktar"], fark
        except Exception:
            self.baglanti.rollback(); raise

    def destek_talebi_olustur(self, talep_turu, konu, mesaj, iletisim=""):
        konu = konu.strip(); mesaj = mesaj.strip(); iletisim = iletisim.strip()
        if len(konu) < 3:
            raise ValueError("Konu en az 3 karakter olmalıdır.")
        if len(mesaj) < 10:
            raise ValueError("Talep açıklaması en az 10 karakter olmalıdır.")
        imlec = self.baglanti.execute(
            """INSERT INTO destek_talepleri
            (talep_turu,konu,mesaj,iletisim,tarih_saat,kullanici_id)
            VALUES(?,?,?,?,?,?)""",
            (talep_turu, konu, mesaj, iletisim,
             datetime.now().strftime("%d.%m.%Y %H:%M:%S"), self.aktif_kullanici_id),
        )
        self.baglanti.commit()
        return f"DPQ-{datetime.now():%Y%m}-{imlec.lastrowid:05d}"

    def kar_raporu_getir(self, donem="TUMU"):
        kosul = ""
        parametreler = []
        simdi = datetime.now()
        if donem == "BUGUN":
            kosul = " AND h.tarih_saat LIKE ?"
            parametreler.append(simdi.strftime("%d.%m.%Y") + "%")
        elif donem == "BU_AY":
            kosul = " AND substr(h.tarih_saat, 4, 7) = ?"
            parametreler.append(simdi.strftime("%m.%Y"))
        return self.baglanti.execute(
            """
            SELECT h.tarih_saat, u.ad AS urun, h.miktar,
                   COALESCE(h.birim_fiyat,0) AS satis_fiyati,
                   COALESCE(h.alis_fiyati,u.alis_fiyati,0) AS alis_fiyati,
                   COALESCE(h.toplam_tutar,0) AS ciro,
                   (COALESCE(h.birim_fiyat,0)-COALESCE(h.alis_fiyati,u.alis_fiyati,0))*h.miktar AS brut_kar
            FROM stok_hareketleri h JOIN urunler u ON u.id=h.urun_id
            WHERE h.hareket_turu='SATIS'
            """ + kosul + " ORDER BY h.id DESC",
            parametreler
        ).fetchall()

    def denetim_kayitlari_getir(self):
        return self.baglanti.execute(
            """
            SELECT d.tarih_saat, COALESCE(k.kullanici_adi,'Silinmiş kullanıcı') kullanici,
                   d.islem, d.aciklama
            FROM denetim_kayitlari d LEFT JOIN kullanicilar k ON k.id=d.kullanici_id
            ORDER BY d.id DESC LIMIT 1000
            """
        ).fetchall()

    def oturum_kayitlari_getir(self):
        return self.baglanti.execute(
            """
            SELECT o.giris_zamani, COALESCE(o.cikis_zamani,'Açık') cikis_zamani,
                   COALESCE(k.kullanici_adi,'Silinmiş kullanıcı') kullanici
            FROM oturum_kayitlari o LEFT JOIN kullanicilar k ON k.id=o.kullanici_id
            ORDER BY o.id DESC LIMIT 1000
            """
        ).fetchall()

    def ilk_verileri_ekle(self):
        """Eski verileri tanır; temiz müşteriye örnek ürün eklemez."""
        self.baglanti.execute(
            """
            UPDATE konumlar SET ad = ?
            WHERE ad = ? AND tur = 'MERKEZ'
            """,
            ("Merkez Depo", "İstanbul Merkez Depo")
        )
        mevcut_konum = self.baglanti.execute(
            "SELECT COUNT(*) FROM konumlar"
        ).fetchone()[0]
        if mevcut_konum > 0 and self.ayar_getir("kurulum_tamamlandi") is None:
            self.ayar_kaydet("kurulum_tamamlandi", "1")
            self.ayar_kaydet("isletme_adi", "Mevcut DeporiaQ İşletmesi")
            self.ayar_kaydet("isletme_turu", "Mevcut işletme")
            self.ayar_kaydet("para_birimi", "TL")
        self.baglanti.commit()

    def ayar_getir(self, anahtar, varsayilan=None):
        kayit = self.baglanti.execute(
            "SELECT deger FROM ayarlar WHERE anahtar = ?", (anahtar,)
        ).fetchone()
        return kayit["deger"] if kayit else varsayilan

    def ayar_kaydet(self, anahtar, deger):
        self.baglanti.execute(
            """
            INSERT INTO ayarlar (anahtar, deger) VALUES (?, ?)
            ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger
            """,
            (anahtar, str(deger))
        )

    def ilk_kurulum_gerekli(self):
        return self.ayar_getir("kurulum_tamamlandi") != "1"

    def kullanici_bul(self, kullanici_adi):
        """Aktif kullanıcıyı büyük/küçük harften bağımsız bulur."""
        aranan = kullanici_adi.strip().casefold()
        kayitlar = self.baglanti.execute(
            "SELECT * FROM kullanicilar WHERE aktif = 1"
        ).fetchall()
        for kayit in kayitlar:
            if kayit["kullanici_adi"].casefold() == aranan:
                return kayit
        return None

    def kimlik_dogrula(self, kullanici_adi, parola):
        kayit = self.kullanici_bul(kullanici_adi)
        if kayit and parola_ozeti_dogrula(parola, kayit["parola_ozeti"]):
            return kayit
        return None

    def kullanicilari_getir(self):
        return self.baglanti.execute(
            """
            SELECT k.id, k.kullanici_adi, k.rol, k.konum_id, k.aktif,
                   COALESCE(kon.ad, 'Atanmamış') AS konum_adi
            FROM kullanicilar AS k
            LEFT JOIN konumlar AS kon ON kon.id = k.konum_id
            ORDER BY k.aktif DESC, k.kullanici_adi COLLATE NOCASE
            """
        ).fetchall()

    def kullanici_ekle(self, kullanici_adi, parola, rol, konum_id):
        try:
            self.baglanti.execute(
                """
                INSERT INTO kullanicilar
                    (kullanici_adi, parola_ozeti, rol, konum_id, aktif)
                VALUES (?, ?, ?, ?, 1)
                """,
                (kullanici_adi, parola_ozeti_olustur(parola), rol, konum_id)
            )
            self.baglanti.commit()
        except sqlite3.IntegrityError as hata:
            self.baglanti.rollback()
            raise ValueError("Bu kullanıcı adı zaten kullanılıyor.") from hata

    def kullanici_durumunu_degistir(self, kullanici_id, aktif):
        self.baglanti.execute(
            "UPDATE kullanicilar SET aktif = ? WHERE id = ?",
            (1 if aktif else 0, kullanici_id)
        )
        self.baglanti.commit()

    def kullanici_parolasi_degistir(self, kullanici_id, yeni_parola):
        self.baglanti.execute(
            "UPDATE kullanicilar SET parola_ozeti = ? WHERE id = ?",
            (parola_ozeti_olustur(yeni_parola), kullanici_id)
        )
        self.baglanti.commit()

    def kullanici_yetkisi_guncelle(self, kullanici_id, rol, konum_id):
        self.baglanti.execute(
            "UPDATE kullanicilar SET rol = ?, konum_id = ? WHERE id = ?",
            (rol, konum_id, kullanici_id)
        )
        self.baglanti.commit()

    def kullanici_sil(self, kullanici_id):
        kayit = self.baglanti.execute(
            "SELECT id, rol, aktif FROM kullanicilar WHERE id = ?",
            (kullanici_id,)
        ).fetchone()
        if not kayit:
            raise ValueError("Kullanıcı kaydı bulunamadı.")
        if kayit["rol"] == "ANA_YONETICI" and kayit["aktif"]:
            aktif_yonetici = self.baglanti.execute(
                """
                SELECT COUNT(*) FROM kullanicilar
                WHERE rol = 'ANA_YONETICI' AND aktif = 1
                """
            ).fetchone()[0]
            if aktif_yonetici <= 1:
                raise ValueError("Sistemdeki son aktif ana yönetici kaldırılamaz.")
        self.baglanti.execute(
            "DELETE FROM kullanicilar WHERE id = ?", (kullanici_id,)
        )
        self.baglanti.commit()

    def ilk_kurulumu_tamamla(
        self, isletme_adi, isletme_turu, merkez_adi,
        para_birimi, kullanici_adi, parola
    ):
        try:
            self.baglanti.execute("BEGIN")
            if not self.ilk_kurulum_gerekli():
                raise ValueError("İlk kurulum daha önce tamamlanmış.")

            # Müşteri kurulumu daima boş başlar. Yarım kalmış deneme veya eski
            # örnek veriler varsa yabancı anahtar sırasına uygun biçimde silinir.
            self.baglanti.execute("DELETE FROM mal_kabul_kayitlari")
            self.baglanti.execute("DELETE FROM stok_sayimlari")
            self.baglanti.execute("DELETE FROM destek_talepleri")
            self.baglanti.execute("DELETE FROM senkron_kuyrugu")
            self.baglanti.execute("DELETE FROM stok_hareketleri")
            self.baglanti.execute("DELETE FROM stoklar")
            self.baglanti.execute("DELETE FROM kullanicilar")
            self.baglanti.execute("DELETE FROM urunler")
            self.baglanti.execute("DELETE FROM konumlar")
            self.baglanti.execute("DELETE FROM ayarlar")
            self.baglanti.execute("DELETE FROM tedarikciler")
            self.baglanti.execute("DELETE FROM kategoriler")
            self.baglanti.execute(
                "DELETE FROM sqlite_sequence "
                "WHERE name IN ('urunler','konumlar','stok_hareketleri','kullanicilar',"
                "'kategoriler','tedarikciler','mal_kabul_kayitlari','stok_sayimlari','destek_talepleri')"
            )
            merkez = self.baglanti.execute(
                "INSERT INTO konumlar (ad, tur) VALUES (?, 'MERKEZ')",
                (merkez_adi,)
            )
            self.baglanti.execute(
                """
                INSERT INTO kullanicilar
                    (kullanici_adi, parola_ozeti, rol, konum_id)
                VALUES (?, ?, 'ANA_YONETICI', ?)
                """,
                (kullanici_adi, parola_ozeti_olustur(parola), merkez.lastrowid)
            )
            for anahtar, deger in (
                ("isletme_adi", isletme_adi),
                ("isletme_turu", isletme_turu),
                ("para_birimi", para_birimi),
                ("kurulum_tamamlandi", "1"),
            ):
                self.ayar_kaydet(anahtar, deger)
            self.baglanti.commit()
        except Exception:
            self.baglanti.rollback()
            raise

    def merkez_depo_id(self):
        kayit = self.baglanti.execute(
            "SELECT id FROM konumlar WHERE tur = 'MERKEZ' LIMIT 1"
        ).fetchone()
        return kayit["id"]

    def urunleri_getir(self, aranan="", konum_id=None):
        if konum_id is None:
            konum_id = self.merkez_depo_id()

        kayitlar = self.baglanti.execute(
            """
            SELECT u.id, u.barkod, u.ad, u.fiyat, u.alis_fiyati, u.kritik_stok, s.miktar
            FROM urunler AS u
            JOIN stoklar AS s ON s.urun_id = u.id
            WHERE s.konum_id = ?
              AND u.aktif = 1
            ORDER BY u.ad COLLATE NOCASE
            """,
            (konum_id,)
        ).fetchall()
        return [
            kayit for kayit in kayitlar
            if urun_arama_eslesir(kayit["ad"], kayit["barkod"], aranan)
        ]

    def barkodla_urun_bul(self, barkod, konum_id=None):
        if konum_id is None:
            konum_id = self.merkez_depo_id()

        return self.baglanti.execute(
            """
            SELECT u.id, u.barkod, u.ad, u.fiyat, u.alis_fiyati, u.kritik_stok, s.miktar
            FROM urunler AS u
            JOIN stoklar AS s ON s.urun_id = u.id
            WHERE u.barkod = ? AND s.konum_id = ? AND u.aktif = 1
            """,
            (barkod, konum_id)
        ).fetchone()

    def tum_aktif_urunleri_getir(self):
        return self.baglanti.execute(
            """
            SELECT id, barkod, ad, fiyat, alis_fiyati, kritik_stok
            FROM urunler
            WHERE aktif = 1
            ORDER BY ad COLLATE NOCASE
            """
        ).fetchall()

    def urun_ekle(self, barkod, ad, fiyat, alis_fiyati=0, kritik_stok=10):
        barkod = barkod.strip()
        ad = ad.strip()

        if barkod == "" or not barkod.isdigit():
            raise ValueError("Barkod yalnızca rakamlardan oluşmalıdır.")
        if ad == "":
            raise ValueError("Ürün adı boş bırakılamaz.")
        if fiyat <= 0:
            raise ValueError("Fiyat sıfırdan büyük olmalıdır.")
        if alis_fiyati < 0:
            raise ValueError("Alış fiyatı negatif olamaz.")
        if kritik_stok < 0:
            raise ValueError("Kritik stok seviyesi negatif olamaz.")

        try:
            self.baglanti.execute("BEGIN")
            imlec = self.baglanti.execute(
                "INSERT INTO urunler (barkod, ad, fiyat, alis_fiyati, kritik_stok) VALUES (?, ?, ?, ?, ?)",
                (barkod, ad, fiyat, alis_fiyati, kritik_stok)
            )
            self.baglanti.execute(
                """
                INSERT INTO stoklar (urun_id, konum_id, miktar)
                SELECT ?, id, 0 FROM konumlar WHERE aktif = 1
                """,
                (imlec.lastrowid,)
            )
            self.baglanti.commit()
        except sqlite3.IntegrityError:
            self.baglanti.rollback()
            raise ValueError("Bu barkod veya ürün adı zaten kullanılıyor.")
        except Exception:
            self.baglanti.rollback()
            raise

    def urun_fiyati_guncelle(self, urun_id, yeni_fiyat):
        if yeni_fiyat <= 0:
            raise ValueError("Fiyat sıfırdan büyük olmalıdır.")
        self.baglanti.execute(
            "UPDATE urunler SET fiyat = ? WHERE id = ? AND aktif = 1",
            (yeni_fiyat, urun_id)
        )
        self.baglanti.commit()

    def urun_maliyet_ve_kritik_guncelle(self, urun_id, alis_fiyati, kritik_stok):
        if alis_fiyati < 0 or kritik_stok < 0:
            raise ValueError("Alış fiyatı ve kritik stok negatif olamaz.")
        self.baglanti.execute(
            "UPDATE urunler SET alis_fiyati=?, kritik_stok=? WHERE id=? AND aktif=1",
            (alis_fiyati, kritik_stok, urun_id)
        )
        self.baglanti.commit()

    def urunu_pasiflestir(self, urun_id):
        toplam_stok = self.baglanti.execute(
            "SELECT COALESCE(SUM(miktar), 0) AS toplam FROM stoklar WHERE urun_id = ?",
            (urun_id,)
        ).fetchone()["toplam"]

        if toplam_stok > 0:
            raise ValueError(
                f"Ürünün konumlarda toplam {toplam_stok} adet stoğu var. Stok sıfırlanmadan kaldırılamaz."
            )

        self.baglanti.execute(
            "UPDATE urunler SET aktif = 0 WHERE id = ?",
            (urun_id,)
        )
        self.baglanti.commit()

    def merkeze_stok_girisi(self, urun_id, miktar):
        merkez_id = self.merkez_depo_id()
        tarih_saat = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        try:
            self.baglanti.execute("BEGIN")
            self.baglanti.execute(
                """
                UPDATE stoklar
                SET miktar = miktar + ?
                WHERE urun_id = ? AND konum_id = ?
                """,
                (miktar, urun_id, merkez_id)
            )
            self.baglanti.execute(
                """
                INSERT INTO stok_hareketleri
                (urun_id, kaynak_konum_id, hedef_konum_id, miktar,
                 hareket_turu, tarih_saat, aciklama)
                VALUES (?, NULL, ?, ?, 'MAL_KABUL', ?, ?)
                """,
                (
                    urun_id,
                    merkez_id,
                    miktar,
                    tarih_saat,
                    "Barkod ile merkez depoya ürün girişi"
                )
            )
            self.baglanti.commit()
        except Exception:
            self.baglanti.rollback()
            raise

    def konumlari_getir(self, tur=None):
        if tur is None:
            return self.baglanti.execute(
                """
                SELECT id, ad, tur
                FROM konumlar
                WHERE aktif = 1
                ORDER BY CASE tur
                    WHEN 'MERKEZ' THEN 1
                    WHEN 'DEPO' THEN 2
                    ELSE 3
                END, ad COLLATE NOCASE
                """
            ).fetchall()

        return self.baglanti.execute(
            """
            SELECT id, ad, tur
            FROM konumlar
            WHERE aktif = 1 AND tur = ?
            ORDER BY ad COLLATE NOCASE
            """,
            (tur,)
        ).fetchall()

    def konum_ekle(self, ad, tur):
        ad = ad.strip()

        if ad == "":
            raise ValueError("Konum adı boş bırakılamaz.")

        if tur not in ("DEPO", "SUBE"):
            raise ValueError("Geçersiz konum türü.")

        eski_konum = self.baglanti.execute(
            """
            SELECT id, aktif FROM konumlar
            WHERE ad = ? COLLATE NOCASE
            """,
            (ad,)
        ).fetchone()

        if eski_konum is not None and eski_konum["aktif"] == 1:
            raise ValueError("Bu isimde aktif bir depo veya şube zaten bulunuyor.")

        if eski_konum is not None:
            try:
                self.baglanti.execute("BEGIN")
                self.baglanti.execute(
                    "UPDATE konumlar SET aktif = 1, tur = ? WHERE id = ?",
                    (tur, eski_konum["id"])
                )
                self.baglanti.execute(
                    """
                    INSERT OR IGNORE INTO stoklar (urun_id, konum_id, miktar)
                    SELECT id, ?, 0 FROM urunler WHERE aktif = 1
                    """,
                    (eski_konum["id"],)
                )
                self.baglanti.commit()
                return
            except Exception:
                self.baglanti.rollback()
                raise

        try:
            self.baglanti.execute("BEGIN")
            imlec = self.baglanti.execute(
                "INSERT INTO konumlar (ad, tur) VALUES (?, ?)",
                (ad, tur)
            )
            konum_id = imlec.lastrowid
            self.baglanti.execute(
                """
                INSERT INTO stoklar (urun_id, konum_id, miktar)
                SELECT id, ?, 0 FROM urunler WHERE aktif = 1
                """,
                (konum_id,)
            )
            self.baglanti.commit()
        except sqlite3.IntegrityError:
            self.baglanti.rollback()
            raise ValueError("Bu isimde bir depo veya şube zaten bulunuyor.")
        except Exception:
            self.baglanti.rollback()
            raise

    def konum_guncelle(self, konum_id, yeni_ad):
        yeni_ad = yeni_ad.strip()
        if yeni_ad == "":
            raise ValueError("Konum adı boş bırakılamaz.")

        konum = self.baglanti.execute(
            "SELECT tur FROM konumlar WHERE id = ? AND aktif = 1",
            (konum_id,)
        ).fetchone()
        if konum is None:
            raise ValueError("Konum bulunamadı.")

        try:
            self.baglanti.execute(
                "UPDATE konumlar SET ad = ? WHERE id = ?",
                (yeni_ad, konum_id)
            )
            self.baglanti.commit()
        except sqlite3.IntegrityError:
            raise ValueError("Bu isimde başka bir konum zaten bulunuyor.")

    def konumu_pasiflestir(self, konum_id):
        konum = self.baglanti.execute(
            "SELECT ad, tur FROM konumlar WHERE id = ? AND aktif = 1",
            (konum_id,)
        ).fetchone()
        if konum is None:
            raise ValueError("Konum bulunamadı.")
        if konum["tur"] == "MERKEZ":
            raise ValueError("Merkez Depo kaldırılamaz.")

        toplam_stok = self.baglanti.execute(
            "SELECT COALESCE(SUM(miktar), 0) AS toplam FROM stoklar WHERE konum_id = ?",
            (konum_id,)
        ).fetchone()["toplam"]
        if toplam_stok > 0:
            raise ValueError(
                f"Bu konumda toplam {toplam_stok} adet stok var. Konum boşaltılmadan kaldırılamaz."
            )

        self.baglanti.execute(
            "UPDATE konumlar SET aktif = 0 WHERE id = ?",
            (konum_id,)
        )
        self.baglanti.commit()

    def konum_getir(self, konum_id):
        return self.baglanti.execute(
            "SELECT id, ad, tur FROM konumlar WHERE id = ? AND aktif = 1",
            (konum_id,)
        ).fetchone()

    def hedef_konumlari_getir(self, kaynak_konum_id):
        kaynak = self.konum_getir(kaynak_konum_id)
        if kaynak is None:
            return []
        if kaynak["tur"] == "SUBE":
            return []
        # Merkez ve depolardan, kaynak dışındaki tüm aktif depo/şubelere
        # transfer yapılabilir. Böylece tek depolu işletmeler de doğrudan
        # şubelerini besleyebilir; depo → depo aktarımı da desteklenir.
        return [
            konum for konum in self.konumlari_getir()
            if konum["id"] != kaynak_konum_id
            and konum["tur"] in ("DEPO", "SUBE")
        ]

    def stok_transferi(self, urun_id, kaynak_id, hedef_id, miktar):
        kaynak = self.konum_getir(kaynak_id)
        hedef = self.konum_getir(hedef_id)
        if kaynak is None or hedef is None:
            raise ValueError("Kaynak veya hedef konum bulunamadı.")

        izinli = (
            kaynak["tur"] in ("MERKEZ", "DEPO")
            and hedef["tur"] in ("DEPO", "SUBE")
            and kaynak["id"] != hedef["id"]
        )
        if not izinli:
            raise ValueError("Kaynak merkez/depo; hedef ise farklı bir depo veya şube olmalıdır.")

        kaynak_stok = self.baglanti.execute(
            "SELECT miktar FROM stoklar WHERE urun_id = ? AND konum_id = ?",
            (urun_id, kaynak_id)
        ).fetchone()
        mevcut = 0 if kaynak_stok is None else kaynak_stok["miktar"]
        if miktar <= 0:
            raise ValueError("Transfer miktarı en az 1 olmalıdır.")
        if mevcut < miktar:
            raise ValueError(f"{kaynak['ad']} konumunda yalnızca {mevcut} adet bulunuyor.")

        tarih_saat = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        try:
            self.baglanti.execute("BEGIN")
            self.baglanti.execute(
                "UPDATE stoklar SET miktar = miktar - ? WHERE urun_id = ? AND konum_id = ?",
                (miktar, urun_id, kaynak_id)
            )
            self.baglanti.execute(
                """INSERT INTO stoklar(urun_id, konum_id, miktar) VALUES(?, ?, ?)
                ON CONFLICT(urun_id, konum_id)
                DO UPDATE SET miktar = stoklar.miktar + excluded.miktar""",
                (urun_id, hedef_id, miktar)
            )
            self.baglanti.execute(
                """
                INSERT INTO stok_hareketleri
                (urun_id, kaynak_konum_id, hedef_konum_id, miktar,
                 hareket_turu, tarih_saat, aciklama)
                VALUES (?, ?, ?, ?, 'TRANSFER', ?, ?)
                """,
                (urun_id, kaynak_id, hedef_id, miktar, tarih_saat, "Barkodlu stok transferi")
            )
            self.baglanti.commit()
        except Exception:
            self.baglanti.rollback()
            raise

        return kaynak["ad"], hedef["ad"]

    def subede_satis_yap(self, urun_id, sube_id, miktar):
        sube = self.konum_getir(sube_id)
        if sube is None or sube["tur"] != "SUBE":
            raise ValueError("Satış için geçerli bir şube seçilmelidir.")
        urun = self.baglanti.execute(
            "SELECT ad, fiyat, alis_fiyati FROM urunler WHERE id = ? AND aktif = 1",
            (urun_id,)
        ).fetchone()
        stok = self.baglanti.execute(
            "SELECT miktar FROM stoklar WHERE urun_id = ? AND konum_id = ?",
            (urun_id, sube_id)
        ).fetchone()
        mevcut = 0 if stok is None else stok["miktar"]
        if miktar <= 0:
            raise ValueError("Satış miktarı en az 1 olmalıdır.")
        if mevcut < miktar:
            raise ValueError(f"{sube['ad']} şubesinde yalnızca {mevcut} adet bulunuyor.")

        toplam = miktar * urun["fiyat"]
        tarih_saat = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        try:
            self.baglanti.execute("BEGIN")
            self.baglanti.execute(
                "UPDATE stoklar SET miktar = miktar - ? WHERE urun_id = ? AND konum_id = ?",
                (miktar, urun_id, sube_id)
            )
            self.baglanti.execute(
                """
                INSERT INTO stok_hareketleri
                (urun_id, kaynak_konum_id, hedef_konum_id, miktar,
                 hareket_turu, tarih_saat, aciklama, birim_fiyat, toplam_tutar,
                 alis_fiyati, kullanici_id)
                VALUES (?, ?, NULL, ?, 'SATIS', ?, ?, ?, ?, ?, ?)
                """,
                (urun_id, sube_id, miktar, tarih_saat, "Şubede barkodlu satış", urun["fiyat"], toplam,
                 urun["alis_fiyati"], self.aktif_kullanici_id)
            )
            self.baglanti.commit()
        except Exception:
            self.baglanti.rollback()
            raise
        return urun["ad"], sube["ad"], urun["fiyat"], toplam

    def konum_ozetleri_getir(self):
        return self.baglanti.execute(
            """
            SELECT k.id, k.ad, k.tur,
                   COALESCE(SUM(s.miktar), 0) AS toplam_stok,
                   COALESCE(SUM(s.miktar * u.fiyat), 0) AS toplam_deger
            FROM konumlar AS k
            LEFT JOIN stoklar AS s ON s.konum_id = k.id
            LEFT JOIN urunler AS u ON u.id = s.urun_id AND u.aktif = 1
            WHERE k.aktif = 1
            GROUP BY k.id, k.ad, k.tur
            ORDER BY CASE k.tur WHEN 'MERKEZ' THEN 1 WHEN 'DEPO' THEN 2 ELSE 3 END,
                     k.ad COLLATE NOCASE
            """
        ).fetchall()

    def merkezden_depoya_transfer(self, urun_id, hedef_konum_id, miktar):
        merkez_id = self.merkez_depo_id()

        hedef = self.baglanti.execute(
            """
            SELECT id, ad FROM konumlar
            WHERE id = ? AND tur = 'DEPO' AND aktif = 1
            """,
            (hedef_konum_id,)
        ).fetchone()

        if hedef is None:
            raise ValueError("Hedef depo bulunamadı.")

        kaynak_stok = self.baglanti.execute(
            """
            SELECT miktar FROM stoklar
            WHERE urun_id = ? AND konum_id = ?
            """,
            (urun_id, merkez_id)
        ).fetchone()

        if kaynak_stok is None or kaynak_stok["miktar"] < miktar:
            mevcut = 0 if kaynak_stok is None else kaynak_stok["miktar"]
            raise ValueError(f"Merkez depoda yalnızca {mevcut} adet bulunuyor.")

        tarih_saat = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        try:
            self.baglanti.execute("BEGIN")
            self.baglanti.execute(
                """
                UPDATE stoklar SET miktar = miktar - ?
                WHERE urun_id = ? AND konum_id = ?
                """,
                (miktar, urun_id, merkez_id)
            )
            self.baglanti.execute(
                """
                UPDATE stoklar SET miktar = miktar + ?
                WHERE urun_id = ? AND konum_id = ?
                """,
                (miktar, urun_id, hedef_konum_id)
            )
            self.baglanti.execute(
                """
                INSERT INTO stok_hareketleri
                (urun_id, kaynak_konum_id, hedef_konum_id, miktar,
                 hareket_turu, tarih_saat, aciklama)
                VALUES (?, ?, ?, ?, 'TRANSFER', ?, ?)
                """,
                (
                    urun_id,
                    merkez_id,
                    hedef_konum_id,
                    miktar,
                    tarih_saat,
                    "Merkez depodan il deposuna barkodlu transfer"
                )
            )
            self.baglanti.commit()
        except Exception:
            self.baglanti.rollback()
            raise

        return hedef["ad"]

    def hareketleri_getir(self):
        return self.baglanti.execute(
            """
            SELECT h.tarih_saat, u.barkod, u.ad, h.miktar,
                   h.hareket_turu,
                   kaynak.ad AS kaynak,
                   hedef.ad AS hedef
            FROM stok_hareketleri AS h
            JOIN urunler AS u ON u.id = h.urun_id
            LEFT JOIN konumlar AS kaynak ON kaynak.id = h.kaynak_konum_id
            LEFT JOIN konumlar AS hedef ON hedef.id = h.hedef_konum_id
            ORDER BY h.id DESC
            """
        ).fetchall()

    def ozet_getir(self, konum_id=None):
        if konum_id is None:
            konum_id = self.merkez_depo_id()

        return self.baglanti.execute(
            """
            SELECT COUNT(*) AS urun_sayisi,
                   COALESCE(SUM(s.miktar), 0) AS toplam_stok,
                   COALESCE(SUM(s.miktar * u.fiyat), 0) AS toplam_deger
            FROM stoklar AS s
            JOIN urunler AS u ON u.id = s.urun_id
            WHERE s.konum_id = ? AND u.aktif = 1
            """,
            (konum_id,)
        ).fetchone()

    def kapat(self):
        self.baglanti.close()


def veritabani_yedegi_al():
    if not VERITABANI_YOLU.exists():
        return

    YEDEK_KLASORU.mkdir(parents=True, exist_ok=True)
    bugun = datetime.now().strftime("%Y-%m-%d")
    if any(YEDEK_KLASORU.glob(f"deporiaq_{bugun}_*.db")):
        return
    zaman = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    shutil.copy2(
        VERITABANI_YOLU,
        YEDEK_KLASORU / f"deporiaq_{zaman}.db"
    )

    # En yeni 30 otomatik yedek korunur.
    yedekler = sorted(YEDEK_KLASORU.glob("deporiaq_*.db"), reverse=True)
    for eski_yedek in yedekler[30:]:
        eski_yedek.unlink()


def geri_alma_noktasi_olustur(aciklama="manuel"):
    """Riskli işlem öncesinde tarih damgalı, bağımsız bir SQLite kopyası üretir."""
    if not VERITABANI_YOLU.exists():
        return None
    YEDEK_KLASORU.mkdir(parents=True, exist_ok=True)
    guvenli = "".join(ch if ch.isalnum() else "_" for ch in str(aciklama))[:35]
    hedef = YEDEK_KLASORU / f"GERI_ALMA_{datetime.now():%Y-%m-%d_%H-%M-%S}_{guvenli}.db"
    kaynak = sqlite3.connect(VERITABANI_YOLU); kopya = sqlite3.connect(hedef)
    try: kaynak.backup(kopya)
    finally: kopya.close(); kaynak.close()
    return hedef


def xlsx_yaz(yol, basliklar, satirlar):
    """Harici paket gerektirmeden Excel'in gerçek XLSX biçimini üretir."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    def sutun_adi(no):
        sonuc = ""
        while no:
            no, kalan = divmod(no - 1, 26); sonuc = chr(65 + kalan) + sonuc
        return sonuc
    def hucre(sutun, satir, deger):
        adres = f"{sutun}{satir}"
        if isinstance(deger, (int, float)) and not isinstance(deger, bool):
            return f'<c r="{adres}"><v>{deger}</v></c>'
        return f'<c r="{adres}" t="inlineStr"><is><t>{html.escape("" if deger is None else str(deger))}</t></is></c>'
    tumu = [list(basliklar)] + [list(s) for s in satirlar]
    satir_xml = []
    for r, satir in enumerate(tumu, 1):
        satir_xml.append(f'<row r="{r}">' + "".join(hucre(sutun_adi(c), r, d) for c, d in enumerate(satir, 1)) + '</row>')
    sayfa = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="{ns}"><sheetData>{"".join(satir_xml)}</sheetData></worksheet>'
    dosyalar = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="DeporiaQ Stok" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": sayfa,
    }
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as paket:
        for ad, icerik in dosyalar.items(): paket.writestr(ad, icerik)


def xlsx_oku(yol):
    """İlk çalışma sayfasını satır listesi olarak okur."""
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(yol) as paket:
        paylasilan = []
        if "xl/sharedStrings.xml" in paket.namelist():
            kok = ET.fromstring(paket.read("xl/sharedStrings.xml"))
            paylasilan = ["".join(t.text or "" for t in si.findall(".//x:t", ns)) for si in kok.findall("x:si", ns)]
        sayfa = ET.fromstring(paket.read("xl/worksheets/sheet1.xml"))
    sonuc = []
    for row in sayfa.findall(".//x:sheetData/x:row", ns):
        degerler = []
        for c in row.findall("x:c", ns):
            tur = c.get("t"); v = c.find("x:v", ns)
            if tur == "inlineStr": deger = "".join(t.text or "" for t in c.findall(".//x:t", ns))
            elif v is None: deger = ""
            elif tur == "s": deger = paylasilan[int(v.text)]
            else: deger = v.text or ""
            degerler.append(deger)
        sonuc.append(degerler)
    return sonuc


def veritabani_butunlugunu_kurtar():
    """Bozuk canlı veritabanını korur ve en yeni sağlam yedekten geri yükler."""
    if not VERITABANI_YOLU.exists():
        return None

    def saglam_mi(yol):
        try:
            baglanti = sqlite3.connect(f"file:{yol}?mode=ro", uri=True)
            sonuc = baglanti.execute("PRAGMA quick_check").fetchone()
            tablolar = {
                satir[0] for satir in baglanti.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            baglanti.close()
            return bool(sonuc and sonuc[0] == "ok" and {"urunler", "konumlar", "stoklar"} <= tablolar)
        except sqlite3.Error:
            return False

    if saglam_mi(VERITABANI_YOLU):
        return None

    YEDEK_KLASORU.mkdir(parents=True, exist_ok=True)
    zaman = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    bozuk_kopya = YEDEK_KLASORU / f"deporiaq_bozuk_{zaman}.db"
    shutil.copy2(VERITABANI_YOLU, bozuk_kopya)

    adaylar = sorted(
        (yol for yol in YEDEK_KLASORU.glob("*.db") if "bozuk_" not in yol.name),
        key=lambda yol: yol.stat().st_mtime,
        reverse=True,
    )
    for yedek in adaylar:
        if not saglam_mi(yedek):
            continue
        gecici = VERITABANI_YOLU.with_suffix(".kurtarma.tmp")
        shutil.copy2(yedek, gecici)
        os.replace(gecici, VERITABANI_YOLU)
        return (
            "Veritabanında bir sorun algılandı. En yeni sağlam yedek otomatik "
            f"olarak geri yüklendi: {yedek.name}"
        )

    raise sqlite3.DatabaseError(
        "Veritabanı bozuk ve kullanılabilir sağlam bir yedek bulunamadı. "
        f"Bozuk dosyanın kopyası korundu: {bozuk_kopya}"
    )


def veritabani_doluluk_bilgisi(yol):
    """Taşıma sırasında hangi veritabanının gerçek verileri içerdiğini belirler."""
    if not yol.exists():
        return (0, 0, 0, 0)
    try:
        baglanti = sqlite3.connect(f"file:{yol}?mode=ro", uri=True)
        konum = baglanti.execute("SELECT COUNT(*) FROM konumlar").fetchone()[0]
        hareket = baglanti.execute("SELECT COUNT(*) FROM stok_hareketleri").fetchone()[0]
        stok = baglanti.execute("SELECT COALESCE(SUM(miktar), 0) FROM stoklar").fetchone()[0]
        urun = baglanti.execute("SELECT COUNT(*) FROM urunler").fetchone()[0]
        baglanti.close()
        return (konum, hareket, stok, urun)
    except sqlite3.Error:
        return (0, 0, 0, 0)


def eski_veritabanini_tasi():
    """En dolu eski veritabanını LocalAppData'ya bir kez ve yedekleyerek taşır."""
    VERI_KLASORU.mkdir(parents=True, exist_ok=True)
    if TASIMA_ISARETI.exists():
        return ""

    eski_adaylar = [
        KURULUM_KLASORU / "deporiaq.db",
        KURULUM_KLASORU / "teknostok_v2.db",
    ]
    mevcut_adaylar = [yol for yol in eski_adaylar if yol.exists()]
    if not mevcut_adaylar:
        return ""

    en_dolu_eski = max(mevcut_adaylar, key=veritabani_doluluk_bilgisi)
    eski_bilgi = veritabani_doluluk_bilgisi(en_dolu_eski)
    yeni_bilgi = veritabani_doluluk_bilgisi(VERITABANI_YOLU)

    if not VERITABANI_YOLU.exists() or eski_bilgi > yeni_bilgi:
        if VERITABANI_YOLU.exists():
            YEDEK_KLASORU.mkdir(parents=True, exist_ok=True)
            zaman = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            shutil.copy2(
                VERITABANI_YOLU,
                YEDEK_KLASORU / f"tasima_oncesi_{zaman}.db"
            )
        shutil.copy2(en_dolu_eski, VERITABANI_YOLU)
        sonuc = "Eski dolu veritabanı güvenle taşındı; depo ve stoklar geri yüklendi."
    else:
        sonuc = ""

    TASIMA_ISARETI.write_text(
        f"Kaynak: {en_dolu_eski}\nKaynak bilgi: {eski_bilgi}\nHedef bilgi: {yeni_bilgi}\n",
        encoding="utf-8"
    )
    return sonuc


def ayarlari_oku():
    """Kullanıcı ayarlarını ve kurulumla gelen güncelleme adresini okur."""
    varsayilan = {
        "guncelleme_manifest_url": (
            "https://raw.githubusercontent.com/DeporiaQ/"
            "DeporiaQ-Updates/main/guncelleme_manifest.json"
        )
    }
    kurulum_ayari = KURULUM_KLASORU / "guncelleme_ayarlari.json"
    for yol in (kurulum_ayari, AYARLAR_YOLU):
        if not yol.exists():
            continue
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
            if isinstance(veri, dict):
                varsayilan.update(veri)
        except (OSError, ValueError):
            pass
    return varsayilan


def yerel_ayari_kaydet(anahtar, deger):
    """Parola saklamadan bu bilgisayara ait küçük tercihleri kaydeder."""
    VERI_KLASORU.mkdir(parents=True, exist_ok=True)
    veri = {}
    if AYARLAR_YOLU.exists():
        try:
            okunan = json.loads(AYARLAR_YOLU.read_text(encoding="utf-8"))
            if isinstance(okunan, dict):
                veri.update(okunan)
        except (OSError, ValueError):
            pass
    if deger in (None, ""):
        veri.pop(anahtar, None)
    else:
        veri[anahtar] = deger
    gecici = AYARLAR_YOLU.with_suffix(".json.tmp")
    gecici.write_text(
        json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    gecici.replace(AYARLAR_YOLU)


def surum_parcalari(surum):
    """1.2.10 gibi sürümleri sayısal karşılaştırmaya hazırlar."""
    try:
        return tuple(int(parca) for parca in str(surum).split("."))
    except ValueError:
        return (0,)


def parola_ozeti_olustur(parola):
    """Parolayı düz metin yerine güvenli PBKDF2 özeti olarak saklar."""
    tuz = secrets.token_hex(16)
    ozet = hashlib.pbkdf2_hmac(
        "sha256", parola.encode("utf-8"), bytes.fromhex(tuz), 200_000
    ).hex()
    return f"pbkdf2_sha256${tuz}${ozet}"


def parola_ozeti_dogrula(parola, kayitli_ozet):
    """Parolayı kayıtlı PBKDF2 özetiyle güvenli biçimde karşılaştırır."""
    try:
        algoritma, tuz, beklenen = kayitli_ozet.split("$", 2)
        if algoritma != "pbkdf2_sha256":
            return False
        hesaplanan = hashlib.pbkdf2_hmac(
            "sha256", parola.encode("utf-8"), bytes.fromhex(tuz), 200_000
        ).hex()
        return secrets.compare_digest(hesaplanan, beklenen)
    except (AttributeError, TypeError, ValueError):
        return False


def parola_guclu_mu(parola):
    """Yönetici parolasının şirket hesabına uygun gücünü denetler."""
    kosullar_saglandi = (
        len(parola) >= 14
        and not any(karakter.isspace() for karakter in parola)
        and any(karakter.isupper() for karakter in parola)
        and any(karakter.islower() for karakter in parola)
        and any(karakter.isdigit() for karakter in parola)
        and any(not karakter.isalnum() for karakter in parola)
    )
    if not kosullar_saglandi:
        return False, (
            "Yönetici parolası en az 14 karakter olmalı; en az bir büyük harf, "
            "bir küçük harf, bir rakam ve *, #, ! gibi bir özel sembol "
            "içermelidir. Boşluk kullanılamaz."
        )
    return True, ""


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def windows_sifrele(metin):
    """Metni yalnızca mevcut Windows kullanıcısının açabileceği DPAPI verisine çevirir."""
    if os.name != "nt" or not metin:
        return ""
    veri = metin.encode("utf-8")
    tampon = ctypes.create_string_buffer(veri)
    giris = _DATA_BLOB(len(veri), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_byte)))
    cikis = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(giris), "DeporiaQ Cloud", None, None, None, 0,
        ctypes.byref(cikis)
    ):
        raise ctypes.WinError()
    try:
        sifreli = ctypes.string_at(cikis.pbData, cikis.cbData)
        return base64.b64encode(sifreli).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(cikis.pbData)


def windows_sifre_coz(sifreli):
    if os.name != "nt" or not sifreli:
        return ""
    veri = base64.b64decode(sifreli)
    tampon = ctypes.create_string_buffer(veri)
    giris = _DATA_BLOB(len(veri), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_byte)))
    cikis = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(giris), None, None, None, None, 0, ctypes.byref(cikis)
    ):
        return ""
    try:
        return ctypes.string_at(cikis.pbData, cikis.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(cikis.pbData)


class DeporiaQCloud:
    """Supabase Auth ve REST API kullanan güvenli istemci.

    Yalnızca yayınlanabilir anahtar kullanır. service_role anahtarı masaüstü
    uygulamasına hiçbir zaman konulmamalıdır.
    """

    def __init__(self, vt, cihaz_kimligi):
        self.vt = vt
        self.cihaz_kimligi = cihaz_kimligi
        self.url = ""
        self.anahtar = ""
        self.access_token = ""
        self.refresh_token = ""
        self.user_id = ""
        self.company_id = ""
        self.company_name = ""
        self.role = ""
        self.local_username = ""
        self.location_name = ""

    @property
    def bagli(self):
        return bool(self.access_token and self.company_id)

    def yapilandir(self, url, anahtar):
        self.url = str(url).strip().rstrip("/")
        self.anahtar = str(anahtar).strip()
        if not self.url.startswith("https://") or ".supabase.co" not in self.url:
            raise ValueError("Geçerli Supabase Project URL giriniz.")
        if len(self.anahtar) < 20:
            raise ValueError("Geçerli publishable/anon key giriniz.")

    def _istek(self, yol, method="GET", veri=None, tercih=None, auth=True):
        govde = None if veri is None else json.dumps(veri).encode("utf-8")
        basliklar = {
            "apikey": self.anahtar,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"{PROGRAM_ADI}/{PROGRAM_SURUMU}",
        }
        if auth and self.access_token:
            basliklar["Authorization"] = f"Bearer {self.access_token}"
        if tercih:
            basliklar["Prefer"] = tercih
        istek = urllib.request.Request(
            self.url + yol, data=govde, headers=basliklar, method=method
        )
        try:
            with urllib.request.urlopen(istek, timeout=12) as cevap:
                ham = cevap.read().decode("utf-8")
                return json.loads(ham) if ham else None
        except urllib.error.HTTPError as hata:
            ayrinti = hata.read().decode("utf-8", errors="replace")
            try:
                mesaj = json.loads(ayrinti).get("message") or json.loads(ayrinti).get("error_description")
            except (ValueError, AttributeError):
                mesaj = ayrinti
            raise RuntimeError(f"Cloud isteği reddedildi ({hata.code}): {mesaj}") from hata
        except urllib.error.URLError as hata:
            raise RuntimeError(f"Cloud sunucusuna ulaşılamadı: {hata.reason}") from hata

    def giris_yap(self, email, parola):
        sonuc = self._istek(
            "/auth/v1/token?grant_type=password", "POST",
            {"email": email.strip(), "password": parola}, auth=False
        )
        self.access_token = sonuc.get("access_token", "")
        self.refresh_token = sonuc.get("refresh_token", "")
        self.user_id = sonuc.get("user", {}).get("id", "")
        if not self.access_token:
            raise RuntimeError("Cloud oturumu açılamadı.")
        uyelikler = self._istek(
            "/rest/v1/company_members?select=company_id,role&active=eq.true&limit=1"
        ) or []
        if not uyelikler:
            self.cikis_yap()
            raise RuntimeError("Bu hesabın etkin bir DeporiaQ işletme üyeliği yok.")
        self.company_id = uyelikler[0]["company_id"]
        self.role = uyelikler[0]["role"]
        sirketler = self._istek(
            f"/rest/v1/companies?select=name&id=eq.{self.company_id}&limit=1"
        ) or []
        self.company_name = sirketler[0]["name"] if sirketler else "DeporiaQ Cloud"
        self._cihazi_kaydet()
        return self.company_name

    def oturumu_yenile(self, refresh_token):
        sonuc = self._istek(
            "/auth/v1/token?grant_type=refresh_token", "POST",
            {"refresh_token": refresh_token}, auth=False
        )
        self.access_token = sonuc.get("access_token", "")
        self.refresh_token = sonuc.get("refresh_token", refresh_token)
        self.user_id = sonuc.get("user", {}).get("id", "")
        if not self.access_token:
            raise RuntimeError("Cloud oturumu yenilenemedi.")
        uyelikler = self._istek(
            "/rest/v1/company_members?select=company_id,role&active=eq.true&limit=1"
        ) or []
        if not uyelikler:
            self.cikis_yap()
            raise RuntimeError("Etkin işletme üyeliği bulunamadı.")
        self.company_id, self.role = uyelikler[0]["company_id"], uyelikler[0]["role"]
        sirketler = self._istek(
            f"/rest/v1/companies?select=name&id=eq.{self.company_id}&limit=1"
        ) or []
        self.company_name = sirketler[0]["name"] if sirketler else "DeporiaQ Cloud"
        self._cihazi_kaydet()
        return self.company_name

    def cikis_yap(self):
        self.access_token = self.refresh_token = self.user_id = self.company_id = ""
        self.company_name = self.role = ""

    def _cihazi_kaydet(self):
        mevcut = self._istek(
            f"/rest/v1/cloud_devices?select=id,active&company_id=eq.{self.company_id}&device_code=eq.{urllib.parse.quote(self.cihaz_kimligi)}&limit=1"
        ) or []
        if mevcut and not mevcut[0].get("active", True):
            raise RuntimeError("Bu cihazın Cloud erişimi işletme yöneticisi tarafından kapatıldı.")
        veri = [{
            "company_id": self.company_id,
            "user_id": self.user_id,
            "device_code": self.cihaz_kimligi,
            "device_name": os.getenv("COMPUTERNAME", "Windows PC"),
            "app_version": PROGRAM_SURUMU,
            "last_seen_at": datetime.now().astimezone().isoformat(),
            "active": True,
            "local_username": self.local_username or os.getenv("USERNAME", "DeporiaQ Kullanıcısı"),
            "location_name": self.location_name or "Atanmamış",
        }]
        try:
            self._istek(
                "/rest/v1/cloud_devices?on_conflict=company_id,device_code",
                "POST", veri, "resolution=merge-duplicates,return=minimal"
            )
        except RuntimeError as hata:
            if "local_username" not in str(hata) and "location_name" not in str(hata):
                raise
            veri[0].pop("local_username", None); veri[0].pop("location_name", None)
            self._istek(
                "/rest/v1/cloud_devices?on_conflict=company_id,device_code",
                "POST", veri, "resolution=merge-duplicates,return=minimal"
            )

    def _liste(self, tablo, select="*"):
        secim = urllib.parse.quote(select, safe="*,()")
        return self._istek(
            f"/rest/v1/{tablo}?select={secim}&company_id=eq.{self.company_id}"
        ) or []

    def _yerel_kanonik(self):
        konumlar = [dict(x) for x in self.vt.baglanti.execute(
            "SELECT ad,tur,aktif FROM konumlar ORDER BY ad"
        )]
        urunler = [dict(x) for x in self.vt.baglanti.execute(
            """SELECT barkod,ad,fiyat,alis_fiyati,kritik_stok,aktif
               FROM urunler ORDER BY barkod"""
        )]
        stoklar = [dict(x) for x in self.vt.baglanti.execute(
            """SELECT u.barkod,k.ad AS konum_adi,s.miktar
               FROM stoklar s JOIN urunler u ON u.id=s.urun_id
               JOIN konumlar k ON k.id=s.konum_id
               ORDER BY u.barkod,k.ad"""
        )]
        return {"konumlar": konumlar, "urunler": urunler, "stoklar": stoklar}

    def _bulut_kanonik(self):
        konumlar = self._liste("locations")
        urunler = self._liste("products")
        stoklar = self._liste("inventory")
        konum_adlari = {k["id"]: k["name"] for k in konumlar}
        urun_barkodlari = {u["id"]: u["barcode"] for u in urunler}
        return {
            "konumlar": sorted([{
                "ad": k["name"],
                "tur": {"center":"MERKEZ","warehouse":"DEPO","branch":"SUBE"}.get(k["location_type"], "DEPO"),
                "aktif": int(bool(k["active"])),
            } for k in konumlar], key=lambda x: x["ad"]),
            "urunler": sorted([{
                "barkod": u["barcode"], "ad": u["name"],
                "fiyat": float(u["sale_price"]), "alis_fiyati": float(u["purchase_price"]),
                "kritik_stok": int(float(u["critical_stock"])), "aktif": int(bool(u["active"])),
            } for u in urunler], key=lambda x: x["barkod"]),
            "stoklar": sorted([{
                "barkod": urun_barkodlari.get(s["product_id"], ""),
                "konum_adi": konum_adlari.get(s["location_id"], ""),
                "miktar": int(float(s["quantity"])),
            } for s in stoklar], key=lambda x: (x["barkod"], x["konum_adi"])),
        }

    @staticmethod
    def _ozet(veri):
        ham = json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(ham.encode("utf-8")).hexdigest()

    def _durum_getir(self, anahtar, varsayilan=""):
        satir = self.vt.baglanti.execute(
            "SELECT deger FROM cloud_sync_durumu WHERE anahtar=?", (anahtar,)
        ).fetchone()
        return satir["deger"] if satir else varsayilan

    def _durum_kaydet(self, anahtar, deger):
        self.vt.baglanti.execute(
            """INSERT INTO cloud_sync_durumu(anahtar,deger) VALUES(?,?)
               ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger""",
            (anahtar, str(deger))
        )
        self.vt.baglanti.commit()

    def senkron_baslangic_noktasi_kaydet(self):
        yerel = self._yerel_kanonik()
        bulut = self._bulut_kanonik()
        self._durum_kaydet("son_yerel_ozet", self._ozet(yerel))
        self._durum_kaydet("son_bulut_ozet", self._ozet(bulut))
        self._durum_kaydet("son_senkron", datetime.now().astimezone().isoformat())
        if not self._durum_getir("son_hareket_id"):
            son = self.vt.baglanti.execute("SELECT COALESCE(MAX(id),0) FROM stok_hareketleri").fetchone()[0]
            self._durum_kaydet("son_hareket_id", son)

    def bekleyen_hareketleri_atomik_gonder(self):
        """Yeni yerel stok hareketlerini idempotent Supabase RPC'lerine yollar."""
        kayitli = self._durum_getir("son_hareket_id")
        if not kayitli:
            son = self.vt.baglanti.execute("SELECT COALESCE(MAX(id),0) FROM stok_hareketleri").fetchone()[0]
            self._durum_kaydet("son_hareket_id", son)
            return 0
        son = int(kayitli)
        hareketler = self.vt.baglanti.execute(
            """SELECT h.*,u.barkod,k1.ad kaynak,k2.ad hedef FROM stok_hareketleri h
               JOIN urunler u ON u.id=h.urun_id LEFT JOIN konumlar k1 ON k1.id=h.kaynak_konum_id
               LEFT JOIN konumlar k2 ON k2.id=h.hedef_konum_id WHERE h.id>? ORDER BY h.id""", (son,)
        ).fetchall()
        if not hareketler: return 0
        uzak_k = {x["name"]: x["id"] for x in self._liste("locations", "id,name")}
        uzak_u = {x["barcode"]: x["id"] for x in self._liste("products", "id,barcode")}
        if any(h["barkod"] not in uzak_u or (h["kaynak"] and h["kaynak"] not in uzak_k)
               or (h["hedef"] and h["hedef"] not in uzak_k) for h in hareketler):
            # Yeni ürün/konum önce tam anlık görüntüyle oluşturulmalıdır.
            return -1
        sayi = 0
        for h in hareketler:
            anahtar = f"{self.cihaz_kimligi}-{h['id']}"
            ortak = {"p_company_id": self.company_id, "p_product_id": uzak_u.get(h["barkod"]),
                     "p_quantity": float(h["miktar"]), "p_device_id": self.cihaz_kimligi,
                     "p_note": h["aciklama"] or "DeporiaQ 0.12 otomatik senkron"}
            if h["kaynak"] and h["hedef"]:
                veri = dict(ortak, p_source_location_id=uzak_k.get(h["kaynak"]),
                            p_target_location_id=uzak_k.get(h["hedef"]), p_operation_key=anahtar)
                self._istek("/rest/v1/rpc/apply_stock_transfer_v2", "POST", veri)
            else:
                konum = h["hedef"] or h["kaynak"]
                veri = dict(ortak, p_location_id=uzak_k.get(konum),
                            p_direction="increase" if h["hedef"] else "decrease",
                            p_movement_type=h["hareket_turu"], p_operation_key=anahtar)
                self._istek("/rest/v1/rpc/apply_stock_movement_v2", "POST", veri)
            self._durum_kaydet("son_hareket_id", h["id"]); sayi += 1
        return sayi

    def akilli_senkronize(self):
        if not self.bagli:
            return "BAGLI_DEGIL", None
        atomik_sonuc = 0
        if self.role in ("owner", "admin", "manager"):
            atomik_sonuc = self.bekleyen_hareketleri_atomik_gonder()
        yerel = self._yerel_kanonik(); bulut = self._bulut_kanonik()
        yerel_ozet, bulut_ozet = self._ozet(yerel), self._ozet(bulut)
        son_yerel = self._durum_getir("son_yerel_ozet")
        son_bulut = self._durum_getir("son_bulut_ozet")
        if not son_yerel or not son_bulut:
            if yerel_ozet == bulut_ozet:
                self.senkron_baslangic_noktasi_kaydet()
                return "GUNCEL", None
            return self._cakisma_ekle(yerel_ozet, bulut_ozet)
        yerel_degisti = yerel_ozet != son_yerel
        bulut_degisti = bulut_ozet != son_bulut
        if yerel_degisti and bulut_degisti and yerel_ozet != bulut_ozet:
            return self._cakisma_ekle(yerel_ozet, bulut_ozet)
        if yerel_degisti:
            if self.role not in ("owner", "admin", "manager"):
                return "YETKI_BEKLIYOR", None
            sonuc = self.yereli_buluta_gonder()
            if atomik_sonuc == -1:
                son = self.vt.baglanti.execute("SELECT COALESCE(MAX(id),0) FROM stok_hareketleri").fetchone()[0]
                self._durum_kaydet("son_hareket_id", son)
            self.senkron_baslangic_noktasi_kaydet()
            return "YUKLENDI", sonuc
        if bulut_degisti:
            sonuc = self.buluttan_yere_indir()
            self.senkron_baslangic_noktasi_kaydet()
            return "INDIRILDI", sonuc
        self._durum_kaydet("son_senkron", datetime.now().astimezone().isoformat())
        self._cihazi_kaydet()
        return "GUNCEL", None

    def _cakisma_ekle(self, yerel_ozet, bulut_ozet):
        kimlik = hashlib.sha256(f"{yerel_ozet}:{bulut_ozet}".encode()).hexdigest()[:24]
        self.vt.baglanti.execute(
            """INSERT OR IGNORE INTO cloud_cakismalari
               (cakisma_kimligi,yerel_ozet,bulut_ozet,durum,tarih_saat)
               VALUES(?,?,?,'BEKLIYOR',?)""",
            (kimlik, yerel_ozet, bulut_ozet, datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        )
        self.vt.baglanti.commit()
        return "CAKISMA", kimlik

    def cakisma_sayisi(self):
        return self.vt.baglanti.execute(
            "SELECT COUNT(*) FROM cloud_cakismalari WHERE durum='BEKLIYOR'"
        ).fetchone()[0]

    def cakismayi_coz(self, secim):
        if secim == "YEREL":
            if self.role not in ("owner", "admin", "manager"):
                raise RuntimeError("Yerel veriyi uygulamak için yönetici yetkisi gerekir.")
            self.yereli_buluta_gonder()
        elif secim == "BULUT":
            veritabani_yedegi_al()
            self.buluttan_yere_indir()
        else:
            raise ValueError("Geçersiz çakışma çözümü.")
        self.vt.baglanti.execute(
            "UPDATE cloud_cakismalari SET durum='COZULDU',cozum=? WHERE durum='BEKLIYOR'",
            (secim,)
        )
        self.vt.baglanti.commit()
        self.senkron_baslangic_noktasi_kaydet()

    def cihazlari_getir(self):
        try:
            return self._liste("cloud_devices", "id,device_code,device_name,app_version,last_seen_at,active,user_id,local_username,location_name")
        except RuntimeError:
            return self._liste("cloud_devices", "id,device_code,device_name,app_version,last_seen_at,active,user_id")

    def uyeleri_getir(self):
        """Oturum açmış kullanıcının görebildiği işletme üyeliklerini getirir."""
        if not self.bagli:
            return []
        return self._liste("company_members", "user_id,role,active")

    def cihaz_durumunu_degistir(self, cihaz_id, aktif):
        if self.role not in ("owner", "admin"):
            raise RuntimeError("Cihaz yönetimi için Ana Yönetici yetkisi gerekir.")
        self._istek(
            f"/rest/v1/cloud_devices?id=eq.{cihaz_id}", "PATCH",
            {"active": bool(aktif)}, "return=minimal"
        )

    def urun_talebi_gonder(self,veri):
        if not self.bagli:return
        kayit=dict(veri);kayit.update({"company_id":self.company_id,"requested_by":self.user_id})
        self._istek("/rest/v1/product_change_requests","POST",[kayit],"return=minimal")

    def urun_talepleri_getir(self):
        if not self.bagli:return []
        return self._istek(f"/rest/v1/product_change_requests?select=*&company_id=eq.{self.company_id}&order=created_at.desc&limit=100") or []

    def urun_talebi_karar(self,talep_id,durum):
        if self.role not in ("owner","admin","manager"):raise RuntimeError("Talep kararı için yönetici yetkisi gerekir.")
        self._istek(f"/rest/v1/product_change_requests?id=eq.{talep_id}","PATCH",{"status":durum,"decided_by":self.user_id,"decided_at":datetime.now().astimezone().isoformat()},"return=minimal")

    def yereli_buluta_gonder(self):
        if not self.bagli:
            raise RuntimeError("Önce Cloud oturumu açın.")
        konumlar = [dict(s) for s in self.vt.baglanti.execute(
            "SELECT id, ad, tur, aktif FROM konumlar"
        ).fetchall()]
        konum_verisi = [{
            "company_id": self.company_id, "name": k["ad"],
            "location_type": {"MERKEZ":"center", "DEPO":"warehouse", "SUBE":"branch"}.get(k["tur"], "warehouse"),
            "active": bool(k["aktif"]),
        } for k in konumlar]
        if konum_verisi:
            self._istek(
                "/rest/v1/locations?on_conflict=company_id,name", "POST",
                konum_verisi, "resolution=merge-duplicates,return=minimal"
            )

        urunler = [dict(s) for s in self.vt.baglanti.execute(
            "SELECT barkod, ad, fiyat, alis_fiyati, kritik_stok, aktif FROM urunler"
        ).fetchall()]
        urun_verisi = [{
            "company_id": self.company_id, "barcode": u["barkod"],
            "name": u["ad"], "purchase_price": float(u["alis_fiyati"] or 0),
            "sale_price": float(u["fiyat"] or 0),
            "critical_stock": float(u["kritik_stok"] or 0), "active": bool(u["aktif"]),
        } for u in urunler]
        if urun_verisi:
            for baslangic in range(0, len(urun_verisi), 250):
                self._istek(
                    "/rest/v1/products?on_conflict=company_id,barcode", "POST",
                    urun_verisi[baslangic:baslangic+250],
                    "resolution=merge-duplicates,return=minimal"
                )

        uzak_konum = {k["name"]: k["id"] for k in self._liste("locations", "id,name")}
        uzak_urun = {u["barcode"]: u["id"] for u in self._liste("products", "id,barcode")}
        stoklar = self.vt.baglanti.execute(
            """SELECT u.barkod, k.ad AS konum_adi, s.miktar
               FROM stoklar s JOIN urunler u ON u.id=s.urun_id
               JOIN konumlar k ON k.id=s.konum_id"""
        ).fetchall()
        stok_verisi = [{
            "company_id": self.company_id,
            "location_id": uzak_konum[s["konum_adi"]],
            "product_id": uzak_urun[s["barkod"]],
            "quantity": float(s["miktar"]),
        } for s in stoklar if s["konum_adi"] in uzak_konum and s["barkod"] in uzak_urun]
        for baslangic in range(0, len(stok_verisi), 250):
            self._istek(
                "/rest/v1/inventory?on_conflict=company_id,location_id,product_id",
                "POST", stok_verisi[baslangic:baslangic+250],
                "resolution=merge-duplicates,return=minimal"
            )
        self.vt.baglanti.execute("UPDATE senkron_kuyrugu SET gonderildi=1")
        self.vt.ayar_kaydet("cloud_etkin", "1")
        self.vt.baglanti.commit()
        self._cihazi_kaydet()
        return len(urun_verisi), len(konum_verisi), len(stok_verisi)

    def buluttan_yere_indir(self):
        if not self.bagli:
            raise RuntimeError("Önce Cloud oturumu açın.")
        konumlar = self._liste("locations")
        urunler = self._liste("products")
        stoklar = self._liste("inventory")
        onceki = self.vt.ayar_getir("cloud_etkin", "0")
        self.vt.ayar_kaydet("cloud_etkin", "0")
        try:
            with self.vt.baglanti:
                for k in konumlar:
                    tur = {"center":"MERKEZ", "warehouse":"DEPO", "branch":"SUBE"}.get(k["location_type"], "DEPO")
                    self.vt.baglanti.execute(
                        """INSERT INTO konumlar(ad,tur,aktif) VALUES(?,?,?)
                           ON CONFLICT(ad) DO UPDATE SET tur=excluded.tur,aktif=excluded.aktif""",
                        (k["name"], tur, int(k["active"]))
                    )
                for u in urunler:
                    self.vt.baglanti.execute(
                        """INSERT INTO urunler(barkod,ad,fiyat,alis_fiyati,kritik_stok,aktif)
                           VALUES(?,?,?,?,?,?) ON CONFLICT(barkod) DO UPDATE SET
                           ad=excluded.ad,fiyat=excluded.fiyat,alis_fiyati=excluded.alis_fiyati,
                           kritik_stok=excluded.kritik_stok,aktif=excluded.aktif""",
                        (u["barcode"], u["name"], float(u["sale_price"]),
                         float(u["purchase_price"]), int(float(u["critical_stock"])), int(u["active"]))
                    )
                uzak_konum = {k["id"]: k["name"] for k in konumlar}
                uzak_urun = {u["id"]: u["barcode"] for u in urunler}
                for s in stoklar:
                    yerel_k = self.vt.baglanti.execute("SELECT id FROM konumlar WHERE ad=?", (uzak_konum.get(s["location_id"]),)).fetchone()
                    yerel_u = self.vt.baglanti.execute("SELECT id FROM urunler WHERE barkod=?", (uzak_urun.get(s["product_id"]),)).fetchone()
                    if yerel_k and yerel_u:
                        self.vt.baglanti.execute(
                            """INSERT INTO stoklar(urun_id,konum_id,miktar) VALUES(?,?,?)
                               ON CONFLICT(urun_id,konum_id) DO UPDATE SET miktar=excluded.miktar""",
                            (yerel_u["id"], yerel_k["id"], int(float(s["quantity"])))
                        )
                self.vt.ayar_kaydet("cloud_etkin", "1" if self.bagli else onceki)
        except Exception:
            self.vt.ayar_kaydet("cloud_etkin", onceki)
            self.vt.baglanti.commit()
            raise
        self._cihazi_kaydet()
        return len(urunler), len(konumlar), len(stoklar)

    def mevcut_isletmeyi_bu_cihaza_kur(self, kullanici_adi, yerel_parola):
        """Temiz bir bilgisayarı doğrulanmış Cloud işletmesine bağlar."""
        if not self.bagli:
            raise RuntimeError("Önce Cloud hesabıyla oturum açın.")
        if not self.vt.ilk_kurulum_gerekli():
            raise RuntimeError("Bu bilgisayarda DeporiaQ kurulumu zaten tamamlanmış.")
        konumlar = self._liste("locations")
        if not konumlar:
            raise RuntimeError("Cloud işletmesinde etkin bir merkez/depo/şube bulunamadı.")
        merkez = next((k for k in konumlar if k.get("location_type") == "center"), konumlar[0])
        yerel_rol = {
            "owner": "ANA_YONETICI", "admin": "ANA_YONETICI", "manager": "ANA_YONETICI",
            "employee": "DEPO_PERSONELI", "warehouse": "DEPO_PERSONELI",
            "branch": "SUBE_PERSONELI", "viewer": "GORUNTULEYICI",
        }.get(str(self.role).lower(), "GORUNTULEYICI")
        try:
            self.vt.ilk_kurulumu_tamamla(
                self.company_name, "Cloud işletmesi", merkez["name"], "TL",
                kullanici_adi.strip(), yerel_parola,
            )
            sonuc = self.buluttan_yere_indir()
            konum = self.vt.baglanti.execute(
                "SELECT id FROM konumlar WHERE ad=? LIMIT 1", (merkez["name"],)
            ).fetchone()
            self.vt.baglanti.execute(
                "UPDATE kullanicilar SET rol=?, konum_id=? WHERE kullanici_adi=?",
                (yerel_rol, konum["id"] if konum else None, kullanici_adi.strip()),
            )
            self.vt.ayar_kaydet("cloud_etkin", "1")
            self.vt.baglanti.commit()
            self.local_username = kullanici_adi.strip()
            self.location_name = merkez["name"]
            self._cihazi_kaydet()
            return sonuc
        except Exception:
            # Yarım kalan ilk bağlantı bir sonraki denemeyi engellemesin.
            with self.vt.baglanti:
                self.vt.baglanti.execute("DELETE FROM kullanicilar")
                self.vt.baglanti.execute("DELETE FROM stoklar")
                self.vt.baglanti.execute("DELETE FROM urunler")
                self.vt.baglanti.execute("DELETE FROM konumlar")
                self.vt.baglanti.execute("DELETE FROM ayarlar")
            raise


class TeknoStokUygulamasi:
    def __init__(self):
        self.hazir = False
        self.tasima_sonucu = eski_veritabanini_tasi()
        self.kurtarma_sonucu = veritabani_butunlugunu_kurtar()
        veritabani_yedegi_al()
        self.vt = Veritabani(VERITABANI_YOLU)
        self.ayarlar = ayarlari_oku()
        self.tema = str(self.ayarlar.get("uygulama_temasi", "koyu")).lower()
        tema_renklerini_ayarla(self.tema)
        self.dil = str(self.ayarlar.get("uygulama_dili", "tr")).lower()
        self.cihaz_kimligi = str(self.ayarlar.get("cihaz_kimligi", "")).strip()
        if not self.cihaz_kimligi:
            self.cihaz_kimligi = "DPQ-" + secrets.token_hex(6).upper()
            yerel_ayari_kaydet("cihaz_kimligi", self.cihaz_kimligi)
            self.ayarlar["cihaz_kimligi"] = self.cihaz_kimligi
        self.cloud = DeporiaQCloud(self.vt, self.cihaz_kimligi)
        self.secili_urun = None
        self.aktif_kullanici = None
        self.oturum_acik = False
        self.oturum_id = None
        self.son_etkinlik_zamani = time.monotonic()
        self.ilk_ana_ekran_acilisi = True
        self.son_satis = None
        self.sayfa_yigini = []

        self.pencere = ttk.Window(themename="flatly" if self.tema == "acik" else "darkly")
        self.cloud_durum_metni = tk.StringVar(value="● Cloud kapalı")
        self.cloud_dongu_aktif = False
        self.stilleri_hazirla()
        self.pencere.title(f"{PROGRAM_ADI} {PROGRAM_SURUMU}")
        self.pencere.geometry("620x520")
        self.pencere.minsize(560, 470)
        self.pencere.protocol("WM_DELETE_WINDOW", self.programi_kapat)
        self.pencere.after(80, self.windows_baslik_cubugunu_duzenle)

        if self.vt.ilk_kurulum_gerekli():
            self.pencere.withdraw()
            if not self.ilk_kurulum_sihirbazini_ac():
                self.vt.kapat()
                self.pencere.destroy()
                return
            self.pencere.deiconify()

        self.isletme_adi = self.vt.ayar_getir("isletme_adi", PROGRAM_ADI)

        self.arama_degiskeni = tk.StringVar()
        self.barkod_degiskeni = tk.StringVar()
        self.miktar_degiskeni = tk.StringVar()
        self.secili_urun_degiskeni = tk.StringVar(
            value="Barkod okutulduğunda ürün burada görünecek"
        )
        self.konum_degiskeni = tk.StringVar(value="Merkez Depo")
        self.konum_haritasi = {}
        self.tum_konum_adlari = []
        self.tum_urun_adlari = []

        self.pencere.bind_all("<Any-KeyPress>", self.etkinlik_kaydet, add="+")
        self.pencere.bind_all("<Any-Button>", self.etkinlik_kaydet, add="+")
        self.giris_ekranini_goster()
        self.pencere.after(30_000, self.otomatik_kilidi_kontrol_et)
        self.hazir = True

    def ekrani_temizle(self):
        """Ana pencerenin içeriğini güvenli biçimde temizler."""
        self.sayfa_yigini.clear()
        for arac in self.pencere.winfo_children():
            arac.destroy()

    def stilleri_hazirla(self):
        """Uygulamanın tamamında okunaklı ve tutarlı yazı sistemini kurar."""
        stil = self.pencere.style
        stil.configure("TLabel", font=(YAZI_TIPI, 10))
        stil.configure("TButton", font=(YAZI_TIPI, 10, "bold"), padding=(12, 7))
        stil.configure("TEntry", font=(YAZI_TIPI, 10))
        stil.configure("TCombobox", font=(YAZI_TIPI, 10))
        stil.configure("TLabelframe.Label", font=(YAZI_TIPI, 10, "bold"))
        stil.configure("Treeview", font=(YAZI_TIPI, 10), rowheight=32)
        stil.configure("Treeview.Heading", font=(YAZI_TIPI, 10, "bold"))

    def cevir(self, metin):
        """Kaynak Türkçe arayüz metnini seçili dile çevirir."""
        if self.dil != "en":
            return metin
        temiz = str(metin).strip()
        ceviri = INGILIZCE_METINLER.get(temiz)
        if ceviri is None:
            # Sayaç içeren düğmeleri de çevir: Kritik Stoklar (12)
            if temiz.startswith("Kritik Stoklar ("):
                ceviri = temiz.replace("Kritik Stoklar", "Critical Stock", 1)
            else:
                return metin
        sol = len(str(metin)) - len(str(metin).lstrip())
        sag = len(str(metin)) - len(str(metin).rstrip())
        return " " * sol + ceviri + " " * sag

    def arayuzu_cevir(self, kok=None):
        """Oluşturulmuş Tk/ttk araçlarını ve tablo başlıklarını yerinde çevirir."""
        if self.dil != "en":
            return
        kok = kok or self.pencere
        try:
            araclar = [kok] + list(kok.winfo_children())
        except tk.TclError:
            return
        for arac in araclar:
            try:
                if "text" in arac.keys():
                    mevcut = arac.cget("text")
                    arac.configure(text=self.cevir(mevcut))
                if isinstance(arac, ttk.Treeview):
                    for sutun in arac["columns"]:
                        baslik = arac.heading(sutun).get("text", "")
                        arac.heading(sutun, text=self.cevir(baslik))
                if isinstance(arac, ttk.Notebook):
                    for sekme in arac.tabs():
                        arac.tab(sekme, text=self.cevir(arac.tab(sekme, "text")))
            except (tk.TclError, KeyError, TypeError):
                pass
            if arac is not kok:
                self.arayuzu_cevir(arac)

    def windows_baslik_cubugunu_duzenle(self):
        """Windows başlık çubuğunu uygulamanın koyu yüzeyiyle bütünleştirir."""
        if os.name != "nt":
            return
        try:
            self.pencere.update_idletasks()
            pencere_tutamaci = ctypes.windll.user32.GetParent(self.pencere.winfo_id())
            koyu = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                pencere_tutamaci, 20, ctypes.byref(koyu), ctypes.sizeof(koyu)
            )
            # COLORREF biçimi: 0x00BBGGRR
            arka_plan = ctypes.c_int(0x00212121)
            beyaz = ctypes.c_int(0x00F8FAFC)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                pencere_tutamaci, 35, ctypes.byref(arka_plan), ctypes.sizeof(arka_plan)
            )
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                pencere_tutamaci, 36, ctypes.byref(beyaz), ctypes.sizeof(beyaz)
            )
        except (AttributeError, OSError, tk.TclError):
            pass

    def kabartmali_marka(
        self, ebeveyn, alt_metin="", boyut=26, dolgu=(0, 0), genislik=560
    ):
        """Arka plan kutusu olmadan gölgeli DeporiaQ marka başlığı oluşturur."""
        alan = tk.Frame(ebeveyn, bg=RENK_ZEMIN, padx=dolgu[0], pady=dolgu[1])
        marka = tk.Frame(alan, bg=RENK_ZEMIN, height=52, width=genislik)
        marka.pack(fill=X)
        marka.pack_propagate(False)
        # Marka ve sürüm aynı görsel ağırlıkta değildir: marka ana kimlik,
        # sürüm ise küçük teknik bilgidir.
        tk.Label(
            marka, text="◈  DeporiaQ", font=(YAZI_TIPI, boyut, "bold"),
            bg=RENK_ZEMIN, fg="#050505"
        ).place(x=3, y=5)
        tk.Label(
            marka, text="◈  DeporiaQ", font=(YAZI_TIPI, boyut, "bold"),
            bg=RENK_ZEMIN, fg=RENK_METIN
        ).place(x=1, y=2)
        tk.Label(
            marka, text=f"v{PROGRAM_SURUMU}",
            font=(YAZI_TIPI, max(9, boyut // 2), "normal"),
            bg=RENK_ZEMIN, fg=RENK_SOLUK
        ).place(x=210, y=17)
        if alt_metin:
            tk.Label(
                marka, text=alt_metin, font=(YAZI_TIPI, 10),
                bg=RENK_ZEMIN, fg=RENK_SOLUK
            ).place(x=350, y=17)
        return alan

    def uygulama_ici_sayfa_ac(self, baslik):
        """Yeni pencere yerine ana uygulamanın içinde geri dönülebilir sayfa açar."""
        kaplama = ttk.Frame(self.pencere, bootstyle="dark")
        kaplama.place(x=0, y=0, relwidth=1, relheight=1)
        kaplama.lift()

        gezinme = tk.Frame(kaplama, bg=RENK_ZEMIN, padx=14, pady=8)
        gezinme.pack(fill=X)
        geri = tk.Button(
            gezinme, text="←", command=lambda: self.sayfadan_geri_don(kaplama),
            font=("Segoe UI Symbol", 23, "bold"), fg=RENK_METIN,
            activeforeground=RENK_VURGU, bg=RENK_ZEMIN,
            activebackground=RENK_PANEL, relief="flat", bd=0,
            highlightthickness=0, cursor="hand2", padx=16, pady=2
        )
        geri.pack(side=LEFT, padx=(0, 8))
        tk.Label(
            gezinme, text=baslik, font=(YAZI_TIPI, 15, "bold"),
            bg=RENK_ZEMIN, fg=RENK_METIN, padx=8, pady=4
        ).pack(side=LEFT)

        icerik = ttk.Frame(kaplama, bootstyle="dark")
        icerik.pack(fill=BOTH, expand=True)
        self.sayfa_yigini.append(kaplama)

        # Eski ekran kodlarının pencere komutları uygulama içi sayfada etkisizdir.
        icerik.title = lambda *_: None
        icerik.geometry = lambda *_: None
        icerik.minsize = lambda *_: None
        icerik.resizable = lambda *_: None
        icerik.transient = lambda *_: None
        icerik.grab_set = lambda *_: None
        icerik.protocol = lambda *_: None
        icerik.destroy = lambda: self.sayfadan_geri_don(kaplama)
        self.pencere.after(80, lambda: self.arayuzu_cevir(kaplama))
        return icerik

    def sayfadan_geri_don(self, kaplama=None):
        """En üst uygulama içi sayfayı kapatıp önceki sayfayı gösterir."""
        if not self.sayfa_yigini:
            return "break"
        hedef = kaplama or self.sayfa_yigini[-1]
        if hedef not in self.sayfa_yigini:
            return "break"
        while self.sayfa_yigini:
            ust = self.sayfa_yigini.pop()
            tk.Widget.destroy(ust)
            if ust is hedef:
                break
        if self.sayfa_yigini:
            self.sayfa_yigini[-1].lift()
        else:
            try:
                self.barkod_kutusu.focus_set()
            except (AttributeError, tk.TclError):
                pass
        return "break"

    def klavyeden_geri_don(self, olay):
        if not self.sayfa_yigini:
            return None
        if olay.keysym == "BackSpace":
            try:
                if olay.widget.winfo_class() in {
                    "Entry", "TEntry", "Text", "TCombobox", "Spinbox", "TSpinbox"
                }:
                    return None
            except tk.TclError:
                pass
        return self.sayfadan_geri_don()

    def giris_ekranini_goster(self):
        """Giriş formunu doğrudan görünür ana pencere içinde oluşturur."""
        self.oturum_acik = False
        self.aktif_kullanici = None
        self.ekrani_temizle()
        self.pencere.title(f"{PROGRAM_ADI} {PROGRAM_SURUMU} - Giriş")
        self.pencere.minsize(560, 470)
        self.pencere.geometry("620x520")
        self.pencere.resizable(False, False)

        self.kabartmali_marka(
            self.pencere, alt_metin="Güvenli işletme yönetimi", boyut=23,
            dolgu=(24, 16), genislik=570
        ).pack(fill=X)
        ttk.Label(
            self.pencere,
            text=f"{self.isletme_adi}\nKullanıcı bilgilerinizle oturum açın.",
            justify="center", font=(YAZI_TIPI, 11), padding=18
        ).pack(fill=X)

        form = ttk.Labelframe(
            self.pencere, text=" Güvenli oturum açma ",
            padding=26, bootstyle="primary"
        )
        form.pack(fill=BOTH, expand=True, padx=34, pady=(4, 14))
        form.columnconfigure(1, weight=1)

        hatirlanan_kullanici = str(
            self.ayarlar.get("hatirlanan_kullanici", "")
        ).strip()
        kullanici = tk.StringVar(value=hatirlanan_kullanici)
        parola = tk.StringVar()
        parola_gorunur = tk.BooleanVar(value=False)
        beni_hatirla = tk.BooleanVar(value=bool(hatirlanan_kullanici))
        ttk.Label(form, text="Kullanıcı adı:").grid(
            row=0, column=0, sticky="w", padx=(0, 14), pady=12
        )
        kullanici_kutusu = ttk.Entry(
            form, textvariable=kullanici, font=(YAZI_TIPI, 11)
        )
        kullanici_kutusu.grid(row=0, column=1, sticky="ew", pady=12)
        ttk.Label(form, text="Parola:").grid(
            row=1, column=0, sticky="w", padx=(0, 14), pady=12
        )
        parola_kutusu = ttk.Entry(
            form, textvariable=parola, show="●", font=(YAZI_TIPI, 11)
        )
        parola_kutusu.grid(row=1, column=1, sticky="ew", pady=12)

        def gorunurlugu_degistir():
            parola_kutusu.configure(show="" if parola_gorunur.get() else "●")

        ttk.Checkbutton(
            form, text="Parolayı göster", variable=parola_gorunur,
            command=gorunurlugu_degistir, bootstyle="round-toggle"
        ).grid(row=2, column=1, sticky="w", pady=(2, 6))
        ttk.Checkbutton(
            form, text="Beni Hatırla",
            variable=beni_hatirla, bootstyle="round-toggle"
        ).grid(row=3, column=1, sticky="w", pady=(2, 12))

        def giris_yap(_olay=None):
            if not kullanici.get().strip() or not parola.get():
                self.olumsuz_bildirimi(
                    "Kullanıcı adı ve parola boş bırakılamaz."
                )
                return "break"
            kayit = self.vt.kimlik_dogrula(kullanici.get(), parola.get())
            if not kayit:
                parola.set("")
                self.olumsuz_bildirimi("Kullanıcı adı veya parola hatalı.")
                parola_kutusu.focus_set()
                return "break"
            self.aktif_kullanici = dict(kayit)
            self.oturum_acik = True
            self.oturum_id = self.vt.oturum_baslat(self.aktif_kullanici["id"])
            self.vt.denetim_ekle("OTURUM_ACILDI", "Başarılı kullanıcı girişi")
            self.son_etkinlik_zamani = time.monotonic()
            hatirlanacak = kullanici.get().strip() if beni_hatirla.get() else ""
            yerel_ayari_kaydet("hatirlanan_kullanici", hatirlanacak)
            if hatirlanacak:
                self.ayarlar["hatirlanan_kullanici"] = hatirlanacak
            else:
                self.ayarlar.pop("hatirlanan_kullanici", None)
            self.ana_ekrani_goster()
            return "break"

        def parolami_unuttum():
            if not kullanici.get().strip():
                self.olumsuz_bildirimi("Önce kullanıcı adınızı yazın.")
                return
            kayit = self.vt.kullanici_bul(kullanici.get())
            if not kayit:
                self.olumsuz_bildirimi(
                    "Bu kullanıcı adına ait aktif hesap bulunamadı."
                )
            elif kayit["rol"] == "ANA_YONETICI":
                self.olumsuz_bildirimi(
                    "Ana yönetici parola kurtarma işlemi için DeporiaQ yazılım sağlayıcınızla iletişime geçin."
                )
            else:
                self.olumsuz_bildirimi(
                    "Parolanızı yenilemek için işletmenizin ana yöneticisiyle iletişime geçin."
                )

        kullanici_kutusu.bind(
            "<Return>", lambda _olay: parola_kutusu.focus_set()
        )
        parola_kutusu.bind("<Return>", giris_yap)

        butonlar = ttk.Frame(self.pencere, padding=(34, 0, 34, 28))
        butonlar.pack(fill=X)
        ttk.Button(
            butonlar, text="Şifremi Unuttum", command=parolami_unuttum,
            bootstyle="warning-outline", padding=(16, 9)
        ).pack(side=LEFT)
        ttk.Button(
            butonlar, text="Programı Kapat", command=self.programi_kapat,
            bootstyle="danger-outline", padding=(16, 9)
        ).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(
            butonlar, text="Giriş Yap", command=giris_yap,
            bootstyle="success", padding=(24, 9)
        ).pack(side=RIGHT)

        self.pencere.after(50, self.pencereyi_ortala)
        self.pencere.after(80, lambda: self.arayuzu_cevir(self.pencere))
        if hatirlanan_kullanici:
            parola_kutusu.focus_set()
        else:
            kullanici_kutusu.focus_set()

    def ana_ekrani_goster(self):
        """Doğrulama sonrasında stok yönetimi ekranını oluşturur."""
        self.ekrani_temizle()
        self.pencere.resizable(True, True)
        self.pencere.minsize(1080, 780)
        self.pencere.geometry("1280x900")
        self.pencere.title(f"{PROGRAM_ADI} {PROGRAM_SURUMU}")
        self.arayuzu_olustur()
        self.pencere.after(80, lambda: self.arayuzu_cevir(self.pencere))
        self.konum_seciciyi_yenile()
        self.tabloyu_yenile()
        try:
            self.pencere.state("zoomed")
        except tk.TclError:
            ekran_w = self.pencere.winfo_screenwidth()
            ekran_h = self.pencere.winfo_screenheight()
            self.pencere.geometry(f"{ekran_w}x{max(700, ekran_h - 70)}+0+0")
        self.pencere.bind("<Escape>", self.klavyeden_geri_don)
        self.pencere.bind("<BackSpace>", self.klavyeden_geri_don)
        self.pencere.bind("<Alt-Left>", self.klavyeden_geri_don)
        self.pencere.bind("<Control-f>", self.hizli_aramaya_git)
        self.pencere.bind("<Control-t>", lambda _olay: self.genel_transfer_penceresini_ac())
        self.pencere.bind("<F5>", self.ana_ekrani_yenile)
        self.barkod_kutusu.focus_set()
        if self.ilk_ana_ekran_acilisi:
            self.ilk_ana_ekran_acilisi = False
            if self.tasima_sonucu:
                self.pencere.after(
                    700, lambda: self.basari_bildirimi(self.tasima_sonucu)
                )
            if self.kurtarma_sonucu:
                self.pencere.after(
                    900, lambda: self.basari_bildirimi(self.kurtarma_sonucu)
                )
            self.pencere.after(
                1800, lambda: self.guncellemeleri_kontrol_et(sessiz=True)
            )
            self.pencere.after(700, self.cloud_hatirlanan_oturumu_ac)

    def cloud_hatirlanan_oturumu_ac(self):
        url = str(self.ayarlar.get("cloud_url", "")).strip()
        anahtar = str(self.ayarlar.get("cloud_publishable_key", "")).strip()
        sifreli = str(self.ayarlar.get("cloud_refresh_token_dpapi", "")).strip()
        if not (url and anahtar and sifreli):
            return
        try:
            self.cloud.yapilandir(url, anahtar)
            token = windows_sifre_coz(sifreli)
            if not token:
                raise RuntimeError("Güvenli Cloud oturumu açılamadı.")
            self.cloud.oturumu_yenile(token)
            if self.cloud.refresh_token:
                yeni = windows_sifrele(self.cloud.refresh_token)
                yerel_ayari_kaydet("cloud_refresh_token_dpapi", yeni)
                self.ayarlar["cloud_refresh_token_dpapi"] = yeni
            self.cloud_durum_metni.set("● Cloud bağlı")
            self.cloud_dongusunu_baslat()
        except Exception:
            self.cloud_durum_metni.set("● Cloud oturumu gerekli")

    def cloud_dongusunu_baslat(self):
        if self.cloud_dongu_aktif:
            return
        self.cloud_dongu_aktif = True
        self.pencere.after(3000, self.cloud_senkron_dongusu)

    def cloud_durum_stilini_guncelle(self, *_args):
        """Cloud durumunu dolu düğme yerine renkli nokta ve metinle gösterir."""
        if not hasattr(self, "cloud_durum_dugmesi"):
            return
        metin = self.cloud_durum_metni.get().lower()
        if any(x in metin for x in ("güncel", "gönderildi", "yenilendi", "bağlı")):
            renk = "#45D483"
        elif "senkronize" in metin:
            renk = "#60A5FA"
        elif any(x in metin for x in ("bekliyor", "oturumu gerekli", "çakışma")):
            renk = "#F6C453"
        elif any(x in metin for x in ("çevrimdışı", "kapalı")):
            renk = "#F45B76"
        else:
            renk = RENK_SOLUK
        try:
            self.pencere.style.configure("CloudDot.TLabel", foreground=renk)
            temiz = self.cloud_durum_metni.get().lstrip("● ")
            self.cloud_durum_yazisi.configure(text=temiz)
        except tk.TclError:
            pass

    def cloud_senkron_dongusu(self):
        if not self.cloud_dongu_aktif:
            return
        try:
            if self.cloud.bagli:
                self.cloud_durum_metni.set("● Senkronize ediliyor")
                durum, _ayrinti = self.cloud.akilli_senkronize()
                metinler = {
                    "GUNCEL": "● Cloud güncel",
                    "YUKLENDI": "● Cloud'a gönderildi",
                    "INDIRILDI": "● Cloud'dan yenilendi",
                    "CAKISMA": f"● Çakışma ({self.cloud.cakisma_sayisi()})",
                    "YETKI_BEKLIYOR": "● Yönetici onayı bekliyor",
                }
                self.cloud_durum_metni.set(metinler.get(durum, "● Cloud bağlı"))
                self.cloud._durum_kaydet("son_hata", "")
                if durum == "INDIRILDI" and not self.sayfa_yigini:
                    self.konum_seciciyi_yenile(); self.tabloyu_yenile()
        except Exception as hata:
            self.cloud._durum_kaydet("son_hata", str(hata))
            bekleyen = self.vt.baglanti.execute(
                "SELECT COUNT(*) FROM senkron_kuyrugu WHERE gonderildi=0"
            ).fetchone()[0]
            self.cloud_durum_metni.set(f"● Çevrimdışı • {bekleyen} bekliyor")
        self.pencere.after(15000, self.cloud_senkron_dongusu)

    def senkronizasyon_merkezini_ac(self):
        pencere = self.uygulama_ici_sayfa_ac("Senkronizasyon Merkezi")
        ttk.Label(
            pencere, text="SENKRONİZASYON MERKEZİ",
            font=(YAZI_TIPI, 20, "bold"), bootstyle="inverse-dark", padding=18
        ).pack(fill=X)
        ozet = tk.StringVar()
        tablo = ttk.Treeview(
            pencere, columns=("tarih","durum","kimlik"), show="headings",
            bootstyle="info", height=10
        )
        for kolon, baslik, genislik in (
            ("tarih","Tarih",180),("durum","Durum",130),("kimlik","Çakışma kimliği",360)
        ):
            tablo.heading(kolon,text=baslik); tablo.column(kolon,width=genislik)

        def yenile():
            bekleyen = self.vt.baglanti.execute(
                "SELECT COUNT(*) FROM senkron_kuyrugu WHERE gonderildi=0"
            ).fetchone()[0]
            son = self.cloud._durum_getir("son_senkron", "Henüz yok")
            hata = self.cloud._durum_getir("son_hata", "") or "Yok"
            ozet.set(
                f"Durum: {self.cloud_durum_metni.get()}   •   Bekleyen: {bekleyen}   •   Son senkronizasyon: {son}\nSon hata: {hata}"
            )
            tablo.delete(*tablo.get_children())
            for satir in self.vt.baglanti.execute(
                "SELECT tarih_saat,durum,cakisma_kimligi FROM cloud_cakismalari ORDER BY id DESC LIMIT 100"
            ):
                tablo.insert("",END,values=(satir["tarih_saat"],satir["durum"],satir["cakisma_kimligi"]))

        ttk.Label(pencere,textvariable=ozet,font=(YAZI_TIPI,11),padding=18).pack(fill=X)
        tablo.pack(fill=BOTH,expand=True,padx=20,pady=(0,12))

        def simdi():
            if not self.cloud.bagli:
                self.olumsuz_bildirimi("Cloud oturumu açık değil.",pencere); return
            try:
                durum,_ = self.cloud.akilli_senkronize()
                self.basari_bildirimi(f"Senkronizasyon sonucu: {durum}",pencere); yenile()
            except Exception as hata:
                self.olumsuz_bildirimi(str(hata),pencere)

        def coz(secim):
            if not self.cloud.bagli:
                self.olumsuz_bildirimi("Cloud oturumu açık değil.",pencere); return
            metin = "bu bilgisayardaki" if secim == "YEREL" else "buluttaki"
            if not self.modern_onay("Çakışmayı çöz",f"{metin.capitalize()} veriler esas alınacak. Devam edilsin mi?",pencere,"Uygula"):
                return
            try:
                self.cloud.cakismayi_coz(secim); yenile()
                self.basari_bildirimi("Çakışma çözüldü.",pencere)
            except Exception as hata:
                self.olumsuz_bildirimi(str(hata),pencere)

        butonlar=ttk.Frame(pencere,padding=(20,0,20,18));butonlar.pack(fill=X)
        ttk.Button(butonlar,text="Şimdi Senkronize Et",command=simdi,bootstyle="info").pack(side=LEFT)
        ttk.Button(butonlar,text="Yerel Veriyi Kullan",command=lambda:coz("YEREL"),bootstyle="warning").pack(side=LEFT,padx=8)
        ttk.Button(butonlar,text="Bulut Verisini Kullan",command=lambda:coz("BULUT"),bootstyle="success").pack(side=LEFT)
        ttk.Button(butonlar,text="Bağlı Cihazlar",command=self.cloud_cihazlarini_ac,bootstyle="secondary-outline").pack(side=RIGHT)
        yenile()

    def cloud_cihazlarini_ac(self):
        if not self.cloud.bagli:
            self.olumsuz_bildirimi("Cloud oturumu açık değil."); return
        pencere=self.uygulama_ici_sayfa_ac("Bağlı Cihazlar")
        tablo=ttk.Treeview(pencere,columns=("ad","kod","surum","son","durum"),show="headings",bootstyle="primary")
        for k,b,w in (("ad","Cihaz",220),("kod","Cihaz kimliği",220),("surum","Sürüm",100),("son","Son bağlantı",260),("durum","Durum",100)):
            tablo.heading(k,text=b);tablo.column(k,width=w)
        tablo.pack(fill=BOTH,expand=True,padx=20,pady=20)
        cihaz_haritasi={}
        def yenile():
            tablo.delete(*tablo.get_children());cihaz_haritasi.clear()
            try:
                for c in self.cloud.cihazlari_getir():
                    oge=tablo.insert("",END,values=(c.get("device_name"),c.get("device_code"),c.get("app_version"),c.get("last_seen_at"),"Aktif" if c.get("active") else "Kapalı"))
                    cihaz_haritasi[oge]=c
            except Exception as hata:self.olumsuz_bildirimi(str(hata),pencere)
        def degistir():
            sec=tablo.selection()
            if not sec:return
            c=cihaz_haritasi[sec[0]]
            if c.get("device_code")==self.cihaz_kimligi:
                self.olumsuz_bildirimi("Kullandığınız cihazı buradan kapatamazsınız.",pencere);return
            try:self.cloud.cihaz_durumunu_degistir(c["id"],not c.get("active"));yenile()
            except Exception as hata:self.olumsuz_bildirimi(str(hata),pencere)
        alt=ttk.Frame(pencere,padding=20);alt.pack(fill=X)
        ttk.Button(alt,text="Seçili Cihazı Aktif/Pasif Yap",command=degistir,bootstyle="warning").pack(side=LEFT)
        ttk.Button(alt,text="Yenile",command=yenile,bootstyle="info").pack(side=LEFT,padx=8)
        yenile()

    def hizli_aramaya_git(self, _olay=None):
        """Ctrl+F ile ana ürün aramasına hızlıca geçer."""
        if self.sayfa_yigini:
            return "break"
        self.urun_arama_kutusu.focus_set()
        try:
            self.urun_arama_kutusu.selection_range(0, END)
        except tk.TclError:
            pass
        return "break"

    def ana_ekrani_yenile(self, _olay=None):
        """F5 ile konumları, özet kartlarını ve stok tablosunu yeniler."""
        if not self.sayfa_yigini:
            self.konum_seciciyi_yenile()
            self.tabloyu_yenile()
            self.basari_bildirimi("Stok ekranı yenilendi.")
        return "break"

    def oturumu_kapat(self):
        """Verileri kapatmadan oturumu sonlandırıp giriş ekranına döner."""
        if self.oturum_acik:
            self.vt.denetim_ekle("OTURUM_KAPANDI", "Kullanıcı çıkış yaptı veya oturum kilitlendi")
            self.vt.oturum_bitir(self.oturum_id)
        self.oturum_id = None
        self.oturum_acik = False
        self.aktif_kullanici = None
        self.giris_ekranini_goster()

    def etkinlik_kaydet(self, _olay=None):
        if self.oturum_acik:
            self.son_etkinlik_zamani = time.monotonic()

    def otomatik_kilidi_kontrol_et(self):
        """Ayarlanan hareketsizlik süresinde giriş ekranına döndürür."""
        if not self.pencere.winfo_exists():
            return
        if self.oturum_acik:
            gecen_sure = time.monotonic() - self.son_etkinlik_zamani
            try:
                kilit_dakika = int(
                    self.vt.ayar_getir("otomatik_kilit_dakika", "15")
                )
            except ValueError:
                kilit_dakika = 15
            if kilit_dakika > 0 and gecen_sure >= kilit_dakika * 60:
                self.oturumu_kapat()
                self.olumsuz_bildirimi(
                    f"Güvenliğiniz için oturum {kilit_dakika} dakika hareketsizlikten sonra kilitlendi."
                )
        self.pencere.after(30_000, self.otomatik_kilidi_kontrol_et)

    def yetki_var_mi(self, islem):
        if not self.aktif_kullanici:
            return False
        rol = self.aktif_kullanici["rol"]
        izinler = {
            "ANA_YONETICI": {"YONETIM", "STOK_GIRIS", "TRANSFER", "SATIS"},
            "DEPO_PERSONELI": {"TRANSFER"},
            "SUBE_PERSONELI": {"SATIS"},
            "GORUNTULEYICI": set(),
        }
        return islem in izinler.get(rol, set())

    def yetki_kontrol(self, islem):
        if self.yetki_var_mi(islem):
            return True
        self.olumsuz_bildirimi("Bu işlemi yapma yetkiniz bulunmamaktadır!")
        return False

    def yonetici_parolasini_dogrula(self, parola):
        return bool(
            self.aktif_kullanici
            and self.vt.kimlik_dogrula(
                self.aktif_kullanici["kullanici_adi"], parola
            )
        )

    def ilk_kurulum_sihirbazini_ac(self):
        """Temiz müşteri kurulumunda işletme ve ilk yönetici bilgilerini alır."""
        sonuc = {"tamam": False}
        pencere = ttk.Toplevel(self.pencere)
        pencere.title("DeporiaQ İlk Kurulum")
        pencere.geometry("720x650")
        pencere.resizable(False, False)

        self.kabartmali_marka(
            pencere, alt_metin="İlk Kurulum", boyut=22, dolgu=(22, 14),
            genislik=670
        ).pack(fill=X)
        ttk.Label(
            pencere,
            text=(
                "Bu bilgisayarda yeni ve boş bir işletme veritabanı oluşturulacak.\n"
                "Başka müşterilere veya geliştiriciye ait ürün ve stoklar yüklenmez."
            ),
            font=(YAZI_TIPI, 11),
            justify="center",
            padding=14
        ).pack(fill=X)

        form = ttk.Labelframe(
            pencere, text=" İşletme ve ana yönetici bilgileri ",
            padding=22, bootstyle="primary"
        )
        form.pack(fill=BOTH, expand=True, padx=28, pady=(4, 16))
        form.columnconfigure(1, weight=1)

        isletme = tk.StringVar()
        sektor = tk.StringVar(value="Diğer")
        merkez = tk.StringVar(value="Merkez Depo")
        para = tk.StringVar(value="TL")
        kullanici = tk.StringVar(value="admin")
        parola = tk.StringVar()
        parola_tekrar = tk.StringVar()
        parola_gorunur = tk.BooleanVar(value=False)

        alanlar = (
            ("İşletme adı:", isletme),
            ("Merkez depo adı:", merkez),
            ("Ana yönetici kullanıcı adı:", kullanici),
        )
        for satir, (etiket, degisken) in enumerate(alanlar):
            ttk.Label(form, text=etiket).grid(row=satir, column=0, sticky="w", pady=8, padx=(0, 12))
            ttk.Entry(form, textvariable=degisken).grid(row=satir, column=1, sticky="ew", pady=8)

        ttk.Label(form, text="İşletme türü:").grid(row=3, column=0, sticky="w", pady=8)
        sektor_kutusu = ttk.Combobox(
            form, textvariable=sektor,
            values=ISLETME_TURLERI,
            state="normal"
        )
        sektor_kutusu.grid(row=3, column=1, sticky="ew", pady=8)
        self.aramali_secim_hazirla(
            sektor_kutusu, sektor, lambda: ISLETME_TURLERI
        )
        ttk.Label(form, text="Para birimi:").grid(row=4, column=0, sticky="w", pady=8)
        ttk.Combobox(
            form, textvariable=para, values=("TL", "USD", "EUR"), state="readonly"
        ).grid(row=4, column=1, sticky="ew", pady=8)
        ttk.Label(form, text="Yönetici parolası:").grid(row=5, column=0, sticky="w", pady=8)
        parola_kutusu = ttk.Entry(form, textvariable=parola, show="●")
        parola_kutusu.grid(row=5, column=1, sticky="ew", pady=8)
        ttk.Label(form, text="Parola tekrarı:").grid(row=6, column=0, sticky="w", pady=8)
        parola_tekrar_kutusu = ttk.Entry(form, textvariable=parola_tekrar, show="●")
        parola_tekrar_kutusu.grid(row=6, column=1, sticky="ew", pady=8)

        def parola_gorunurlugunu_degistir():
            gosterim = "" if parola_gorunur.get() else "●"
            parola_kutusu.configure(show=gosterim)
            parola_tekrar_kutusu.configure(show=gosterim)

        ttk.Checkbutton(
            form,
            text="Parolayı göster",
            variable=parola_gorunur,
            command=parola_gorunurlugunu_degistir,
            bootstyle="round-toggle"
        ).grid(row=7, column=1, sticky="w", pady=(4, 8))

        def tamamla():
            if not isletme.get().strip():
                self.olumsuz_bildirimi("İşletme adı boş bırakılamaz.", pencere)
                return
            if not merkez.get().strip():
                self.olumsuz_bildirimi("Merkez depo adı boş bırakılamaz.", pencere)
                return
            if len(kullanici.get().strip()) < 3:
                self.olumsuz_bildirimi("Kullanıcı adı en az 3 karakter olmalıdır.", pencere)
                return
            parola_gecerli, parola_hatasi = parola_guclu_mu(parola.get())
            if not parola_gecerli:
                self.olumsuz_bildirimi(parola_hatasi, pencere)
                return
            if parola.get() != parola_tekrar.get():
                self.olumsuz_bildirimi("Parolalar birbiriyle aynı değil.", pencere)
                return
            try:
                self.vt.ilk_kurulumu_tamamla(
                    isletme.get().strip(), sektor.get(), merkez.get().strip(),
                    para.get(), kullanici.get().strip(), parola.get()
                )
            except (sqlite3.Error, ValueError) as hata:
                self.olumsuz_bildirimi(f"İlk kurulum tamamlanamadı: {hata}", pencere)
                return
            sonuc["tamam"] = True
            pencere.destroy()

        alt = ttk.Frame(pencere, padding=(28, 0, 28, 22))
        alt.pack(fill=X)
        ttk.Button(
            alt, text="Kurulumu Tamamla", command=tamamla,
            bootstyle="success", padding=(22, 10)
        ).pack(side=RIGHT)
        ttk.Button(
            alt, text="İptal", command=pencere.destroy,
            bootstyle="secondary-outline", padding=(22, 10)
        ).pack(side=RIGHT, padx=8)

        pencere.protocol("WM_DELETE_WINDOW", pencere.destroy)
        pencere.grab_set()
        pencere.wait_window()
        return sonuc["tamam"]

    def pencereyi_ortala(self):
        self.pencere.update_idletasks()
        genislik = self.pencere.winfo_width()
        yukseklik = self.pencere.winfo_height()
        x = (self.pencere.winfo_screenwidth() - genislik) // 2
        y = (self.pencere.winfo_screenheight() - yukseklik) // 2
        self.pencere.geometry(f"{genislik}x{yukseklik}+{x}+{y}")

    def bildirim_goster(self, mesaj, ebeveyn=None, basarili=True):
        """Bildirimi işlem yapılan pencerenin sağ altında animasyonla gösterir."""
        if ebeveyn is None:
            ebeveyn = self.pencere

        bildirim = ttk.Toplevel(ebeveyn)
        bildirim.overrideredirect(True)
        bildirim.attributes("-topmost", True)
        bildirim.attributes("-alpha", 0.0)

        renk = "success" if basarili else "danger"
        simge = "✓" if basarili else "✕"
        cerceve = ttk.Frame(bildirim, padding=(18, 13), bootstyle=renk)
        cerceve.pack(fill=BOTH, expand=True)
        ttk.Label(
            cerceve,
            text=simge + "  " + mesaj,
            font=(YAZI_TIPI, 11, "bold"),
            bootstyle="inverse-" + renk,
            wraplength=340
        ).pack()

        ebeveyn.update_idletasks()
        bildirim.update_idletasks()
        genislik = max(340, bildirim.winfo_reqwidth())
        yukseklik = max(58, bildirim.winfo_reqheight())
        x = ebeveyn.winfo_rootx() + ebeveyn.winfo_width() - genislik - 18
        y = ebeveyn.winfo_rooty() + ebeveyn.winfo_height() - yukseklik - 18
        bildirim.geometry(f"{genislik}x{yukseklik}+{x}+{y}")

        def gorunur_yap(adim=1):
            if not bildirim.winfo_exists():
                return
            bildirim.attributes("-alpha", min(1.0, adim / 10))
            if adim < 10:
                bildirim.after(25, lambda: gorunur_yap(adim + 1))
            else:
                bildirim.after(2200, kaybol)

        def kaybol(adim=10):
            if not bildirim.winfo_exists():
                return
            bildirim.attributes("-alpha", max(0.0, adim / 10))
            if adim > 0:
                bildirim.after(35, lambda: kaybol(adim - 1))
            else:
                bildirim.destroy()

        gorunur_yap()

    def basari_bildirimi(self, mesaj, ebeveyn=None):
        self.bildirim_goster(mesaj, ebeveyn, True)

    def olumsuz_bildirimi(self, mesaj, ebeveyn=None):
        self.bildirim_goster(mesaj, ebeveyn, False)

    def modern_onay(self, baslik, mesaj, ebeveyn=None, onay_metni="Onayla"):
        """Windows ileti kutusu yerine pencerenin içinde temalı onay kartı açar."""
        ebeveyn = ebeveyn or self.pencere
        sonuc = tk.IntVar(master=ebeveyn, value=-1)

        kart = ttk.Frame(
            ebeveyn, padding=2, bootstyle="danger"
        )
        icerik = ttk.Frame(kart, padding=(28, 22), bootstyle="dark")
        icerik.pack(fill=BOTH, expand=True)
        ttk.Label(
            icerik, text="!", font=(YAZI_TIPI, 24, "bold"),
            bootstyle="inverse-dark", width=3, anchor=CENTER
        ).pack(side=LEFT, fill=Y, padx=(0, 18))
        metin_alani = ttk.Frame(icerik, bootstyle="dark")
        metin_alani.pack(side=LEFT, fill=BOTH, expand=True)
        ttk.Label(
            metin_alani, text=baslik, font=(YAZI_TIPI, 15, "bold"),
            bootstyle="inverse-dark"
        ).pack(anchor="w")
        ttk.Label(
            metin_alani, text=mesaj, font=(YAZI_TIPI, 10),
            bootstyle="inverse-dark", wraplength=440, justify=LEFT
        ).pack(anchor="w", pady=(8, 18))
        dugmeler = ttk.Frame(metin_alani, bootstyle="dark")
        dugmeler.pack(fill=X)

        def bitir(deger):
            if sonuc.get() == -1:
                sonuc.set(deger)

        ttk.Button(
            dugmeler, text="Vazgeç", command=lambda: bitir(0),
            bootstyle="secondary-outline", padding=(18, 8)
        ).pack(side=RIGHT)
        ttk.Button(
            dugmeler, text=onay_metni, command=lambda: bitir(1),
            bootstyle="danger", padding=(18, 8)
        ).pack(side=RIGHT, padx=(0, 10))

        kart.place(relx=0.5, rely=0.44, anchor=CENTER, width=620)
        kart.lift()
        kart.focus_set()
        kart.bind("<Escape>", lambda _olay: bitir(0))
        kart.bind("<Return>", lambda _olay: bitir(1))

        def kaydir(adim=0):
            if kart.winfo_exists() and sonuc.get() == -1:
                kart.place_configure(rely=min(0.5, 0.44 + adim * 0.006))
                if adim < 10:
                    kart.after(16, lambda: kaydir(adim + 1))

        kaydir()
        ebeveyn.wait_variable(sonuc)
        cevap = sonuc.get() == 1
        kart.destroy()
        return cevap

    def aramali_secim_hazirla(self, kutu, degisken, degerleri_getir, secilince=None):
        """Bir Combobox'ı kısmi metinle aranan, Enter ile seçilen kutuya dönüştürür."""
        kutu.configure(state="normal")

        def filtrele(olay=None):
            if olay and olay.keysym in (
                "Up", "Down", "Left", "Right", "Return", "Escape", "Tab"
            ):
                return
            aranan = degisken.get().strip().casefold()
            tum_degerler = list(degerleri_getir())
            sonuclar = [deger for deger in tum_degerler if aranan in deger.casefold()]
            kutu["values"] = sonuclar

        def secimi_tamamla(_olay=None):
            sonuclar = list(kutu["values"])
            if sonuclar:
                degisken.set(sonuclar[0])
                kutu["values"] = list(degerleri_getir())
                if secilince:
                    secilince()
            return "break"

        kutu.bind("<KeyRelease>", filtrele)
        kutu.bind("<Return>", secimi_tamamla)
        if secilince:
            kutu.bind("<<ComboboxSelected>>", lambda _olay: secilince())

    def guncellemeleri_kontrol_et(self, sessiz=False):
        """Güncelleme bilgisini arka planda denetler; çevrimdışı çalışmayı engellemez."""
        manifest_url = self.ayarlar.get("guncelleme_manifest_url", "").strip()
        if not manifest_url:
            if not sessiz:
                self.olumsuz_bildirimi(
                    "Güncelleme adresi henüz ayarlanmamış. Kurulum belgesine bakın."
                )
            return
        if not manifest_url.lower().startswith("https://"):
            if not sessiz:
                self.olumsuz_bildirimi("Güncelleme adresi güvenli HTTPS olmalıdır.")
            return

        if not sessiz:
            self.basari_bildirimi("Güncellemeler kontrol ediliyor...")

        def internetten_oku():
            try:
                istek = urllib.request.Request(
                    manifest_url,
                    headers={"User-Agent": f"{PROGRAM_ADI}/{PROGRAM_SURUMU}"}
                )
                with urllib.request.urlopen(istek, timeout=6) as cevap:
                    veri = json.loads(cevap.read(65536).decode("utf-8"))
                self.pencere.after(
                    0, lambda: self.guncelleme_sonucunu_goster(veri, sessiz)
                )
            except Exception:
                if not sessiz:
                    try:
                        self.pencere.after(
                            0,
                            lambda: self.olumsuz_bildirimi(
                                "İnternet bağlantısı kurulamadı. Program çevrimdışı çalışmaya devam ediyor."
                            )
                        )
                    except tk.TclError:
                        pass

        threading.Thread(target=internetten_oku, daemon=True).start()

    def guncelleme_sonucunu_goster(self, veri, sessiz=False):
        """Sunucudan gelen sürüm bilgisini doğrular ve kullanıcıya sunar."""
        yeni_surum = str(veri.get("version", "0.0.0"))
        indirme_adresi = str(veri.get("download_url", "")).strip()
        beklenen_sha256 = str(veri.get("sha256", "")).strip().lower()
        aciklama = str(veri.get("notes", "Yeni geliştirmeler ve hata düzeltmeleri."))

        if surum_parcalari(yeni_surum) <= surum_parcalari(PROGRAM_SURUMU):
            if not sessiz:
                self.basari_bildirimi(f"DeporiaQ {PROGRAM_SURUMU} güncel.")
            return

        if not indirme_adresi.lower().startswith("https://"):
            if not sessiz:
                self.olumsuz_bildirimi("Güncellemenin indirme adresi güvenli değil.")
            return

        if len(beklenen_sha256) != 64 or any(
            karakter not in "0123456789abcdef" for karakter in beklenen_sha256
        ):
            if not sessiz:
                self.olumsuz_bildirimi(
                    "Güncelleme güvenlik özeti (SHA-256) eksik veya geçersiz."
                )
            return

        indirilsin_mi = self.modern_onay(
            "DeporiaQ güncellemesi hazır",
            (
                f"Yeni sürüm: {yeni_surum}\n"
                f"Kullandığınız sürüm: {PROGRAM_SURUMU}\n\n"
                f"{aciklama}\n\n"
                "Güncelleme indirilsin ve kurulum başlatılsın mı?\n\n"
                "Program kapanabilir; stok ve işletme verileriniz korunur."
            ), self.pencere, "İndir ve Kur"
        )
        if indirilsin_mi:
            self.guncellemeyi_indir_ve_baslat(
                indirme_adresi, beklenen_sha256, yeni_surum
            )

    def guncellemeyi_indir_ve_baslat(
        self, indirme_adresi, beklenen_sha256, yeni_surum
    ):
        """Kurulumu indirir, özetini doğrular ve güvenli biçimde başlatır."""
        self.basari_bildirimi(f"DeporiaQ {yeni_surum} indiriliyor...")

        def indir():
            hedef = Path(tempfile.gettempdir()) / (
                f"DeporiaQ_Setup_{yeni_surum}.exe"
            )
            gecici = hedef.with_suffix(".indiriliyor")
            ozet = hashlib.sha256()
            toplam = 0
            azami_boyut = 1024 * 1024 * 1024
            try:
                istek = urllib.request.Request(
                    indirme_adresi,
                    headers={"User-Agent": f"{PROGRAM_ADI}/{PROGRAM_SURUMU}"}
                )
                with urllib.request.urlopen(istek, timeout=30) as cevap, open(
                    gecici, "wb"
                ) as dosya:
                    while True:
                        parca = cevap.read(1024 * 1024)
                        if not parca:
                            break
                        toplam += len(parca)
                        if toplam > azami_boyut:
                            raise ValueError("Güncelleme dosyası beklenenden büyük.")
                        dosya.write(parca)
                        ozet.update(parca)

                if not secrets.compare_digest(ozet.hexdigest(), beklenen_sha256):
                    raise ValueError(
                        "Güncelleme dosyasının güvenlik doğrulaması başarısız."
                    )
                os.replace(gecici, hedef)

                def kurulumu_baslat():
                    try:
                        alt_surec_ortami = os.environ.copy()
                        # Başka bir PyInstaller EXE'si başlatılıyor; eski onefile
                        # sürecinin güvenlik işaretleri kurulum EXE'sine taşınmamalı.
                        alt_surec_ortami["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                        subprocess.Popen([
                            str(hedef), "/SP-", "/CLOSEAPPLICATIONS",
                            "/RESTARTAPPLICATIONS"
                        ], env=alt_surec_ortami)
                        self.basari_bildirimi(
                            "Güncelleme doğrulandı. Kurulum başlatılıyor."
                        )
                        self.pencere.after(900, self.programi_kapat)
                    except OSError as hata:
                        self.olumsuz_bildirimi(
                            f"Kurulum başlatılamadı: {hata}"
                        )

                self.pencere.after(0, kurulumu_baslat)
            except Exception as hata:
                try:
                    gecici.unlink(missing_ok=True)
                except OSError:
                    pass
                try:
                    self.pencere.after(
                        0, lambda mesaj=str(hata): self.olumsuz_bildirimi(
                            f"Güncelleme indirilemedi: {mesaj}"
                        )
                    )
                except tk.TclError:
                    pass

        threading.Thread(target=indir, daemon=True).start()

    def arayuzu_olustur(self):
        ust = ttk.Frame(self.pencere, padding=(24, 14), bootstyle="primary")
        ust.pack(fill=X)

        marka = self.kabartmali_marka(ust, boyut=24, genislik=330)
        marka.pack(side=LEFT)

        self.ust_bilgi_etiketi = ttk.Label(
            ust,
            text=self.ust_bilgi_metni(),
            font=(YAZI_TIPI, 11),
            bootstyle="inverse-primary"
        )
        self.ust_bilgi_etiketi.pack(side=LEFT, padx=18)

        self.cloud_durum_dugmesi = ttk.Frame(ust, bootstyle="primary", cursor="hand2")
        self.cloud_durum_dugmesi.pack(side=LEFT, padx=(0, 10))
        ana_renk = self.pencere.style.colors.primary
        self.pencere.style.configure(
            "CloudDot.TLabel", background=ana_renk, foreground="#F45B76",
            font=(YAZI_TIPI, 13, "bold")
        )
        self.pencere.style.configure(
            "CloudText.TLabel", background=ana_renk, foreground="#FFFFFF",
            font=(YAZI_TIPI, 10, "bold")
        )
        self.cloud_durum_noktasi = ttk.Label(
            self.cloud_durum_dugmesi, text="●", style="CloudDot.TLabel", cursor="hand2"
        )
        self.cloud_durum_noktasi.pack(side=LEFT, padx=(4, 5))
        self.cloud_durum_yazisi = ttk.Label(
            self.cloud_durum_dugmesi, text="Cloud kapalı",
            style="CloudText.TLabel", cursor="hand2"
        )
        self.cloud_durum_yazisi.pack(side=LEFT, padx=(0, 4))
        for arac in (self.cloud_durum_dugmesi, self.cloud_durum_noktasi, self.cloud_durum_yazisi):
            arac.bind("<Button-1>", lambda _olay: self.senkronizasyon_merkezini_ac())
        self.cloud_durum_metni.trace_add("write", self.cloud_durum_stilini_guncelle)
        self.cloud_durum_stilini_guncelle()

        ttk.Button(
            ust,
            text="Hareket Geçmişi",
            command=self.hareket_gecmisini_goster,
            bootstyle="info-outline"
        ).pack(side=RIGHT)

        self.kritik_stok_dugmesi = ttk.Button(
            ust, text="Kritik Stoklar (0)",
            command=self.kritik_stok_raporu_ac,
            bootstyle="danger-outline"
        )
        self.kritik_stok_dugmesi.pack(side=RIGHT, padx=8)

        govde = ttk.Frame(self.pencere)
        govde.pack(fill=BOTH, expand=True)

        yan_menu = ttk.Frame(govde, padding=(12, 18), bootstyle="primary")
        yan_menu.pack(side=LEFT, fill=Y)
        ttk.Label(yan_menu,text="MENÜ",font=(YAZI_TIPI,11,"bold"),bootstyle="inverse-primary").pack(anchor="w",padx=8,pady=(0,12))
        menu_ogeleri = (
            ("⌂  Gösterge Paneli", self.ana_ekrani_yenile, "light"),
            ("▦  Ürünler", self.urun_yonetimini_ac, "primary"),
            ("⇆  Stok Transferi", self.genel_transfer_penceresini_ac, "success"),
            ("⇄  Operasyonlar", self.operasyon_merkezi_ac, "info"),
            ("▤  Raporlar", self.genel_raporu_ac, "success"),
            ("⌂  Depo ve Şubeler", self.konum_yonetimini_ac, "warning"),
            ("♙  Kullanıcılar", self.kullanici_yonetimini_ac, "secondary"),
            ("⚙  Ayarlar", self.ayarlar_penceresini_ac, "light"),
            ("?  Yardım", self.yardim_merkezini_ac, "light"),
        )
        for metin, komut, stil in menu_ogeleri:
            ttk.Button(yan_menu,text=metin,command=komut,bootstyle=stil,padding=(14,11),width=20).pack(fill=X,pady=4)
        ttk.Separator(yan_menu).pack(fill=X,pady=14)
        ttk.Label(yan_menu,text="DeporiaQ Modern\nGüvenli • Hızlı • Bulut",justify="left",bootstyle="inverse-primary").pack(anchor="w",padx=8)
        ttk.Label(
            yan_menu, text=TELIF_METNI, justify="left", wraplength=175,
            font=(YAZI_TIPI, 8), bootstyle="inverse-primary"
        ).pack(side=tk.BOTTOM, anchor="w", padx=8, pady=(12, 0))

        sag = ttk.Frame(govde)
        sag.pack(side=RIGHT, fill=BOTH, expand=True)

        # Oturum ve program düğmeleri görünür alanın dışına çıkmasın.
        alt_sabit = ttk.Frame(sag, padding=(16, 8), bootstyle="dark")
        alt_sabit.pack(side=tk.BOTTOM, fill=X)
        ttk.Label(
            alt_sabit,
            text="İpucu: Barkodu okutun, Enter'a basın, miktarı girip tekrar Enter'a basın.",
            bootstyle="inverse-dark"
        ).pack(side=LEFT)
        ttk.Button(
            alt_sabit, text="Çıkış Yap", command=self.oturumu_kapat,
            bootstyle="warning", padding=(18, 8)
        ).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(
            alt_sabit, text="Programı Kapat", command=self.programi_kapat,
            bootstyle="danger", padding=(18, 8)
        ).pack(side=RIGHT)

        kaydirma_alani = ttk.Frame(sag)
        kaydirma_alani.pack(fill=BOTH, expand=True)
        dikey = ttk.Scrollbar(kaydirma_alani, orient="vertical")
        yatay = ttk.Scrollbar(kaydirma_alani, orient="horizontal")
        icerik_canvas = tk.Canvas(
            kaydirma_alani, bg=RENK_ZEMIN, highlightthickness=0,
            yscrollcommand=dikey.set, xscrollcommand=yatay.set
        )
        dikey.configure(command=icerik_canvas.yview); yatay.configure(command=icerik_canvas.xview)
        dikey.pack(side=RIGHT, fill=Y); yatay.pack(side=tk.BOTTOM, fill=X)
        icerik_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        icerik = ttk.Frame(icerik_canvas)
        self.ana_icerik = icerik
        icerik_penceresi = icerik_canvas.create_window((0, 0), window=icerik, anchor="nw")
        icerik.bind(
            "<Configure>", lambda _e: icerik_canvas.configure(scrollregion=icerik_canvas.bbox("all"))
        )
        def tuvali_boyutlandir(olay):
            icerik_canvas.itemconfigure(icerik_penceresi, width=max(1050, olay.width))
        icerik_canvas.bind("<Configure>", tuvali_boyutlandir)
        icerik_canvas.bind(
            "<Enter>", lambda _e: icerik_canvas.bind_all(
                "<MouseWheel>", lambda e: icerik_canvas.yview_scroll(int(-e.delta/120), "units")
            )
        )
        icerik_canvas.bind("<Leave>", lambda _e: icerik_canvas.unbind_all("<MouseWheel>"))

        karsilama = ttk.Frame(icerik, padding=(24, 15))
        karsilama.pack(fill=X)
        ttk.Label(karsilama,text="İşletme Kontrol Paneli",font=(YAZI_TIPI,20,"bold"),foreground=RENK_METIN).pack(side=LEFT)
        ttk.Label(karsilama,text="Stok, satış, şube ve Cloud işlemleriniz tek ekranda.",foreground=RENK_SOLUK).pack(side=LEFT,padx=18)

        hizli_islemler = ttk.Labelframe(icerik, text=" Hızlı işlemler ", padding=(16, 10), bootstyle="primary")
        hizli_islemler.pack(fill=X, padx=24, pady=(0, 10))

        ttk.Button(
            hizli_islemler,
            text="Ürün Ekle",
            command=self.urun_yonetimini_ac,
            bootstyle="success",
            padding=(18, 8)
        ).pack(side=LEFT, padx=(0, 8))

        ttk.Button(
            hizli_islemler,
            text="Ürün Sil",
            command=self.urun_yonetimini_ac,
            bootstyle="danger-outline",
            padding=(18, 8)
        ).pack(side=LEFT, padx=(0, 8))

        ttk.Button(
            hizli_islemler,
            text="Fiyat Güncelle",
            command=self.urun_yonetimini_ac,
            bootstyle="warning",
            padding=(18, 8)
        ).pack(side=LEFT, padx=(0, 8))

        ttk.Button(
            hizli_islemler,
            text="Şubede Satış",
            command=self.sube_satis_penceresini_ac,
            bootstyle="success",
            padding=(18, 8)
        ).pack(side=LEFT, padx=(0, 8))

        ttk.Button(
            hizli_islemler,
            text="Genel Yönetici Raporu",
            command=self.genel_raporu_ac,
            bootstyle="info",
            padding=(18, 8)
        ).pack(side=LEFT)

        ttk.Button(
            hizli_islemler, text="Profesyonel Araçlar",
            command=self.profesyonel_araclar_ac,
            bootstyle="primary", padding=(18, 8)
        ).pack(side=LEFT, padx=8)

        ttk.Button(
            hizli_islemler, text="Operasyon Merkezi",
            command=self.operasyon_merkezi_ac,
            bootstyle="info", padding=(18, 8)
        ).pack(side=LEFT)

        ttk.Button(
            hizli_islemler,
            text="Kullanıcılar",
            command=self.kullanici_yonetimini_ac,
            bootstyle="primary-outline",
            padding=(18, 8)
        ).pack(side=RIGHT, padx=(0, 8))

        ttk.Button(
            hizli_islemler,
            text="Ayarlar",
            command=self.ayarlar_penceresini_ac,
            bootstyle="warning-outline",
            padding=(18, 8)
        ).pack(side=RIGHT, padx=(0, 8))

        ttk.Button(
            hizli_islemler,
            text="Güncellemeleri Kontrol Et",
            command=self.guncellemeleri_kontrol_et,
            bootstyle="secondary-outline",
            padding=(18, 8)
        ).pack(side=RIGHT)

        ttk.Button(
            hizli_islemler,
            text="Veri ve Yedekleme",
            command=self.veri_yonetimini_ac,
            bootstyle="info-outline",
            padding=(18, 8)
        ).pack(side=RIGHT, padx=(0, 8))

        self.ozet_alani = ttk.Frame(icerik, padding=(24, 4))
        self.ozet_alani.pack(fill=X)
        for sutun in range(4):
            self.ozet_alani.columnconfigure(sutun, weight=1)

        self.urun_sayisi = self.ozet_karti("Ürün çeşidi", 0, "primary")
        self.toplam_stok = self.ozet_karti("Seçili konum stoğu", 1, "success")
        self.toplam_deger = self.ozet_karti("Toplam stok değeri", 2, "warning")
        self.kritik_ozet = self.ozet_karti("Kritik stok uyarısı", 3, "danger")

        self.dashboard_analizlerini_olustur()

        konum_alani = ttk.Labelframe(
            icerik,
            text=" Görüntülenecek stok konumu ",
            padding=(18, 12),
            bootstyle="info"
        )
        konum_alani.pack(fill=X, padx=24, pady=(12, 2))
        konum_alani.columnconfigure(1, weight=1)

        ttk.Label(
            konum_alani,
            text="Konum seç:",
            font=(YAZI_TIPI, 11, "bold")
        ).grid(row=0, column=0, padx=(0, 12))

        self.konum_kutusu = ttk.Combobox(
            konum_alani,
            textvariable=self.konum_degiskeni,
            state="normal",
            font=(YAZI_TIPI, 11)
        )
        self.konum_kutusu.grid(row=0, column=1, sticky="ew")
        self.konum_kutusu.bind("<<ComboboxSelected>>", self.konum_degisti)
        self.konum_kutusu.bind("<KeyRelease>", self.konum_yazarak_ara)
        self.konum_kutusu.bind("<Return>", self.ilk_konumu_sec)

        ttk.Label(
            konum_alani,
            text="Depo veya şube seçtiğinizde tablo ve özet kartları otomatik yenilenir.",
            foreground=RENK_SOLUK
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        barkod_karti = ttk.Labelframe(
            icerik,
            text=" Barkod ile mal kabul ",
            padding=18,
            bootstyle="primary"
        )
        barkod_karti.pack(fill=X, padx=24, pady=(14, 8))
        self.barkod_karti = barkod_karti
        barkod_karti.columnconfigure(1, weight=2)
        barkod_karti.columnconfigure(3, weight=1)

        ttk.Label(barkod_karti, text="Barkod:").grid(row=0, column=0, padx=(0, 8))
        self.barkod_kutusu = ttk.Entry(
            barkod_karti,
            textvariable=self.barkod_degiskeni,
            font=("Consolas", 13)
        )
        self.barkod_kutusu.grid(row=0, column=1, sticky="ew", padx=(0, 16))
        self.barkod_kutusu.bind("<Return>", self.barkodu_bul)

        ttk.Label(barkod_karti, text="Miktar:").grid(row=0, column=2, padx=(0, 8))
        self.miktar_kutusu = ttk.Entry(
            barkod_karti,
            textvariable=self.miktar_degiskeni,
            font=(YAZI_TIPI, 12),
            width=14
        )
        self.miktar_kutusu.grid(row=0, column=3, sticky="ew", padx=(0, 16))
        self.miktar_kutusu.bind("<Return>", self.stok_girisi_yap)

        ttk.Button(
            barkod_karti,
            text="Stoğa Ekle",
            command=self.stok_girisi_yap,
            bootstyle="success",
            padding=(22, 10)
        ).grid(row=0, column=4)

        ttk.Label(
            barkod_karti,
            textvariable=self.secili_urun_degiskeni,
            font=(YAZI_TIPI, 11, "bold"),
            bootstyle="info"
        ).grid(row=1, column=0, columnspan=5, sticky="w", pady=(13, 0))

        arama_alani = ttk.Frame(icerik, padding=(24, 6))
        arama_alani.pack(fill=X)
        ttk.Label(arama_alani, text="Ürün veya barkod ara:").pack(side=LEFT, padx=(0, 9))
        self.urun_arama_kutusu = ttk.Combobox(
            arama_alani,
            textvariable=self.arama_degiskeni,
            state="normal"
        )
        self.urun_arama_kutusu.pack(side=LEFT, fill=X, expand=True)
        self.urun_arama_kutusu.bind("<KeyRelease>", self.urun_yazarak_ara)
        self.urun_arama_kutusu.bind("<<ComboboxSelected>>", lambda _olay: self.tabloyu_yenile())
        self.arama_degiskeni.trace_add("write", lambda *_: self.tabloyu_yenile())

        tablo_alani = ttk.Frame(icerik, padding=(24, 5))
        tablo_alani.pack(fill=BOTH, expand=True)

        self.tablo = ttk.Treeview(
            tablo_alani,
            columns=("barkod", "urun", "stok", "fiyat", "deger"),
            show="headings",
            bootstyle="primary",
            height=14
        )
        basliklar = {
            "barkod": "Barkod",
            "urun": "Ürün",
            "stok": "Stok miktarı",
            "fiyat": "Birim fiyat",
            "deger": "Stok değeri"
        }
        for sutun, baslik in basliklar.items():
            self.tablo.heading(sutun, text=baslik)

        self.tablo.column("barkod", width=170, anchor=CENTER)
        self.tablo.column("urun", width=280, anchor="w")
        self.tablo.column("stok", width=130, anchor=CENTER)
        self.tablo.column("fiyat", width=170, anchor="e")
        self.tablo.column("deger", width=190, anchor="e")

        kaydirma = ttk.Scrollbar(tablo_alani, command=self.tablo.yview)
        self.tablo.configure(yscrollcommand=kaydirma.set)
        self.tablo.pack(side=LEFT, fill=BOTH, expand=True)
        kaydirma.pack(side=RIGHT, fill=Y)

        self.yetkiye_gore_dugmeleri_duzenle()

    def yetkiye_gore_dugmeleri_duzenle(self):
        """Kullanıcının yapamayacağı işlemleri yalnızca kilitlemez, tamamen gizler."""
        rol = self.aktif_kullanici["rol"]
        izinli = {
            "ANA_YONETICI": None,
            "DEPO_PERSONELI": {"Stok Transferi", "⇆  Stok Transferi", "Hareket Geçmişi", "Yardım", "Çıkış Yap", "Programı Kapat"},
            "SUBE_PERSONELI": {"Şubede Satış", "Hareket Geçmişi", "Yardım", "Çıkış Yap", "Programı Kapat"},
            "GORUNTULEYICI": {"Genel Yönetici Raporu", "Hareket Geçmişi", "Yardım", "Çıkış Yap", "Programı Kapat"},
        }.get(rol, set())
        if izinli is None:
            return

        def tara(arac):
            for cocuk in arac.winfo_children():
                if isinstance(cocuk, ttk.Button):
                    try:
                        metin = str(cocuk.cget("text"))
                        if metin not in izinli:
                            yonetici = cocuk.winfo_manager()
                            if yonetici == "pack": cocuk.pack_forget()
                            elif yonetici == "grid": cocuk.grid_remove()
                    except tk.TclError:
                        pass
                tara(cocuk)
        tara(self.pencere)
        if rol != "ANA_YONETICI" and hasattr(self, "barkod_karti"):
            self.barkod_karti.pack_forget()

    def ozet_karti(self, baslik, sutun, renk):
        kart = ttk.Labelframe(
            self.ozet_alani,
            text=f" {baslik} ",
            padding=14,
            bootstyle=renk
        )
        kart.grid(row=0, column=sutun, sticky="ew", padx=6)
        deger = ttk.Label(kart, text="0", font=(YAZI_TIPI, 20, "bold"))
        deger.pack()
        return deger

    def dashboard_analizlerini_olustur(self):
        """Ana ekrana boşluk bırakmadan iki grafik ve son hareketleri yerleştirir."""
        alan = ttk.Labelframe(
            self.ana_icerik, text=" Canlı işletme görünümü ", padding=8, bootstyle="info"
        )
        alan.pack(fill=X, padx=24, pady=(8, 2))
        for sutun in range(3):
            alan.columnconfigure(sutun, weight=1)

        self.konum_grafigi = tk.Canvas(
            alan, height=112, bg=RENK_PANEL, highlightthickness=0
        )
        self.konum_grafigi.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.saglik_grafigi = tk.Canvas(
            alan, height=112, bg=RENK_PANEL, highlightthickness=0
        )
        self.saglik_grafigi.grid(row=0, column=1, sticky="nsew", padx=6)
        self.son_hareketler_tablosu = ttk.Treeview(
            alan, columns=("zaman", "urun", "adet"), show="headings",
            height=4, bootstyle="primary"
        )
        for kolon, baslik in (("zaman", "Son hareket"), ("urun", "Ürün"), ("adet", "Adet")):
            self.son_hareketler_tablosu.heading(kolon, text=baslik)
        self.son_hareketler_tablosu.column("zaman", width=125)
        self.son_hareketler_tablosu.column("urun", width=180)
        self.son_hareketler_tablosu.column("adet", width=65, anchor=CENTER)
        self.son_hareketler_tablosu.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self.dashboard_analizlerini_yenile()

    def dashboard_analizlerini_yenile(self):
        if not hasattr(self, "konum_grafigi"):
            return
        satirlar = self.vt.baglanti.execute(
            """SELECT k.ad, COALESCE(SUM(s.miktar),0) toplam
               FROM konumlar k LEFT JOIN stoklar s ON s.konum_id=k.id
               WHERE k.aktif=1 GROUP BY k.id ORDER BY toplam DESC LIMIT 5"""
        ).fetchall()
        c = self.konum_grafigi; c.delete("all")
        c.create_text(10, 9, anchor="nw", text="Konumlara göre stok", fill=RENK_METIN,
                      font=(YAZI_TIPI, 10, "bold"))
        en_buyuk = max([int(x["toplam"] or 0) for x in satirlar] or [1]) or 1
        for i, x in enumerate(satirlar):
            y = 34 + i * 15; oran = int(x["toplam"] or 0) / en_buyuk
            c.create_text(10, y, anchor="w", text=str(x["ad"])[:16], fill=RENK_METIN,
                          font=(YAZI_TIPI, 8))
            c.create_rectangle(118, y-5, 118 + 145*oran, y+5, fill="#38BDF8", outline="")
            c.create_text(270, y, anchor="e", text=str(int(x["toplam"] or 0)),
                          fill=RENK_METIN, font=(YAZI_TIPI, 8, "bold"))

        toplam = self.vt.baglanti.execute("SELECT COUNT(*) FROM stoklar").fetchone()[0]
        kritik = len(self.vt.kritik_stoklari_getir()); saglikli = max(0, toplam-kritik)
        c = self.saglik_grafigi; c.delete("all")
        c.create_text(10, 9, anchor="nw", text="Stok sağlığı", fill=RENK_METIN,
                      font=(YAZI_TIPI, 10, "bold"))
        oran = saglikli / max(1, toplam)
        c.create_rectangle(15, 46, 275, 70, fill="#374151", outline="")
        c.create_rectangle(15, 46, 15+260*oran, 70, fill="#34D399", outline="")
        c.create_text(145, 58, text=f"%{oran*100:.0f} sağlıklı", fill="#FFFFFF",
                      font=(YAZI_TIPI, 10, "bold"))
        c.create_text(15, 92, anchor="w", text=f"Sağlıklı: {saglikli}   Kritik: {kritik}",
                      fill=RENK_METIN, font=(YAZI_TIPI, 9))

        tablo = self.son_hareketler_tablosu
        tablo.delete(*tablo.get_children())
        hareketler = self.vt.baglanti.execute(
            """SELECT h.tarih_saat, u.ad, h.miktar FROM stok_hareketleri h
               JOIN urunler u ON u.id=h.urun_id ORDER BY h.id DESC LIMIT 4"""
        ).fetchall()
        for h in hareketler:
            tablo.insert("", END, values=(h["tarih_saat"], h["ad"], h["miktar"]))

    def konum_seciciyi_yenile(self):
        eski_secim = self.konum_degiskeni.get()
        konumlar = self.vt.konumlari_getir()
        self.konum_haritasi = {konum["ad"]: konum["id"] for konum in konumlar}
        konum_adlari = list(self.konum_haritasi)
        self.tum_konum_adlari = konum_adlari
        self.konum_kutusu["values"] = konum_adlari

        self.tum_urun_adlari = [
            urun["ad"] for urun in self.vt.tum_aktif_urunleri_getir()
        ]
        self.urun_arama_kutusu["values"] = self.tum_urun_adlari

        if eski_secim in self.konum_haritasi:
            self.konum_degiskeni.set(eski_secim)
        elif "Merkez Depo" in self.konum_haritasi:
            self.konum_degiskeni.set("Merkez Depo")
        elif konum_adlari:
            self.konum_degiskeni.set(konum_adlari[0])

    def konum_degisti(self, _olay=None):
        self.konum_kutusu["values"] = self.tum_konum_adlari
        self.tabloyu_yenile()

    def konum_yazarak_ara(self, olay=None):
        """Konum kutusunu yazılan parçaya göre anında daraltır."""
        if olay and olay.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab"):
            return
        aranan = self.konum_degiskeni.get().strip().casefold()
        sonuclar = [
            ad for ad in self.tum_konum_adlari
            if aranan in ad.casefold()
        ]
        self.konum_kutusu["values"] = sonuclar

    def ilk_konumu_sec(self, _olay=None):
        """Enter'a basıldığında filtrelenen ilk konumu seçer."""
        sonuclar = list(self.konum_kutusu["values"])
        if sonuclar:
            self.konum_degiskeni.set(sonuclar[0])
            self.konum_degisti()
        return "break"

    def urun_yazarak_ara(self, olay=None):
        """Ürün ararken eşleşen adları açılır öneri olarak gösterir."""
        if olay and olay.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab"):
            return
        aranan = self.arama_degiskeni.get().strip()
        sonuclar = [
            ad for ad in self.tum_urun_adlari
            if urun_arama_eslesir(ad, "", aranan)
        ]
        self.urun_arama_kutusu["values"] = sonuclar

    def secili_konum_id(self):
        return self.konum_haritasi.get(
            self.konum_degiskeni.get(),
            self.vt.merkez_depo_id()
        )

    def tabloyu_yenile(self):
        for satir in self.tablo.get_children():
            self.tablo.delete(satir)

        konum_id = self.secili_konum_id()

        self.tablo.tag_configure("tek", background="#202A3A" if self.tema != "acik" else "#F8FAFC")
        self.tablo.tag_configure("cift", background="#17202E" if self.tema != "acik" else "#EEF4FF")
        for sira, urun in enumerate(self.vt.urunleri_getir(
            self.arama_degiskeni.get().strip(),
            konum_id
        )):
            self.tablo.insert(
                "",
                END,
                tags=("tek" if sira % 2 == 0 else "cift",),
                values=(
                    urun["barkod"],
                    urun["ad"],
                    f"{urun['miktar']:,}".replace(",", "."),
                    para_bicimlendir(urun["fiyat"]),
                    para_bicimlendir(urun["miktar"] * urun["fiyat"])
                )
            )

        ozet = self.vt.ozet_getir(konum_id)
        self.urun_sayisi.config(text=str(ozet["urun_sayisi"]))
        self.toplam_stok.config(
            text=f"{ozet['toplam_stok']:,}".replace(",", ".")
        )
        self.toplam_deger.config(text=para_bicimlendir(ozet["toplam_deger"]))
        kritik_sayisi = len(self.vt.kritik_stoklari_getir())
        if hasattr(self, "kritik_ozet"):
            self.kritik_ozet.config(text=str(kritik_sayisi))
        if hasattr(self, "kritik_stok_dugmesi"):
            self.kritik_stok_dugmesi.configure(
                text=f"Kritik Stoklar ({kritik_sayisi})"
            )
        self.dashboard_analizlerini_yenile()

    def barkodu_bul(self, _olay=None):
        barkod = self.barkod_degiskeni.get().strip()

        if barkod == "":
            self.olumsuz_bildirimi("Lütfen barkod okutun veya yazın.")
            return

        urun = self.vt.barkodla_urun_bul(barkod)

        if urun is None:
            self.secili_urun = None
            self.secili_urun_degiskeni.set("Barkod kayıtlı değil")
            self.olumsuz_bildirimi("Bu barkoda ait ürün bulunamadı.")
            self.barkod_kutusu.select_range(0, END)
            return

        self.secili_urun = urun
        self.secili_urun_degiskeni.set(
            f"Seçilen ürün: {urun['ad']}  •  Mevcut stok: {urun['miktar']:,}".replace(",", ".")
        )
        self.miktar_kutusu.focus_set()

    def stok_girisi_yap(self, _olay=None):
        if not self.yetki_kontrol("STOK_GIRIS"):
            return
        if self.secili_urun is None:
            self.barkodu_bul()
            if self.secili_urun is None:
                return

        try:
            miktar = int(self.miktar_degiskeni.get().strip())
        except ValueError:
            self.olumsuz_bildirimi("Miktar tam sayı olmalıdır.")
            self.miktar_kutusu.focus_set()
            return

        if miktar <= 0:
            self.olumsuz_bildirimi("Miktar en az 1 olmalıdır.")
            return

        urun_adi = self.secili_urun["ad"]
        self.vt.merkeze_stok_girisi(self.secili_urun["id"], miktar)
        self.vt.denetim_ekle("STOK_GIRISI", f"{urun_adi} • Merkez Depo • {miktar} adet")
        self.tabloyu_yenile()

        self.basari_bildirimi(
            f"{urun_adi}: merkez depoya {miktar:,} adet eklendi.".replace(",", ".")
        )
        self.barkod_degiskeni.set("")
        self.miktar_degiskeni.set("")
        self.secili_urun = None
        self.secili_urun_degiskeni.set("Yeni ürün için barkod okutun")
        self.barkod_kutusu.focus_set()

    def urun_yonetimini_ac(self):
        if not self.yetki_kontrol("YONETIM"):
            return
        pencere = self.uygulama_ici_sayfa_ac("Ürün Yönetimi")
        pencere.title("Ürün Yönetimi")
        pencere.geometry("980x720")
        pencere.transient(self.pencere)

        ttk.Label(
            pencere,
            text="ÜRÜN YÖNETİMİ",
            font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark",
            padding=18
        ).pack(fill=X)

        form = ttk.Labelframe(pencere, text=" Ürün bilgileri ", padding=16, bootstyle="primary")
        form.pack(fill=X, padx=20, pady=16)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        barkod = tk.StringVar()
        ad = tk.StringVar()
        fiyat = tk.StringVar(); alis = tk.StringVar(value="0"); kritik = tk.StringVar(value="10")
        urun_arama = tk.StringVar()

        ttk.Label(form, text="Barkod:").grid(row=0, column=0, padx=(0, 7), pady=6)
        barkod_kutusu = ttk.Entry(form, textvariable=barkod)
        barkod_kutusu.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=6)
        ttk.Label(form, text="Ürün adı:").grid(row=0, column=2, padx=(0, 7), pady=6)
        ttk.Entry(form, textvariable=ad).grid(row=0, column=3, sticky="ew", pady=6)
        ttk.Label(form, text="Birim fiyat:").grid(row=1, column=0, padx=(0, 7), pady=6)
        ttk.Entry(form, textvariable=fiyat).grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=6)
        ttk.Label(form, text="Alış fiyatı:").grid(row=1, column=2, padx=(0, 7), pady=6)
        ttk.Entry(form, textvariable=alis).grid(row=1, column=3, sticky="ew", pady=6)
        ttk.Label(form, text="Kritik stok:").grid(row=2, column=0, padx=(0, 7), pady=6)
        ttk.Entry(form, textvariable=kritik).grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=6)

        arama_alani = ttk.Frame(pencere, padding=(20, 0, 20, 10))
        arama_alani.pack(fill=X)
        ttk.Label(arama_alani, text="Ürün veya barkod ara:").pack(side=LEFT, padx=(0, 9))
        urun_arama_kutusu = ttk.Combobox(
            arama_alani,
            textvariable=urun_arama,
            state="normal"
        )
        urun_arama_kutusu.pack(side=LEFT, fill=X, expand=True)

        tablo_alani = ttk.Frame(pencere, padding=(20, 0, 20, 12))
        tablo_alani.pack(fill=BOTH, expand=True)
        urun_tablosu = ttk.Treeview(
            tablo_alani,
            columns=("barkod", "ad", "fiyat", "alis", "kritik"),
            show="headings",
            bootstyle="primary"
        )
        urun_tablosu.heading("barkod", text="Barkod")
        urun_tablosu.heading("ad", text="Ürün adı")
        urun_tablosu.heading("fiyat", text="Birim fiyat")
        urun_tablosu.heading("alis", text="Alış fiyatı")
        urun_tablosu.heading("kritik", text="Kritik stok")
        urun_tablosu.column("barkod", width=210, anchor=CENTER)
        urun_tablosu.column("ad", width=300, anchor="w")
        urun_tablosu.column("fiyat", width=150, anchor="e")
        urun_tablosu.column("alis", width=150, anchor="e")
        urun_tablosu.column("kritik", width=100, anchor=CENTER)
        urun_tablosu.pack(fill=BOTH, expand=True)

        def listeyi_yenile(*_args):
            for satir in urun_tablosu.get_children():
                urun_tablosu.delete(satir)
            aranan = urun_arama.get().strip()
            for urun in self.vt.tum_aktif_urunleri_getir():
                if not urun_arama_eslesir(urun["ad"], urun["barkod"], aranan):
                    continue
                urun_tablosu.insert(
                    "", END, iid=str(urun["id"]),
                    values=(urun["barkod"], urun["ad"], para_bicimlendir(urun["fiyat"]),
                            para_bicimlendir(urun["alis_fiyati"]), urun["kritik_stok"])
                )

        def secimi_getir(_olay=None):
            secim = urun_tablosu.selection()
            if not secim:
                return
            degerler = urun_tablosu.item(secim[0], "values")
            barkod.set(degerler[0])
            ad.set(degerler[1])
            fiyat.set(degerler[2].replace(" TL", "").replace(".", "").replace(",", "."))
            alis.set(degerler[3].replace(" TL", "").replace(".", "").replace(",", ".")); kritik.set(degerler[4])

        def fiyat_degeri():
            try:
                return float(fiyat.get().strip().replace(",", "."))
            except ValueError:
                raise ValueError("Lütfen geçerli bir fiyat girin.")

        def alis_ve_kritik_degeri():
            try: return float(alis.get().strip().replace(",", ".")), int(kritik.get().strip())
            except ValueError: raise ValueError("Alış fiyatı ve kritik stok geçerli sayı olmalıdır.")

        def urun_ekle():
            try:
                a,k=alis_ve_kritik_degeri(); self.vt.urun_ekle(barkod.get(), ad.get(), fiyat_degeri(), a, k)
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return
            barkod.set(""); ad.set(""); fiyat.set(""); alis.set("0"); kritik.set("10")
            listeyi_yenile(); self.konum_seciciyi_yenile(); self.tabloyu_yenile()
            self.basari_bildirimi("Ürün tüm konumlara 0 stokla eklendi.", pencere)

        def fiyati_guncelle():
            secim = urun_tablosu.selection()
            if not secim:
                self.olumsuz_bildirimi("Önce listeden ürün seçin.", pencere)
                return
            try:
                self.vt.urun_fiyati_guncelle(int(secim[0]), fiyat_degeri())
                a,k=alis_ve_kritik_degeri(); self.vt.urun_maliyet_ve_kritik_guncelle(int(secim[0]),a,k)
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return
            listeyi_yenile(); self.tabloyu_yenile()
            self.vt.denetim_ekle("URUN_GUNCELLENDI",ad.get())
            self.basari_bildirimi("Satış, alış fiyatı ve kritik stok güncellendi.", pencere)

        def urunu_kaldir():
            secim = urun_tablosu.selection()
            if not secim:
                self.olumsuz_bildirimi("Önce listeden ürün seçin.", pencere)
                return
            urun_adi = urun_tablosu.item(secim[0], "values")[1]
            if not self.modern_onay("Ürünü kaldır", f"{urun_adi} ürününü kaldırmak istiyor musunuz?", pencere, "Ürünü Kaldır"):
                return
            try:
                self.vt.urunu_pasiflestir(int(secim[0]))
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return
            barkod.set(""); ad.set(""); fiyat.set("")
            listeyi_yenile(); self.konum_seciciyi_yenile(); self.tabloyu_yenile()
            self.basari_bildirimi("Ürün aktif listeden kaldırıldı; geçmişi korundu.", pencere)

        butonlar = ttk.Frame(pencere, padding=(20, 0, 20, 16))
        butonlar.pack(fill=X)
        ttk.Button(butonlar, text="Yeni Ürün Ekle", command=urun_ekle, bootstyle="success").pack(side=LEFT, padx=(0, 8))
        ttk.Button(butonlar, text="Fiyatı Güncelle", command=fiyati_guncelle, bootstyle="info").pack(side=LEFT, padx=(0, 8))
        ttk.Button(butonlar, text="Ürünü Kaldır", command=urunu_kaldir, bootstyle="danger-outline").pack(side=LEFT)
        urun_tablosu.bind("<<TreeviewSelect>>", secimi_getir)
        urun_arama.trace_add("write", listeyi_yenile)
        self.aramali_secim_hazirla(
            urun_arama_kutusu,
            urun_arama,
            lambda: [urun["ad"] for urun in self.vt.tum_aktif_urunleri_getir()]
        )
        listeyi_yenile(); barkod_kutusu.focus_set()

    def konum_yonetimini_ac(self):
        if not self.yetki_kontrol("YONETIM"):
            return
        pencere = self.uygulama_ici_sayfa_ac("Depo ve Şube Yönetimi")
        pencere.title("Depo ve Şube Yönetimi")
        pencere.geometry("850x680")
        pencere.transient(self.pencere)

        ttk.Label(
            pencere,
            text="DEPO VE ŞUBE YÖNETİMİ",
            font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark",
            padding=18
        ).pack(fill=X)

        form = ttk.Labelframe(
            pencere,
            text=" Yeni konum ekle ",
            padding=16,
            bootstyle="warning"
        )
        form.pack(fill=X, padx=20, pady=16)
        form.columnconfigure(1, weight=1)

        ad_degiskeni = tk.StringVar()
        tur_degiskeni = tk.StringVar(value="Depo")
        konum_arama = tk.StringVar()

        ttk.Label(form, text="Konum adı:").grid(row=0, column=0, padx=(0, 8))
        ad_kutusu = ttk.Entry(form, textvariable=ad_degiskeni)
        ad_kutusu.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        ttk.Label(form, text="Tür:").grid(row=0, column=2, padx=(0, 8))
        tur_kutusu = ttk.Combobox(
            form,
            textvariable=tur_degiskeni,
            values=("Depo", "Şube"),
            state="readonly",
            width=12
        )
        tur_kutusu.grid(row=0, column=3, padx=(0, 12))

        arama_alani = ttk.Frame(pencere, padding=(20, 0, 20, 10))
        arama_alani.pack(fill=X)
        ttk.Label(arama_alani, text="Depo veya şube ara:").pack(side=LEFT, padx=(0, 9))
        konum_arama_kutusu = ttk.Combobox(
            arama_alani,
            textvariable=konum_arama,
            state="normal"
        )
        konum_arama_kutusu.pack(side=LEFT, fill=X, expand=True)

        liste_alani = ttk.Frame(pencere, padding=(20, 0, 20, 15))
        liste_alani.pack(fill=BOTH, expand=True)
        konum_tablosu = ttk.Treeview(
            liste_alani,
            columns=("ad", "tur"),
            show="headings",
            bootstyle="warning"
        )
        konum_tablosu.heading("ad", text="Konum adı")
        konum_tablosu.heading("tur", text="Konum türü")
        konum_tablosu.column("ad", width=480, anchor="w")
        konum_tablosu.column("tur", width=180, anchor=CENTER)
        konum_tablosu.tag_configure("merkez", background="#244b63", foreground="#ffffff")
        konum_tablosu.tag_configure("depo", background="#24513f", foreground="#ffffff")
        konum_tablosu.tag_configure("sube", background="#493968", foreground="#ffffff")
        konum_tablosu.pack(fill=BOTH, expand=True)

        def konum_listesini_yenile(*_args):
            for satir in konum_tablosu.get_children():
                konum_tablosu.delete(satir)

            tur_adlari = {
                "MERKEZ": "Merkez Depo",
                "DEPO": "Depo",
                "SUBE": "Şube"
            }
            aranan = konum_arama.get().strip().casefold()
            for konum in self.vt.konumlari_getir():
                if aranan and aranan not in konum["ad"].casefold():
                    continue
                konum_tablosu.insert(
                    "",
                    END,
                    iid=str(konum["id"]),
                    values=(konum["ad"], tur_adlari[konum["tur"]]),
                    tags=(konum["tur"].lower(),)
                )

        def secimi_forma_getir(_olay=None):
            secim = konum_tablosu.selection()
            if not secim:
                return
            degerler = konum_tablosu.item(secim[0], "values")
            ad_degiskeni.set(degerler[0])
            if degerler[1] != "Merkez Depo":
                tur_degiskeni.set(degerler[1])

        def konumu_kaydet():
            tur = "DEPO" if tur_degiskeni.get() == "Depo" else "SUBE"
            try:
                self.vt.konum_ekle(ad_degiskeni.get(), tur)
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return

            self.basari_bildirimi(f"{ad_degiskeni.get().strip()} başarıyla eklendi.", pencere)
            ad_degiskeni.set("")
            konum_listesini_yenile()
            self.konum_seciciyi_yenile()
            self.tabloyu_yenile()
            ad_kutusu.focus_set()

        def konumu_guncelle():
            secim = konum_tablosu.selection()
            if not secim:
                self.olumsuz_bildirimi("Önce listeden bir konum seçin.", pencere)
                return
            try:
                self.vt.konum_guncelle(int(secim[0]), ad_degiskeni.get())
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return
            konum_listesini_yenile()
            self.konum_seciciyi_yenile()
            self.tabloyu_yenile()
            self.basari_bildirimi("Konum adı güncellendi.", pencere)

        def konumu_kaldir():
            secim = konum_tablosu.selection()
            if not secim:
                self.olumsuz_bildirimi("Önce listeden bir konum seçin.", pencere)
                return
            ad = konum_tablosu.item(secim[0], "values")[0]
            if not self.modern_onay(
                "Konumu kaldır",
                f"{ad} konumunu kaldırmak istediğinize emin misiniz?",
                pencere, "Konumu Kaldır"
            ):
                return
            try:
                self.vt.konumu_pasiflestir(int(secim[0]))
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return
            ad_degiskeni.set("")
            konum_listesini_yenile()
            self.konum_seciciyi_yenile()
            self.tabloyu_yenile()
            self.basari_bildirimi("Konum aktif listeden kaldırıldı.", pencere)

        ttk.Button(
            form,
            text="Konumu Ekle",
            command=konumu_kaydet,
            bootstyle="warning",
            padding=(16, 8)
        ).grid(row=0, column=4)

        duzenleme_alani = ttk.Frame(pencere, padding=(20, 0, 20, 14))
        duzenleme_alani.pack(fill=X)
        ttk.Label(
            duzenleme_alani,
            text="■ Merkez Depo",
            foreground="#69b7e6"
        ).pack(side=RIGHT, padx=8)
        ttk.Label(
            duzenleme_alani,
            text="■ Depo",
            foreground="#68c99a"
        ).pack(side=RIGHT, padx=8)
        ttk.Label(
            duzenleme_alani,
            text="■ Şube",
            foreground="#b59aee"
        ).pack(side=RIGHT, padx=8)
        ttk.Button(
            duzenleme_alani,
            text="Seçili Konumun Adını Güncelle",
            command=konumu_guncelle,
            bootstyle="info"
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Button(
            duzenleme_alani,
            text="Seçili Konumu Kaldır",
            command=konumu_kaldir,
            bootstyle="danger-outline"
        ).pack(side=LEFT)

        konum_tablosu.bind("<<TreeviewSelect>>", secimi_forma_getir)
        konum_arama.trace_add("write", konum_listesini_yenile)
        self.aramali_secim_hazirla(
            konum_arama_kutusu,
            konum_arama,
            lambda: [konum["ad"] for konum in self.vt.konumlari_getir()]
        )

        konum_listesini_yenile()
        ad_kutusu.focus_set()

    def genel_transfer_penceresini_ac(self):
        if not self.yetki_kontrol("TRANSFER"):
            return
        kaynaklar = [k for k in self.vt.konumlari_getir() if k["tur"] in ("MERKEZ", "DEPO")]
        if self.aktif_kullanici["rol"] == "DEPO_PERSONELI":
            kaynaklar = [
                k for k in kaynaklar
                if k["id"] == self.aktif_kullanici["konum_id"]
            ]
        if not kaynaklar:
            self.olumsuz_bildirimi("Hesabınıza atanmış aktif bir kaynak depo bulunamadı.")
            return
        if not any(self.vt.hedef_konumlari_getir(k["id"]) for k in kaynaklar):
            self.olumsuz_bildirimi("Transfer için kaynak dışında en az bir aktif depo veya şube ekleyin.")
            return

        pencere = self.uygulama_ici_sayfa_ac("Barkodlu Stok Transferi")
        pencere.title("Barkodlu Stok Transferi")
        pencere.geometry("820x580")
        pencere.transient(self.pencere)
        ttk.Label(
            pencere, text="BARKODLU STOK TRANSFERİ",
            font=(YAZI_TIPI, 19, "bold"), bootstyle="inverse-dark", padding=18
        ).pack(fill=X)

        form = ttk.Labelframe(pencere, text=" Transfer bilgileri ", padding=22, bootstyle="success")
        form.pack(fill=BOTH, expand=True, padx=24, pady=22)
        form.columnconfigure(1, weight=1)

        kaynak_haritasi = {k["ad"]: k["id"] for k in kaynaklar}
        kaynak_ad = tk.StringVar(value=kaynaklar[0]["ad"])
        hedef_ad = tk.StringVar()
        barkod = tk.StringVar()
        miktar = tk.StringVar()
        bilgi = tk.StringVar(value="Barkodu okutun")
        secili = {"urun": None}
        hedef_haritasi = {}

        ttk.Label(form, text="Kaynak:").grid(row=0, column=0, sticky="w", pady=8)
        kaynak_kutusu = ttk.Combobox(form, textvariable=kaynak_ad, values=list(kaynak_haritasi), state="normal")
        kaynak_kutusu.grid(row=0, column=1, sticky="ew", pady=8)
        ttk.Label(form, text="Hedef:").grid(row=1, column=0, sticky="w", pady=8)
        hedef_kutusu = ttk.Combobox(form, textvariable=hedef_ad, state="normal")
        hedef_kutusu.grid(row=1, column=1, sticky="ew", pady=8)
        ttk.Label(form, text="Barkod:").grid(row=2, column=0, sticky="w", pady=8)
        barkod_kutusu = ttk.Entry(form, textvariable=barkod, font=("Consolas", 13))
        barkod_kutusu.grid(row=2, column=1, sticky="ew", pady=8)
        ttk.Label(form, text="Miktar:").grid(row=3, column=0, sticky="w", pady=8)
        miktar_kutusu = ttk.Entry(form, textvariable=miktar)
        miktar_kutusu.grid(row=3, column=1, sticky="ew", pady=8)
        ttk.Label(form, textvariable=bilgi, font=(YAZI_TIPI, 11, "bold"), bootstyle="info").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=14
        )

        def hedefleri_yenile(_olay=None):
            nonlocal hedef_haritasi
            hedefler = self.vt.hedef_konumlari_getir(kaynak_haritasi[kaynak_ad.get()])
            hedef_haritasi = {k["ad"]: k["id"] for k in hedefler}
            hedef_kutusu["values"] = list(hedef_haritasi)
            hedef_ad.set(next(iter(hedef_haritasi), ""))
            secili["urun"] = None; barkod.set(""); miktar.set(""); bilgi.set("Barkodu okutun")

        def barkodu_bul(_olay=None):
            kaynak_id = kaynak_haritasi[kaynak_ad.get()]
            urun = self.vt.barkodla_urun_bul(barkod.get().strip(), kaynak_id)
            if urun is None:
                secili["urun"] = None
                self.olumsuz_bildirimi("Barkod kaynak konumda bulunamadı.", pencere)
                return
            secili["urun"] = urun
            bilgi.set(f"{urun['ad']} • Kaynak stok: {urun['miktar']:,}".replace(",", "."))
            miktar_kutusu.focus_set()

        def transfer(_olay=None):
            if not hedef_ad.get():
                self.olumsuz_bildirimi("Bu kaynak için uygun hedef bulunmuyor.", pencere)
                return
            if secili["urun"] is None:
                barkodu_bul()
                if secili["urun"] is None:
                    return
            try:
                adet = int(miktar.get().strip())
                kaynak_adi, hedef_adi = self.vt.stok_transferi(
                    secili["urun"]["id"], kaynak_haritasi[kaynak_ad.get()],
                    hedef_haritasi[hedef_ad.get()], adet
                )
                self.vt.denetim_ekle("STOK_TRANSFERI",f"{kaynak_adi} → {hedef_adi} • {secili['urun']['ad']} • {adet} adet")
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return
            self.basari_bildirimi(
                f"{secili['urun']['ad']}: {kaynak_adi} → {hedef_adi}, {adet:,} adet".replace(",", "."),
                pencere
            )
            self.tabloyu_yenile(); secili["urun"] = None
            barkod.set(""); miktar.set(""); bilgi.set("Yeni transfer için barkodu okutun")
            barkod_kutusu.focus_set()

        self.aramali_secim_hazirla(
            kaynak_kutusu, kaynak_ad, lambda: list(kaynak_haritasi), hedefleri_yenile
        )
        self.aramali_secim_hazirla(
            hedef_kutusu, hedef_ad, lambda: list(hedef_haritasi)
        )
        barkod_kutusu.bind("<Return>", barkodu_bul)
        miktar_kutusu.bind("<Return>", transfer)
        ttk.Button(form, text="Transferi Tamamla", command=transfer, bootstyle="success", padding=(22, 10)).grid(
            row=5, column=0, columnspan=2, pady=12
        )
        hedefleri_yenile(); barkod_kutusu.focus_set()

    def sube_satis_penceresini_ac(self):
        if not self.yetki_kontrol("SATIS"):
            return
        subeler = self.vt.konumlari_getir("SUBE")
        if self.aktif_kullanici["rol"] == "SUBE_PERSONELI":
            subeler = [
                s for s in subeler
                if s["id"] == self.aktif_kullanici["konum_id"]
            ]
        if not subeler:
            self.olumsuz_bildirimi("Önce en az bir şube ekleyin.")
            return

        pencere = self.uygulama_ici_sayfa_ac("Şubede Barkodlu Satış")
        pencere.title("Şubede Barkodlu Satış")
        pencere.geometry("760x510")
        pencere.transient(self.pencere)
        ttk.Label(
            pencere, text="ŞUBEDE BARKODLU SATIŞ", font=(YAZI_TIPI, 19, "bold"),
            bootstyle="inverse-dark", padding=18
        ).pack(fill=X)
        form = ttk.Labelframe(pencere, text=" Satış bilgileri ", padding=22, bootstyle="primary")
        form.pack(fill=BOTH, expand=True, padx=24, pady=22); form.columnconfigure(1, weight=1)

        sube_haritasi = {s["ad"]: s["id"] for s in subeler}
        sube_ad = tk.StringVar(value=subeler[0]["ad"]); barkod = tk.StringVar(); miktar = tk.StringVar()
        bilgi = tk.StringVar(value="Barkodu okutun"); secili = {"urun": None}
        ttk.Label(form, text="Şube:").grid(row=0, column=0, sticky="w", pady=8)
        sube_kutusu = ttk.Combobox(form, textvariable=sube_ad, values=list(sube_haritasi), state="normal")
        sube_kutusu.grid(row=0, column=1, sticky="ew", pady=8)
        ttk.Label(form, text="Barkod:").grid(row=1, column=0, sticky="w", pady=8)
        barkod_kutusu = ttk.Entry(form, textvariable=barkod, font=("Consolas", 13)); barkod_kutusu.grid(row=1, column=1, sticky="ew", pady=8)
        ttk.Label(form, text="Adet:").grid(row=2, column=0, sticky="w", pady=8)
        miktar_kutusu = ttk.Entry(form, textvariable=miktar); miktar_kutusu.grid(row=2, column=1, sticky="ew", pady=8)
        ttk.Label(form, textvariable=bilgi, font=(YAZI_TIPI, 11, "bold"), bootstyle="info").grid(row=3, column=0, columnspan=2, sticky="w", pady=14)

        def barkodu_bul(_olay=None):
            urun = self.vt.barkodla_urun_bul(barkod.get().strip(), sube_haritasi[sube_ad.get()])
            if urun is None:
                secili["urun"] = None; self.olumsuz_bildirimi("Ürün şubede bulunamadı.", pencere); return
            secili["urun"] = urun
            bilgi.set(f"{urun['ad']} • Şube stoğu: {urun['miktar']} • {para_bicimlendir(urun['fiyat'])}")
            miktar_kutusu.focus_set()

        def satis(_olay=None):
            if secili["urun"] is None:
                barkodu_bul()
                if secili["urun"] is None: return
            try:
                adet = int(miktar.get().strip())
                urun_ad, sube_adi, birim, toplam = self.vt.subede_satis_yap(
                    secili["urun"]["id"], sube_haritasi[sube_ad.get()], adet
                )
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere); return
            self.basari_bildirimi(
                f"Satış tamamlandı: {sube_adi}, {urun_ad}, {adet} adet, {para_bicimlendir(toplam)}",
                pencere
            )
            self.tabloyu_yenile(); secili["urun"] = None; barkod.set(""); miktar.set(""); bilgi.set("Yeni satış için barkodu okutun")
            barkod_kutusu.focus_set()

        def sube_degisti(_olay=None):
            secili["urun"] = None; barkod.set(""); miktar.set(""); bilgi.set("Barkodu okutun")

        self.aramali_secim_hazirla(
            sube_kutusu, sube_ad, lambda: list(sube_haritasi), sube_degisti
        )
        barkod_kutusu.bind("<Return>", barkodu_bul); miktar_kutusu.bind("<Return>", satis)
        ttk.Button(form, text="Satışı Tamamla", command=satis, bootstyle="success", padding=(22, 10)).grid(row=4, column=0, pady=12)
        ttk.Button(form, text="Son Fişi Aç / Yazdır", command=self.son_satis_fisini_ac,
                   bootstyle="info-outline", padding=(22, 10)).grid(row=4, column=1, pady=12)
        barkod_kutusu.focus_set()

    def son_satis_fisini_ac(self):
        if not self.son_satis:
            self.olumsuz_bildirimi("Bu oturumda yazdırılacak satış bulunmuyor.")
            return
        s=self.son_satis
        belge=f'''<!doctype html><meta charset="utf-8"><title>DeporiaQ Satış Fişi</title>
        <style>@page{{size:80mm auto;margin:6mm}}body{{width:68mm;font:14px Arial;color:#000}}h2,p{{text-align:center}}table{{width:100%;border-collapse:collapse}}td{{padding:6px 0;border-bottom:1px dashed #777}}.t{{font-size:18px;font-weight:bold}}</style>
        <h2>{html.escape(self.isletme_adi)}</h2><p>{html.escape(s['sube'])}<br>{s['tarih']}</p>
        <table><tr><td>{html.escape(s['urun'])} × {s['adet']}</td><td>{para_bicimlendir(s['toplam'])}</td></tr>
        <tr><td>Birim fiyat</td><td>{para_bicimlendir(s['birim'])}</td></tr><tr class="t"><td>TOPLAM</td><td>{para_bicimlendir(s['toplam'])}</td></tr></table>
        <p>Teşekkür ederiz</p><script>window.onload=()=>window.print()</script>'''
        yol=Path(tempfile.gettempdir())/"DeporiaQ_Son_Satis_Fisi.html"; yol.write_text(belge,encoding="utf-8"); webbrowser.open(yol.as_uri())

    def tablo_raporunu_yazdir(self, baslik, tablo, alt_bilgi=""):
        """Ekrandaki tabloyu yazıcı seçilebilen, temiz bir A4 raporuna dönüştürür."""
        baslik = self.cevir(baslik)
        sutunlar = list(tablo["columns"])
        basliklar = [tablo.heading(s).get("text", s) for s in sutunlar]
        satirlar = [tablo.item(i, "values") for i in tablo.get_children()]
        if not satirlar:
            self.olumsuz_bildirimi("Yazdırılacak rapor kaydı bulunmuyor.")
            return
        th = "".join(f"<th>{html.escape(str(x))}</th>" for x in basliklar)
        trs = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in satir) + "</tr>"
            for satir in satirlar
        )
        belge = f'''<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(baslik)}</title>
        <style>@page{{size:A4 landscape;margin:12mm}}body{{font:12px "Segoe UI",Arial;color:#111}}
        header{{display:flex;justify-content:space-between;align-items:end;border-bottom:3px solid #2563eb;margin-bottom:16px}}
        h1{{font-size:22px;margin:0 0 8px}}.meta{{text-align:right;color:#555}}table{{width:100%;border-collapse:collapse}}
        th{{background:#1e3a5f;color:#fff;text-align:left;padding:8px}}td{{padding:7px;border-bottom:1px solid #ccc}}
        tr:nth-child(even){{background:#f3f6fa}}footer{{margin-top:14px;font-weight:600}}</style></head><body>
        <header><h1>DeporiaQ · {html.escape(baslik)}</h1><div class="meta">{html.escape(self.isletme_adi)}<br>{datetime.now():%d.%m.%Y %H:%M}</div></header>
        <table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table><footer>{html.escape(alt_bilgi)}</footer>
        <script>window.onload=()=>window.print()</script></body></html>'''
        guvenli_ad = "".join(c if c.isalnum() else "_" for c in baslik)[:50]
        yol = Path(tempfile.gettempdir()) / f"DeporiaQ_{guvenli_ad}.html"
        yol.write_text(belge, encoding="utf-8")
        self.vt.denetim_ekle("RAPOR_YAZDIRMA", baslik)
        webbrowser.open(yol.as_uri())

    def genel_raporu_ac(self):
        pencere = self.uygulama_ici_sayfa_ac("Genel Yönetici Stok Raporu")
        pencere.title("Genel Yönetici Stok Raporu")
        pencere.geometry("950x650")
        ttk.Label(
            pencere, text="GENEL YÖNETİCİ STOK RAPORU", font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark", padding=18
        ).pack(fill=X)
        alan = ttk.Frame(pencere, padding=20)
        alan.pack(fill=BOTH, expand=True)
        tablo = ttk.Treeview(
            alan, columns=("konum", "tur", "stok", "deger"),
            show="headings", bootstyle="info"
        )
        for sutun, baslik in zip(
            tablo["columns"], ("Konum", "Tür", "Toplam stok", "Stok değeri")
        ):
            tablo.heading(sutun, text=baslik)
        tablo.column("konum", width=380, anchor="w")
        tablo.column("tur", width=140, anchor=CENTER)
        tablo.column("stok", width=150, anchor="e")
        tablo.column("deger", width=210, anchor="e")
        tablo.pack(fill=BOTH, expand=True)
        turler = {"MERKEZ": "Merkez Depo", "DEPO": "Depo", "SUBE": "Şube"}
        genel_stok = 0
        genel_deger = 0
        for kayit in self.vt.konum_ozetleri_getir():
            genel_stok += kayit["toplam_stok"]
            genel_deger += kayit["toplam_deger"]
            tablo.insert("", END, values=(
                kayit["ad"], turler[kayit["tur"]],
                f"{kayit['toplam_stok']:,}".replace(",", "."),
                para_bicimlendir(kayit["toplam_deger"])
            ))
        ttk.Label(
            pencere,
            text=(
                "Şirket geneli: " + f"{genel_stok:,}".replace(",", ".")
                + " adet • " + para_bicimlendir(genel_deger)
            ),
            font=(YAZI_TIPI, 13, "bold"), bootstyle="success", padding=15
        ).pack(fill=X)
        ttk.Button(
            pencere, text="Raporu Yazdır",
            command=lambda: self.tablo_raporunu_yazdir(
                "Genel Yönetici Stok Raporu", tablo,
                "Şirket geneli: " + f"{genel_stok:,}".replace(",", ".")
                + " adet · " + para_bicimlendir(genel_deger)
            ), bootstyle="info", padding=(20, 9)
        ).pack(pady=(0, 12))

    def kritik_stok_raporu_ac(self):
        pencere = self.uygulama_ici_sayfa_ac("Kritik Stok Raporu")
        pencere.title("Kritik Stok Raporu")
        pencere.geometry("950x650")
        ttk.Label(pencere, text="KRİTİK STOK RAPORU", font=(YAZI_TIPI, 20, "bold"),
                  bootstyle="inverse-dark", padding=18).pack(fill=X)
        tablo = ttk.Treeview(pencere, columns=("konum","barkod","urun","stok","kritik"),
                             show="headings", bootstyle="danger")
        for k,b in zip(tablo["columns"],("Konum","Barkod","Ürün","Mevcut","Kritik seviye")):
            tablo.heading(k,text=b)
        tablo.column("konum",width=260); tablo.column("barkod",width=150)
        tablo.column("urun",width=280); tablo.column("stok",width=100,anchor=CENTER)
        tablo.column("kritik",width=110,anchor=CENTER)
        for x in self.vt.kritik_stoklari_getir():
            tablo.insert("",END,values=(x["konum"],x["barkod"],x["urun"],x["miktar"],x["kritik_stok"]))
        tablo.pack(fill=BOTH,expand=True,padx=20,pady=20)
        ttk.Button(
            pencere, text="Raporu Yazdır",
            command=lambda: self.tablo_raporunu_yazdir("Kritik Stok Raporu", tablo),
            bootstyle="danger", padding=(20, 9)
        ).pack(pady=(0, 14))

    def kar_raporu_ac(self):
        pencere = self.uygulama_ici_sayfa_ac("Satış ve Brüt Kâr Raporu")
        pencere.title("Satış ve Brüt Kâr Raporu")
        pencere.geometry("1050x680")
        ttk.Label(pencere,text="SATIŞ VE BRÜT KÂR RAPORU",font=(YAZI_TIPI,20,"bold"),
                  bootstyle="inverse-dark",padding=18).pack(fill=X)
        filtre_alani = ttk.Frame(pencere, padding=(20, 12))
        filtre_alani.pack(fill=X)
        ttk.Label(filtre_alani, text="Dönem:").pack(side=LEFT, padx=(0, 8))
        donem = tk.StringVar(value="Bu ay")
        ttk.Combobox(filtre_alani, textvariable=donem,
                     values=("Bugün", "Bu ay", "Tümü"), state="readonly", width=18).pack(side=LEFT)
        tablo=ttk.Treeview(pencere,columns=("tarih","urun","adet","alis","satis","ciro","kar"),show="headings",bootstyle="success")
        for k,b in zip(tablo["columns"],("Tarih","Ürün","Adet","Alış","Satış","Ciro","Brüt kâr")):
            tablo.heading(k,text=b)
        tablo.pack(fill=BOTH,expand=True,padx=20,pady=20)
        toplam = ttk.Label(pencere, font=(YAZI_TIPI,13,"bold"),
                           bootstyle="success", padding=14)
        toplam.pack(fill=X)

        def raporu_yenile(*_):
            for satir in tablo.get_children():
                tablo.delete(satir)
            anahtar = {"Bugün": "BUGUN", "Bu ay": "BU_AY", "Tümü": "TUMU"}[donem.get()]
            toplam_ciro = 0
            toplam_kar = 0
            for x in self.vt.kar_raporu_getir(anahtar):
                toplam_ciro += x["ciro"]
                toplam_kar += x["brut_kar"]
                tablo.insert("", END, values=(x["tarih_saat"], x["urun"], x["miktar"],
                    para_bicimlendir(x["alis_fiyati"]), para_bicimlendir(x["satis_fiyati"]),
                    para_bicimlendir(x["ciro"]), para_bicimlendir(x["brut_kar"])))
            toplam.configure(text=f"Toplam ciro: {para_bicimlendir(toplam_ciro)}  •  Brüt kâr: {para_bicimlendir(toplam_kar)}")

        donem.trace_add("write", raporu_yenile)
        raporu_yenile()
        ttk.Button(
            pencere, text="Raporu Yazdır",
            command=lambda: self.tablo_raporunu_yazdir(
                "Satış ve Brüt Kâr Raporu", tablo, toplam.cget("text")
            ), bootstyle="success", padding=(20, 9)
        ).pack(pady=(0, 14))

    def guvenlik_gecmisi_ac(self):
        pencere=self.uygulama_ici_sayfa_ac("Kullanıcı İşlem ve Oturum Geçmişi"); pencere.title("Kullanıcı İşlem ve Oturum Geçmişi"); pencere.geometry("1100x760")
        ttk.Label(pencere,text="KULLANICI İŞLEM VE OTURUM GEÇMİŞİ",font=(YAZI_TIPI,20,"bold"),bootstyle="inverse-dark",padding=18).pack(fill=X)
        notlar=ttk.Notebook(pencere); notlar.pack(fill=BOTH,expand=True,padx=18,pady=18)
        islem=ttk.Frame(notlar); oturum=ttk.Frame(notlar); notlar.add(islem,text="İşlem Kayıtları"); notlar.add(oturum,text="Oturumlar")
        t1=ttk.Treeview(islem,columns=("tarih","kullanici","islem","aciklama"),show="headings",bootstyle="info")
        for k,b in zip(t1["columns"],("Tarih","Kullanıcı","İşlem","Açıklama")): t1.heading(k,text=b)
        t1.column("tarih",width=170); t1.column("kullanici",width=180); t1.column("islem",width=190); t1.column("aciklama",width=480)
        for x in self.vt.denetim_kayitlari_getir(): t1.insert("",END,values=(x["tarih_saat"],x["kullanici"],x["islem"],x["aciklama"]))
        t1.pack(fill=BOTH,expand=True)
        t2=ttk.Treeview(oturum,columns=("giris","cikis","kullanici"),show="headings",bootstyle="primary")
        for k,b in zip(t2["columns"],("Giriş","Çıkış","Kullanıcı")): t2.heading(k,text=b)
        for x in self.vt.oturum_kayitlari_getir(): t2.insert("",END,values=(x["giris_zamani"],x["cikis_zamani"],x["kullanici"]))
        t2.pack(fill=BOTH,expand=True)

    def excel_stok_aktar(self):
        konum_id=self.konum_haritasi.get(self.konum_degiskeni.get())
        if not konum_id: return
        hedef=filedialog.asksaveasfilename(parent=self.pencere,defaultextension=".xlsx",filetypes=[("Excel çalışma kitabı","*.xlsx")],initialfile="DeporiaQ_Stok_Raporu.xlsx")
        if not hedef: return
        satirlar=[(x["barkod"],x["ad"],x["miktar"],x["fiyat"],x["alis_fiyati"],x["miktar"]*x["fiyat"])
                  for x in self.vt.urunleri_getir("",konum_id)]
        xlsx_yaz(hedef,("Barkod","Ürün","Stok","Satış fiyatı","Alış fiyatı","Stok değeri"),satirlar)
        self.vt.denetim_ekle("EXCEL_AKTARIMI",self.konum_degiskeni.get())
        self.basari_bildirimi("Stok raporu gerçek Excel (.xlsx) dosyası olarak kaydedildi.")

    def excel_stok_ice_aktar(self):
        kaynak=filedialog.askopenfilename(parent=self.pencere,filetypes=[("Excel çalışma kitabı","*.xlsx")])
        if not kaynak: return
        try:
            satirlar=xlsx_oku(kaynak)
            if not satirlar: raise ValueError("Excel dosyası boş.")
            baslik=[str(x).strip().lower() for x in satirlar[0]]
            zorunlu=("barkod","ürün","stok","satış fiyatı")
            if any(x not in baslik for x in zorunlu): raise ValueError("Sütunlar Barkod, Ürün, Stok ve Satış fiyatı olmalıdır.")
            idx={ad:baslik.index(ad) for ad in baslik}
            konum_id=self.konum_haritasi.get(self.konum_degiskeni.get())
            if not konum_id: raise ValueError("Önce stok konumu seçin.")
            if not messagebox.askyesno("Excel İçe Aktarma",f"{len(satirlar)-1} satır seçili konuma aktarılacak. Devam edilsin mi?",parent=self.pencere): return
            geri_alma_noktasi_olustur("excel_ice_aktarma"); adet=0
            with self.vt.baglanti:
                for s in satirlar[1:]:
                    if not s or not str(s[idx["barkod"]]).strip(): continue
                    barkod=str(s[idx["barkod"]]).strip(); ad=str(s[idx["ürün"]]).strip()
                    stok=int(float(s[idx["stok"]] or 0)); fiyat=float(s[idx["satış fiyatı"]] or 0)
                    alis=float(s[idx.get("alış fiyatı",idx["satış fiyatı"])] or 0)
                    self.vt.baglanti.execute("""INSERT INTO urunler(barkod,ad,fiyat,alis_fiyati,aktif) VALUES(?,?,?,?,1)
                        ON CONFLICT(barkod) DO UPDATE SET ad=excluded.ad,fiyat=excluded.fiyat,alis_fiyati=excluded.alis_fiyati""",(barkod,ad,fiyat,alis))
                    uid=self.vt.baglanti.execute("SELECT id FROM urunler WHERE barkod=?",(barkod,)).fetchone()[0]
                    self.vt.baglanti.execute("""INSERT INTO stoklar(urun_id,konum_id,miktar) VALUES(?,?,?)
                        ON CONFLICT(urun_id,konum_id) DO UPDATE SET miktar=excluded.miktar""",(uid,konum_id,max(0,stok)))
                    adet+=1
            self.vt.denetim_ekle("EXCEL_ICE_AKTARIM",f"{adet} ürün")
            self.tabloyu_yenile(); self.basari_bildirimi(f"{adet} ürün Excel'den aktarıldı; geri alma noktası oluşturuldu.")
        except (ValueError,KeyError,IndexError,zipfile.BadZipFile,ET.ParseError) as hata:
            self.olumsuz_bildirimi(f"Excel dosyası okunamadı: {hata}")

    def barkod_etiketi_ac(self):
        urunler=self.vt.tum_aktif_urunleri_getir()
        if not urunler: self.olumsuz_bildirimi("Etiket oluşturmak için ürün ekleyin."); return
        p=self.uygulama_ici_sayfa_ac("Barkod Etiketi"); p.title("Barkod Etiketi"); p.geometry("650x360"); p.transient(self.pencere)
        harita={f"{u['ad']} — {u['barkod']}":u for u in urunler}; sec=tk.StringVar(value=next(iter(harita))); adet=tk.StringVar(value="1")
        f=ttk.Labelframe(p,text=" Yazdırılacak etiket ",padding=24,bootstyle="primary"); f.pack(fill=BOTH,expand=True,padx=24,pady=24); f.columnconfigure(1,weight=1)
        ttk.Label(f,text="Ürün:").grid(row=0,column=0,sticky="w",pady=10); ttk.Combobox(f,textvariable=sec,values=list(harita),state="readonly").grid(row=0,column=1,sticky="ew",pady=10)
        ttk.Label(f,text="Etiket adedi:").grid(row=1,column=0,sticky="w",pady=10); ttk.Entry(f,textvariable=adet).grid(row=1,column=1,sticky="ew",pady=10)
        def olustur():
            try: n=int(adet.get()); assert 1<=n<=200
            except (ValueError,AssertionError): self.olumsuz_bildirimi("Etiket adedi 1–200 arasında olmalıdır.",p); return
            u=harita[sec.get()]; svg=ean13_svg(u["barkod"])
            if not svg: self.olumsuz_bildirimi("Etiket için 13 haneli EAN barkodu gerekir.",p); return
            kart=f'<div class="etiket"><b>{html.escape(u["ad"])}</b>{svg}<span>{para_bicimlendir(u["fiyat"])}</span></div>'
            belge='<!doctype html><meta charset="utf-8"><title>DeporiaQ Etiket</title><style>@page{margin:8mm}.etiket{display:inline-flex;vertical-align:top;flex-direction:column;align-items:center;width:380px;padding:12px;border:1px dashed #aaa;margin:5px;font:18px Arial}.etiket span{font-weight:bold}</style>'+kart*n+'<script>window.onload=()=>window.print()</script>'
            yol=Path(tempfile.gettempdir())/"DeporiaQ_Barkod_Etiketleri.html"; yol.write_text(belge,encoding="utf-8"); webbrowser.open(yol.as_uri()); self.vt.denetim_ekle("BARKOD_ETIKETI",f"{u['ad']} x{n}")
        ttk.Button(f,text="Etiketleri Aç ve Yazdır",command=olustur,bootstyle="success",padding=(18,10)).grid(row=2,column=0,columnspan=2,pady=18)

    def yardim_merkezini_ac(self):
        """SSS ve kayıt numaralı destek taleplerini uygulama içinde sunar."""
        sayfa = self.uygulama_ici_sayfa_ac("Yardım Merkezi")
        ttk.Label(
            sayfa, text="YARDIM MERKEZİ", font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark", padding=18
        ).pack(fill=X)
        ttk.Label(
            sayfa,
            text="Sorunuzun yanıtını bulun veya takip numaralı bir destek talebi oluşturun.",
            bootstyle="secondary", padding=(20, 8)
        ).pack(fill=X)
        sekmeler = ttk.Notebook(sayfa, bootstyle="info")
        sekmeler.pack(fill=BOTH, expand=True, padx=22, pady=(8, 22))
        sss = ttk.Frame(sekmeler, padding=22)
        ticket = ttk.Frame(sekmeler, padding=22)
        canli = ttk.Frame(sekmeler, padding=22)
        sekmeler.add(sss, text="Sıkça Sorulanlar")
        sekmeler.add(ticket, text="Ticket At")
        sekmeler.add(canli, text="Canlı Destek Talebi")

        sorular = (
            ("Verilerim güncellemede silinir mi?", "Hayır. Normal sürüm güncellemesi ürün, stok, şube, depo ve kullanıcı verilerinizi korur."),
            ("Yedekler nerede tutulur?", "Veri ve Yedekleme ekranından yedek klasörünü açabilir, anlık yedek oluşturabilirsiniz."),
            ("Parolamı unuttum, ne yapmalıyım?", "Personel kullanıcıları ana yöneticiye; ana yönetici ise DeporiaQ yazılım sağlayıcısına başvurmalıdır."),
            ("Kritik stok ne anlama gelir?", "Mevcut miktarı ürünün belirlenen kritik seviyesine eşit veya daha düşük olan stoktur."),
            ("Raporu nasıl yazdırırım?", "Rapor ekranındaki Raporu Yazdır düğmesine basın ve açılan sistem yazdırma ekranından yazıcınızı seçin."),
            ("Birden fazla bilgisayar aynı veriyi kullanabilir mi?", "DeporiaQ Cloud bağlantısı etkinleştirildiğinde yetkili cihazlar aynı işletme verisine güvenli biçimde bağlanabilir."),
        )
        tuval = tk.Canvas(sss, bg=RENK_ZEMIN, highlightthickness=0)
        kaydir = ttk.Scrollbar(sss, orient="vertical", command=tuval.yview)
        govde = ttk.Frame(tuval, padding=4)
        govde.bind("<Configure>", lambda _e: tuval.configure(scrollregion=tuval.bbox("all")))
        tuval.create_window((0, 0), window=govde, anchor="nw")
        tuval.configure(yscrollcommand=kaydir.set)
        tuval.pack(side=LEFT, fill=BOTH, expand=True); kaydir.pack(side=RIGHT, fill=Y)
        for soru, cevap in sorular:
            kart = ttk.Labelframe(govde, text=f" {soru} ", padding=14, bootstyle="primary")
            kart.pack(fill=X, pady=7)
            ttk.Label(kart, text=cevap, wraplength=950, justify="left").pack(fill=X)

        def talep_formu(ebeveyn, tur, canli_mi=False):
            ebeveyn.columnconfigure(1, weight=1)
            konu = tk.StringVar(); iletisim = tk.StringVar()
            ttk.Label(ebeveyn, text="Konu:").grid(row=0, column=0, sticky="nw", padx=(0, 14), pady=10)
            ttk.Entry(ebeveyn, textvariable=konu).grid(row=0, column=1, sticky="ew", pady=10)
            ttk.Label(ebeveyn, text="Telefon / e-posta:").grid(row=1, column=0, sticky="nw", padx=(0, 14), pady=10)
            ttk.Entry(ebeveyn, textvariable=iletisim).grid(row=1, column=1, sticky="ew", pady=10)
            ttk.Label(ebeveyn, text="Mesajınız:").grid(row=2, column=0, sticky="nw", padx=(0, 14), pady=10)
            mesaj = tk.Text(
                ebeveyn, height=12, wrap="word", bg=RENK_PANEL, fg=RENK_METIN,
                insertbackground=RENK_METIN, relief="flat", font=(YAZI_TIPI, 11), padx=12, pady=10
            )
            mesaj.grid(row=2, column=1, sticky="nsew", pady=10); ebeveyn.rowconfigure(2, weight=1)
            bilgi = (
                "Canlı temsilci uygun olduğunda verdiğiniz iletişim bilgisi üzerinden dönüş yapılır. "
                "Bu sürüm talebi kayıt altına alır; çevrimiçi destek bağlantısı etkinleştirildiğinde otomatik gönderilecektir."
                if canli_mi else
                "Talebiniz yerel olarak kayıt altına alınır ve size bir takip numarası verilir."
            )
            ttk.Label(ebeveyn, text=bilgi, wraplength=850, bootstyle="secondary").grid(row=3,column=1,sticky="w",pady=(4,12))
            def kaydet():
                try:
                    takip = self.vt.destek_talebi_olustur(tur, konu.get(), mesaj.get("1.0", "end"), iletisim.get())
                    self.vt.denetim_ekle("DESTEK_TALEBI", f"{tur} • {takip}")
                    self.pencere.clipboard_clear(); self.pencere.clipboard_append(takip)
                    konu.set(""); iletisim.set(""); mesaj.delete("1.0", "end")
                    self.basari_bildirimi(f"Talep kaydedildi. Takip numarası: {takip} (panoya kopyalandı)", sayfa)
                except ValueError as hata:
                    self.olumsuz_bildirimi(str(hata), sayfa)
            ttk.Button(ebeveyn, text="Talebi Kaydet", command=kaydet, bootstyle="success", padding=(22,10)).grid(row=4,column=1,sticky="e")
        talep_formu(ticket, "TICKET")
        talep_formu(canli, "CANLI_DESTEK", True)
        self.pencere.after(100, lambda: self.arayuzu_cevir(sayfa))

    def operasyon_merkezi_ac(self):
        """Satın alma ve stok doğruluğu işlemlerini tek uygulama içi ekranda toplar."""
        sayfa = self.uygulama_ici_sayfa_ac("Operasyon Merkezi")
        ttk.Label(
            sayfa, text="OPERASYON MERKEZİ", font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark", padding=18
        ).pack(fill=X)
        ttk.Label(
            sayfa,
            text="Kategoriler, tedarikçiler, mal kabul ve fiziksel stok sayımı",
            bootstyle="secondary", padding=(20, 8)
        ).pack(fill=X)
        sekmeler = ttk.Notebook(sayfa, bootstyle="primary")
        sekmeler.pack(fill=BOTH, expand=True, padx=20, pady=(8, 20))

        kategori = ttk.Frame(sekmeler, padding=20)
        tedarikci = ttk.Frame(sekmeler, padding=20)
        mal_kabul = ttk.Frame(sekmeler, padding=20)
        sayim = ttk.Frame(sekmeler, padding=20)
        kritik = ttk.Frame(sekmeler, padding=20)
        for alan, baslik in (
            (kategori, "Kategoriler"), (tedarikci, "Tedarikçiler"),
            (mal_kabul, "Mal Kabul"), (sayim, "Stok Sayımı"),
            (kritik, "Kritik Stok")
        ):
            sekmeler.add(alan, text=baslik)

        # Kategori yönetimi
        kategori.columnconfigure(0, weight=1); kategori.rowconfigure(2, weight=1)
        kategori_adi = tk.StringVar()
        kat_form = ttk.Frame(kategori); kat_form.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        kat_form.columnconfigure(1, weight=1)
        ttk.Label(kat_form, text="Yeni kategori:").grid(row=0, column=0, padx=(0, 10))
        ttk.Entry(kat_form, textvariable=kategori_adi).grid(row=0, column=1, sticky="ew")
        kategori_tablosu = ttk.Treeview(kategori, columns=("ad",), show="headings", height=8)
        kategori_tablosu.heading("ad", text="Kategori adı"); kategori_tablosu.column("ad", anchor="w")
        kategori_tablosu.grid(row=2, column=0, sticky="nsew", pady=12)
        atama = ttk.Labelframe(kategori, text=" Ürüne kategori ata ", padding=14)
        atama.grid(row=3, column=0, sticky="ew"); atama.columnconfigure(1, weight=1); atama.columnconfigure(3, weight=1)
        urun_kategori = tk.StringVar(); kategori_secimi = tk.StringVar()
        ttk.Label(atama, text="Ürün:").grid(row=0, column=0, padx=(0, 8))
        urun_kategori_kutusu = ttk.Combobox(atama, textvariable=urun_kategori, state="readonly")
        urun_kategori_kutusu.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        ttk.Label(atama, text="Kategori:").grid(row=0, column=2, padx=(0, 8))
        kategori_kutusu = ttk.Combobox(atama, textvariable=kategori_secimi, state="readonly")
        kategori_kutusu.grid(row=0, column=3, sticky="ew", padx=(0, 14))

        haritalar = {"urun": {}, "kategori": {}, "tedarikci": {}, "konum": {}}
        def ortak_listeleri_yenile():
            urunler = self.vt.tum_aktif_urunleri_getir()
            haritalar["urun"] = {f"{u['ad']} — {u['barkod']}": u["id"] for u in urunler}
            kategoriler = self.vt.kategorileri_getir()
            haritalar["kategori"] = {x["ad"]: x["id"] for x in kategoriler}
            tedarikciler = self.vt.tedarikcileri_getir()
            haritalar["tedarikci"] = {x["unvan"]: x["id"] for x in tedarikciler}
            konumlar = self.vt.konumlari_getir()
            haritalar["konum"] = {x["ad"]: x["id"] for x in konumlar}
            urun_degerleri = list(haritalar["urun"]); kategori_degerleri = list(haritalar["kategori"])
            urun_kategori_kutusu["values"] = urun_degerleri; kategori_kutusu["values"] = kategori_degerleri
            for kutu in (mal_urun_kutusu, sayim_urun_kutusu): kutu["values"] = urun_degerleri
            mal_tedarikci_kutusu["values"] = list(haritalar["tedarikci"])
            for kutu in (mal_konum_kutusu, sayim_konum_kutusu): kutu["values"] = list(haritalar["konum"])
            for tablo in (kategori_tablosu, tedarikci_tablosu):
                for satir in tablo.get_children(): tablo.delete(satir)
            for x in kategoriler: kategori_tablosu.insert("", END, values=(x["ad"],))
            for x in tedarikciler: tedarikci_tablosu.insert("", END, values=(x["unvan"], x["telefon"], x["eposta"]))
            for degisken, degerler in ((urun_kategori,urun_degerleri),(kategori_secimi,kategori_degerleri),
                                      (mal_urun,urun_degerleri),(sayim_urun,urun_degerleri),
                                      (mal_tedarikci,list(haritalar["tedarikci"])),
                                      (mal_konum,list(haritalar["konum"])),(sayim_konum,list(haritalar["konum"]))):
                if not degisken.get() and degerler: degisken.set(degerler[0])

        def kategori_ekle():
            try:
                self.vt.kategori_ekle(kategori_adi.get()); kategori_adi.set("")
                ortak_listeleri_yenile(); self.basari_bildirimi("Kategori eklendi.", sayfa)
            except ValueError as hata: self.olumsuz_bildirimi(str(hata), sayfa)
        ttk.Button(kat_form, text="Kategori Ekle", command=kategori_ekle, bootstyle="success").grid(row=0,column=2,padx=(10,0))
        def kategori_ata():
            if urun_kategori.get() not in haritalar["urun"] or kategori_secimi.get() not in haritalar["kategori"]:
                self.olumsuz_bildirimi("Ürün ve kategori seçin.", sayfa); return
            self.vt.urun_kategori_guncelle(haritalar["urun"][urun_kategori.get()], haritalar["kategori"][kategori_secimi.get()])
            self.vt.denetim_ekle("URUN_KATEGORI", f"{urun_kategori.get()} → {kategori_secimi.get()}")
            self.basari_bildirimi("Ürünün kategorisi güncellendi.", sayfa)
        ttk.Button(atama, text="Kategoriyi Ata", command=kategori_ata, bootstyle="primary").grid(row=0,column=4)

        # Tedarikçi yönetimi
        tedarikci.columnconfigure(0, weight=1); tedarikci.rowconfigure(1, weight=1)
        tf = ttk.Labelframe(tedarikci, text=" Yeni tedarikçi ", padding=14); tf.grid(row=0,column=0,sticky="ew")
        tf.columnconfigure(1,weight=1); tf.columnconfigure(3,weight=1); tf.columnconfigure(5,weight=1)
        ted_unvan=tk.StringVar(); ted_tel=tk.StringVar(); ted_eposta=tk.StringVar()
        for sutun,(etiket,degisken) in enumerate((("Unvan:",ted_unvan),("Telefon:",ted_tel),("E-posta:",ted_eposta))):
            ttk.Label(tf,text=etiket).grid(row=0,column=sutun*2,sticky="w",padx=(0,6))
            ttk.Entry(tf,textvariable=degisken).grid(row=0,column=sutun*2+1,sticky="ew",padx=(0,12))
        tedarikci_tablosu=ttk.Treeview(tedarikci,columns=("unvan","telefon","eposta"),show="headings")
        for k,b in (("unvan","Tedarikçi unvanı"),("telefon","Telefon"),("eposta","E-posta")): tedarikci_tablosu.heading(k,text=b)
        tedarikci_tablosu.grid(row=1,column=0,sticky="nsew",pady=14)
        def tedarikci_ekle():
            try:
                self.vt.tedarikci_ekle(ted_unvan.get(),ted_tel.get(),ted_eposta.get())
                ted_unvan.set(""); ted_tel.set(""); ted_eposta.set(""); ortak_listeleri_yenile()
                self.basari_bildirimi("Tedarikçi eklendi.",sayfa)
            except ValueError as hata: self.olumsuz_bildirimi(str(hata),sayfa)
        ttk.Button(tf,text="Tedarikçi Ekle",command=tedarikci_ekle,bootstyle="success").grid(row=1,column=0,columnspan=6,pady=(14,0))

        # Mal kabul
        mal_kabul.columnconfigure(1,weight=1); mal_urun=tk.StringVar(); mal_tedarikci=tk.StringVar(); mal_konum=tk.StringVar()
        mal_miktar=tk.StringVar(); mal_maliyet=tk.StringVar(); mal_belge=tk.StringVar()
        mal_urun_kutusu=ttk.Combobox(mal_kabul,textvariable=mal_urun,state="readonly")
        mal_tedarikci_kutusu=ttk.Combobox(mal_kabul,textvariable=mal_tedarikci,state="readonly")
        mal_konum_kutusu=ttk.Combobox(mal_kabul,textvariable=mal_konum,state="readonly")
        mal_alanlari=(("Ürün:",mal_urun_kutusu),("Tedarikçi:",mal_tedarikci_kutusu),("Teslim alan konum:",mal_konum_kutusu),
                     ("Miktar:",ttk.Entry(mal_kabul,textvariable=mal_miktar)),("Birim alış maliyeti:",ttk.Entry(mal_kabul,textvariable=mal_maliyet)),
                     ("Fatura / irsaliye no:",ttk.Entry(mal_kabul,textvariable=mal_belge)))
        for satir,(etiket,arac) in enumerate(mal_alanlari):
            ttk.Label(mal_kabul,text=etiket).grid(row=satir,column=0,sticky="w",padx=(10,18),pady=10); arac.grid(row=satir,column=1,sticky="ew",pady=10)
        def mal_kabul_et():
            try:
                if not all((mal_urun.get() in haritalar["urun"],mal_tedarikci.get() in haritalar["tedarikci"],mal_konum.get() in haritalar["konum"])): raise ValueError("Ürün, tedarikçi ve konum seçin.")
                miktar=int(mal_miktar.get()); maliyet=float(mal_maliyet.get().replace(",","."))
                self.vt.mal_kabul_yap(haritalar["urun"][mal_urun.get()],haritalar["konum"][mal_konum.get()],haritalar["tedarikci"][mal_tedarikci.get()],miktar,maliyet,mal_belge.get())
                self.vt.denetim_ekle("MAL_KABUL",f"{mal_urun.get()} • {miktar} adet • {mal_konum.get()}")
                mal_miktar.set(""); mal_maliyet.set(""); mal_belge.set(""); self.tabloyu_yenile(); kritik_yenile()
                self.basari_bildirimi("Mal kabul tamamlandı ve stok güncellendi.",sayfa)
            except (ValueError,KeyError) as hata: self.olumsuz_bildirimi(str(hata) or "Bilgileri kontrol edin.",sayfa)
        ttk.Button(mal_kabul,text="Mal Kabulü Tamamla",command=mal_kabul_et,bootstyle="success",padding=(22,12)).grid(row=6,column=0,columnspan=2,pady=18)

        # Fiziksel stok sayımı
        sayim.columnconfigure(1,weight=1); sayim_urun=tk.StringVar(); sayim_konum=tk.StringVar(); sayim_miktar=tk.StringVar(); sayim_aciklama=tk.StringVar()
        sayim_urun_kutusu=ttk.Combobox(sayim,textvariable=sayim_urun,state="readonly"); sayim_konum_kutusu=ttk.Combobox(sayim,textvariable=sayim_konum,state="readonly")
        for satir,(etiket,arac) in enumerate((("Ürün:",sayim_urun_kutusu),("Konum:",sayim_konum_kutusu),("Fiziksel sayım miktarı:",ttk.Entry(sayim,textvariable=sayim_miktar)),("Açıklama:",ttk.Entry(sayim,textvariable=sayim_aciklama)))):
            ttk.Label(sayim,text=etiket).grid(row=satir,column=0,sticky="w",padx=(10,18),pady=12); arac.grid(row=satir,column=1,sticky="ew",pady=12)
        def sayimi_kaydet():
            try:
                if sayim_urun.get() not in haritalar["urun"] or sayim_konum.get() not in haritalar["konum"]: raise ValueError("Ürün ve konum seçin.")
                yeni=int(sayim_miktar.get()); eski,fark=self.vt.stok_sayim_duzelt(haritalar["urun"][sayim_urun.get()],haritalar["konum"][sayim_konum.get()],yeni,sayim_aciklama.get())
                self.vt.denetim_ekle("STOK_SAYIMI",f"{sayim_urun.get()} • {eski} → {yeni}")
                sayim_miktar.set(""); sayim_aciklama.set(""); self.tabloyu_yenile(); kritik_yenile()
                self.basari_bildirimi(f"Sayım kaydedildi. Stok farkı: {fark:+d}",sayfa)
            except (ValueError,KeyError) as hata: self.olumsuz_bildirimi(str(hata) or "Bilgileri kontrol edin.",sayfa)
        ttk.Button(sayim,text="Sayım Sonucunu Uygula",command=sayimi_kaydet,bootstyle="warning",padding=(22,12)).grid(row=4,column=0,columnspan=2,pady=20)

        # Kritik stok paneli
        kritik.columnconfigure(0,weight=1); kritik.rowconfigure(1,weight=1)
        kritik_ozet=ttk.Label(kritik,font=(YAZI_TIPI,13,"bold"),bootstyle="danger",padding=10); kritik_ozet.grid(row=0,column=0,sticky="ew")
        kritik_tablosu=ttk.Treeview(kritik,columns=("konum","barkod","urun","mevcut","kritik"),show="headings",bootstyle="danger")
        for k,b in zip(kritik_tablosu["columns"],("Konum","Barkod","Ürün","Mevcut stok","Kritik seviye")): kritik_tablosu.heading(k,text=b)
        kritik_tablosu.grid(row=1,column=0,sticky="nsew",pady=12)
        def kritik_yenile():
            for satir in kritik_tablosu.get_children(): kritik_tablosu.delete(satir)
            kayitlar=self.vt.kritik_stoklari_getir()
            for x in kayitlar: kritik_tablosu.insert("",END,values=(x["konum"],x["barkod"],x["urun"],x["miktar"],x["kritik_stok"]))
            kritik_ozet.configure(text=f"Sipariş veya sayım gerektiren {len(kayitlar)} stok kaydı bulunuyor.")
            if hasattr(self,"kritik_stok_dugmesi"): self.kritik_stok_dugmesi.configure(text=f"Kritik Stoklar ({len(kayitlar)})")
        ttk.Button(kritik,text="Listeyi Yenile",command=kritik_yenile,bootstyle="danger-outline").grid(row=2,column=0,pady=6)

        ortak_listeleri_yenile(); kritik_yenile()

    def profesyonel_araclar_ac(self):
        p=self.uygulama_ici_sayfa_ac("Profesyonel Araçlar"); p.title("DeporiaQ Profesyonel Araçlar"); p.geometry("760x520"); p.transient(self.pencere)
        ttk.Label(p,text="PROFESYONEL ARAÇLAR",font=(YAZI_TIPI,20,"bold"),bootstyle="inverse-dark",padding=18).pack(fill=X)
        f=ttk.Frame(p,padding=28); f.pack(fill=BOTH,expand=True)
        araclar=(("Kritik Stoklar",self.kritik_stok_raporu_ac,"danger"),("Satış ve Kâr Raporu",self.kar_raporu_ac,"success"),("Excel'e Stok Aktar",self.excel_stok_aktar,"info"),("Excel'den Stok Al",self.excel_stok_ice_aktar,"info-outline"),("Barkod Etiketi",self.barkod_etiketi_ac,"warning"),("Kullanıcı ve Oturum Geçmişi",self.guvenlik_gecmisi_ac,"primary"),("Geri Alma Noktası Oluştur",lambda:self.basari_bildirimi(f"Geri alma noktası oluşturuldu: {geri_alma_noktasi_olustur('manuel').name}",p),"warning-outline"),("Veritabanı Sağlık Kontrolü",lambda:self.basari_bildirimi("Veritabanı bütünlüğü doğrulandı.",p) if self.vt.butunluk_kontrolu() else self.olumsuz_bildirimi("Veritabanı bütünlük sorunu tespit edildi.",p),"secondary"))
        for i,(metin,komut,stil) in enumerate(araclar):
            ttk.Button(f,text=metin,command=komut,bootstyle=stil,padding=(20,16)).grid(row=i//2,column=i%2,sticky="ew",padx=10,pady=10)
        f.columnconfigure(0,weight=1); f.columnconfigure(1,weight=1)

    def transfer_penceresini_ac(self):
        depolar = self.vt.konumlari_getir("DEPO")

        if not depolar:
            self.olumsuz_bildirimi(
                "Transferden önce Depo / Şube Ekle ekranından en az bir depo ekleyin."
            )
            return

        pencere = self.uygulama_ici_sayfa_ac("Merkez Depodan Stok Transferi")
        pencere.title("Merkez Depodan Stok Transferi")
        pencere.geometry("760x510")
        pencere.transient(self.pencere)

        ttk.Label(
            pencere,
            text="MERKEZ DEPODAN STOK TRANSFERİ",
            font=(YAZI_TIPI, 19, "bold"),
            bootstyle="inverse-dark",
            padding=18
        ).pack(fill=X)

        form = ttk.Labelframe(
            pencere,
            text=" Barkodlu transfer ",
            padding=22,
            bootstyle="success"
        )
        form.pack(fill=BOTH, expand=True, padx=24, pady=22)
        form.columnconfigure(1, weight=1)

        depo_haritasi = {depo["ad"]: depo["id"] for depo in depolar}
        depo_degiskeni = tk.StringVar(value=depolar[0]["ad"])
        barkod_degiskeni = tk.StringVar()
        miktar_degiskeni = tk.StringVar()
        urun_bilgisi = tk.StringVar(value="Barkod okutulduğunda ürün burada görünecek")
        secili = {"urun": None}

        ttk.Label(form, text="Kaynak:").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Label(
            form,
            text="Merkez Depo",
            font=(YAZI_TIPI, 11, "bold"),
            bootstyle="info"
        ).grid(row=0, column=1, sticky="w", pady=8)

        ttk.Label(form, text="Hedef depo:").grid(row=1, column=0, sticky="w", pady=8)
        depo_kutusu = ttk.Combobox(
            form,
            textvariable=depo_degiskeni,
            values=list(depo_haritasi),
            state="normal"
        )
        depo_kutusu.grid(row=1, column=1, sticky="ew", pady=8)
        self.aramali_secim_hazirla(
            depo_kutusu, depo_degiskeni, lambda: list(depo_haritasi)
        )

        ttk.Label(form, text="Barkod:").grid(row=2, column=0, sticky="w", pady=8)
        barkod_kutusu = ttk.Entry(form, textvariable=barkod_degiskeni, font=("Consolas", 13))
        barkod_kutusu.grid(row=2, column=1, sticky="ew", pady=8)

        ttk.Label(form, text="Miktar:").grid(row=3, column=0, sticky="w", pady=8)
        miktar_kutusu = ttk.Entry(form, textvariable=miktar_degiskeni)
        miktar_kutusu.grid(row=3, column=1, sticky="ew", pady=8)

        ttk.Label(
            form,
            textvariable=urun_bilgisi,
            font=(YAZI_TIPI, 11, "bold"),
            bootstyle="info"
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(15, 12))

        def barkodu_bul(_olay=None):
            urun = self.vt.barkodla_urun_bul(barkod_degiskeni.get().strip())
            if urun is None:
                secili["urun"] = None
                self.olumsuz_bildirimi("Bu barkoda ait ürün bulunamadı.", pencere)
                return
            secili["urun"] = urun
            urun_bilgisi.set(
                f"{urun['ad']}  •  Merkez stok: {urun['miktar']:,}".replace(",", ".")
            )
            miktar_kutusu.focus_set()

        def transferi_yap(_olay=None):
            if secili["urun"] is None:
                barkodu_bul()
                if secili["urun"] is None:
                    return

            try:
                miktar = int(miktar_degiskeni.get().strip())
                if miktar <= 0:
                    raise ValueError("Transfer miktarı en az 1 olmalıdır.")
                hedef_adi = self.vt.merkezden_depoya_transfer(
                    secili["urun"]["id"],
                    depo_haritasi[depo_degiskeni.get()],
                    miktar
                )
                self.vt.denetim_ekle("STOK_TRANSFERI",f"Merkez Depo → {hedef_adi} • {secili['urun']['ad']} • {miktar} adet")
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return

            self.basari_bildirimi(
                (
                    f"{secili['urun']['ad']}: Merkez Depo → {hedef_adi}, "
                    f"{miktar:,} adet"
                ).replace(",", "."),
                pencere
            )
            self.tabloyu_yenile()
            barkod_degiskeni.set("")
            miktar_degiskeni.set("")
            secili["urun"] = None
            urun_bilgisi.set("Yeni transfer için barkod okutun")
            barkod_kutusu.focus_set()

        barkod_kutusu.bind("<Return>", barkodu_bul)
        miktar_kutusu.bind("<Return>", transferi_yap)
        ttk.Button(
            form,
            text="Transferi Tamamla",
            command=transferi_yap,
            bootstyle="success",
            padding=(20, 10)
        ).grid(row=5, column=0, columnspan=2, pady=14)
        barkod_kutusu.focus_set()

    def hareket_gecmisini_goster(self):
        pencere = self.uygulama_ici_sayfa_ac("Stok Hareket Geçmişi")
        pencere.title("Stok Hareket Geçmişi")
        pencere.geometry("1050x600")

        ttk.Label(
            pencere,
            text="STOK HAREKET GEÇMİŞİ",
            font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark",
            padding=18
        ).pack(fill=X)

        alan = ttk.Frame(pencere, padding=20)
        alan.pack(fill=BOTH, expand=True)
        tablo = ttk.Treeview(
            alan,
            columns=("tarih", "barkod", "urun", "miktar", "tur", "kaynak", "hedef"),
            show="headings",
            bootstyle="info"
        )
        basliklar = ("Tarih", "Barkod", "Ürün", "Miktar", "Hareket", "Kaynak", "Hedef")
        for sutun, baslik in zip(tablo["columns"], basliklar):
            tablo.heading(sutun, text=baslik)
        tablo.column("tarih", width=160)
        tablo.column("barkod", width=150)
        tablo.column("urun", width=230)
        tablo.column("miktar", width=90, anchor=CENTER)
        tablo.column("tur", width=130, anchor=CENTER)
        tablo.column("kaynak", width=170)
        tablo.column("hedef", width=170)

        kaydirma = ttk.Scrollbar(alan, command=tablo.yview)
        tablo.configure(yscrollcommand=kaydirma.set)
        tablo.pack(side=LEFT, fill=BOTH, expand=True)
        kaydirma.pack(side=RIGHT, fill=Y)

        for hareket in self.vt.hareketleri_getir():
            tablo.insert(
                "",
                END,
                values=(
                    hareket["tarih_saat"],
                    hareket["barkod"],
                    hareket["ad"],
                    hareket["miktar"],
                    hareket["hareket_turu"],
                    hareket["kaynak"] or "Dış giriş",
                    hareket["hedef"]
                )
            )
        ttk.Button(
            pencere, text="Raporu Yazdır",
            command=lambda: self.tablo_raporunu_yazdir("Stok Hareket Geçmişi", tablo),
            bootstyle="info", padding=(20, 9)
        ).pack(pady=(0, 14))

    def anlik_yedek_olustur(self, on_ek="manuel"):
        """Açık SQLite bağlantısını tutarlı bir yedek dosyasına kopyalar."""
        YEDEK_KLASORU.mkdir(parents=True, exist_ok=True)
        zaman = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        hedef = YEDEK_KLASORU / f"{on_ek}_{zaman}.db"
        self.vt.baglanti.commit()
        hedef_baglanti = sqlite3.connect(hedef)
        try:
            self.vt.baglanti.backup(hedef_baglanti)
        finally:
            hedef_baglanti.close()
        return hedef

    def veri_klasorunu_ac(self):
        VERI_KLASORU.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(VERI_KLASORU)
        except AttributeError:
            webbrowser.open(VERI_KLASORU.as_uri())

    def veri_yonetimini_ac(self):
        if not self.yetki_kontrol("YONETIM"):
            return
        """Etkin veritabanını, özetini ve geri yüklenebilir yedekleri gösterir."""
        pencere = self.uygulama_ici_sayfa_ac("Veri ve Yedekleme Merkezi")
        pencere.title(f"Veri ve Yedekleme - {PROGRAM_ADI} {PROGRAM_SURUMU}")
        pencere.geometry("980x700")
        pencere.minsize(850, 600)
        pencere.transient(self.pencere)

        ttk.Label(
            pencere,
            text="VERİ VE YEDEKLEME MERKEZİ",
            font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark",
            padding=18
        ).pack(fill=X)

        bilgi = veritabani_doluluk_bilgisi(VERITABANI_YOLU)
        bilgi_alani = ttk.Labelframe(
            pencere, text=" Kullanılan ana veritabanı ", padding=16, bootstyle="info"
        )
        bilgi_alani.pack(fill=X, padx=20, pady=(16, 10))
        ttk.Label(
            bilgi_alani,
            text=str(VERITABANI_YOLU),
            font=("Consolas", 10, "bold"),
            bootstyle="info",
            wraplength=900
        ).pack(anchor="w")
        ozet_degiskeni = tk.StringVar()
        ttk.Label(
            bilgi_alani,
            textvariable=ozet_degiskeni,
            font=(YAZI_TIPI, 11, "bold"),
            padding=(0, 10, 0, 0)
        ).pack(anchor="w")

        liste_alani = ttk.Labelframe(
            pencere, text=" Kullanılabilir yedekler ", padding=12, bootstyle="primary"
        )
        liste_alani.pack(fill=BOTH, expand=True, padx=20, pady=10)
        tablo = ttk.Treeview(
            liste_alani,
            columns=("dosya", "tarih", "boyut", "konum", "stok", "hareket"),
            show="headings",
            bootstyle="primary"
        )
        basliklar = (
            ("dosya", "Yedek dosyası", 300, "w"),
            ("tarih", "Tarih", 145, CENTER),
            ("boyut", "Boyut", 90, "e"),
            ("konum", "Konum", 80, CENTER),
            ("stok", "Stok", 100, "e"),
            ("hareket", "Hareket", 90, "e"),
        )
        for sutun, baslik, genislik, hizalama in basliklar:
            tablo.heading(sutun, text=baslik)
            tablo.column(sutun, width=genislik, anchor=hizalama)
        kaydirma = ttk.Scrollbar(liste_alani, command=tablo.yview)
        tablo.configure(yscrollcommand=kaydirma.set)
        tablo.pack(side=LEFT, fill=BOTH, expand=True)
        kaydirma.pack(side=RIGHT, fill=Y)
        yedek_haritasi = {}

        def ana_ozeti_yenile():
            ana_bilgi = veritabani_doluluk_bilgisi(VERITABANI_YOLU)
            ozet_degiskeni.set(
                "Ürün: " + f"{ana_bilgi[3]:,}".replace(",", ".")
                + "   •   Konum: " + f"{ana_bilgi[0]:,}".replace(",", ".")
                + "   •   Toplam stok: " + f"{ana_bilgi[2]:,}".replace(",", ".")
                + "   •   Hareket: " + f"{ana_bilgi[1]:,}".replace(",", ".")
            )

        def yedekleri_yenile():
            yedek_haritasi.clear()
            for satir in tablo.get_children():
                tablo.delete(satir)
            YEDEK_KLASORU.mkdir(parents=True, exist_ok=True)
            for sira, yol in enumerate(
                sorted(YEDEK_KLASORU.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True)
            ):
                yedek_bilgisi = veritabani_doluluk_bilgisi(yol)
                if yedek_bilgisi == (0, 0, 0, 0):
                    continue
                iid = str(sira)
                yedek_haritasi[iid] = yol
                tarih = datetime.fromtimestamp(yol.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
                tablo.insert(
                    "", END, iid=iid,
                    values=(
                        yol.name,
                        tarih,
                        f"{yol.stat().st_size / 1024:.0f} KB",
                        yedek_bilgisi[0],
                        f"{yedek_bilgisi[2]:,}".replace(",", "."),
                        f"{yedek_bilgisi[1]:,}".replace(",", "."),
                    )
                )

        def simdi_yedekle():
            try:
                hedef = self.anlik_yedek_olustur("manuel")
            except (OSError, sqlite3.Error) as hata:
                self.olumsuz_bildirimi(f"Yedek alınamadı: {hata}", pencere)
                return
            yedekleri_yenile()
            self.basari_bildirimi(f"Yedek oluşturuldu: {hedef.name}", pencere)

        def yedegi_geri_yukle():
            secim = tablo.selection()
            if not secim:
                self.olumsuz_bildirimi("Önce listeden bir yedek seçin.", pencere)
                return
            kaynak = yedek_haritasi[secim[0]]
            kaynak_bilgi = veritabani_doluluk_bilgisi(kaynak)
            if kaynak_bilgi[3] == 0 or kaynak_bilgi[0] == 0:
                self.olumsuz_bildirimi("Seçilen dosya geçerli bir DeporiaQ yedeği değil.", pencere)
                return
            if not self.modern_onay(
                "Yedeği geri yükle",
                (
                    f"{kaynak.name} geri yüklenecek.\n\n"
                    "Mevcut veritabanı önce acil durum yedeğine alınacaktır. "
                    "Devam edilsin mi?"
                ),
                pencere, "Geri Yükle"
            ):
                return

            acil_yedek = None
            gecici = VERITABANI_YOLU.with_name("deporiaq_geri_yukleme_gecici.db")
            try:
                acil_yedek = self.anlik_yedek_olustur("geri_yukleme_oncesi")
                if gecici.exists():
                    gecici.unlink()
                kaynak_baglanti = sqlite3.connect(f"file:{kaynak}?mode=ro", uri=True)
                gecici_baglanti = sqlite3.connect(gecici)
                try:
                    kaynak_baglanti.backup(gecici_baglanti)
                finally:
                    gecici_baglanti.close()
                    kaynak_baglanti.close()

                self.vt.kapat()
                os.replace(gecici, VERITABANI_YOLU)
                self.vt = Veritabani(VERITABANI_YOLU)
                self.secili_urun = None
                self.konum_seciciyi_yenile()
                self.tabloyu_yenile()
                ana_ozeti_yenile()
                yedekleri_yenile()
                self.basari_bildirimi("Yedek başarıyla geri yüklendi.", pencere)
            except Exception as hata:
                try:
                    if gecici.exists():
                        gecici.unlink()
                    if acil_yedek and acil_yedek.exists():
                        shutil.copy2(acil_yedek, VERITABANI_YOLU)
                    self.vt = Veritabani(VERITABANI_YOLU)
                    self.konum_seciciyi_yenile()
                    self.tabloyu_yenile()
                except Exception:
                    pass
                self.olumsuz_bildirimi(f"Geri yükleme tamamlanamadı: {hata}", pencere)

        butonlar = ttk.Frame(pencere, padding=(20, 4, 20, 18))
        butonlar.pack(fill=X)
        ttk.Button(
            butonlar, text="Şimdi Yedekle", command=simdi_yedekle,
            bootstyle="success", padding=(18, 9)
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Button(
            butonlar, text="Seçili Yedeği Geri Yükle", command=yedegi_geri_yukle,
            bootstyle="warning", padding=(18, 9)
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Button(
            butonlar, text="Veri Klasörünü Aç", command=self.veri_klasorunu_ac,
            bootstyle="info-outline", padding=(18, 9)
        ).pack(side=LEFT)
        ttk.Button(
            butonlar, text="Kapat", command=pencere.destroy,
            bootstyle="secondary-outline", padding=(18, 9)
        ).pack(side=RIGHT)

        ana_ozeti_yenile()
        yedekleri_yenile()

    def ust_bilgi_metni(self):
        return (
            f"{self.isletme_adi}  •  "
            f"{self.aktif_kullanici['kullanici_adi']} "
            f"({ROL_ADLARI.get(self.aktif_kullanici['rol'], self.aktif_kullanici['rol'])})"
        )

    def kullanici_yonetimini_ac(self):
        if not self.yetki_kontrol("YONETIM"):
            return

        pencere = self.uygulama_ici_sayfa_ac("Kullanıcı ve Yetki Yönetimi")
        pencere.title("Kullanıcı ve Yetki Yönetimi")
        pencere.geometry("1050x760")
        pencere.transient(self.pencere)
        ttk.Label(
            pencere, text="KULLANICI VE YETKİ YÖNETİMİ",
            font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark", padding=18
        ).pack(fill=X)
        ttk.Label(
            pencere,
            text=("Yerel hesaplar bu bilgisayarda oturum açar. Cloud üyeleri işletmenin "
                  "çevrimiçi erişim listesidir; güvenlik nedeniyle otomatik yerel parola oluşturulmaz."),
            foreground=RENK_METIN, wraplength=1200, justify="left", padding=(22, 10)
        ).pack(fill=X)

        form = ttk.Labelframe(
            pencere, text=" Yeni kullanıcı oluştur ", padding=18,
            bootstyle="primary"
        )
        form.pack(fill=X, padx=22, pady=16)
        for sutun in (1, 3):
            form.columnconfigure(sutun, weight=1)

        kullanici_adi = tk.StringVar()
        rol_adi = tk.StringVar(value="Görüntüleyici")
        konum_adi = tk.StringVar(value="Atanmamış")
        gecici_parola = tk.StringVar()
        yonetici_parolasi = tk.StringVar()
        parolalar_gorunur = tk.BooleanVar(value=False)
        parola_kutulari = []
        rol_haritasi = {ad: kod for kod, ad in ROL_ADLARI.items()}
        konumlar = self.vt.konumlari_getir()
        konum_haritasi = {"Atanmamış": None}
        konum_haritasi.update({k["ad"]: k["id"] for k in konumlar})
        konum_turleri = {k["id"]: k["tur"] for k in konumlar}

        alanlar = (
            ("Kullanıcı adı:", kullanici_adi, 0, 0),
            ("Geçici parola:", gecici_parola, 0, 2),
            ("Rol:", rol_adi, 1, 0),
            ("Konum:", konum_adi, 1, 2),
            ("Mevcut yönetici parolanız:", yonetici_parolasi, 2, 0),
        )
        for etiket, degisken, satir, sutun in alanlar:
            ttk.Label(form, text=etiket).grid(
                row=satir, column=sutun, sticky="w", padx=(0, 8), pady=8
            )
            if etiket == "Rol:":
                kutu = ttk.Combobox(
                    form, textvariable=degisken,
                    values=list(rol_haritasi), state="readonly"
                )
            elif etiket == "Konum:":
                kutu = ttk.Combobox(
                    form, textvariable=degisken,
                    values=list(konum_haritasi), state="readonly"
                )
            else:
                kutu = ttk.Entry(
                    form, textvariable=degisken,
                    show="●" if "parola" in etiket.casefold() else ""
                )
                if "parola" in etiket.casefold():
                    parola_kutulari.append(kutu)
            kolon_birlesimi = 3 if satir == 2 else 1
            kutu.grid(
                row=satir, column=sutun + 1, columnspan=kolon_birlesimi,
                sticky="ew", pady=8, padx=(0, 14)
            )

        def parolalari_goster_gizle():
            isaret = "" if parolalar_gorunur.get() else "●"
            for parola_kutusu in parola_kutulari:
                parola_kutusu.configure(show=isaret)

        ttk.Checkbutton(
            form, text="Parolaları Göster", variable=parolalar_gorunur,
            command=parolalari_goster_gizle, bootstyle="round-toggle"
        ).grid(row=3, column=1, columnspan=3, sticky="w", pady=(3, 0))

        tablo = ttk.Treeview(
            pencere,
            columns=("id", "kullanici", "rol", "konum", "durum"),
            show="headings", bootstyle="primary", height=8
        )
        for kolon, baslik in (
            ("id", "ID"), ("kullanici", "Kullanıcı adı"),
            ("rol", "Rol"), ("konum", "Atanan konum"),
            ("durum", "Durum")
        ):
            tablo.heading(kolon, text=baslik)
        tablo.column("id", width=55, anchor=CENTER)
        tablo.column("kullanici", width=220)
        tablo.column("rol", width=190)
        tablo.column("konum", width=280)
        tablo.column("durum", width=100, anchor=CENTER)
        tablo.pack(fill=X, padx=22, pady=(0, 10))

        cloud_alan = ttk.Labelframe(
            pencere, text=" Cloud işletme üyeleri ", padding=10, bootstyle="info"
        )
        cloud_alan.pack(fill=BOTH, expand=True, padx=22, pady=(0, 10))
        cloud_alan.columnconfigure(0, weight=1); cloud_alan.rowconfigure(1, weight=1)
        cloud_bilgi = tk.StringVar(value="Cloud üyelerini görmek için Cloud bağlantısı gerekir.")
        ttk.Label(cloud_alan, textvariable=cloud_bilgi, foreground=RENK_METIN).grid(
            row=0, column=0, sticky="w", pady=(0, 7)
        )
        cloud_tablo = ttk.Treeview(
            cloud_alan, columns=("hesap", "rol", "durum", "kayit"),
            show="headings", bootstyle="info", height=5
        )
        for kolon, baslik in (("hesap", "Cloud kullanıcı kimliği"), ("rol", "Cloud rolü"),
                              ("durum", "Durum"), ("kayit", "Üyelik tarihi")):
            cloud_tablo.heading(kolon, text=baslik)
        cloud_tablo.column("hesap", width=330); cloud_tablo.column("rol", width=150)
        cloud_tablo.column("durum", width=100, anchor=CENTER); cloud_tablo.column("kayit", width=220)
        cloud_tablo.grid(row=1, column=0, sticky="nsew")

        def cloud_uyelerini_yenile():
            cloud_tablo.delete(*cloud_tablo.get_children())
            if not self.cloud.bagli:
                cloud_bilgi.set("Cloud bağlı değil. Cloud ve Senkronizasyon ayarlarından giriş yapın.")
                return
            try:
                uyeler = self.cloud.uyeleri_getir()
                for uye in uyeler:
                    cloud_tablo.insert("", END, values=(
                        uye.get("user_id", ""), uye.get("role", ""),
                        "Aktif" if uye.get("active", True) else "Pasif",
                        uye.get("created_at", "") or "—"
                    ))
                cloud_bilgi.set(
                    f"{len(uyeler)} Cloud üyesi • Yeni üyeler Cloud üyeliği verildiğinde burada otomatik görünür."
                )
            except Exception as hata:
                cloud_bilgi.set(f"Cloud üye listesi alınamadı: {hata}")

        def listeyi_yenile():
            tablo.delete(*tablo.get_children())
            for kayit in self.vt.kullanicilari_getir():
                tablo.insert("", END, values=(
                    kayit["id"], kayit["kullanici_adi"],
                    ROL_ADLARI.get(kayit["rol"], kayit["rol"]),
                    kayit["konum_adi"], "Aktif" if kayit["aktif"] else "Pasif"
                ))

        def yonetici_onayi():
            if not self.yonetici_parolasini_dogrula(yonetici_parolasi.get()):
                self.olumsuz_bildirimi(
                    "İşlem için mevcut ana yönetici parolanız doğrulanamadı.", pencere
                )
                return False
            return True

        def kullanici_ekle():
            if len(kullanici_adi.get().strip()) < 3:
                self.olumsuz_bildirimi("Kullanıcı adı en az 3 karakter olmalıdır.", pencere)
                return
            parola_gecerli, hata = parola_guclu_mu(gecici_parola.get())
            if not parola_gecerli:
                self.olumsuz_bildirimi(hata, pencere)
                return
            rol = rol_haritasi[rol_adi.get()]
            konum_id = konum_haritasi[konum_adi.get()]
            if rol in ("DEPO_PERSONELI", "SUBE_PERSONELI") and konum_id is None:
                self.olumsuz_bildirimi("Bu rol için depo veya şube seçmelisiniz.", pencere)
                return
            if rol == "DEPO_PERSONELI" and konum_turleri.get(konum_id) not in ("MERKEZ", "DEPO"):
                self.olumsuz_bildirimi("Depo personeline yalnızca bir depo atanabilir.", pencere)
                return
            if rol == "SUBE_PERSONELI" and konum_turleri.get(konum_id) != "SUBE":
                self.olumsuz_bildirimi("Şube personeline yalnızca bir şube atanabilir.", pencere)
                return
            if not yonetici_onayi():
                return
            try:
                self.vt.kullanici_ekle(
                    kullanici_adi.get().strip(), gecici_parola.get(), rol, konum_id
                )
            except ValueError as hata_mesaji:
                self.olumsuz_bildirimi(str(hata_mesaji), pencere)
                return
            kullanici_adi.set(""); gecici_parola.set("")
            self.basari_bildirimi("Yeni kullanıcı başarıyla oluşturuldu.", pencere)
            listeyi_yenile()

        def secili_kayit():
            secim = tablo.selection()
            if not secim:
                self.olumsuz_bildirimi("Önce listeden bir kullanıcı seçin.", pencere)
                return None
            return tablo.item(secim[0], "values")

        def durumu_degistir():
            degerler = secili_kayit()
            if not degerler or not yonetici_onayi():
                return
            kullanici_id = int(degerler[0])
            if kullanici_id == self.aktif_kullanici["id"]:
                self.olumsuz_bildirimi("Kendi aktif hesabınızı kapatamazsınız.", pencere)
                return
            yeni_aktif = degerler[4] != "Aktif"
            self.vt.kullanici_durumunu_degistir(kullanici_id, yeni_aktif)
            self.basari_bildirimi("Kullanıcı durumu güncellendi.", pencere)
            listeyi_yenile()

        def parolayi_sifirla():
            degerler = secili_kayit()
            if not degerler:
                return
            parola_gecerli, hata = parola_guclu_mu(gecici_parola.get())
            if not parola_gecerli:
                self.olumsuz_bildirimi(
                    "Seçili kullanıcı için Geçici parola alanına yeni güçlü parolayı yazın. " + hata,
                    pencere
                )
                return
            if not yonetici_onayi():
                return
            self.vt.kullanici_parolasi_degistir(int(degerler[0]), gecici_parola.get())
            gecici_parola.set("")
            self.basari_bildirimi("Seçili kullanıcının parolası yenilendi.", pencere)

        def yetkiyi_guncelle():
            degerler = secili_kayit()
            if not degerler:
                return
            kullanici_id = int(degerler[0])
            if kullanici_id == self.aktif_kullanici["id"]:
                self.olumsuz_bildirimi("Kendi ana yönetici rolünüzü bu ekrandan değiştiremezsiniz.", pencere)
                return
            rol = rol_haritasi[rol_adi.get()]
            konum_id = konum_haritasi[konum_adi.get()]
            if rol in ("DEPO_PERSONELI", "SUBE_PERSONELI") and konum_id is None:
                self.olumsuz_bildirimi("Seçilen rol için konum atamalısınız.", pencere)
                return
            if rol == "DEPO_PERSONELI" and konum_turleri.get(konum_id) not in ("MERKEZ", "DEPO"):
                self.olumsuz_bildirimi("Depo personeline yalnızca bir depo atanabilir.", pencere)
                return
            if rol == "SUBE_PERSONELI" and konum_turleri.get(konum_id) != "SUBE":
                self.olumsuz_bildirimi("Şube personeline yalnızca bir şube atanabilir.", pencere)
                return
            if not yonetici_onayi():
                return
            self.vt.kullanici_yetkisi_guncelle(kullanici_id, rol, konum_id)
            self.basari_bildirimi("Kullanıcının rol ve konum yetkisi güncellendi.", pencere)
            listeyi_yenile()

        def kullaniciyi_kaldir():
            degerler = secili_kayit()
            if not degerler:
                return
            kullanici_id = int(degerler[0])
            kullanici_ismi = str(degerler[1])
            if kullanici_id == self.aktif_kullanici["id"]:
                self.olumsuz_bildirimi(
                    "Açık olan kendi hesabınızı kaldıramazsınız.", pencere
                )
                return
            if not yonetici_onayi():
                return
            if not self.modern_onay(
                "Kullanıcıyı kaldır",
                (
                    f"'{kullanici_ismi}' kullanıcısı kalıcı olarak kaldırılsın mı?\n\n"
                    "Stok ve işlem geçmişi korunacaktır; yalnızca giriş hesabı silinir."
                ), pencere, "Kullanıcıyı Kaldır"
            ):
                return
            try:
                self.vt.kullanici_sil(kullanici_id)
            except ValueError as hata:
                self.olumsuz_bildirimi(str(hata), pencere)
                return
            if str(self.ayarlar.get("hatirlanan_kullanici", "")).casefold() == (
                kullanici_ismi.casefold()
            ):
                yerel_ayari_kaydet("hatirlanan_kullanici", "")
                self.ayarlar.pop("hatirlanan_kullanici", None)
            self.basari_bildirimi(
                f"{kullanici_ismi} kullanıcısı kaldırıldı.", pencere
            )
            listeyi_yenile()

        butonlar = ttk.Frame(pencere, padding=(22, 0, 22, 18))
        butonlar.pack(fill=X)
        ttk.Button(butonlar, text="Kullanıcı Oluştur", command=kullanici_ekle, bootstyle="success").pack(side=LEFT, padx=(0, 8))
        ttk.Button(butonlar, text="Aktif / Pasif Yap", command=durumu_degistir, bootstyle="warning").pack(side=LEFT, padx=(0, 8))
        ttk.Button(butonlar, text="Parolayı Yenile", command=parolayi_sifirla, bootstyle="info").pack(side=LEFT)
        ttk.Button(butonlar, text="Rol/Konum Güncelle", command=yetkiyi_guncelle, bootstyle="primary-outline").pack(side=LEFT, padx=8)
        ttk.Button(butonlar, text="Kullanıcı Kaldır", command=kullaniciyi_kaldir, bootstyle="danger-outline").pack(side=LEFT)
        ttk.Button(butonlar, text="Cloud Üyelerini Yenile", command=cloud_uyelerini_yenile, bootstyle="info-outline").pack(side=LEFT, padx=8)
        ttk.Button(butonlar, text="Kapat", command=pencere.destroy, bootstyle="secondary-outline").pack(side=RIGHT)
        listeyi_yenile(); cloud_uyelerini_yenile()

    def ayarlar_penceresini_ac(self):
        """0.13 modern, beş bölümlü Ayarlar merkezini açar."""
        if not self.yetki_kontrol("YONETIM"):
            return
        sayfa = self.uygulama_ici_sayfa_ac("Ayarlar Merkezi")
        ttk.Label(
            sayfa, text="AYARLAR MERKEZİ", font=(YAZI_TIPI, 22, "bold"),
            bootstyle="inverse-primary", padding=22
        ).pack(fill=X)
        ttk.Label(
            sayfa, text="DeporiaQ'yu işletmenizin çalışma biçimine göre yönetin.",
            font=(YAZI_TIPI, 11), foreground=RENK_METIN, padding=(24, 14)
        ).pack(fill=X)
        govde = ttk.Frame(sayfa, padding=22); govde.pack(fill=BOTH, expand=True)
        for sutun in range(2): govde.columnconfigure(sutun, weight=1)
        for satir in range(3): govde.rowconfigure(satir, weight=1)

        kartlar = (
            ("◐  Genel ve Görünüm", "Dil, işletme bilgileri, açık ve koyu tema", self.genel_gorunum_ayarlari_ac, "primary"),
            ("☁  Cloud ve Senkronizasyon", "Cloud hesabı, cihazlar, eşitleme ve çakışmalar", self.cloud_ayarlari_ac, "info"),
            ("🔐  Kullanıcılar ve Güvenlik", "Yetkiler, parolalar, otomatik kilit ve oturumlar", self.guvenlik_ayarlari_ac, "warning"),
            ("⛁  Veri, Yedekleme ve Kurtarma", "Yedekler, Excel, sağlık kontrolü ve geri alma", self.veri_yonetimini_ac, "success"),
            ("🔔  Bildirimler ve Güncellemeler", "Masaüstü bildirimleri, sürüm ve kritik stok uyarıları", self.bildirim_ayarlari_ac, "danger"),
        )
        for i, (baslik, aciklama, komut, stil) in enumerate(kartlar):
            kart = ttk.Labelframe(govde, text=f" {baslik} ", padding=20, bootstyle=stil)
            kart.grid(row=i//2, column=i%2, sticky="nsew", padx=10, pady=10)
            ttk.Label(
                kart, text=aciklama, wraplength=430, justify="left",
                font=(YAZI_TIPI, 10), foreground=RENK_METIN
            ).pack(anchor="w", fill=X, pady=(0, 18))
            ttk.Button(kart, text="Ayarları Aç  →", command=komut, bootstyle=stil, padding=(18, 10)).pack(anchor="e")

    def genel_gorunum_ayarlari_ac(self):
        sayfa = self.uygulama_ici_sayfa_ac("Genel ve Görünüm")
        ttk.Label(sayfa,text="GENEL VE GÖRÜNÜM",font=(YAZI_TIPI,20,"bold"),bootstyle="inverse-primary",padding=20).pack(fill=X)
        alan=ttk.Labelframe(sayfa,text=" Tema ve dil ",padding=24,bootstyle="primary"); alan.pack(fill=X,padx=28,pady=24); alan.columnconfigure(1,weight=1)
        tema=tk.StringVar(value="Açık" if self.tema=="acik" else "Koyu")
        dil=tk.StringVar(value="İngilizce" if self.dil=="en" else "Türkçe")
        ttk.Label(alan,text="Görünüm teması:").grid(row=0,column=0,sticky="w",pady=10)
        ttk.Combobox(alan,textvariable=tema,values=("Koyu","Açık"),state="readonly").grid(row=0,column=1,sticky="ew",pady=10)
        ttk.Label(alan,text="Uygulama dili:").grid(row=1,column=0,sticky="w",pady=10)
        ttk.Combobox(alan,textvariable=dil,values=("Türkçe","İngilizce"),state="readonly").grid(row=1,column=1,sticky="ew",pady=10)
        def kaydet():
            self.tema="acik" if tema.get()=="Açık" else "koyu"; self.dil="en" if dil.get()=="İngilizce" else "tr"
            yerel_ayari_kaydet("uygulama_temasi",self.tema); yerel_ayari_kaydet("uygulama_dili",self.dil)
            self.ayarlar.update({"uygulama_temasi":self.tema,"uygulama_dili":self.dil})
            tema_renklerini_ayarla(self.tema)
            self.pencere.style.theme_use("flatly" if self.tema=="acik" else "darkly")
            self.basari_bildirimi("Tema ve dil kaydedildi. Ana panel yenileniyor.",sayfa)
            self.pencere.after(500,self.ana_ekrani_goster)
        ttk.Button(alan,text="Görünümü Kaydet ve Uygula",command=kaydet,bootstyle="primary",padding=(20,12)).grid(row=2,column=0,columnspan=2,pady=18)
        isletme=ttk.Labelframe(sayfa,text=" İşletme profili ",padding=24,bootstyle="info"); isletme.pack(fill=X,padx=28,pady=(0,24)); isletme.columnconfigure(1,weight=1)
        isletme_adi=tk.StringVar(value=self.isletme_adi)
        ttk.Label(isletme,text="İşletme adı:").grid(row=0,column=0,sticky="w",padx=(0,12),pady=8)
        ttk.Entry(isletme,textvariable=isletme_adi).grid(row=0,column=1,sticky="ew",pady=8)
        def isletmeyi_kaydet():
            ad=isletme_adi.get().strip()
            if not 2<=len(ad)<=120: self.olumsuz_bildirimi("İşletme adı 2–120 karakter olmalıdır.",sayfa); return
            self.vt.ayar_kaydet("isletme_adi",ad); self.isletme_adi=ad
            if hasattr(self,"ust_bilgi_etiketi"): self.ust_bilgi_etiketi.configure(text=self.ust_bilgi_metni())
            self.basari_bildirimi("İşletme profili güncellendi.",sayfa)
        ttk.Button(isletme,text="İşletme Bilgisini Kaydet",command=isletmeyi_kaydet,bootstyle="info").grid(row=1,column=0,columnspan=2,pady=12)

    def cloud_ayarlari_ac(self):
        self.guvenlik_ayarlari_ac(bolum="cloud")

    def bildirim_ayarlari_ac(self):
        sayfa=self.uygulama_ici_sayfa_ac("Bildirimler ve Güncellemeler")
        ttk.Label(sayfa,text="BİLDİRİMLER VE GÜNCELLEMELER",font=(YAZI_TIPI,20,"bold"),bootstyle="inverse-danger",padding=20).pack(fill=X)
        alan=ttk.Labelframe(sayfa,text=" Bildirim tercihleri ",padding=24,bootstyle="danger"); alan.pack(fill=X,padx=28,pady=24)
        masaustu=tk.BooleanVar(value=self.ayarlar.get("masaustu_bildirimleri",True)); kritik=tk.BooleanVar(value=self.ayarlar.get("kritik_stok_bildirimi",True))
        ttk.Checkbutton(alan,text="Yeni sürümlerde masaüstü bildirimi göster",variable=masaustu,bootstyle="success-round-toggle").pack(anchor="w",pady=10)
        ttk.Checkbutton(alan,text="Kritik stok uyarılarını göster",variable=kritik,bootstyle="warning-round-toggle").pack(anchor="w",pady=10)
        def kaydet():
            yerel_ayari_kaydet("masaustu_bildirimleri",bool(masaustu.get())); yerel_ayari_kaydet("kritik_stok_bildirimi",bool(kritik.get()))
            self.ayarlar.update({"masaustu_bildirimleri":bool(masaustu.get()),"kritik_stok_bildirimi":bool(kritik.get())}); self.basari_bildirimi("Bildirim tercihleri kaydedildi.",sayfa)
        ttk.Button(alan,text="Tercihleri Kaydet",command=kaydet,bootstyle="danger",padding=(18,10)).pack(anchor="e",pady=14)
        ttk.Button(alan,text="Şimdi Güncellemeleri Kontrol Et",command=self.guncellemeleri_kontrol_et,bootstyle="info-outline").pack(anchor="e")

    def guvenlik_ayarlari_ac(self, bolum=None):
        if not self.yetki_kontrol("YONETIM"):
            return
        ekran_basligi = "Cloud ve Senkronizasyon" if bolum == "cloud" else "Kullanıcılar ve Güvenlik"
        pencere = self.uygulama_ici_sayfa_ac(ekran_basligi)
        pencere.title(ekran_basligi)
        pencere.geometry("760x760")
        pencere.transient(self.pencere)
        ttk.Label(
            pencere, text=ekran_basligi.upper(),
            font=(YAZI_TIPI, 20, "bold"),
            bootstyle="inverse-dark", padding=18
        ).pack(fill=X)

        kilit = tk.StringVar(
            value=self.vt.ayar_getir("otomatik_kilit_dakika", "15")
        )
        mevcut = tk.StringVar(); yeni = tk.StringVar(); tekrar = tk.StringVar()
        isletme_adi_yeni = tk.StringVar(value=self.isletme_adi)
        dil_secimi = tk.StringVar(value="İngilizce" if self.dil == "en" else "Türkçe")
        parolalar_gorunur = tk.BooleanVar(value=False)

        dil_formu = ttk.Labelframe(
            pencere, text=" Dil ve görünüm ", padding=16, bootstyle="info"
        )
        dil_formu.pack(fill=X, padx=26, pady=(18, 0))
        dil_formu.columnconfigure(1, weight=1)
        ttk.Label(dil_formu, text="Uygulama dili:").grid(row=0, column=0, padx=(0, 12))
        ttk.Combobox(
            dil_formu, textvariable=dil_secimi,
            values=("Türkçe", "İngilizce"), state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=(0, 12))

        def dili_kaydet():
            self.dil = "en" if dil_secimi.get() in ("İngilizce", "English") else "tr"
            yerel_ayari_kaydet("uygulama_dili", self.dil)
            self.ayarlar["uygulama_dili"] = self.dil
            self.basari_bildirimi(
                "Language saved. The interface is being refreshed."
                if self.dil == "en" else "Dil ayarı kaydedildi. Arayüz yenileniyor.", pencere
            )
            self.pencere.after(500, self.ana_ekrani_goster)

        ttk.Button(
            dil_formu, text="Dil Ayarını Kaydet", command=dili_kaydet,
            bootstyle="info"
        ).grid(row=0, column=2)

        cloud_formu = ttk.Labelframe(
            pencere, text=" DeporiaQ Cloud Test ", padding=14,
            bootstyle="info"
        )
        cloud_formu.pack(fill=X, padx=26, pady=(10, 0))
        cloud_formu.columnconfigure(1, weight=1)
        cloud_url = tk.StringVar(value=str(self.ayarlar.get(
            "cloud_url", "https://eaqevlstfkelrtyfcnxj.supabase.co"
        )))
        cloud_key = tk.StringVar(value=str(self.ayarlar.get("cloud_publishable_key", "")))
        cloud_email = tk.StringVar(value=str(self.ayarlar.get("cloud_email", "")))
        cloud_parola = tk.StringVar()
        cloud_hatirla = tk.BooleanVar(value=bool(self.ayarlar.get("cloud_refresh_token_dpapi")))
        cloud_durum = tk.StringVar(value=(
            f"✓ Bağlı • {self.cloud.company_name} • {self.cloud.role} • Cihaz: {self.cihaz_kimligi}"
            if self.cloud.bagli else f"Bağlı değil • Cihaz: {self.cihaz_kimligi}"
        ))
        cloud_parola_gorunur = tk.BooleanVar(value=False)
        cloud_giris_alanlari = []
        for satir, (etiket, degisken, gizli) in enumerate((
            ("Project URL:", cloud_url, False),
            ("Publishable / anon key:", cloud_key, True),
            ("Cloud e-posta:", cloud_email, False),
            ("Cloud parola:", cloud_parola, True),
        )):
            ttk.Label(cloud_formu, text=etiket).grid(row=satir, column=0, sticky="w", padx=(0, 10), pady=4)
            kutu = ttk.Entry(cloud_formu, textvariable=degisken, show="●" if gizli else "")
            kutu.grid(row=satir, column=1, columnspan=4, sticky="ew", pady=4)
            cloud_giris_alanlari.append(kutu)
            if satir == 3:
                cloud_parola_kutusu = kutu

        def cloud_parolayi_goster():
            cloud_parola_kutusu.configure(show="" if cloud_parola_gorunur.get() else "●")

        ttk.Checkbutton(
            cloud_formu, text="Parolayı göster", variable=cloud_parola_gorunur,
            command=cloud_parolayi_goster, bootstyle="round-toggle"
        ).grid(row=4, column=1, sticky="w", pady=(2, 6))
        ttk.Checkbutton(
            cloud_formu, text="Bu cihazı hatırla", variable=cloud_hatirla,
            bootstyle="round-toggle"
        ).grid(row=4, column=2, sticky="w", pady=(2, 6))
        ttk.Label(cloud_formu, textvariable=cloud_durum, bootstyle="info").grid(
            row=5, column=0, columnspan=5, sticky="w", pady=(2, 8)
        )

        def cloud_islemde(islem, basari_metni):
            cloud_durum.set("İşlem sürüyor, lütfen bekleyin…")
            pencere.update_idletasks()
            try:
                sonuc = islem()
                mesaj = basari_metni(sonuc) if callable(basari_metni) else basari_metni
                cloud_durum.set(mesaj)
                self.basari_bildirimi(mesaj, pencere)
            except Exception as hata:
                cloud_durum.set("İşlem başarısız")
                self.olumsuz_bildirimi(str(hata), pencere)

        def cloud_giris():
            url, anahtar = cloud_url.get().strip(), cloud_key.get().strip()
            email, parola = cloud_email.get().strip(), cloud_parola.get()
            if not email or not parola:
                self.olumsuz_bildirimi("Cloud e-posta ve parola boş bırakılamaz.", pencere)
                return
            self.cloud.yapilandir(url, anahtar)
            yerel_ayari_kaydet("cloud_url", url)
            yerel_ayari_kaydet("cloud_publishable_key", anahtar)
            yerel_ayari_kaydet("cloud_email", email)
            self.ayarlar.update({"cloud_url":url, "cloud_publishable_key":anahtar, "cloud_email":email})
            def giris_ve_hatirla():
                ad = self.cloud.giris_yap(email, parola)
                if cloud_hatirla.get() and self.cloud.refresh_token:
                    sifreli = windows_sifrele(self.cloud.refresh_token)
                    yerel_ayari_kaydet("cloud_refresh_token_dpapi", sifreli)
                    self.ayarlar["cloud_refresh_token_dpapi"] = sifreli
                else:
                    yerel_ayari_kaydet("cloud_refresh_token_dpapi", "")
                    self.ayarlar.pop("cloud_refresh_token_dpapi", None)
                self.cloud_durum_metni.set("● Cloud bağlı")
                self.cloud_dongusunu_baslat()
                return ad
            cloud_islemde(giris_ve_hatirla, lambda ad: f"Cloud bağlantısı hazır: {ad} ({self.cloud.role})")
            cloud_alanlarini_guncelle()

        def buluta_yukle():
            if not self.cloud.bagli:
                self.olumsuz_bildirimi("Önce Cloud Giriş düğmesine basın.", pencere); return
            if not messagebox.askyesno(
                "Yerel veriyi buluta gönder",
                "Bu bilgisayardaki ürün, konum ve stok değerleri buluta yazılacak. Devam edilsin mi?",
                parent=pencere
            ): return
            cloud_islemde(
                lambda: (self.cloud.yereli_buluta_gonder(), self.cloud.senkron_baslangic_noktasi_kaydet())[0],
                lambda s: f"Buluta aktarıldı: {s[0]} ürün, {s[1]} konum, {s[2]} stok kaydı."
            )

        def buluttan_indir():
            if not self.cloud.bagli:
                self.olumsuz_bildirimi("Önce Cloud Giriş düğmesine basın.", pencere); return
            if not messagebox.askyesno(
                "Buluttan yenile",
                "Buluttaki ürün, konum ve stoklar bu bilgisayara uygulanacak. Önce otomatik veritabanı yedeği alınacaktır. Devam edilsin mi?",
                parent=pencere
            ): return
            veritabani_yedegi_al()
            cloud_islemde(
                lambda: (self.cloud.buluttan_yere_indir(), self.cloud.senkron_baslangic_noktasi_kaydet())[0],
                lambda s: f"Buluttan yenilendi: {s[0]} ürün, {s[1]} konum, {s[2]} stok kaydı. Program ekranını F5 ile yenileyin."
            )

        def cloud_cikis_yap():
            self.cloud.cikis_yap()
            self.cloud_dongu_aktif = False
            yerel_ayari_kaydet("cloud_refresh_token_dpapi", "")
            self.ayarlar.pop("cloud_refresh_token_dpapi", None)
            cloud_hatirla.set(False)
            self.cloud_durum_metni.set("● Cloud oturumu gerekli")
            cloud_alanlarini_guncelle()

        cloud_butonlar = ttk.Frame(cloud_formu)
        cloud_butonlar.grid(row=6, column=0, columnspan=5, sticky="ew", pady=(4, 0))
        cloud_giris_dugmesi = ttk.Button(cloud_butonlar, text="Cloud Giriş", command=cloud_giris, bootstyle="info")
        cloud_giris_dugmesi.pack(side=LEFT, padx=(0, 8))
        ttk.Button(cloud_butonlar, text="Yerel Veriyi Buluta Gönder", command=buluta_yukle, bootstyle="warning").pack(side=LEFT, padx=(0, 8))
        ttk.Button(cloud_butonlar, text="Buluttan Yenile", command=buluttan_indir, bootstyle="success").pack(side=LEFT)
        ttk.Button(cloud_butonlar, text="Senkronizasyon Merkezi", command=self.senkronizasyon_merkezini_ac, bootstyle="secondary-outline").pack(side=LEFT,padx=8)
        cloud_cikis_dugmesi = ttk.Button(cloud_butonlar, text="Hesap Değiştir / Cloud'dan Çık", command=cloud_cikis_yap, bootstyle="danger-outline")
        cloud_cikis_dugmesi.pack(side=RIGHT)

        def cloud_alanlarini_guncelle():
            bagli = self.cloud.bagli
            for alan in cloud_giris_alanlari:
                alan.configure(state="disabled" if bagli else "normal")
            cloud_giris_dugmesi.configure(state="disabled" if bagli else "normal")
            cloud_cikis_dugmesi.configure(state="normal" if bagli else "disabled")
            if bagli:
                cloud_durum.set(
                    f"✓ CLOUD BAĞLI  •  {self.cloud.company_name}  •  {self.cloud.role}  •  {self.ayarlar.get('cloud_email','')}"
                )
            else:
                cloud_durum.set(f"Bağlı değil • Cihaz: {self.cihaz_kimligi}")

        cloud_alanlarini_guncelle()
        ttk.Label(
            cloud_formu,
            text="Akıllı senkronizasyon 15 saniyede bir değişiklikleri kontrol eder. Parola kaydedilmez; hatırlama anahtarı Windows DPAPI ile korunur.",
            wraplength=900, justify="left", bootstyle="secondary"
        ).grid(row=7, column=0, columnspan=5, sticky="w", pady=(8, 0))

        isletme_formu = ttk.Labelframe(
            pencere, text=" İşletme bilgileri ", padding=18,
            bootstyle="primary"
        )
        isletme_formu.pack(fill=X, padx=26, pady=(12, 0))
        isletme_formu.columnconfigure(1, weight=1)
        ttk.Label(isletme_formu, text="İşletme adı:").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        ttk.Entry(
            isletme_formu, textvariable=isletme_adi_yeni
        ).grid(row=0, column=1, sticky="ew")
        form = ttk.Labelframe(
            pencere, text=" Oturum ve parola güvenliği ",
            padding=24, bootstyle="warning"
        )
        form.pack(fill=BOTH, expand=True, padx=26, pady=14)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Otomatik kilit süresi:").grid(row=0, column=0, sticky="w", pady=12)
        ttk.Combobox(
            form, textvariable=kilit,
            values=("0", "5", "10", "15", "30", "60"), state="readonly"
        ).grid(row=0, column=1, sticky="ew", pady=12)
        ttk.Label(
            form, text="0 = otomatik kilit kapalı", bootstyle="secondary"
        ).grid(row=1, column=1, sticky="w")
        parola_kutulari = []
        for satir, (etiket, degisken) in enumerate((
            ("Mevcut yönetici parolası:", mevcut),
            ("Yeni yönetici parolası:", yeni),
            ("Yeni parola tekrarı:", tekrar)
        ), start=2):
            ttk.Label(form, text=etiket).grid(row=satir, column=0, sticky="w", pady=12, padx=(0, 12))
            parola_kutusu = ttk.Entry(form, textvariable=degisken, show="●")
            parola_kutusu.grid(row=satir, column=1, sticky="ew", pady=12)
            parola_kutulari.append(parola_kutusu)

        def parolalari_goster_gizle():
            isaret = "" if parolalar_gorunur.get() else "●"
            for parola_kutusu in parola_kutulari:
                parola_kutusu.configure(show=isaret)

        ttk.Checkbutton(
            form, text="Parolaları Göster", variable=parolalar_gorunur,
            command=parolalari_goster_gizle, bootstyle="round-toggle"
        ).grid(row=5, column=1, sticky="w", pady=(2, 10))

        def isletme_adini_kaydet():
            yeni_ad = isletme_adi_yeni.get().strip()
            if len(yeni_ad) < 2:
                self.olumsuz_bildirimi(
                    "İşletme adı en az 2 karakter olmalıdır.", pencere
                )
                return
            if len(yeni_ad) > 120:
                self.olumsuz_bildirimi(
                    "İşletme adı en fazla 120 karakter olabilir.", pencere
                )
                return
            if not self.yonetici_parolasini_dogrula(mevcut.get()):
                self.olumsuz_bildirimi(
                    "İşletme adını değiştirmek için mevcut yönetici parolanızı yazın.",
                    pencere
                )
                return
            self.vt.ayar_kaydet("isletme_adi", yeni_ad)
            self.vt.baglanti.commit()
            self.isletme_adi = yeni_ad
            if hasattr(self, "ust_bilgi_etiketi"):
                self.ust_bilgi_etiketi.configure(text=self.ust_bilgi_metni())
            self.basari_bildirimi("İşletme adı güncellendi.", pencere)

        def kilidi_kaydet():
            if not self.yonetici_parolasini_dogrula(mevcut.get()):
                self.olumsuz_bildirimi("Mevcut yönetici parolası hatalı.", pencere)
                return
            self.vt.ayar_kaydet("otomatik_kilit_dakika", kilit.get())
            self.vt.baglanti.commit()
            self.basari_bildirimi("Otomatik kilit ayarı kaydedildi.", pencere)

        def kendi_parolasini_degistir():
            if not self.yonetici_parolasini_dogrula(mevcut.get()):
                self.olumsuz_bildirimi("Mevcut yönetici parolası hatalı.", pencere)
                return
            gecerli, hata = parola_guclu_mu(yeni.get())
            if not gecerli:
                self.olumsuz_bildirimi(hata, pencere)
                return
            if yeni.get() != tekrar.get():
                self.olumsuz_bildirimi("Yeni parolalar birbiriyle aynı değil.", pencere)
                return
            self.vt.kullanici_parolasi_degistir(self.aktif_kullanici["id"], yeni.get())
            mevcut.set(""); yeni.set(""); tekrar.set("")
            self.basari_bildirimi("Yönetici parolanız başarıyla değiştirildi.", pencere)

        butonlar = ttk.Frame(pencere, padding=(26, 0, 26, 22))
        butonlar.pack(fill=X)
        kilit_dugmesi=ttk.Button(butonlar, text="Kilit Ayarını Kaydet", command=kilidi_kaydet, bootstyle="warning"); kilit_dugmesi.pack(side=LEFT)
        parola_dugmesi=ttk.Button(butonlar, text="Parolamı Değiştir", command=kendi_parolasini_degistir, bootstyle="success"); parola_dugmesi.pack(side=LEFT, padx=8)
        isletme_dugmesi=ttk.Button(butonlar, text="İşletme Adını Kaydet", command=isletme_adini_kaydet, bootstyle="primary"); isletme_dugmesi.pack(side=LEFT)
        ttk.Button(butonlar, text="Kapat", command=pencere.destroy, bootstyle="secondary-outline").pack(side=RIGHT)
        if bolum == "cloud":
            dil_formu.pack_forget(); isletme_formu.pack_forget(); form.pack_forget(); butonlar.pack_forget()
        else:
            dil_formu.pack_forget(); cloud_formu.pack_forget(); isletme_formu.pack_forget(); isletme_dugmesi.pack_forget()

    def programi_kapat(self):
        if self.oturum_acik:
            self.vt.denetim_ekle("PROGRAM_KAPATILDI", "Program kapatıldı")
            self.vt.oturum_bitir(self.oturum_id)
        self.vt.kapat()
        self.pencere.destroy()

    def baslat(self):
        self.pencere.mainloop()


if __name__ == "__main__":
    uygulama = TeknoStokUygulamasi()
    if uygulama.hazir:
        uygulama.baslat()
