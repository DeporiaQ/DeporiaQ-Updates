"""DeporiaQ 0.21.4 görünür ilerlemeli güvenli güncelleme yardımcısı."""
import ctypes
import hashlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
from pathlib import Path

MEVCUT_SURUM = "0.21.4"
PROGRAM_ADI = "DeporiaQ"
AZAMI_GUNCELLEME_BOYUTU = 1024 * 1024 * 1024


def uygulama_klasoru():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def surum_parcalari(surum):
    try:
        return tuple(int(x) for x in str(surum).split("."))
    except ValueError:
        return (0,)


def ayarlari_oku():
    yol = uygulama_klasoru() / "guncelleme_ayarlari.json"
    varsayilan = "https://raw.githubusercontent.com/DeporiaQ/DeporiaQ-Updates/main/guncelleme_manifest.json"
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return str(veri.get("guncelleme_manifest_url", varsayilan))
    except (OSError, ValueError, AttributeError):
        return varsayilan


def ingilizce_mi():
    try:
        yol = Path(os.getenv("LOCALAPPDATA", Path.home())) / "DeporiaQ" / "ayarlar.json"
        return json.loads(yol.read_text(encoding="utf-8")).get("uygulama_dili") == "en"
    except (OSError, ValueError, AttributeError):
        return False


def tek_ornek_calissin():
    if os.name != "nt":
        return True
    tutamac = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\DeporiaQUpdateNotifier")
    return bool(tutamac) and ctypes.windll.kernel32.GetLastError() != 183


def manifest_getir():
    adres = ayarlari_oku().strip()
    if not adres.lower().startswith("https://"):
        return None
    istek = urllib.request.Request(adres, headers={"User-Agent": f"DeporiaQ-Notifier/{MEVCUT_SURUM}"})
    with urllib.request.urlopen(istek, timeout=8) as cevap:
        veri = json.loads(cevap.read(65536).decode("utf-8"))
    yeni = str(veri.get("version", "0"))
    url = str(veri.get("download_url", ""))
    ozet = str(veri.get("sha256", "")).lower()
    if surum_parcalari(yeni) <= surum_parcalari(MEVCUT_SURUM):
        return None
    if not url.lower().startswith("https://") or len(ozet) != 64 or any(c not in "0123456789abcdef" for c in ozet):
        return None
    return {"version": yeni, "url": url, "sha256": ozet, "notes": str(veri.get("notes", ""))}


class Bildirim:
    def __init__(self, manifest):
        self.manifest = manifest
        self.en = ingilizce_mi()
        self.root = tk.Tk(); self.root.withdraw()
        self.pencere = tk.Toplevel(self.root)
        self.pencere.overrideredirect(True); self.pencere.attributes("-topmost", True)
        self.pencere.configure(bg="#111827")
        genislik, yukseklik = 430, 270
        x = self.pencere.winfo_screenwidth() - genislik - 18
        y = self.pencere.winfo_screenheight() - yukseklik - 62
        self.pencere.geometry(f"{genislik}x{yukseklik}+{x}+{y}")
        govde = tk.Frame(self.pencere, bg="#111827", padx=20, pady=17); govde.pack(fill="both", expand=True)
        tk.Label(govde, text="◆  DeporiaQ Update Available" if self.en else "◆  DeporiaQ Güncellemesi Hazır", fg="#f8fafc", bg="#111827", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        aciklama = f"Version {manifest['version']} is ready. Install now?" if self.en else f"Yeni sürüm {manifest['version']} hazır. Şimdi kurmak ister misiniz?"
        tk.Label(govde, text=aciklama, fg="#cbd5e1", bg="#111827", font=("Segoe UI", 10), wraplength=365, justify="left").pack(anchor="w", pady=(12, 5))
        self.durum = tk.StringVar(value=manifest["notes"][:150] or "Stok ve işletme verileriniz korunacaktır.")
        tk.Label(govde, textvariable=self.durum, fg="#94a3b8", bg="#111827", font=("Segoe UI", 9), wraplength=365, justify="left").pack(anchor="w")
        self.yuzde = tk.StringVar(value="")
        self.ilerleme_degeri = tk.DoubleVar(value=0)
        self.kurulum_suruyor = False
        self.stil = ttk.Style(self.root); self.stil.theme_use("clam")
        self.stil.configure("DeporiaQ.Horizontal.TProgressbar", troughcolor="#263449", background="#38BDF8", bordercolor="#263449", lightcolor="#38BDF8", darkcolor="#38BDF8", thickness=12)
        ilerleme_satiri=tk.Frame(govde,bg="#111827");ilerleme_satiri.pack(fill="x",pady=(12,8))
        self.ilerleme=ttk.Progressbar(ilerleme_satiri,style="DeporiaQ.Horizontal.TProgressbar",maximum=100,variable=self.ilerleme_degeri)
        self.ilerleme.pack(side="left",fill="x",expand=True)
        tk.Label(ilerleme_satiri,textvariable=self.yuzde,fg="#F8FAFC",bg="#111827",font=("Segoe UI",9,"bold"),width=5).pack(side="right",padx=(8,0))
        dugmeler = tk.Frame(govde, bg="#111827"); dugmeler.pack(fill="x", side="bottom")
        tk.Button(dugmeler, text="Later" if self.en else "Daha Sonra", command=self.kapat, bg="#374151", fg="white", relief="flat", padx=16, pady=8).pack(side="right")
        self.kur = tk.Button(dugmeler, text="Download and Install" if self.en else "Şimdi İndir ve Kur", command=self.indir, bg="#0ea5e9", fg="white", activebackground="#0284c7", relief="flat", padx=16, pady=8)
        self.kur.pack(side="right", padx=(0, 9))
        self.otomatik_kapatma=self.pencere.after(60_000, self.kapat)

    def ilerleme_ayarla(self, deger, metin):
        def uygula():
            self.ilerleme_degeri.set(max(0,min(100,deger)));self.yuzde.set(f"%{int(deger)}");self.durum.set(metin)
        self.root.after(0,uygula)

    def kurulum_animasyonu(self):
        if not self.kurulum_suruyor:return
        mevcut=float(self.ilerleme_degeri.get())
        if mevcut<99:
            self.ilerleme_degeri.set(mevcut+1);self.yuzde.set(f"%{int(mevcut+1)}")
        self.root.after(700,self.kurulum_animasyonu)

    def indir(self):
        try:self.pencere.after_cancel(self.otomatik_kapatma)
        except tk.TclError:pass
        self.kur.configure(state="disabled");self.pencere.protocol("WM_DELETE_WINDOW",lambda:None)
        self.ilerleme_ayarla(2,"Downloading update securely..." if self.en else "DeporiaQ güncelleniyor • İndirme hazırlanıyor…")
        def islem():
            hedef = Path(tempfile.gettempdir()) / f"DeporiaQ_Setup_{self.manifest['version']}.exe"
            gecici = hedef.with_suffix(".indiriliyor"); ozet = hashlib.sha256(); toplam = 0
            try:
                req = urllib.request.Request(self.manifest["url"], headers={"User-Agent": f"DeporiaQ-Notifier/{MEVCUT_SURUM}"})
                with urllib.request.urlopen(req, timeout=40) as cevap, open(gecici, "wb") as dosya:
                    beklenen=int(cevap.headers.get("Content-Length") or 0)
                    while True:
                        parca = cevap.read(1024 * 1024)
                        if not parca: break
                        toplam += len(parca)
                        if toplam > AZAMI_GUNCELLEME_BOYUTU: raise ValueError("Dosya güvenli indirme sınırını aşıyor.")
                        dosya.write(parca); ozet.update(parca)
                        oran=(toplam/beklenen) if beklenen else min(.95,toplam/(80*1024*1024))
                        self.ilerleme_ayarla(5+oran*73,f"DeporiaQ güncelleniyor • {toplam/(1024*1024):.1f} MB indirildi")
                self.ilerleme_ayarla(82,"DeporiaQ güncelleniyor • Dosya güvenliği doğrulanıyor…")
                if not secrets.compare_digest(ozet.hexdigest(), self.manifest["sha256"]):
                    raise ValueError("Güvenlik doğrulaması başarısız.")
                os.replace(gecici, hedef)
                self.ilerleme_ayarla(88,"DeporiaQ güncelleniyor • Uygulama güvenle kapatılıyor…")
                time.sleep(.7)
                if os.name=="nt":
                    subprocess.run(["taskkill","/F","/IM","DeporiaQ.exe"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                ortam = os.environ.copy()
                for anahtar in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "PYINSTALLER_RESET_ENVIRONMENT"):
                    ortam.pop(anahtar, None)
                ortam["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                self.ilerleme_ayarla(94,"DeporiaQ güncelleniyor • Windows izni ve kurulum bekleniyor…")
                self.kurulum_suruyor=True;self.root.after(700,self.kurulum_animasyonu)
                sonuc=subprocess.run([str(hedef),"/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART","/CLOSEAPPLICATIONS","/FORCECLOSEAPPLICATIONS"],env=ortam,close_fds=True)
                self.kurulum_suruyor=False
                if sonuc.returncode!=0:raise RuntimeError(f"Kurulum tamamlanamadı (kod {sonuc.returncode}).")
                self.ilerleme_ayarla(100,"Güncelleme tamamlandı • DeporiaQ yeniden açılıyor…")
                uygulama=uygulama_klasoru()/"DeporiaQ.exe"
                if uygulama.exists():subprocess.Popen([str(uygulama)],env=ortam,close_fds=True)
                self.root.after(1400,self.kapat)
            except Exception as hata:
                self.kurulum_suruyor=False
                try: gecici.unlink(missing_ok=True)
                except OSError: pass
                self.root.after(0,lambda:(self.yuzde.set("!"),self.durum.set(f"Güncelleme tamamlanamadı: {hata}"),self.kur.configure(state="normal"),self.pencere.protocol("WM_DELETE_WINDOW",self.kapat)))
        threading.Thread(target=islem, daemon=True).start()

    def kapat(self):
        try: self.root.destroy()
        except tk.TclError: pass

    def calistir(self):
        self.root.mainloop()


def sessiz_indir_ve_kur(manifest):
    """Kurulumu doğrular, DeporiaQ'yu kapatır, görünmeden kurar ve yeniden açar."""
    uygulama = uygulama_klasoru() / "DeporiaQ.exe"
    hedef = Path(tempfile.gettempdir()) / f"DeporiaQ_Setup_{manifest['version']}.exe"
    gecici = hedef.with_suffix(".indiriliyor"); ozet=hashlib.sha256(); toplam=0
    req=urllib.request.Request(manifest["url"],headers={"User-Agent":f"DeporiaQ-Updater/{MEVCUT_SURUM}"})
    with urllib.request.urlopen(req,timeout=60) as cevap,open(gecici,"wb") as dosya:
        while True:
            parca=cevap.read(1024*1024)
            if not parca:break
            toplam+=len(parca)
            if toplam>AZAMI_GUNCELLEME_BOYUTU:raise ValueError("Dosya güvenli indirme sınırını aşıyor.")
            dosya.write(parca);ozet.update(parca)
    if not secrets.compare_digest(ozet.hexdigest(),manifest["sha256"]):
        gecici.unlink(missing_ok=True);raise ValueError("Güncelleme güvenlik doğrulaması başarısız.")
    os.replace(gecici,hedef);time.sleep(2)
    if os.name=="nt":
        subprocess.run(["taskkill","/F","/IM","DeporiaQ.exe"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    ortam=os.environ.copy()
    for anahtar in ("_MEIPASS2","_PYI_APPLICATION_HOME_DIR","PYINSTALLER_RESET_ENVIRONMENT"):ortam.pop(anahtar,None)
    ortam["PYINSTALLER_RESET_ENVIRONMENT"]="1"
    sonuc=subprocess.run([str(hedef),"/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART","/CLOSEAPPLICATIONS","/FORCECLOSEAPPLICATIONS"],env=ortam,close_fds=True)
    if sonuc.returncode != 0:raise RuntimeError(f"Kurulum tamamlanamadı (kod {sonuc.returncode}).")


if __name__ == "__main__" and tek_ornek_calissin():
    try:
        bilgi = manifest_getir()
        if bilgi and "--install-now" in sys.argv:sessiz_indir_ve_kur(bilgi)
        elif bilgi and "--notify" in sys.argv:Bildirim(bilgi).calistir()
    except Exception:
        pass
