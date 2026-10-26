# DeporiaQ 0.28.0 — hazırlanmış aday sürüm

Henüz yayımlanmadı. Sunucu geçişi tamamlanmadan kurulumu kullanıma açmayın.

## Değişiklikler
- Paneller 12 piksel aralıklarla ızgaraya oturur; kapatılan panelin boşluğu korunur.
- Aydınlık modda daha belirgin yazılar, panel yüzeyleri ve oklar.
- Panellerim içinde başlangıçta gizli 3D Raf ve Doluluk, Satış Kasası, Kampanyalar, Set ve Paketler, Mali Tablo ve Müşteriler panelleri. Ana ekrana eklemeden de açılabilir.
- Düzenlenebilir raf sırası, raf, kat, ölçüler ve koridor/raf aralıkları; ürün arama, renkli konum vurgusu, boş alan önerileri ve doluluk.
- Örnek yerleşim gerçek stok miktarını değiştirmez; 2 cm/kitap varsayımıyla hazırlanır ve fiziksel olarak doğrulanmamış şeklinde işaretlenir.
- Barkod/isimle satış, tekrar okutmayla adet artırma, set satışı, nakit/kart tutarı kaydı, kısmi iade ve sepet taslağı.
- Sunucuda güncel fiyat/maliyet kontrolü, maliyet altı indirim engeli, tek kampanya veya set indirimi ve eşzamanlı stok koruması.
- Kampanya yetkileri kullanıcı ve bilgisayara bağlı; ana yönetici yetki atayabilir.
- Gün/hafta/ay/yıl satış, iade, maliyet, brüt kâr, kayıtlı giderler; şube/kanal filtreleri, CSV ve geçmişi koruyan kapatma.
- Müşteri kartları, isteğe bağlı üyelik, ayrı e-posta/SMS izinleri ve izin geri çekme geçmişi. Otomatik pazarlama mesajı gönderilmez.

## Doğrulama
125 uygulama testi geçti. Gerçek PostgreSQL üzerinde son ürünü iki bağlantının aynı anda satması engellendi. Windows kurulum, açık uygulamada yükseltme ve yeniden açılma testleri geçti. Yerel 3D çizimler Windows üzerinde kontrol edildi. Aynı kurulum ve kurulu dosyalar Defender, kurulu dosyalar ayrıca ClamAV taramasından geçti.

## Kalan yayın koşulu
Supabase bağlantısı geçiş sırasında `Invalid or expired requestState` döndürdü. `DEPORIAQ_CLOUD_0.28.0_UPDATE.sql` henüz canlı sunucuya uygulanmadı. Bağlantı düzeldikten sonra geçiş uygulanmalı; gerçek şirket verilerinde geri alınan bir deneme işlemiyle kasa/rapor/yetkiler doğrulanmalı; stok ve abonelik korunması kontrol edilmeli; istenen örnek raflar hazırlanmalı. Sonrasında sürüm yayımlanıp otomatik güncelleme manifesti değiştirilebilir.
