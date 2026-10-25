# DeporiaQ 0.27.1

Mevcut işletmeler için ürün yönetimi ve masaüstü görünümü güncellemesi.

- **Ürün düzenleme ve kaldırma:** Stok ve Ürünler → Ürünler ve Stoklar → Ürünleri Düzenle / Sil ekranında barkod, ad, satış/alış fiyatı ve kritik stok düzenlenebilir. Stoksuz ürünler de listelenir.
- **Arşiv ve geri açma:** Stoğu biten ürün satıştan kaldırılıp arşivlenebilir; gerektiğinde yeniden etkinleştirilebilir. İşlem geçmişi korunur.
- **Kalıcı silme:** Yalnız ana yönetici, stoğu ve işlem geçmişi olmayan ürün kartını adını görerek ve SİL yazarak kaldırabilir. Kullanılmış ürünlerin satış ve stok kayıtları silinmez.
- **Daha güvenilir ürün eşleştirme:** Barkod düzeltildiğinde ürün kimliği değişmez. Aynı ada sahip farklı ürünler desteklenir; barkodun başındaki sıfırlar korunur ve görünmeyen karakterler denetlenir. Eski yerel veritabanı uyarlanırken önce yedeği alınır.
- **Sabit oturan 3D kedi:** Sol menüde ayrılmış alanda oturur, başı ve gözleri fareyi izler. Gezinme ve uyku hareketleri kaldırıldı. Kısa yardım ve mama tabelaları Türkçe/İngilizce gösterilir. Besleme, ad değiştirme, boyut ve gizleme ayarları korunur.
- **Küçük pencere düzeni:** Menü kaydırılırken bayraklar, kedi ve Cloud bilgisi görünür kalır.
- **Türk bayrağı:** Ay, yıldız ve en-boy oranları düzeltildi.

Cloud 0.27.1 geçişi uygulandı; mevcut ürünler, stok miktarları ve abonelik tarihleri korunarak doğrulandı. Kullanıcının yeniden SQL çalıştırması gerekmez.

Bu bakım sürümü mevcut işletmelerin kullanımına yöneliktir. Yeni işletmeler için herkese açık kayıt ve gerçek ödeme kabulü sunucuda kapalı kalır. Asistan ücretsiz, uygulama içi kullanım rehberidir; ücretli yapay zekâ API'si kullanmaz.
