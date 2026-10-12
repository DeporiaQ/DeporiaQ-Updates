# DeporiaQ 0.24.3

## İstenen düzenlemeler
- Tam adet stokları 80.0 yerine 80 gösterilir. Kesirli tutarsız kayıtlar gizlenmez; stok girişinde tam adet zorunluluğu sürer.
- Paket bitişi Türkiye saatiyle gösterilir; kalan süre sunucu saati ve monoton zamanla hesaplanır. İstemci güncellemesi abonelik kaydını değiştirmez.
- Gece Mavisi, Grafit ve Yüksek Kontrast temaları; özel arka plan, karartma ve yazı boyutu.
- Otomatik/manuel ekran kilidi, hatırlanan girişi silme ve yerel yedek bağlantısı.
- Kritik stok, bağlantı, paket bitişi ve açılış güncelleme tercihleri; ses seçimi.
- Ctrl+1 açık pencereden onayla Ana Sayfaya döner; çalışan işlemi kesmez.
- Genel Bakış adı Ana Sayfa oldu; konum seçme oku yenilendi.
- WhatsApp ve X düğmeleri eklendi. Hesaplar henüz tanımlanmadığından Yakında bilgisi gösterir.
- Satış penceresi daraltıldı; gereksiz sunucu doğrulama yazısı kaldırıldı. Stok miktar kontrolleri büyük −/+ düğmelerini kullanır.

## Ek işlevler
1. Stok tablosunda ürün adı ve barkodla anlık arama.
2. Konuma göre stok filtresi.
3. Satılabilir, tükenmiş ve ayrılmış stok filtreleri.
4. Yalnız görünen stokları CSV aktarma.
5. Seçili barkodu panoya kopyalama.
6. Tablo satırından işlem ürününü ve konumunu seçme.
7. Filtrelenmiş kayıt sayısı ve satılabilir adet toplamı.
8. Kasa F2 barkoda odaklanma ve F8 satış düğmesi kısayolları.
9. İşlem pencerelerinde F5 ile yenileme.
10. Bu oturumun bildirim geçmişi ve temizleme.
11. Parola, anahtar ve müşteri verisi içermeyen tanılama raporu.
12. Ürün adı kesilirse üzerine gelerek tam adını görme.

0.24.2 üzerinden yeni SQL gerekmez. Arayüz ayarları yerel olarak korunur. Cloud ve yerel kullanıcı parolaları ayrı kavramlardır; ekran kilidi yerel kullanıcı parolasını kullanır.

Kurulum ve güncelleyici sürümleri eşitlendi. Yayın, aynı kaynak sürümünün istemci/sunucu testleri ve açık uygulamada Windows kurulum/yeniden açılma kontrolünden sonra etkinleştirilir.
