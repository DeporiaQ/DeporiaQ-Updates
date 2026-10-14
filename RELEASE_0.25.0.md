# DeporiaQ 0.25.0 — aday sürüm

Bu dal geliştirme ve doğrulama içindir. Canlı güncelleme bildirimi henüz değiştirilmedi.

## Mevcut ekran düzeltmeleri
- Paketlerde “Yönetici dahil” ifadesi.
- Eşit boyutlu sosyal düğmeler, WhatsApp ve X ikonları; X yalnız ikon.
- Alt ekrandan kapanınca ilgili menüye dönüş; ana pencereyi engellemeyen iş ekranları.
- Ortak açılır oklar, rapora uygun tarih alanları.
- Cihaz envanterinden ayrı kullanıcı oturumu, 10 saniyelik yoklama ve 30 saniyelik bağlantı kaybı süresi.
- Beş standart arka plan ve özel görsel seçimi.
- Sunucudan doğrudan destek e-postası ve talep durumu ekranı. Edge Function kurulumu gerektirir.

## Son dört arayüz isteği
- Profil yanında abonelik durumu, 30 dakikalık doğrulama; geçici bağlantı hatası ayrı gösterilir.
- Sol altta bağlantısız destek e-postası.
- Zil, okunmamış sayı, sarı hareketli bildirim çerçevesi ve kullanıcıya özel geçmiş.
- Kapatılabilir açılış/kapanış logo animasyonu.

## Yirmi geliştirme
1. Tek işlemde çok ürünlü satış sepeti.
2. Sunucuda bekletilen satış sepetleri (stok ayırmaz).
3. Nakit, kart ve bölünmüş ödeme kaydı (banka/POS entegrasyonu değildir).
4. Personel indirim sınırı ve tek sepete bağlı, 15 dakikalık yönetici onayı.
5. Ürün görselleri.
6. Kategori, etiket, yazar/marka ve yayınevi/üretici alanları ve arama.
7. Varyant grubu ve varyant değeri ile ürünleri bulma.
8. Set bileşenlerini sepete ekleme ve atomik stok düşümü.
9. Raf/koridor adresi ve arama.
10. Code128 barkodlu PDF raf etiketi.
11. Tedarikçi kartları.
12. Tedarikçiye bağlı satın alma siparişleri.
13. Sağlam/hasarlı teslim, önceki teslim ve kalan adet farkları.
14. Satılabilir stoktan ayrı hasarlı ürün kayıtları.
15. Ürüne bağlı parti numarası ve son kullanma tarihi kayıtları; otomatik FEFO tahsisi değildir.
16. Excel/CSV sütun eşleştirme, barkod ve sayı doğrulama, önizlemeli toplu ürün ekleme.
17. Eski fiyatı doğrulayan toplu fiyat önizlemesi.
18. İşletme üyelerine atanabilen görevler ve durum takibi.
19. Ana sayfa özet kartlarının sırası ve görünürlüğü.
20. Yeni veri giriş ekranlarında kaydedilmemiş değişiklik göstergesi ve çıkış seçenekleri.

## Sunucu kurulumu
1. Mevcut 0.24.1 veya üzeri sunucuya `DEPORIAQ_CLOUD_0.25.0_UPDATE.sql` uygulanır.
2. SQL sonucu `installed_version = 0.25.0` olmalı. Geçiş abonelik tarihlerini veya mevcut stokları değiştirmez.
3. Destek e-postası için GitHub Actions secrets alanında `SUPABASE_ACCESS_TOKEN` gerekir. Mevcut `DPQ_SMTP_PASSWORD` sunucu sırrı olarak aktarılır, istemciye eklenmez.
4. `DeporiaQ 0.25 Support Deployment` çalıştırılır. Gerçek bir talepte SMTP kabulü ayrıca doğrulanır.
5. Windows kurulum/açık uygulama yükseltmesi ve güvenlik taramaları başarılı olduktan sonra sürüm ve güncelleme manifesti yayınlanır.

## Doğrulama sınırı
Kod ve testler, canlı müşteri hesabında yeni sunucu geçişinin uygulandığı anlamına gelmez. Yayın öncesi canlı şema ve destek kurulumu ayrı doğrulanmalıdır.
