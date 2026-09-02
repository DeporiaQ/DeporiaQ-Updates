import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def veritabani_saglam_mi(yol):
    if not yol.exists():
        return False
    try:
        baglanti = sqlite3.connect(f"file:{yol}?mode=ro", uri=True)
        sonuc = baglanti.execute("PRAGMA integrity_check").fetchone()[0]
        baglanti.close()
        return sonuc == "ok"
    except sqlite3.Error:
        return False


def main():
    print("=" * 68)
    print("DEPORIAQ - YENI MUSTERI ICIN TAM SIFIRLAMA")
    print("=" * 68)
    print("Bu arac ana veritabanini silmez; tarihli arsive tasir.\n")

    onay = input("Devam etmek icin BUYUK HARFLERLE SIFIRLA yazin: ").strip()
    if onay != "SIFIRLA":
        print("Islem iptal edildi. Hicbir dosya degistirilmedi.")
        return 1

    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        print("HATA: Windows LOCALAPPDATA klasoru bulunamadi.")
        return 1

    veri_klasoru = Path(local_appdata) / "DeporiaQ"
    veritabani = veri_klasoru / "deporiaq.db"
    arsiv = veri_klasoru / "sifirlama_arsivi"
    arsiv.mkdir(parents=True, exist_ok=True)
    zaman = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if veritabani.exists():
        if not veritabani_saglam_mi(veritabani):
            print("HATA: Ana veritabani dogrulanamadi. Guvenlik icin islem durduruldu.")
            return 1
        arsiv_dosyasi = arsiv / f"sifirlama_oncesi_{zaman}.db"
        shutil.move(str(veritabani), str(arsiv_dosyasi))
        print(f"Eski veritabani arsivlendi:\n{arsiv_dosyasi}\n")
    else:
        print("Ana veritabani zaten bulunmuyor; temiz baslangic hazirlaniyor.\n")

    for uzanti in ("-wal", "-shm"):
        yan_dosya = Path(str(veritabani) + uzanti)
        if yan_dosya.exists():
            shutil.move(str(yan_dosya), str(arsiv / f"deporiaq_{zaman}.db{uzanti}"))

    # Proje/dist klasörlerindeki eski DB'nin yeniden otomatik taşınmasını engeller.
    tasima_isareti = veri_klasoru / "veritabani_tasima_0_3_1.tamam"
    tasima_isareti.write_text(
        "Yeni müşteri sıfırlaması yapıldı. Eski yerel veritabanlarını taşıma.\n",
        encoding="utf-8"
    )

    print("SIFIRLAMA HAZIR.")
    print("DeporiaQ sonraki acilista bos veritabani ve ilk kurulum sihirbaziyla baslayacak.")
    print("Eski veriler sifirlama_arsivi klasorunde korunuyor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
