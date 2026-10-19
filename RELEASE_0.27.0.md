# DeporiaQ 0.27.0 doğrulama ve yayın durumu

**Aday sürüm — müşterilere yayımlanmadı.** Ana güncelleme manifesti ve en son kararlı sürüm 0.26.0 olarak korunuyor.

## İncelenen kaynak

Masaüstü kaynak commit'i: `e30e6cfb9eef3d5352d44a51d7c7f0816d9197cb`.

- [Windows derleme, gerçek 3D ve kurulum testleri](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39172829950)
- [PostgreSQL, ödeme HTTP işleyicisi ve Windows işlev testleri](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39172829884)
- [Ek sunucu erişim testleri](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39173148304)
- [Aynı kurulum paketinin Microsoft Defender ve ClamAV taramaları](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39173148614)

Sonradan eklenen sunucu erişim geçişi ve belgeler masaüstü kodunu değiştirmez. Önceki adayın güvenlik sonucu, yeniden derlenen dosya için kanıt olarak kullanılmaz.

## Yapılan değişiklikler

- On ana sayfa panelinde bağımsız taşıma, boyutlandırma, gizleme, kilitleme ve yerleşim sıfırlama. Gizlenen panelin verisi yenilenir; diğer paneller boşluğa taşınmaz.
- Qt Quick 3D ile eklemli kedi; bakış, gezinme, oyun, el sallama, panel kenarından bakma, beslenme, uyku ve irkilme. Adı, görünürlüğü, boyutu ve hareket tercihi kullanıcıya göre saklanır.
- Kediye tıklama ile uygulama içi asistan; kedi gizlenince üst menü düğmesi. Asistan ana sayfayı daraltmaz ve açılışta konu kataloğu göstermez.
- Asistan: 116 ayrı kullanım anlatımı; 1.392 Türkçe/İngilizce soru biçimi. Bunlar 1.392 farklı konu değildir. Dizin, uygulamaya sahte içerik eklenmeden 1.500 ayrı test kaydıyla kapasite kontrolünden geçirildi.
- Mavi D ve kutu temalı uygulama/kurulum simgesi.
- Doğrulanmış e-posta, işletme oluşturma, yarım kalan kayda devam etme ve 30 günlük deneme altyapısı. Mevcut üyelik tekrar kayıtla yeni denemeye dönüşmez.
- Sunucunun belirlediği fiyat, iyzico Checkout Form, doğrulanmış sonuç, webhook/IFN ve tekrar ödeme bildirimi koruması. Gerçek tahsilat henüz etkin değil.

## Doğrulama

- Son kaynakta 110 Windows işlev testi başarılı. Uzun yanıtta satır kesilmesi ve yanıtın altında boşluğa kayma için görünürlük kontrolleri eklendi.
- PostgreSQL yetki/işletme ayrımı, kayıt tekrarları, mevcut abonelik süresi, ödeme tutarı/para birimi, tekrar iletim, sandbox ayrımı ve eşzamanlı işlem kontrolleri başarılı.
- Gerçek Edge HTTP işleyicisi, taklit dış hizmet yanıtlarıyla sınandı. Sahte ödeme bildirimi abonelik açmaz. Bu test gerçek iyzico sandbox kabul testi değildir.
- Gerçek Windows grafik sistemiyle dokuz kedi duruşunda görünür piksellerin maske tarafından kesilmediği kontrol edildi. Asistanın üstte açılması, beslenme, uyku/irkilme, küçük pencere ve gizlenen panelin yerinin korunması sınandı.
- Son adayda temiz kurulum, açık uygulama üzerinden yükseltme, eski 0.22.4/0.22.5/0.23 kurulumlarından yükseltme, eski PyInstaller süreçleri ve otomatik yeniden açılma kontrolleri başarılı.
- Microsoft Defender kurulum dosyası ve kurulan içerikte tehdit bulmadı. ClamAV taramasında enfekte dosya sayısı sıfır. Bu sonuçlar kod imzalama veya Windows SmartScreen uyarılarının kaldırıldığı anlamına gelmez.

## Doğrulanan 0.27.0 paketi

19 Ekim 2026'da sonuçları doğrulandı. Windows derleme işlemi `39172829950`; kurulum artifact'i `12153870560`, test kanıtı artifact'i `12153512505`. Son test raporu: 110 test, sıfır hata, sıfır başarısızlık, sıfır atlanan test.

`DeporiaQ_Setup_0.27.0.exe` SHA-256:

```
ce48f107acb267bab9c40e95ea38e53eaf608338d2a8d1d0d4202fdf08916113
```

Kurulum artifact ZIP SHA-256: `61149e744a584174db98c1a0d8dac0cca6feb0dd84187effddea9c940102dd9c`.
Test kanıtı ZIP SHA-256: `21efa4302b9e0985185f0350b93d48cad333e7637aeb667e63a50e5b7d18ffa4`.

Yayın hazırlama iş akışı bu kaynak ve başarılı kontrol işlemlerini sabitler, aynı dosyayı sürümlü ve sabit adlarla taslağa yükler. Taslak oluşturma ana manifesti veya genel `latest` sürümünü değiştirmez.

[Yayın taslağı](https://github.com/DeporiaQ/DeporiaQ-Updates/releases/tag/untagged-f48024453dff2077d142), [39295043521 numaralı hazırlama işlemi](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39295043521) ile oluşturuldu. Release ID: `417562061`; kaynak: `f29febd46e74b3e1f009dd624d48d1148c0f1252`. İki EXE dosyası da 199.350.787 bayt ve yukarıdaki SHA-256 değerine sahip. `draft=true`, dört varlığın yükleme durumu `uploaded` ve genel `latest` sürümünün hâlâ 0.26.0 olduğu GitHub API üzerinden doğrulandı. Taslağa erişim için depo yetkisi gerekir.

## Canlı hizmette kalanlar

0.27 SQL ve kayıt erişim geçişleri doğrudan Supabase bağlantısıyla uygulandı; mevcut paket tarih, plan ve durumları veritabanı içinde karşılaştırılarak korundu. Yeni işletme/sahip/30 günlük deneme ve tekrar kayıt akışı canlı şemada geri alınan işlemle sınandı. Test hesabı kalmadı. Ödeme Edge Function dağıtıldı; yetkisiz istekler reddediliyor.

19 Ekim'de Supabase web panelinde e-posta sağlayıcısının ve e-posta onay zorunluluğunun açık olduğu doğrulandı. Yeni kayıt/parola değişikliği politikası en az 14 karakter; küçük/büyük harf, rakam ve sembol olarak kaydedildi ve panel yeniden açılarak doğrulandı. E-posta OTP uzunluğu 8, geçerlilik süresi 3600 saniye olarak korundu. CAPTCHA ayarı mevcut kapalı durumunda bırakıldı; bir koruma devre dışı bırakılmadı. Mevcut hesap parolaları veya oturum ayarları değiştirilmedi.

Özel SMTP henüz yapılandırılmamış. Gönderici formu açıldı; SMTP şifresi girilmedi ve form kaydedilmedi. Kayıt e-postasının gerçek teslimi ve uçtan uca yeni kullanıcı kaydı henüz doğrulanmadığı için DeporiaQ işletme kayıt kapısı kapalı tutuluyor. Bu uygulama kapısı, açık olan Supabase Auth kayıt ayarından ayrıdır. Bağlı Supabase aracı Auth/SMTP yapılandırması sunmuyor; GitHub Management token'ı bu ayarda da HTTP 403 veriyor. Gönderici kurulumu web panelinden tamamlanmalı.

Eski işletme oluşturma çağrısı da doğrulanmış kayıt kurallarına bağlandı. Anonim rolün eski yönetici yetkili işlevlere erişimi kaldırıldı; oturum açmış kullanıcıların gerekli üyelik/işlem erişimi korundu. Yeni özel tabloların RLS politikası olmaması doğrudan istemci erişimini kapatmak için kasıtlıdır. Supabase'in mevcut Auth parola sızıntısı koruması kapalı uyarısı ve eski tabloların performans önerileri ayrıca değerlendirilmelidir; tüm danışman uyarılarının temizlendiği iddia edilmiyor.

Gerçek ödeme için onaylı üye işyeri hesabı, paket fiyatları, satış/gizlilik adresleri, sağlayıcı test hesabı ve gerçek callback/webhook/IFN teslim kontrolleri gerekiyor. Bu bilgiler tamamlanmadan canlı ödeme açılmaz.

[Bir defalık ticari kurulum adımları](server/COMMERCIAL_SETUP_0270.md)

## Kalıcı indirme bağlantısı

[Windows kurulumunu indir](https://github.com/DeporiaQ/DeporiaQ-Updates/releases/latest/download/DeporiaQ_Setup.exe)

18 Ekim 2026'da mevcut **0.26.0** kurulumunun aynı dosya içeriği `DeporiaQ_Setup.exe` adıyla eklendi. [Bağlantı hazırlama işlemi](https://github.com/DeporiaQ/DeporiaQ-Updates/actions/runs/39138941168) başarılı. Dosya 80.453.458 bayt; SHA-256:

```
c603d5103b798f3d3f5d6c25cb2fa450c80299759760c17099e521550add5761
```

Bu işlem 0.27.0'ı yayımlamaz veya uygulama içi güncelleme manifestini değiştirmez. Her yeni sürüm `latest` yapılmadan önce test edilmiş dosyanın aynı sabit adı da yüklenmelidir.
