# WhatsApp Test Numarasi Runbook

Bu dokuman Meta'nin verdigi WhatsApp Cloud API test numarasini bir tenant'a baglayip bot akisini dogrulamak icin kullanilir.

## 1. Meta'dan Bilgileri Al

Meta Developer panelinde WhatsApp API Setup ekranindan su bilgileri al:

- Temporary access token
- Test phone number ID
- WhatsApp Business Account ID
- Test phone display number

Test numarasi sadece Meta panelinde test recipient olarak eklenen telefonlarla konusur. Kendi telefon numarani recipient olarak ekleyip dogrula.

## 2. Backend Ortami

VPS backend env dosyasinda su alanlar dolu olmali:

```env
WA_ACCESS_TOKEN=meta_temporary_or_system_user_token
WA_VERIFY_TOKEN=meta_webhook_verify_token
```

`WA_VERIFY_TOKEN` Meta webhook ekranina yazilan verify token ile ayni olmalidir.

Temporary token sureli oldugu icin test aniden durursa ilk kontrol edilecek yer `WA_ACCESS_TOKEN` olur.

## 3. Meta Webhook

Meta Developer panelinde WhatsApp webhook ayari:

```text
Callback URL: https://api.bbsoft.com.tr/api/v1/whatsapp/webhook
Verify token: VPS WA_VERIFY_TOKEN degeri
Subscribed field: messages
```

Meta "Verify and Save" basarili donmeli.

## 4. Superadmin Tenant Baglantisi

Superadmin tenant detayinda WhatsApp Coexistence bolumunu doldur:

```text
Phone Number ID: Meta test phone number ID
WABA ID: Meta WABA ID
Display Phone: Meta test numarasi
Status: connected
Bot varsayilan acik: isaretli
```

`connected` secilebilmesi icin `Phone Number ID` zorunludur. Bu kasitli bir guvenlik kuralidir; disconnected/pending tenant bot cevaplamaz.

## 5. Hizli Test Senaryolari

Kendi WhatsApp hesabindan Meta test numarasina yaz:

- `merhaba` -> ana menu gelmeli.
- `/bot` veya `/menu` -> ana menu gelmeli.
- `randevu var mi` -> ana menu veya randevu akisi tetiklenmeli.
- `Randevu Al` -> tarih secimi gelmeli.
- Tarih secip 15 dakika bekle -> sonraki mesajda akisin sifirlanmasi beklenir.
- `{BerberAdi} ile Konus` -> bot 3 saat susar; `/bot` yazinca geri acilir.
- Superadmin veya berber panelinden botu kapat -> sohbet botu cevap vermemeli.

## 6. Hata Bakilacak Yerler

Superadmin `WhatsApp Bot` ekraninda:

- Health: token var mi, connected tenant sayisi, son 24 saat hata sayisi.
- Error logs:
  - `unknown_phone_number_id`: Meta'dan gelen phone number ID hicbir connected tenant'a bagli degil.
  - `config_error`: `WA_ACCESS_TOKEN` yok.
  - `message_status_error`: Meta mesaj status webhook'u mesaj gonderim hatasi bildirdi.
  - `webhook_error`: Webhook parse/handler tarafinda beklenmeyen hata.

## 7. Test Numarasinin Sinirlari

Bu test gercek coexistence testi degildir. Sunlari dogrular:

- Webhook geliyor mu?
- Tenant `phone_number_id` ile dogru cozuluyor mu?
- Bot randevu ve menu akislari calisiyor mu?
- Panelden bot ac/kapat etkili mi?

Sunlari dogrulamaz:

- Berber WhatsApp Business App'ten manuel cevap yazinca webhook dusuyor mu?
- Bot mesajlari berberin Business App ekraninda nasil gorunuyor?
- Gercek numarada unread/bildirim davranisi nasil?

Bu ucu ancak Meta coexistence gercek numarada acilinca test edilebilir.
