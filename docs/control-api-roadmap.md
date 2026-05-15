# Control API Roadmap

Control API, ana uygulama backend'i veya tenant frontend'i bozuldugunda superadmin panelinin
operasyon yapabilmesi icin ayri deploy edilecek kucuk servis olmalidir.

## V1 hedefleri

- Servis health: tenant frontend, superadmin frontend, backend, DB, Redis, WhatsApp, Coolify
- Coolify app status ve son deploy bilgisi
- Deploy retry
- Son basarili deploy'a rollback
- Coolify deploy loglarini goruntuleme
- Domain/SSL kontrolu
- Maintenance mode ac/kapat
- Tum operasyonlari audit log'a yazma

## Ilk mimari

- Host: `control-api.bbsoft.com.tr`
- Deploy: ayri Coolify app veya ayri lightweight container
- Auth: superadmin panelinden gelen guvenli token veya service-to-service secret
- Bagimlilik: ana uygulama backend'inden bagimsiz olmali
- Veri kaynagi: Coolify API, VPS local health endpointleri ve dis HTTP kontrolleri

## Superadmin entegrasyonu

Superadmin frontend ayri deploy edildikten sonra Monitoring/Ops sayfalari:

- Ana uygulama istatistikleri icin mevcut backend'i kullanabilir.
- Kriz/kurtarma aksiyonlari icin sadece Control API'ye baglanmalidir.

## Guvenlik notlari

- Deploy/rollback endpointleri rate limit ve audit log zorunlu olmalidir.
- Rollback gibi riskli islemler ikinci onay istemelidir.
- Token/env degerleri superadmin UI'da gosterilmemelidir.
- Control API public internete aciksa yalnizca HTTPS + auth ile erisilebilir olmalidir.
