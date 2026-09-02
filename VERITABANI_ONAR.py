import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def veritabani_bilgisi(yol):
    try:
        baglanti = sqlite3.connect(f"file:{yol}?mode=ro", uri=True)
        saglamlik = baglanti.execute("PRAGMA integrity_check").fetchone()[0]
        if saglamlik != "ok":
            baglanti.close()
            return None
        konum = baglanti.execute("SELECT COUNT(*) FROM konumlar").fetchone()[0]
        aktif_konum = baglanti.execute(
            "SELECT COUNT(*) FROM konumlar WHERE aktif = 1"
        ).fetchone()[0]
        urun = baglanti.execute("SELECT COUNT(*) FROM urunler").fetchone()[0]
        stok = baglanti.execute(
            "SELECT COALESCE(SUM(miktar), 0) FROM stoklar"
        ).fetchone()[0]
        hareket = baglanti.execute(
            "SELECT COUNT(*) FROM stok_hareketleri"
        ).fetchone()[0]
        baglanti.close()
        return {
            "konum": konum,
            "aktif_konum": aktif_konum,
            "urun": urun,
            "stok": stok,
            "hareket": hareket,
            "boyut": yol.stat().st_size,
        }
    except (sqlite3.Error, OSError):
        return None


def puan(bilgi):
    return (
        bilgi["aktif_konum"],
        bilgi["konum"],
        bilgi["stok"],
        bilgi["hareket"],
        bilgi["urun"],
        bilgi["boyut"],
    )


def guvenli_kopyala(kaynak, hedef):
    gecici = hedef.with_name("deporiaq_onarim_gecici.db")
    if gecici.exists():
        gecici.unlink()
    kaynak_baglanti = sqlite3.connect(f"file:{kaynak}?mode=ro", uri=True)
    hedef_baglanti = sqlite3.connect(gecici)
    kaynak_baglanti.backup(hedef_baglanti)
    hedef_baglanti.close()
    kaynak_baglanti.close()
    os.replace(gecici, hedef)


def main():
    print("=" * 65)
    print("DEPORIAQ VERITABANI TESPIT VE ONARIM")
    print("=" * 65)
    print("Tum DeporiaQ pencerelerinin kapali oldugundan emin olun.\n")

    proje = Path(__file__).resolve().parent
    local_appdata = Path(os.environ["LOCALAPPDATA"]) / "DeporiaQ"
    hedef = local_appdata / "deporiaq.db"
    local_appdata.mkdir(parents=True, exist_ok=True)

    adaylar = set(proje.rglob("*.db"))
    adaylar.update(local_appdata.rglob("*.db"))
    sonuclar = []
    for yol in sorted(adaylar):
        bilgi = veritabani_bilgisi(yol)
        if bilgi:
            sonuclar.append((yol, bilgi))
            print(
                f"BULUNDU: {yol}\n"
                f"  Aktif konum: {bilgi['aktif_konum']} | "
                f"Toplam konum: {bilgi['konum']} | "
                f"Urun: {bilgi['urun']} | Stok: {bilgi['stok']} | "
                f"Hareket: {bilgi['hareket']} | "
                f"Boyut: {bilgi['boyut'] // 1024} KB\n"
            )

    if not sonuclar:
        print("HATA: Gecerli bir DeporiaQ veritabani bulunamadi.")
        return 1

    kaynak, kaynak_bilgi = max(sonuclar, key=lambda kayit: puan(kayit[1]))
    print("SECILEN EN DOLU VERITABANI:")
    print(kaynak)
    print(
        f"Aktif konum: {kaynak_bilgi['aktif_konum']} | "
        f"Stok: {kaynak_bilgi['stok']} | Hareket: {kaynak_bilgi['hareket']}\n"
    )

    if hedef.exists() and hedef.resolve() != kaynak.resolve():
        yedek_klasoru = local_appdata / "yedekler"
        yedek_klasoru.mkdir(exist_ok=True)
        zaman = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        yedek = yedek_klasoru / f"manuel_onarim_oncesi_{zaman}.db"
        shutil.copy2(hedef, yedek)
        print(f"Mevcut hedef yedeklendi: {yedek}")

    if hedef.resolve() != kaynak.resolve():
        guvenli_kopyala(kaynak, hedef)

    kontrol = veritabani_bilgisi(hedef)
    if not kontrol or puan(kontrol)[:-1] != puan(kaynak_bilgi)[:-1]:
        print("HATA: Kopyalama sonrasi dogrulama basarisiz.")
        return 1

    print("\nONARIM BASARILI.")
    print(f"DeporiaQ artik su veritabanini kullanacak:\n{hedef}")
    print(
        f"Aktif konum: {kontrol['aktif_konum']} | "
        f"Toplam stok: {kontrol['stok']} | Hareket: {kontrol['hareket']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
