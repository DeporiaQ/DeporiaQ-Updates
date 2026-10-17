# DeporiaQ 0.26.0 yayın doğrulaması

**Yayınlandı:** 17 Ekim 2026, 15:09 UTC (18:09 Türkiye).

- [GitHub Release v0.26.0](https://github.com/DeporiaQ/DeporiaQ-Updates/releases/tag/v0.26.0)
- Kaynak: `9d1c2356e1a68f681b6fb21aa3c2aa358feab7c7`.
- Yayın iş akışı kaynağı: `04204e9658a74e554d1016fd6487aa13e31fc0d1`.
- Ana dalın `guncelleme_manifest.json` dosyası 0.26.0 sürümünü ve aşağıdaki doğrulanmış dosya özetini gösterir. Normal uygulama içi güncelleme etkinleştirildi.

## Paket

Dosya: `DeporiaQ_Setup_0.26.0.exe` — 80.453.458 bayt.

SHA-256:
```
c603d5103b798f3d3f5d6c25cb2fa450c80299759760c17099e521550add5761
```

Derleme çıktısı: `12103849908`; ZIP SHA-256: `3491db6eb928a46c1438384ba42a4bb56da852d9fb4102d83fe9127c59d70de1`.

Yayın dosyasının GitHub özeti, Defender ile taranan kurulum dosyasının özeti ve ana güncelleme manifesti karşılaştırıldı: aynı. `v0.26.0` etiketi test edilen kaynak commit'ine bağlıdır.

## Tamamlanan kontroller

1. Yerel Python/Qt testleri: **98 başarılı**.
2. [Windows ve PostgreSQL işlev testleri](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39043008551): başarılı. İşletme sınırı, sahip yetkisi, eski düzenleme koruması, stok/ödeme atomikliği, dört eşzamanlı işlem senaryosu ve abonelik tarihinin korunması dahil.
3. [Canlı SQL 0.26.0 doğrulaması](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39043008574): başarılı.
4. [Windows derleme ve gerçek kurulum](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39043008621): başarılı. Windows'ta 98 test, üç pencere boyutunda çizim, görsel paketleme, yeni kurulum, açık uygulama yükseltmesi, 0.22.4/0.22.5/0.23.0 güncelleyici geçişi, eski işlemlerin kapanması, tek pencereyle açılma ve eski PyInstaller ortamından kurtarma doğrulandı. Test edilen sistem Windows Server 2022 GitHub Actions ortamıdır.
5. [Güvenlik ve yayın](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39043127103): başarılı. Microsoft Defender (`1.461.72.0`) kurulum paketinde ve kurulan dosyalarda tehdit bulmadı. ClamAV (`1.5.4`) kurulan altı dosyayı taradı: **0 enfekte dosya**.

Kurulum dosyası dijital olarak imzalı değildir. Tarama sonuçları kod imzası veya bütün Windows sürümlerinde sorunsuz çalışma garantisi değildir.

## Ücretsiz asistan

- 29 Türkçe/İngilizce konu; hazır kullanım anlatımları ve ilgili ekranları açan düğmeler.
- Soru eşleştirme, konu seçimi, belirsiz soruda seçim, bilinmeyen soruda rehber/destek seçenekleri.
- API anahtarı, harici yapay zekâ isteği, soru başına ücret veya asistan sunucu kurulumu yoktur.
- Mesajlar yalnızca uygulama belleğinde tutulur; Yeni Sohbet ile veya uygulama kapanınca temizlenir.
- Düğmelerde yönetici, görüntüleyici ve abonelik yetkileri denetlenir; işlem kendiliğinden kaydedilmez.
- Ağ erişimi engellenmiş test ortamında yanıt ve gezinme doğrulandı.

Önceki `7ba5ddfe0813083488700eed4c866372aea48664` ücretli API adayı yayınlanmadı ve bu sürümde kullanılmadı. Ücretli asistan istemcisi, Edge Function kaynakları ve dağıtım adımları kaldırıldı. Önceden uygulanmış SQL geçişinin yeniden çalıştırılması gerekmez.

## Kullanım

Açık işlemleri kaydedin. DeporiaQ içinde **Güncellemeleri Denetle → Şimdi İndir ve Kur** seçin. Kurulum uygulamayı kapatır ve tamamlanınca tekrar açar.
