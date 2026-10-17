# DeporiaQ 0.26.0 — Doğrulama ve yayın durumu

17 Ekim 2026. Uygulama geliştirmesi ve aday paket doğrulamaları tamamlandı. Normal güncelleme kanalı hâlâ **0.25.0**. Bu belge 0.26.0'ın müşterilere yayınlandığı anlamına gelmez.

## Test edilen kaynak ve paket

- Kaynak commit: `7ba5ddfe0813083488700eed4c866372aea48664`.
- Çalışma dalı: `codex/deporiaq-0.26.0`. Sonraki commit'ler yalnızca doğrulama iş akışı, kurulum açıklaması ve hazır olma denetimi ekler; paket kodunu değiştirmez.
- [Windows aday derlemesi ve kurulum testi](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39020394020): başarılı.
- Aday artifact: `12096561887`, `DeporiaQ-0.26.0-candidate-setup`.
- Artifact ZIP SHA-256: `32f016df213a8ea8bc2c81e562edb659f352a7f72164e7729a38a78be4f467f7`.
- **Kurulum EXE SHA-256:** `c5c563d2dc004fe456d2726a82951a3d48a74ce5e407f9a93eae058200e28cc2`.

Yayın sırasında ZIP özeti ile EXE özeti karıştırılmamalı. Normal güncelleme manifesti EXE özetini kullanır. Test edilen ve taranan artifact yeniden derlenmeden yayınlanmalıdır.

## Tamamlanan doğrulamalar

| Kontrol | Sonuç |
|---|---|
| Python/Qt uygulama davranışları | 95 test geçti; yerel ortam ve Windows |
| Asistan sınırları ve hata davranışları | 8 test geçti; gerçek sağlayıcı kullanılmadan |
| PostgreSQL, yalıtım, yetki ve eşzamanlılık | Başarılı |
| Yeni kurulum ve açık uygulamada yükseltme | Başarılı; eski uygulama kapanıyor ve tek yeni pencere açılıyor |
| Eski 0.22.4 / 0.22.5 / 0.23.0 güncelleyicilerden geçiş | Başarılı |
| PyInstaller ortamı temizliği ve yeniden açılma | Başarılı |
| Türkçe/İngilizce, açık form verileri, yardım ve başlıklar | Başarılı |
| 1920 / 1366 / 900 piksel pencere genişlikleri, açık/koyu görünüm | Qt görüntüleri oluşturuldu ve düzen kontrol edildi |
| Microsoft Defender, kurulum ve kurulan dosyalar | Tehdit bulunmadı; imza sürümü 1.461.67.0 |
| ClamAV, kurulan dosyalar | 6 dosya tarandı, 0 bulaşmış dosya; motor 1.5.4 |

- [Kaynak commit'in uygulama ve PostgreSQL testleri](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39020393897)
- [Güvenlik taramaları](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39020519170)
- Windows görüntüleri ve günlükler: artifact `12095779516`.
- Defender kanıtları: artifact `12096631612`; ClamAV kanıtları: artifact `12096742125`.

Tarama sonuçları dijital kod imzası yerine geçmez. Bu aday EXE dijital olarak imzalı değildir.

## Canlı sunucuda kalanlar

[Son hazır olma kontrolü](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39020699597), 17 Ekim 2026 09:19 UTC:

- SQL 0.26.0 işareti doğrulanamadı; geçiş uygulanmalı.
- `OPENAI_API_KEY` eksik.
- `preflight` başarılı, **`deploy` atlandı**. Asistan henüz canlıya alınmadı; sağlayıcıya gerçek istek gönderilmedi.

Kullanıcı adımları: [Asistan ve arama kurulumu](server/ASSISTANT_SETUP_0260.md).

SQL ve anahtar tamamlandığında:

1. `server/ACTIVATE_ASSISTANT_0260` dosyasında yeni bir etkinleştirme notu commit ederek dağıtımı tetikle.
2. `deploy` işinin gerçekten başarılı olduğunu, sağlayıcının yanıt verdiğini ve kimliksiz isteğin reddedildiğini doğrula. Yalnızca yeşil `preflight` sonucu yeterli değildir.
3. Yukarıdaki kaynak, artifact ve güvenlik sonuçlarını esas alan 0.26.0 yayın iş akışını hazırla. Test edilmiş EXE'yi ve SHA256SUMS.txt'yi GitHub Release'e koy.
4. `main/guncelleme_manifest.json` dosyasını mevcut dosyanın SHA'sı ile karşılaştırarak güncelle. `version`, `download_url`, EXE `sha256`, Türkçe `notes` ve İngilizce `notes_en` alanlarını kullan; daha yeni manifestin üzerine yazma.
5. Release bağlantısını ve manifestin aynı EXE'yi gösterdiğini doğrula. Kullanıcı uygulama içindeki güncelleme denetimini kullanır.

Yayın için kullanıcı onayı önceki konuşmada verilmiştir; tekrar onay istenmesi gerekmiyor. Eksik olan onay değil, kullanıcının hesabında tamamlanması gereken iki sunucu ayarıdır.
