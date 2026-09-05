"""DeporiaQ 0.21.3 güvenli ve sessiz güncelleme yardımcısı."""
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
import urllib.request
from pathlib import Path

MEVCUT_SURUM = "0.21.3"
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
        genislik, yukseklik = 410, 230
        x = self.pencere.winfo_screenwidth() - genislik - 18
        y = self.pencere.winfo_screenheight() - yukseklik - 62
        self.pencere.geometry(f"{genislik}x{yukseklik}+{x}+{y}")
        govde = tk.Frame(self.pencere, bg="#111827", padx=20, pady=17); govde.pack(fill="both", expand=True)
        tk.Label(govde, text="◆  DeporiaQ Update Available" if self.en else "◆  DeporiaQ Güncellemesi Hazır", fg="#f8fafc", bg="#111827", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        aciklama = f"Version {manifest['version']} is ready. Install now?" if self.en else f"Yeni sürüm {manifest['version']} hazır. Şimdi kurmak ister misiniz?"
        tk.Label(govde, text=aciklama, fg="#cbd5e1", bg="#111827", font=("Segoe UI", 10), wraplength=365, justify="left").pack(anchor="w", pady=(12, 5))
        self.durum = tk.StringVar(value=manifest["notes"][:150] or "Stok ve işletme verileriniz korunacaktır.")
        tk.Label(govde, textvariable=self.durum, fg="#94a3b8", bg="#111827", font=("Segoe UI", 9), wraplength=365, justify="left").pack(anchor="w")
        dugmeler = tk.Frame(govde, bg="#111827"); dugmeler.pack(fill="x", side="bottom")
        tk.Button(dugmeler, text="Later" if self.en else "Daha Sonra", command=self.kapat, bg="#374151", fg="white", relief="flat", padx=16, pady=8).pack(side="right")
        self.kur = tk.Button(dugmeler, text="Download and Install" if self.en else "Şimdi İndir ve Kur", command=self.indir, bg="#0ea5e9", fg="white", activebackground="#0284c7", relief="flat", padx=16, pady=8)
        self.kur.pack(side="right", padx=(0, 9))
        self.pencere.after(60_000, self.kapat)

    def indir(self):
        self.kur.configure(state="disabled"); self.durum.set("Downloading update securely..." if self.en else "Güncelleme güvenli biçimde indiriliyor...")
        def islem():
            hedef = Path(tempfile.gettempdir()) / f"DeporiaQ_Setup_{self.manifest['version']}.exe"
            gecici = hedef.with_suffix(".indiriliyor"); ozet = hashlib.sha256(); toplam = 0
            try:
                req = urllib.request.Request(self.manifest["url"], headers={"User-Agent": f"DeporiaQ-Notifier/{MEVCUT_SURUM}"})
                with urllib.request.urlopen(req, timeout=40) as cevap, open(gecici, "wb") as dosya:
                    while True:
                        parca = cevap.read(1024 * 1024)
                        if not parca: break
                        toplam += len(parca)
                        if toplam > AZAMI_GUNCELLEME_BOYUTU: raise ValueError("Dosya güvenli indirme sınırını aşıyor.")
                        dosya.write(parca); ozet.update(parca)
                if not secrets.compare_digest(ozet.hexdigest(), self.manifest["sha256"]):
                    raise ValueError("Güvenlik doğrulaması başarısız.")
                os.replace(gecici, hedef)
                ortam = os.environ.copy()
                for anahtar in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "PYINSTALLER_RESET_ENVIRONMENT"):
                    ortam.pop(anahtar, None)
                ortam["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                subprocess.Popen([str(hedef)], env=ortam, close_fds=True)
                self.root.after(0, self.kapat)
            except Exception as hata:
                try: gecici.unlink(missing_ok=True)
                except OSError: pass
                self.root.after(0, lambda: (self.durum.set(f"İndirme başarısız: {hata}"), self.kur.configure(state="normal")))
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
