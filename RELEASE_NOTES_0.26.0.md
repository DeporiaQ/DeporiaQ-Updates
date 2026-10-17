# DeporiaQ 0.26.0 — İki dil, uygulama içi arama ve asistan

Aday sürüm. Canlı SQL geçişi, asistan hizmeti ve Windows yayın doğrulamaları tamamlanmadan normal güncelleme kanalına verilmez.

- Türkçe ve İngilizce arayüz; sol menüde yazısız TR/UK bayrakları. Dil seçimi kaydedilir. Ürün adları, barkodlar ve açık form girişleri korunur.
- Kurulum ve otomatik güncelleme mesajları da iki dili destekler; güncelleyici uygulamadaki dil seçimini izler.
- Ortalanmış, yarı saydam üst arama alanı; büyüteç alanın içinde. Menüler, ürün adları, barkodlar, ürün ayrıntıları ve konumlar birlikte aranır. Türkçe harfler aramada desteklenir.
- Arama sonucundan ürünün stok ekranına veya menüsüne geçiş. İşletme sınırı ve erişim kontrolü sunucuda uygulanır.
- DeporiaQ Asistan uygulama içinde bir yan panelde çalışır. Gerçek OpenAI API bağlantısı sunucu üzerinden kurulur; anahtar masaüstüne taşınmaz. Asistan kayıt değiştirmez ve canlı stok gördüğünü iddia etmez.
- Sağ üstte kutusuz ayarlar, bildirim ve açık/karanlık görünüm simgeleri. Bildirimler sade kart listesi ve okunmamış sayı ile gösterilir.
- Cloud durumu yeşil noktayla sol alta taşınır; üstte kayıtlı cihaz sayısı gösterilmez.
- İşletme adı yalnızca Cloud `owner` rolü tarafından değiştirilebilir. Sunucu onayı sonrası başlık ve yerel önbellek güncellenir. Aynı anda yapılan değişikliklerde eski veriyle yeni adın üzerine yazılmaz.
- Ayarlardaki uzun özet kartı sıralama/gizleme bölümü kaldırıldı. Özetler görünür kalır.
- İngilizce metinlere ve açık görünümün okunabilirliğine göre menü, sosyal düğme ve finans özeti düzenlendi.

Sunucu kurulumu: `server/ASSISTANT_SETUP_0260.md`.

Doğrulama: 95 uygulama testi, farklı pencere boylarında Qt çizimi, owner/yönetici ayrımı, şirketler arası arama yalıtımı, değişmeyen stok/abonelik kayıtları ve 8 asistan sınır/hata testi geçti. Windows kurulum, açık uygulamada yükseltme ve otomatik yeniden açılma başarılı. Test edilen paket Microsoft Defender ve ClamAV taramalarından geçti. Kanıtlar ve canlı kurulumda kalanlar: `RELEASE_0.26.0.md`.
