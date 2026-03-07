# BerberRandevu - Polling, Ölçeklenebilirlik ve Performans Notu

## 1) Problem Özeti
Projede admin ve user panellerinde canlılık için polling kullanılıyor.

Aktif polling bölgeleri:
- User panel:
  - `Mevcut Randevunuz`
  - `MUSAIT SAATLER`
- Admin panel:
  - `Bugunun Randevulari`
  - `Randevu Yontemi` (slot verisi)

Semptom:
- Veri güncelleniyor, ancak yoğun yükte gecikmeler artıyor.
- Özellikle çok yüksek eşzamanlı kullanıcıda timeout/hata görülüyor.

## 2) Yapılan Ölçüm (Bot Load Test)
Bu repo içinde bot tabanlı test scripti eklendi:
- `backend/scripts/load_test.py`

Script ne yapıyor:
- Test tenant + profile + test user’ları hazırlar.
- Eşzamanlı user botlarıyla aşağıdaki endpointleri çağırır:
  - `GET /api/v1/bookings/my`
  - `GET /api/v1/slots?date=YYYY-MM-DD`
- Başarı oranı, throughput, p95/p99 latency raporlar.

### Ölçüm Sonuçları

#### Senaryo A
- Parametre: `users=100`, `loops=5`, `concurrency=100`, `mode=mixed`
- Toplam istek: `1000`
- Başarılı: `1000`
- Başarısız: `0`
- Throughput: `58.01 req/s`
- Ortalama latency: `1373.75 ms`
- p95: `3683.85 ms`
- p99: `4717.74 ms`

Yorum:
- Sistem ayakta ve hatasız, ancak latency yüksek.

#### Senaryo B
- Parametre: `users=1000`, `loops=1`, `concurrency=300`, `mode=mixed`
- Toplam istek: `2000`
- Başarılı: `1923`
- Başarısız: `77` (çoğu timeout benzeri, status `0`)
- Throughput: `35.03 req/s`
- Ortalama latency: `7273.51 ms`
- p95: `14663.06 ms`
- p99: `18887.84 ms`

Yorum:
- Sistem tamamen çökmedi ama konfor seviyesi düştü.
- Çok yüksek eşzamanlılıkta kullanıcı deneyimi zayıflıyor.

## 3) Ana Riskler
1. Polling trafiği kullanıcı sayısıyla lineer artıyor.
2. Birden fazla endpoint’in aynı sekmede ayrı ayrı poll edilmesi backend/DB yükünü büyütüyor.
3. 5 saniye gibi agresif interval’ler 15 saniyeye göre yaklaşık 3x istek üretir.
4. Yoğun anlarda p95/p99 latency kritik seviyeye çıkıyor.

## 4) Kısa Vadede (Hızlı Kazanç) Ne Yapılabilir?
1. Polling interval’ini 15s veya daha yukarıda tut.
2. Adaptive polling uygula:
   - Kullanıcı etkileşimi yoksa 30–60s
   - Etkileşim/aksiyon sonrası kısa süre 10–15s
3. Sessiz refresh (loading flicker olmadan) kullan.
4. Focus/visibility tabanlı refresh (arka sekmede gereksiz poll yok).
5. Poll edilen endpoint sayısını azalt (mümkünse birleştir).

## 5) Orta Vadede Ne Yapılabilir?
1. Dashboard verisini birleştiren hafif endpoint:
   - Tek çağrıda gerekli özet + liste
2. Kısa TTL cache (2–5s):
   - `slots` ve `dashboard` sonuçları
3. ETag/If-None-Match ile değişmeyen veri için 304.
4. DB sorgu optimizasyonu:
   - `EXPLAIN ANALYZE`
   - uygun index doğrulaması (`tenant_id`, `slot_time`, `status`, `user_id`)

## 6) Uzun Vadede En İyi Mimari
Polling yerine event-driven yaklaşım:
- WebSocket veya SSE
- `booking_changed`, `slot_changed` gibi event publish
- UI sadece değiştiğinde güncellenir

Kazanç:
- Gereksiz istekler ciddi azalır
- Yüksek kullanıcı altında daha stabil davranış

## 7) Kapasite Yorumu (İş Diline Uygun)
- “Yüzlerce aktif kullanıcıyı kaldırır ama gecikmeler artar.”
- “1000 eşzamanlı kullanıcı testinde sistem tamamen kapanmadı fakat bazı istekler timeout oldu ve bekleme süreleri ciddi uzadı.”
- “Gerçek büyüme için polling optimizasyonu + cache + endpoint sadeleştirme + gerekirse yatay ölçek şart.”

## 8) Başka Agent’a Verilecek Net Görev Listesi
1. Polling envanteri çıkar (sayfa bazlı endpoint sayısı, interval, tetikleyiciler).
2. `dashboard` ve `slots` için hedef RPS/latency belirle (SLO tanımı).
3. Kısa TTL cache prototipi uygula ve ölç.
4. Tek endpoint ile dashboard toplama PoC hazırla.
5. `EXPLAIN ANALYZE` ile ilk 3 yavaş sorguyu optimize et.
6. 100/300/1000 kullanıcı yük testini aynı script ile tekrar al ve kıyas raporu çıkar.

## 9) Çalıştırma Notu (Load Test)
Örnek:

```powershell
cd backend
.venv\Scripts\python.exe scripts\load_test.py --users 100 --loops 5 --concurrency 100 --mode mixed --secret-key dev_secret_key_min_32_chars_placeholder
.venv\Scripts\python.exe scripts\load_test.py --users 1000 --loops 1 --concurrency 300 --mode mixed --secret-key dev_secret_key_min_32_chars_placeholder
```

Not:
- `--secret-key` backend ile aynı olmalı.
- Test local makinede alındığı için sonuçlar production için birebir değil, yön göstericidir.
