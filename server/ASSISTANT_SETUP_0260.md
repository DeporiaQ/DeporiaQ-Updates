# DeporiaQ 0.26.0 — Ücretsiz yerleşik kullanım rehberi

17 Ekim 2026 tarihinde kullanıcı, API ile ücretlenen yapay zekâ yerine uygulamaya gömülü rehber asistanını seçti.

- Asistan Türkçe ve İngilizce soruları hazır kullanım anlatımlarıyla eşleştirir.
- İnternetsiz çalışır; API anahtarı, yapay zekâ hizmeti aboneliği veya soru başına ücret gerektirmez.
- Mesajlar yalnızca uygulama belleğinde tutulur. Yeni sohbet veya uygulamanın kapanması geçmişi temizler.
- Üretken yapay zekâ değildir. Eşleşmeyen sorular için konu seçimi ve destek seçenekleri sunar.
- Düğmeler mevcut uygulama ekranlarını açar. Asistan stok değiştirmez, satış yapmaz veya otomatik e-posta göndermez. İşlem ekranları mevcut sunucu ve yetki kontrollerini kullanır.

## Sunucu kurulumu

Asistan için sunucu kurulumu yapılmaz. `OPENAI_API_KEY` eklemeyin. Önceki ücretli asistan dağıtımı kaldırıldı; aynı iş akışı dosyası yalnızca SQL hazır olma kontrolünü yapar.

Ürün araması ve yalnızca hesap sahibinin işletme adını değiştirebilmesi için `DEPORIAQ_CLOUD_0.26.0_UPDATE.sql` geçişi gereklidir. Kullanıcının gönderdiği CSV'de `installed_version = 0.26.0` doğrulandı; yayın öncesi sunucudan tekrar kontrol edilir. Daha önce geçişi çalıştırdıysanız sırf asistan değişti diye SQL'i tekrar çalıştırmanız gerekmez. Mevcut stok ve abonelik kayıtları korunur.
