# WhatsApp Coexistence Bot Plan

Bu dokuman, WhatsApp Business App + Cloud API Coexistence modeline gecis icin urun kurallarini ve uygulama planini toplar.

## Hedef

Her tenant kendi WhatsApp Business numarasini kullanmaya devam eder. Ayni numarada arka planda Cloud API botu calisir. Berber normal WhatsApp Business App aliskanligini korur; bot sadece randevu alma ve temel randevu yonlendirmelerini hizlandirir.

Ana hedefler:

- Bir WhatsApp numarasi bir tenant'a aittir.
- Musteri hangi berberin numarasina yazarsa bot o tenant icin calisir.
- Bot kisi bazli acilip kapanir; Mehmet icin bot susarsa Ayse etkilenmez.
- Berber manuel cevap verdiginde bot ilgili kisi icin susar.
- Bot mumkun oldugunca kisa, net ve web sitesine yonlendiren cevaplar verir.

## Mevcut Durumdan Fark

Mevcut sistemde tek platform WhatsApp numarasi vardir. Gelen kullanici once tenant secimi veya telefon numarasi eslesmesi ile ilgili isletmeye baglanir.

Yeni modelde tenant cozumu su sekilde olur:

```text
webhook.metadata.phone_number_id -> tenant.whatsapp_phone_number_id -> tenant
```

Bu nedenle isletme secim akisi buyuk olcude kalkar.

## Temel Kavramlar

`tenant`: WhatsApp numarasinin sahibi olan berber/isletme.

`conversation`: Bir tenant ile bir kisi arasindaki WhatsApp konusmasi.

`bot state`: Konusmanin bot tarafinda hangi modda oldugu.

`human handoff`: Berberin konusmayi devralmasi ve botun ilgili kisi icin susmasi.

## Konusma Modlari

Her conversation icin ayri mod tutulur:

- `idle`: Ana menu gosterilebilir.
- `booking_flow`: Randevu alma akisi devam ediyor.
- `human_requested`: Kullanici berberle konusmak istedi, bot sustu.
- `human_handoff`: Berber manuel cevap verdi, bot sustu.
- `muted`: Berberin botun konusmayacagi kisiler listesinde; otomatik bot cevabi yok.

## Sure Kurallari

### Randevu Akisi Hafizasi

Yarim kalan randevu akisi 15 dakika hatirlanir.

Ornek:

1. Mehmet saat 10:00'da `Randevu Al` secer.
2. Gun secer ama saat secmeden cikar.
3. 10:10'da yazarsa bot kaldigi yerden devam eder.
4. 10:20'de yazarsa onceki akis iptal edilmis sayilir ve ana menu gonderilir.

Bu sure icinde slot kilitlenmez. Slot sadece randevu onaylandiginda olusturulur. Bu arada baska biri ayni slota randevu alirsa onay aninda mevcut `slot_taken` hata mesaji doner ve kullanicidan baska saat secmesi istenir.

### Berber Devralma Suresi

Berber manuel cevap verdiginde bot ilgili conversation icin 3 saat susar.

Bu sure su durumlarda bozulur:

- Kullanici `/bot` yazar.
- Kullanici `/menu` yazar.
- Kullanici randevu niyeti iceren bir mesaj yazar.

### Berberin Ilk Mesaji

Berber bir kisiye ilk mesaj atan tarafsa bot hemen devreye girmez. 3 saat sessizlikten sonra kisi tekrar yazarsa bot yeniden devreye girebilir.

## Ana Menu

Ana menu uc secenekli olur:

- `Randevu Al`
- `Mevcut Randevularim`
- `{BerberAdi} ile Konusmak Istiyorum`

Buton metni WhatsApp limitlerine takilirsa berber adi kisaltilabilir.

`{BerberAdi} ile Konusmak Istiyorum` secilince bot su mesaji gonderir ve ilgili kisi icin susar:

```text
Tamam, {BerberAdi}'ye haber verildi. Benimle devam etmek isterseniz /bot yazabilirsiniz.
```

## Komutlar ve Tetikleyiciler

Baslangic komutlari:

- `/bot`
- `/menu`

Iki komut da botu ana menuye dondurur.

Baslangic dogal tetikleyici kelimeleri:

- `randevu`
- `saat`
- `musait`
- `müsait`
- `bosluk`
- `boşluk`
- `sira`
- `sıra`

Bu kelimelerin tek basina yazilmasi gerekmez. Cumle icinde gecmeleri yeterlidir.

Ornek tetikler:

- `randevu almak istiyorum`
- `bugun saat var mi`
- `yarin musait misiniz`
- `bosluk var mi`

Eslesme kelime siniri ile yapilmalidir. Yani `randevulaşalım` gibi alakasiz/ekli kelimeler veya baska kelimelerin icindeki parcalar dogrudan tetikleyici sayilmamalidir. Turkce karakterli ve karaktersiz yazimlar desteklenmelidir.

## Serbest Mesaj Davranisi

Conversation bot tarafinda aktifse ve kullanici menu disi serbest mesaj yazarsa ana menu tekrar gonderilir.

Human handoff aktifse bot normalde cevap vermez. Ancak `/bot`, `/menu` veya randevu niyeti iceren mesaj gelirse bot tekrar acilir.

## Botun Konusmayacagi Kisiler

Berber admin panelinde telefon numarasi bazli bir liste yonetir.

Bu listedeki kisilere bot otomatik cevap vermez.

Ancak listedeki kisi `/bot` veya `/menu` yazarsa bot acilabilir. Bu karar, berberin yakinlarina otomatik bot mesajlari gitmesini engellerken gerekirse botun manuel olarak cagirilmasina izin verir.

## Spam ve Tekrar Koruma

Bot hizli cevap vermelidir. Bu nedenle genel dusuk bir "5 dakikada 5 cevap" limiti kullanilmayacak.

Onun yerine yumusak tekrar korumasi kullanilir:

- Ayni kisiye ayni ana menu cok kisa sure icinde tekrar tekrar gonderilmez.
- Onerilen menu cooldown: 10-15 saniye.
- Cok anormal donguler icin teknik guvenlik limiti Redis uzerinden tutulur, fakat normal kullanicinin randevu akisini kesmeyecek kadar yuksek ayarlanir.

Amac spam'i engellemek, botu yavaslatmak degil.

## Performans Notlari

Webhook cevaplari hizli islenmelidir.

Onerilen yapi:

- `phone_number_id -> tenant_id` eslesmesi Redis cache.
- Conversation state Redis.
- Rate limit ve tekrar korumasi Redis.
- Bot ayarlari DB kaynakli, Redis cache destekli.
- Hata ve temas loglari ana akisi bozmayacak sekilde yazilmali.

Uzun vadede trafik artarsa webhook isleme ile mesaj gonderme ayrilabilir. Bunun icin background job veya queue dusunulebilir.

## Bildirimler

Bir kisi `{BerberAdi} ile Konusmak Istiyorum` secince asil beklenti WhatsApp Business App konusmasinin berber tarafinda gorunmesidir.

Web app uzerinden telefon bildirimleri teknik olarak PWA/Web Push ile mumkundur, ancak izin, cihaz ve tarayici kosullarina baglidir. V1 icin ana bildirim kanali WhatsApp Business App olmalidir. Web push daha sonra panel bildirimi olarak eklenebilir.

## Kritik Test

Asla unutulmamasi gereken test:

```text
Berber WhatsApp Business App'ten manuel mesaj yazinca Cloud API webhook'una event dusuyor mu?
```

Bu test sonucu human handoff mimarisini belirler.

Eger manuel mesaj webhook'a duserse:

- Bot otomatik olarak ilgili conversation icin `human_handoff` moduna gecer.
- Randevu akisi ortadaysa iptal edilir.
- Bot 3 saat susar.

Eger manuel mesaj webhook'a dusmezse:

- Bot berberin manuel devraldigini otomatik anlayamaz.
- Bu durumda human handoff yalnizca kullanici `{BerberAdi} ile Konusmak Istiyorum` sectiginde veya panelden kisi bazli bot susturma yapildiginda calisir.

## Randevu Kurallari

Mevcut merkezi booking servisi kullanilmaya devam eder.

Bot ozelinde ek kararlar:

- Randevu olusunca mevcut web linkli basari mesaji korunur.
- Basari mesajina `/menu` ile tekrar menuye donulebilecegi eklenir.
- Ayni gun icin birden fazla randevu alinacaksa bot ekstra onay sorar.
- Iptal ve randevu duzenleme ilk asamada web sitesine yonlendirilir.

## Ayarlanabilir Ozellikler

Ilk etapta tum berberlerde calisma mantigi ayni olur. Zamanla panelden acilip kapanabilecek ayarlar:

- Bot aktif/pasif.
- Otomatik ana menu aktif/pasif.
- Hatirlatma mesaji aktif/pasif.
- Iptal bildirimi aktif/pasif.
- Randevu degisiklik bildirimi aktif/pasif.
- Botun konusmayacagi kisiler listesi.
- Dogal tetikleyici kelimeler.
- Human handoff susma suresi.

## Uygulama Plani

### Faz 1: Meta ve Coexistence Testi

- Bir test tenant ve test WhatsApp Business App numarasi sec.
- Numarayi Cloud API Coexistence akisiyle bagla.
- Webhook'ta `phone_number_id` geldigini dogrula.
- Business App'ten manuel mesaj yazinca webhook event'i gelip gelmedigini test et.
- Bot mesajlari Business App tarafinda nasil gorunuyor, unread/bildirim davranisi nasil, kaydet.

### Faz 2: Veri Modeli

- Tenant'a WhatsApp baglanti alanlari ekle.
- Phone number ID icin benzersiz index ekle.
- Conversation bazli state/handoff yapisini tasarla.
- Botun konusmayacagi kisiler icin telefon numarasi bazli tablo ekle.
- Bot ayarlari icin tenant bazli ayar modeli planla.

### Faz 3: Webhook ve Tenant Cozumu

- Webhook'ta tenant'i `metadata.phone_number_id` ile bul.
- Eski tenant secim akisini yeni modelde devre disi birak veya fallback olarak sinirla.
- Mesaj gonderirken global `WA_PHONE_NUMBER_ID` yerine tenant'in phone number ID bilgisini kullan.

### Faz 4: Conversation Kurallari

- 15 dakikalik randevu akisi suresini uygula.
- 3 saatlik human handoff suresini uygula.
- `/bot`, `/menu` ve dogal randevu tetikleyicilerini ekle.
- Serbest mesajlarda ana menu davranisini ekle.
- Yumusak menu tekrar korumasini Redis ile ekle.

### Faz 5: Panel Ayarlari

- Berber admin paneline WhatsApp Bot Ayarlari ekrani ekle.
- Bot aktif/pasif ayari ekle.
- Botun konusmayacagi kisiler listesi ekle.
- Superadmin panelinde tenant WhatsApp baglanti durumunu goster.

### Faz 6: Test ve Guvenlik

- Handler/state unit testleri ekle.
- Webhook fixture testleri ekle.
- Randevu akisi timeout testleri ekle.
- Human handoff testleri ekle.
- Ayni slotu iki kisinin almaya calistigi durumda mevcut booking servisinin korumasi dogrulanir.

## Acik Sorular

- Business App manuel mesajlari webhook'a dusuyor mu?
- Business App tarafinda bot mesajlari okunmus/bildirim durumunu nasil etkiliyor?
- Coexistence baglantisi her tenant icin elle mi, daha sonra embedded signup ile mi yapilacak?
- 24 saat disi hatirlatma, iptal ve degisiklik mesajlari icin template stratejisi ne olacak?
- Web push/panel bildirimi V1'e dahil mi, sonraki faz mi?

## V1 Uygulama Kararlari

Bu fazda hedef backend + panel gecisini tamamlamak ve Meta Coexistence canli testi icin sistemi hazir hale getirmektir.

V1 kapsaminda uygulananlar:

- Tenant WhatsApp baglantisi `phone_number_id` uzerinden tutulur.
- Webhook tenant'i `metadata.phone_number_id -> tenant.whatsapp_phone_number_id` ile cozer.
- Bilinmeyen `phone_number_id` icin bot cevap vermez ve `unknown_phone_number_id` loglanir.
- Berber admin panelinde bot aktif/pasif kontrolu vardir.
- Superadmin tenant detayinda WhatsApp baglanti bilgilerini yonetir.
- Superadmin WhatsApp saglik ekraninda bagli tenant ve botu acik tenant sayilari gosterilir.
- Randevu akisi 15 dakika hatirlanir; slot kilitleme yapilmaz.
- `/bot`, `/menu` ve dogal randevu niyeti kelimeleri botu uyandirir.
- `{BerberAdi} ile Konus` secimi ilgili kisi icin 3 saatlik human handoff baslatir.
- Ayni gun ek randevu icin bot ekstra onay sorar.
- Randevu basari mesajinda mevcut web linki korunur ve `/menu` bilgisi eklenir.
- Tenant WhatsApp baglantisi yoksa OTP, hatirlatma, admin iptal ve admin degisiklik WhatsApp mesajlari atlanir.

V1 disinda birakilanlar:

- Botun konusmayacagi kisiler listesi.
- Web push veya panel push bildirimi.
- 24 saat disi template altyapisi.
- Tenant bazli access token saklama.
- Business App manuel mesajindan otomatik handoff. Bu kural Meta canli test sonucu dogrulanmadan kesinlestirilmeyecek.

Canli test sonucu beklenenler:

- Inbound musteri mesaji webhook'a dogru `phone_number_id` ile dusuyor mu?
- Business App'ten berber manuel mesaj yazinca webhook event'i geliyor mu?
- Bot mesajlari Business App tarafinda gorunuyor mu?
- Bildirim ve okunmamis sayaci berberin kullanimi icin kabul edilebilir mi?
