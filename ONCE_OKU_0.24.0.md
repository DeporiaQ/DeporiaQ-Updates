# DeporiaQ 0.24.0 — geliştirme / inceleme adayı

Bu paket **müşteriye kurulacak tamamlanmış sürüm değildir**. 0.23.0'ı mevcut işletmede kullanmaya devam edin. Bu pakette Windows EXE veya Setup yoktur; kaynak, SQL, testler ve gerçek Qt ekranlarından alınmış örnek görüntüler vardır. Üretim Supabase projesine değişiklik uygulanmadı; GitHub'a gönderilmedi.

## Yapılanlar

- Demo (30 gün/1 cihaz), Single (1), Duo (3), Plus (6), Ultra (20) paket tanımları.
- Sunucu saatine göre süre kontrolü; mevcut aboneliğin tarihi migration ile uzatılmaz/sıfırlanmaz. Önceki `standard` paketi geçişte açıkça eşleştirilir.
- Hatırlanan Cloud oturumu yerel kullanıcı kimliği ve Cloud kullanıcı kimliğiyle eşleştirilir. Önceki ortak oturum kaydından geçişte ilk kez Cloud e-postası/parolası gerekir.
- Aynı şirket kilidi altında kayıtlı cihaz kotası, kasa satışı, stok girişi, sayım, transfer ve çok satırlı internet rezervasyonu.
- Eski tam stok yüklemelerini ve eski cihaz yazımlarını, geçişi etkinleşmiş şirketlerde engelleyen sunucu tetikleyicileri.
- Kanal ekleme/düzenleme/arşivleme, konum seçimi, konum başına güvenlik stoğu. Kanallar şimdilik ELLE sipariş girişlidir. Otomatik pazaryeri entegrasyonu yapılmış değildir.
- Önce merkez, sonra ürün için en yüksek kullanılabilir stoğa sahip konum sırası. Tek ürünlü örnekte merkez 2 + C 2. Çok ürünlü siparişler için bütün sepeti küresel olarak en az depoya indiren optimizasyon değildir.
- 30 dakikalık ödenmemiş rezervasyon; ödeme elle doğrulanınca hazırlama; merkeze sevk/teslim alma; ayrı gönderi; takip numarası; iptal; tam ayırma satırı iadesi ve teslim onayı.
- İade gerçekten alınmadan stok açılmaz. Kısmi ayırma satırı iadesi, otomatik eksik ürün yeniden dağıtımı ve kargo etiketi API entegrasyonu bu adayda yoktur.
- İşlem UUID'si istekten önce diske yazılır; belirsiz ağ sonucunda aynı kimlikle yeniden sorgulanır. Farklı satışla devam edilerek mükerrer işlem riski alınmaz.
- Salt okunur hesap satış yapamaz; yönetici olmayan personel için sunucuda konum ataması gerekir (`dpq.staff_locations`). Bu adayda personel atama paneli yerine yetkili sunucu yönetimi kullanılır.
- Paket ekranı, giriş ekranında küçük paket bağlantısı, sunucu destek formu ve TLS SMTP destek kuyruğu işçisi.
- Menü 9 başlık; Ayarlar → Gizli Komutlar'da tam 5 geçiş: Ctrl+K, Ctrl+1, Ctrl+2, Ctrl+3, Ctrl+4.
- Yeni satış/iade kayıtları eski rapor önbelleğine bir kez alınır; tekrar senkron ciroyu ikiye katlamaz.

## Test kanıtları

`test-results/unit-results.xml`: 54 Python/Qt testi (yeniden çalıştırmanın sonucu esas alınmalıdır).
`test-results/server-tests.json`: 22 PostgreSQL işlev senaryosu PGlite motorunda. Bu gerçek PostgreSQL sorgu yürütmesidir fakat TEK BAĞLANTILI ortamdır; çok oturumlu yarış testi yerine geçmez.
`test-results/dashboard-test.log`: 3 pencere boyutunda depo arka planı ve panel görünürlüğü testi.
`test-results/*.png`: gerçek Qt pencereleri; müşteri verisi değil örnek veriler.

`tests/server/concurrency.mjs`: yerel PostgreSQL'de 12 ayrı oturumla cihaz kotası, kasa/internet son ürün yarışı ve aynı satışın 12 eşzamanlı tekrarı. Bu ortamda native PostgreSQL sunucusu başlatılamadığı için **çalıştırılmadı**. CI tanımı hazırdır.
`tests/test_windows_install.py`: temiz kurulum; 0.22.4/0.22.5/0.23.0 güncelleyicilerinden geçiş; bağımsız yeniden açılma; tek pencere ve READY kaydı. Linux ortamında **çalıştırılmadı**.

## Yayından önce tamamlanması gerekenler

1. **Canlı şema ve RLS incelemesi:** `server/000_preflight.sql` salt okunurdur. Canlı veritabanı tanımı bu oturumda alınamadı; test şeması eski SQL ve istemci alanlarından yeniden kuruldu. Özellikle mevcut SECURITY DEFINER fonksiyonları ve doğrudan yazım izinleri denetlenmeli.
2. **Veri geçişi:** Bütün eski cihazların bekleyen hareketleri bitirilip stoklar uzlaştırılmalı; yerel ve sunucu yedekleri alınmalı. Kasa işlemleri kısa süre durdurulmalı. Önce test projesinde migration, sonra kontrollü gerçek geçiş yapılmalı. Eski senkron kuyruğu otomatik gönderilmez.
3. **Cihaz kimliği:** Kota sunucuda kayıtlı cihaz kodlarını sınırlar. Kod/kullanıcı oturumu kopyalama saldırısına karşı donanıma bağlı cihaz kanıtı bu adayda tamamlanmadı. “Başka bilgisayarda kesinlikle kullanılamaz” iddiası YOKTUR. Bu nedenle güvenlik yayını kapalıdır.
4. **Yeni müşteri kaydı:** 30 günlük deneme başlangıç fonksiyonu yalnızca güvenilir sunucu içindir. Kimlik doğrulama/onboarding servisi ve yeni hesaplarla tekrarlı deneme kötüye kullanımını önleme henüz uçtan uca tamamlanmadı. Masaüstünden gelişigüzel yeni deneme açılmaz.
5. **Ödeme:** Paket fiyatları ve satıcı hesabı belirtilmedi. Satın alma/yükseltme düğmesi bilerek devre dışıdır. Sunucu ödeme kaydı sadece doğrulanmış sağlayıcı adaptörüne izin verecek şekilde hazırdır; sağlayıcı imza doğrulaması, ödeme sayfası ve uçtan uca tahsilat entegrasyonu henüz YOKTUR. Ödeme dekontu/istemci bildirimi abonelik açamaz. Karttan otomatik tahsilat yapılmaz; yenileme düğmesi şimdilik sunucudaki tercihi kaydeder.
6. **Destek e-postası:** Talep sunucuda kaydedilir, mail durumu `pending` olur. `server/support_worker.py` SMTP TLS ve sunucu servis anahtarı yapılandırılınca çalıştırılmalıdır. Gerçek e-posta teslimi yapılmadı/test edilmedi. SMTP kabulü ile son alıcı posta kutusuna teslim aynı şey değildir. İşçi kesintisinde aynı Message-ID ile tekrar gönderim olabilir.
7. **Windows + gerçek PostgreSQL:** Aşağıdaki CI işleri başarıyla tamamlanmalı; cihaz ve canlı entegrasyon testleriyle birlikte sonuçlar incelenmeli.

## Güvenli doğrulama akışı

- Ayrı geliştirme dalında çalışın; üretim veritabanıyla ilk denemeyi yapmayın.
- GitHub → Actions → **DeporiaQ Commerce Tests**: bağımsız PostgreSQL 16 servisi ve Windows Qt testleri; üretim anahtarı istemez.
- GitHub → Actions → **DeporiaQ Windows Release**: `version=0.24.0`, `publish=false` varsayılanı. Derler, Windows yeniden açılmayı test eder, aday Setup'ı yalnızca Actions artifact'i olarak saklar. Release veya güncelleme manifesti yayımlamaz.
- `publish=true`, eksik kanıtlar varken `check_release.py` tarafından engellenir. `release_readiness.json` değerlerini yalnızca ilgili test/entegrasyon gerçekten tamamlandığında değiştirin.
- SQL geçişi varsayılan olarak hiçbir işletmeyi yeni moda almaz. `dpq_enable` yalnızca yetkili sunucu hesabıyla; şirket, paket ve merkez doğrulandıktan sonra çağrılır. Mevcut ücretli bitiş tarihi korunur.
- Aktif rezervasyonlar başladıktan sonra eski sürüme/yerel stok yüklemesine doğrudan dönüş yapılmaz. Önce sipariş/transfer ve stok uzlaştırması gerekir. Çözüm olarak veri sıfırlama aracını çalıştırmayın.

## Yerel test komutları

```bash
python -m pip install PySide6==6.11.2 ttkbootstrap==2.2.3 pytest==9.1.1
python -m pytest tests/test_analysis.py tests/test_runtime.py tests/test_operations_ui.py tests/test_commerce_client.py tests/test_commerce_cache.py tests/test_commerce_ui.py tests/test_support_worker.py tests/test_config_security.py -q
npm ci
npm run test:server
```

Native PostgreSQL için ayrı, boş, yalnızca test amaçlı veritabanı bağlantısını `DPQ_TEST_DATABASE_URL` ortam değişkenine koyun; `npm run test:server` ardından `npm run test:concurrency` çalıştırın. Üretim bağlantısı kullanmayın.

## İletişim

Destek: deporiaq@gmail.com. Henüz alınmamış `iletisim@deporiaq.com` adresi kullanılmaz.

Bu paketin amacı somut kodu, ekranları ve test kanıtlarını kaybetmeden tamamlanmış işlerle kalan güvenlik/yayın kapılarını açıkça ayırmaktır.
