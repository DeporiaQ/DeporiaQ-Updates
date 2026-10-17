# DeporiaQ 0.26.0 — İki dil, uygulama içi arama ve ücretsiz rehber asistanı

- Türkçe ve İngilizce arayüz; sol menüde yazısız TR/UK bayrakları. Dil seçimi kaydedilir. Ürün adları, barkodlar ve açık form girişleri korunur.
- Kurulum ve otomatik güncelleme mesajları da iki dili destekler; güncelleyici uygulamadaki dil seçimini izler.
- Ortalanmış, yarı saydam üst arama alanı; büyüteç alanın içinde. Menüler, ürün adları, barkodlar, ürün ayrıntıları ve konumlar birlikte aranır. Türkçe harfler desteklenir.
- Arama sonucundan ürünün stok ekranına veya ilgili menüye geçiş. İşletme sınırı ve erişim kontrolü sunucuda uygulanır.
- **DeporiaQ Asistan ücretsiz yerleşik kullanım rehberidir.** Türkçe ve İngilizce 29 konuya ait hazır anlatımları sunar; internet, API anahtarı veya soru başına ücret gerektirmez. Üretken yapay zekâ değildir.
- Asistanın ekran açma düğmeleri mevcut kullanıcı yetkilerini korur. Asistan kendi başına satış, stok değişikliği veya e-posta gönderimi yapmaz. Mesajlar dışarı gönderilmez; geçmiş uygulama belleğinde tutulur ve Yeni Sohbet ile temizlenir.
- Eşleşmeyen sorularda konu seçimi ve destek seçenekleri; birden fazla eşleşmede konu seçimi. Enter ile gönderme, Shift+Enter ile yeni satır.
- Sağ üstte kutusuz ayarlar, bildirim ve açık/karanlık görünüm simgeleri. Bildirimler sade kart listesi ve okunmamış sayı ile gösterilir.
- Cloud durumu yeşil noktayla sol alta taşınır; üstte kayıtlı cihaz sayısı gösterilmez.
- İşletme adı yalnızca Cloud hesap sahibi tarafından değiştirilebilir. Sunucu onayından sonra üst başlık güncellenir. Başka cihazdan yapılmış yeni değişikliğin üzerine eski adla yazılmaz.
- Ayarlardaki uzun özet kartı sıralama/gizleme bölümü kaldırıldı. Özetler görünür kalır.
- İngilizce metinler ve açık görünüm için menü, sosyal düğme ve finans özeti düzenlendi.

Arama ve işletme adı yetkisi için `DEPORIAQ_CLOUD_0.26.0_UPDATE.sql` gerekir. Asistan için sunucu kurulumu veya OpenAI anahtarı gerekmez. Güncelleme mevcut stok kayıtlarını veya abonelik bitiş tarihini sıfırlamaz.

Windows güncellemesi uygulamayı kapatıp kurulumdan sonra yeniden açar. Güncellemeden önce açık işlemlerinizi kaydedin.
