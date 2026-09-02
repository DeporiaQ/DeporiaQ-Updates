import hashlib
import json
import shutil
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 4:
        print(
            "Kullanim: py GUNCELLEME_YAYINA_HAZIRLA.py "
            '"kurulum\\DeporiaQ_Setup_0.17.0.exe" 0.17.0 "https://...exe"'
        )
        return 1

    kurulum = Path(sys.argv[1]).resolve()
    surum = sys.argv[2].strip()
    adres = sys.argv[3].strip()
    if not kurulum.is_file():
        print(f"HATA: Kurulum dosyasi bulunamadi: {kurulum}")
        return 1
    if not adres.lower().startswith("https://"):
        print("HATA: Indirme adresi HTTPS ile baslamalidir.")
        return 1

    ozet = hashlib.sha256()
    with kurulum.open("rb") as dosya:
        for parca in iter(lambda: dosya.read(1024 * 1024), b""):
            ozet.update(parca)

    yayin = Path(__file__).resolve().parent / "yayin"
    yayin.mkdir(exist_ok=True)
    shutil.copy2(kurulum, yayin / kurulum.name)
    manifest = {
        "version": surum,
        "download_url": adres,
        "sha256": ozet.hexdigest(),
        "notes": "DeporiaQ Cloud test bağlantısı, güvenli Supabase oturumu, yerel veriyi buluta gönderme, buluttan yenileme ve cihaz kaydı eklendi.",
    }
    (yayin / "guncelleme_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("HAZIR: yayin klasorundeki iki dosyayi sunucunuza yukleyin.")
    print(f"SHA-256: {ozet.hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
