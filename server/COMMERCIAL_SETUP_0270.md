# DeporiaQ 0.27: bir kez yapılacak ticari kurulum

Müşterilere Supabase erişimi verilmez. Kurulum bir kez hizmet sahibi tarafından tamamlanır; sonraki kullanıcı işletmesini uygulamadan açar.

## Şu anki durum

18 Ekim 2026 UTC: Doğrudan Supabase bağlantısıyla 0.27 kayıt/ödeme SQL'i ve kayıt erişim geçişi uygulandı. Mevcut aboneliklerin tarih, plan ve durumları geçiş boyunca veritabanı içinde karşılaştırıldı ve korundu. Canlı şemadaki zorunlu `companies.created_by` alanına doğrulanmış kullanıcı kimliği yazılır.

Yeni işletme, sahip yetkisi, 30 günlük deneme ve aynı kaydı tekrar çağırma işlemleri canlı şemada geri alınan bir işlem içinde sınandı; test hesabı/verileri kalmadı. `payment-checkout` Edge Function dağıtıldı. Anonim istek 401, desteklenmeyen HTTP yöntemi 405 döndürdü. Genel kayıt ve tahsilat bayrakları henüz kapalıdır.

Kalan kayıt engeli Auth/SMTP ayarı ve gerçek kod teslimidir. Doğrudan bağlantı bu ayarları düzenleme işlemi sunmuyor; GitHub'daki mevcut Management anahtarı hem veritabanı hem Auth yapılandırması isteğinde HTTP 403 verdi. Supabase web paneli açıldı fakat giriş gerekiyor. Parola veya anahtar sohbet içine gönderilmemelidir. Aşağıdaki Actions yolu alternatif olarak yetkili bir Management token gerektirir.

## Sunucu erişimi ve kayıt

1. [Supabase erişim anahtarları](https://supabase.com/dashboard/account/tokens) bölümünde doğru projeyi yöneten hesabın geçerli token'ını hazırlayın. Veritabanı okuma/yazma, Auth yapılandırması ve Edge Functions dağıtımı için gerekli proje izinleri bulunmalı. Mevcut 403'ün token kapsamı veya proje üyeliği gibi hangi erişim ayarından kaynaklandığı henüz belirlenmedi; kullanıcı parolasını sohbete göndermeyin.
2. [GitHub Actions secrets](https://github.com/DeporiaQ/DeporiaQ-Updates/settings/secrets/actions) içinde `SUPABASE_ACCESS_TOKEN` değerini güncelleyin. Secret'ın değerini sohbete veya kaynak koda yazmayın.
3. `DeporiaQ 0.27 Read-only Server Preflight` yalnızca başarı/hata sonucu verir; üretim verisini veya şema raporunu dışarı aktarmadan çalışır.
4. **SQL tamamlandı.** Tekrar kurulum gerekirse `DeporiaQ 0.27 One-time Server Setup` içindeki **migrate** adımı kayıt/ödeme ve `20261018224000_enrollment_access.sql` geçişlerini uygular. Mevcut abonelikler veritabanı içinde karşılaştırılır; tarih/plan/durum değişirse işlem geri alınır.
5. **email** adımı e-posta onay kodunu ve en az 14 karakter kuralını hazırlar. Mevcut özel SMTP korunur; yoksa önceden güvenli kaydedilen `DPQ_SMTP_PASSWORD` ile DeporiaQ Gmail hesabı kullanılır. MFA, oturum ve CAPTCHA ayarları gevşetilmez.
6. Gerçek bir kayıt doğrulama kodunun teslimini kontrol edin; ardından **enrollment** adımında teslim kontrolünü işaretleyin. Şirket ve 30 günlük deneme e-posta doğrulamasından sonra sunucuda açılır. Var olan üyelik/deneme sıfırlanmaz.

CAPTCHA projede açıksa kayıt ekranına uygun CAPTCHA akışı eklenmeden kayıt açılmamalı; CAPTCHA'yı kapatmayın. Özel SMTP gönderim sınırları gerçek kullanıcı hacmiyle ayrıca izlenmelidir.

## Ödeme için gereken kararlar

- Onaylı iyzico üye işyeri hesabı ve Checkout Form API erişimi.
- Paket başına cihaz sayısı, aylık/yıllık dönem ve **müşterinin ödeyeceği toplam TL fiyatı**.
- İşletmenin gerçek bilgileriyle hazırlanmış HTTPS satış koşulları ve gizlilik sayfaları.
- Test ortamında başarılı, reddedilen, gecikmeli onaylanan ve tekrar iletilen ödeme denemeleri.

Uygulama bu bilgileri tahmin etmez. Kodda deneme testi fiyatları vardır; bunlar canlı satış kataloğuna aktarılmaz.

## Güvenli sağlayıcı yapılandırması

Supabase Edge Function secrets alanına şunları kaydedin:

| İsim | Değer |
|---|---|
| `DPQ_IYZICO_ENVIRONMENT` | Önce `sandbox`, doğrulamalardan sonra `live` |
| `DPQ_IYZICO_API_KEY` | Aynı ortamın iyzico API anahtarı |
| `DPQ_IYZICO_SECRET_KEY` | Aynı ortamın iyzico gizli anahtarı |

`SUPABASE_SERVICE_ROLE_KEY` Edge ortamında kalır. Masaüstü pakete ve `deporiaq_cloud.json` dosyasına eklenmez. İşlev mevcut projeye dağıtıldı; başka ortamda `supabase functions deploy payment-checkout --project-ref PROJE_KIMLIGI` kullanılabilir. Webhook/callback nedeniyle platform JWT kontrolü kapalıdır; masaüstü işlemleri işleyicide Supabase Auth ile, webhook sağlayıcı imzasıyla doğrulanır. API anahtarları kaynak koda yazılmaz.

iyzico panelinde proje adresinizi kullanarak:

- Ödeme sonucu bildirimi: `https://PROJE.supabase.co/functions/v1/payment-checkout?action=webhook`
- Fraud incelemesi bildirimi (IFN): `https://PROJE.supabase.co/functions/v1/payment-checkout?action=fraud`
- Tarayıcı dönüşü: Uygulama `...?action=callback` adresini otomatik gönderir.

Webhook için **X-IYZ-SIGNATURE-V3** etkin olmalı. Bildirim tek başına abonelik açmaz: sağlayıcıdan ödeme ayrıntısı tekrar alınır; tutar, para birimi, sipariş, ürün kalemi ve fraud onayı eşleşmelidir. İnceleme sonrası `fraudStatus=2` de doğrulanmış onaydır. IFN içindeki onay/ret değeri doğrudan kullanılmaz.

SQL'de fiyatlar `dpq.offers` tablosuna **kuruş** olarak, koşul URL'leri `dpq.commercial_config` tablosuna yazılır. Katalog ve ödeme yalnızca testler bittikten sonra sunucudan açılır. İstemcinin gönderdiği fiyata güvenilmez. Sandbox ödemesi gerçek aboneliği değiştirmez. Bir ödeme ikinci kez süre eklemez; ayrı geçerli alışveriş mevcut süreye eklenir.

Canlıya geçişte webhook ve IFN teslimi, uygulama kapalıyken ödeme aktivasyonu ve e-posta teslimi ayrıca doğrulanmalıdır. Bu doğrulamalar tamamlanmadan müşteriden gerçek ücret alınmaz.

## Paylaşılabilir indirme adresi

https://github.com/DeporiaQ/DeporiaQ-Updates/releases/latest/download/DeporiaQ_Setup.exe

Bu bağlantı Instagram ve YouTube profil bağlantısına eklenebilir. Her sürüm için yeni bir Drive bağlantısı gerektirmez. Doğrudan `.exe` dosyasını indirir. 18 Ekim'de yayımlanmış 0.26.0 paketinin aynı SHA-256 özetiyle bu sabit dosya adı eklendi; yeni 0.27.0 sürümü yayımlanmadı. Her sonraki sürüm `latest` yapılmadan önce aynı sabit dosya adı ve özeti de yüklenmelidir. Kaynak kod ZIP'i kurulum dosyası değildir.

## Uygulama dayanakları

- [iyzico Checkout Form](https://docs.iyzico.com/en/payment-methods/checkoutform)
- [iyzico webhook imzası](https://docs.iyzico.com/en/advanced/webhook)
- [iyzico fraud inceleme sonucu](https://docs.iyzico.com/en/advanced/fraud-notifications)
- [Supabase Auth yapılandırması](https://supabase.com/docs/reference/api/v1-update-auth-service-config)

`tests/server/onboarding.mjs` SQL yetki/ödeme sözleşmesini; `tests/server/payment_edge.mjs` gerçek Edge HTTP işleyicisini, dış bağlantı kurmayan test yanıtlarıyla denetler. Bunlar gerçek sağlayıcı sandbox kabul testinin yerine geçmez.
