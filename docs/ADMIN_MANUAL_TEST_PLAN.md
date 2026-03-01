# Admin Manual Test Plan (Hizli)

Bu dokuman, admin akisinin hizli manuel dogrulamasi icin adim adim rehberdir.

## 1. Ortam Hazirlik

1. Backend ayakta olmali (FastAPI).
2. Frontend ayakta olmali (Next.js).
3. Tenant host dogru olmali (subdomain/host header).
4. En az bir admin kaydi olmali.
5. Test gunu icin schedule ayarlari tanimli olmali:
   - Calisma saatleri
   - Slot suresi

Beklenen sonuc:
- `/admin/login` acilir.
- API cagrilari 404 tenant hatasi vermeden islenir.

## 2. Login Akislari

### 2.1 SMS ile giris

1. `/admin/login` ac.
2. `SMS ile Giris` sekmesini sec.
3. Telefon gir, `Kod Gonder`.
4. OTP gir.

Beklenen sonuc:
- Basarili dogrulamada `/admin` yonlendirmesi.
- Cookie olarak `admin_session` set edilir.

### 2.2 Sifre ile giris

1. `/admin/login` ac.
2. `Sifre ile Giris` sekmesini sec.
3. Email + sifre gir, `Giris Yap`.

Beklenen sonuc:
- Basarili giriste `/admin` acilir.
- Hatali bilgide anlamli hata mesaji gorunur.

## 3. Dashboard Yukleme

1. `/admin` sayfasini ac.
2. Varsayilan tarihin bugun oldugunu kontrol et.
3. Ustte randevu sayacini kontrol et.
4. Randevu listesinin saat + musteri adini gosterdigini kontrol et.

Beklenen sonuc:
- Sayfa hata vermeden yuklenir.
- Tarih secince dashboard verisi yenilenir.

## 4. Ayarlar Kaydetme

1. `Ayarlar` butonuyla `/admin/settings` sayfasina git.
2. Baslangic/bitis saatini degistir.
3. Slot suresini (30/40/60) sec.
4. `Kaydet` butonuna bas.

Beklenen sonuc:
- Basarili kayit mesaji gorunur.
- Tekrar acinca yeni degerler yuklenir.

## 5. Slot Kapat / Ac (Onay Sheet ile)

1. `/admin` dashboard'a don.
2. `Slot Yonetimi` alaninda `available` bir slota tikla.
3. Acilan onay sheet'inde:
   - `Vazgec` secenegini test et.
   - Sonra tekrar tiklayip `Onayla` sec.
4. `blocked` slota tiklayip acma akisinda ayni adimlari test et.

Beklenen sonuc:
- Tiklama aninda API cagrisi gitmez, once onay sheet acilir.
- `Vazgec` ile API cagrisi olmaz.
- `Onayla` ile tek API cagrisi gider.
- Islem sonrasi basari mesaji gorunur ve grid guncellenir.

## 6. Manuel Randevu Ekleme

### 6.1 Kayitli telefon

1. `+ Randevu Ekle` ac.
2. Kayitli bir telefon gir.
3. Uygun saat sec.
4. `Randevu Olustur`.

Beklenen sonuc:
- Islem basarili olur.
- Randevu listesi ve sayaç guncellenir.

### 6.2 Kayitsiz telefon

1. Kayitsiz telefonla tekrar dene.
2. Ad/soyad bos birakip gonder.
3. Sonra ad/soyad doldurup tekrar gonder.

Beklenen sonuc:
- Ilk denemede `missing_user_info` benzeri hata.
- Ad/soyad ile ikinci denemede basarili olusturma.

## 7. Randevu Iptal (Onay Sheet ile)

1. Dashboard listesinden iptal edilmemis bir randevuda `Iptal Et` tikla.
2. Onay sheet'te once `Vazgec`, sonra `Onayla` test et.

Beklenen sonuc:
- `Vazgec`te API cagrisi olmaz.
- `Onayla`da iptal cagrisi gider.
- Satir `Iptal edildi` gorunumune gecis yapar.

## 8. Hata Durumlari (Hizli)

1. `401`: Cookie olmadan `/admin` ac.
2. `409`: Dolu slota kapatma dene.
3. `422`: Manuel randevuda kayitsiz telefon + eksik ad/soyad.

Beklenen sonuc:
- Hatalar anlamli mesajla UI'da gorunur.

## 9. Bitti Kriteri

Asagidaki tum maddeler saglanmis olmali:

1. Login (SMS + sifre) calisiyor.
2. Dashboard ve ayarlar ekranlari calisiyor.
3. Slot kapat/ac onay sheet ile dogru calisiyor.
4. Manuel randevu ekleme (kayitli/kayitsiz) calisiyor.
5. Randevu iptal onay sheet ile calisiyor.
6. Kritik hata durumlari anlamli mesajla gorunuyor.
