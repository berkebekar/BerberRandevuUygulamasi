# CLAUDE.md ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Single Barber Appointment System
# Cursor'un Ana Referans DosyasÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±

> Bu dosyayÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± her prompt'ta oku. Buradaki kararlar deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸tirilemez.
> EÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸er bir ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ey bu dosyayla ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§eliÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸iyorsa, DUR ve kullanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±cÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ya sor.

---

## NASIL DAVRANACAKSIN ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â TEMEL KURALLAR

Bu bir **production uygulamasÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±dÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r.** Demo deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸il, tutorial deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸il, oyuncak proje deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸il.

### ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“ncelik sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rasÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± (her zaman bu sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rayla dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼n)
1. DoÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸ruluk ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â yanlÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§alÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸an kod yoktur
2. Veri tutarlÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±lÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â sessiz veri bozulmasÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± kabul edilemez
3. Race condition gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼venliÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸i ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶zellikle booking iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸lemlerinde
4. Sadelik ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â akÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±llÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼nen ama riskli ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶zÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼m yerine sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±kÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±cÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± ama kanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±tlanmÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶zÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼m
5. SÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±fÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r sessiz hata ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â her hata loglanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r veya kullanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±cÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ya dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶ner

### Kod yazmadan ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶nce
- Belirsiz bir ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ey varsa ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ **DUR, sor**
- Bir karar ileride sistemi bozabilecekse ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ **uyar, sonra uygula**
- Bu dosyayla ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§eliÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸en bir istek gelirse ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ **reddet, aÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±kla**

### Her zaman yap
- Her modÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼lÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ kendi klasÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼nde tut (router / service / schema ayrÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± dosyalar)
- Her DB sorgusuna tenant_id filtresi ekle ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â istisnasÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±z
- Business rule'larÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± API (service) katmanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±nda kontrol et, frontend'e gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼venme
- Hata mesajlarÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± anlamlÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± olsun ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â "something went wrong" kabul edilmez
- Her kritik iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸lemi logla

### Asla yapma
- Frontend validation'a gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼venme
- Plain text ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ifre veya OTP saklama
- Tenant filtresi olmadan DB sorgusu ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§alÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸tÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rma
- Booking iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸lemini transaction dÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±nda yapma
- MVP dÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶zellik kodlama ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â sadece yorum olarak belirt

### Kod ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼retim sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rasÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± (her adÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±mda bu sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rayÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± izle)
1. Veri modelini/schema'yÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± yaz
2. Service katmanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±nÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± yaz (business logic)
3. Router'ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± yaz (HTTP katmanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±)
4. Test yaz
5. ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¡alÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸tÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r, geÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§

---

## YORUM SATIRI KURALLARI ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â KESÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°NLÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°KLE UYULACAK

Bu proje aynÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± zamanda bir ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶ÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸renme sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼recidir.
YazdÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±n her kodun yanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±na TÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼rkÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§e yorum satÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± ekle.

### Ne zaman yorum yazacaksÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±n
- Her dosyanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±n en ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼stÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ne: bu dosya ne iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸e yarar, sistemdeki rolÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ nedir
- Her class/fonksiyon tanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±mÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±nÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±n ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼stÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ne: ne yapar, neden var, ne dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶ner
- Her ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶nemli satÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±n yanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±na veya ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼stÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ne: bu satÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r ne yapÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yor, neden bu ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ekilde yazÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ldÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±
- Her if/else bloÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸una: bu koÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ul neden kontrol ediliyor
- Her DB sorgusuna: ne arÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yor, neden bu ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ekilde yazÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ldÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±
- Her hata fÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rlatÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±lan yere: bu hata neden fÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rlatÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±lÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yor, ne anlama geliyor
- Her config veya sabit deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸ere: bu deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸er ne anlama geliyor, neden bu seÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ildi

### Yorum tonu
- Sade ve anlaÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±lÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r TÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼rkÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§e
- Sadece "ne yapÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yor" deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸il, "neden bÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶yle yapÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yor" da aÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±kla
- Teknik terim kullanmak zorundaysan yanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±na parantez iÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§inde aÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±kla
  ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“rnek: # transaction baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸latÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yoruz (transaction: ya hepsi olur ya hiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§biri)

### DoÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸ru yorum ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶rneÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸i ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â bÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶yle yaz

```python
# =============================================
# booking/service.py
# Randevu oluÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸turma ve yÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶netim iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸lemleri.
# Bu dosya sistemin en kritik parÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§asÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±dÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â
# ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ift randevu oluÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸masÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±nÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± buradaki kurallar engeller.
# =============================================

async def create_booking(db, tenant_id, user_id, slot_time):
    # Bu fonksiyon bir randevu oluÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸turur.
    # 'async' kullanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yoruz ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼nkÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ veritabanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸lemi bitene kadar
    # sunucunun baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ka isteklere de bakabilmesi gerekiyor.

    async with db.begin() as transaction:
        # transaction baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸latÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±yoruz.
        # transaction = ya hepsi baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸arÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±lÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± olur, ya hiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§biri olmaz.
        # ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“rnek: randevu yazÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±lÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rken elektrik giderse yarÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±m kayÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±t oluÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸maz.

        existing = await db.execute(
            select(Booking)
            .where(Booking.slot_time == slot_time)
            .with_for_update()  # bu satÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r o kaydÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± kilitler ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â
                                # aynÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± anda baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ka biri de aynÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± slotu almaya
                                # ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§alÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rsa sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rada bekletilir, ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ift randevu olmaz
        )

        if existing.scalar():
            raise HTTPException(409)
            # 409 = "Conflict" (ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§akÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ma) HTTP kodu.
            # Slot dolu olduÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸u iÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§in iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸lemi durduruyoruz.
```

### YanlÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ yorum ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶rneÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸i ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â bÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶yle yazma

```python
async def create_booking(db, tenant_id, user_id, slot_time):
    # randevu oluÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸tur
    async with db.begin():
        existing = await db.execute(...)
        if existing.scalar():
            raise HTTPException(409)  # hata
```

Bu kurala her dosyada, her fonksiyonda istisnasÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±z uy.

---

---

## PROJE NE?

Tek bir berber iÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§in mobil uyumlu web tabanlÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± randevu sistemi.
Gelecekte SaaS'a dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶nÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ebilecek ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ekilde tasarlanmÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸.

---

## TEK SATIR KURAL

Bir ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶zellik MVP olarak bu dosyada aÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±kÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§a belirtilmemiÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸se ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ KODLAMA **YOK**. Sadece yorum satÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± olarak dokÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼mante et.

---

## ASLA ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°HLAL EDÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°LMEYECEK KISITLAR

```
- Berber sayÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±      : TAM OLARAK 1
- AynÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± anda mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸teri  : TAM OLARAK 1
- Slot baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±na randevu: TAM OLARAK 1
- GÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼nlÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼k mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸teri     : 1 mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸teri = max 3 randevu/gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼n
- ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“deme              : YOK
- ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¡oklu berber       : YOK
- Otomatik slot kaydÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rma : YOK
- Timezone           : SADECE Europe/Istanbul (UTC+3, sabit)
- Native mobil app   : YOK
```

---

## TECH STACK

```
Backend  : FastAPI (Python 3.12+)
Database : PostgreSQL 15+
ORM      : SQLAlchemy (async) + Alembic (migrations)
Frontend : Next.js 14 (App Router)
SMS      : Twilio (MVP) ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â config'den deÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸tirilebilir
Deploy   : Platformdan bagimsiz (ornek: Vercel + Neon)
```

---

## PROJE KLASÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“R YAPISI

```
/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ backend/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ app/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ main.py
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ core/          # config, security, db baÃƒÆ’Ã¢â‚¬ÂÃƒâ€¦Ã‚Â¸lantÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ middleware/    # tenant resolver
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ modules/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ auth/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ user/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ admin/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ tenant/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ schedule/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ booking/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ notification/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ models/        # SQLAlchemy modelleri
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ alembic/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ tests/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ requirements.txt
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ frontend/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ app/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ (customer)/    # MÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸teri akÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ admin/         # Admin paneli
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ components/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ docs/
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ CLAUDE.md          # Bu dosya
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ TASKS.md           # ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°lerleme takibi
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡   ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ ARCHITECTURE.md    # Mimari kararlar
ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ docker-compose.yml     # Local geliÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸tirme
```

---

## KULLANICI ROLLERÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°

### Admin (Berber)
- Sistemde TAM OLARAK 1 admin vardÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±r
- **KayÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±t:** email + telefon + ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ifre (tek seferlik)
- **GiriÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ Yol 1:** telefon ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ SMS OTP
- **GiriÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ Yol 2:** email + ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ifre
- Session: HTTP-only cookie

### User (MÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸teri)
- **GiriÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸/KayÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±t:** telefon ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ SMS OTP (tek akÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸)
- Session: HTTP-only cookie
- Cookie geÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§erliyse OTP istenmez

---

## VERÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°TABANI MODELLERÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°

### Tenant
```
id            UUID PK
subdomain     VARCHAR UNIQUE NOT NULL
name          VARCHAR NOT NULL
is_active     BOOLEAN DEFAULT true
created_at    TIMESTAMPTZ NOT NULL
```

### Admin
```
id            UUID PK
tenant_id     UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢Tenant  [UNIQUE ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â tenant baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±na 1 admin]
email         VARCHAR UNIQUE NOT NULL
phone         VARCHAR UNIQUE NOT NULL
password_hash VARCHAR NOT NULL
created_at    TIMESTAMPTZ NOT NULL
```

### User
```
id            UUID PK
tenant_id     UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢Tenant
phone         VARCHAR NOT NULL
first_name    VARCHAR NOT NULL
last_name     VARCHAR NOT NULL
created_at    TIMESTAMPTZ NOT NULL
[UNIQUE: tenant_id + phone]
```

### BarberProfile
```
id                    UUID PK
tenant_id             UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢Tenant  [UNIQUE]
slot_duration_minutes INTEGER NOT NULL  -- 30 | 40 | 60
work_start_time       TIME NOT NULL     -- ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶rn: 09:00
work_end_time         TIME NOT NULL     -- ornek: 19:00
weekly_closed_days    INTEGER[] NOT NULL DEFAULT {}
max_booking_days_ahead INTEGER NOT NULL DEFAULT 14  -- 1..60 (bugun + N. gun dahil)
updated_at            TIMESTAMPTZ NOT NULL
```

### DayOverride
```
id               UUID PK
tenant_id        UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢Tenant
date             DATE NOT NULL
is_closed        BOOLEAN DEFAULT false
work_start_time  TIME NULLABLE
work_end_time    TIME NULLABLE
[UNIQUE: tenant_id + date]
```

### SlotBlock
```
id          UUID PK
tenant_id   UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢Tenant
blocked_at  TIMESTAMPTZ NOT NULL  -- TR timezone
reason      VARCHAR NULLABLE
created_at  TIMESTAMPTZ NOT NULL
[UNIQUE: tenant_id + blocked_at]
```

### Booking
```
id           UUID PK
tenant_id    UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢Tenant
user_id      UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢User
slot_time    TIMESTAMPTZ NOT NULL  -- TR timezone
status       ENUM: confirmed | cancelled
cancelled_by ENUM NULLABLE: admin | user
created_at   TIMESTAMPTZ NOT NULL
updated_at   TIMESTAMPTZ NOT NULL

[UNIQUE: tenant_id + slot_time]        WHERE status='confirmed'
[UNIQUE: tenant_id + user_id + date]   YOK (MVP kurali: ayni gunde max 3 randevu API katmaninda kontrol edilir)
```

### OTPRecord
```
id            UUID PK
phone         VARCHAR NOT NULL
code_hash     VARCHAR NOT NULL  -- bcrypt, plain text SAKLANMAZ
role          ENUM: user | admin
expires_at    TIMESTAMPTZ NOT NULL  -- +5 dakika
is_used       BOOLEAN DEFAULT false
attempt_count INTEGER DEFAULT 0
created_at    TIMESTAMPTZ NOT NULL
```

### NotificationLog
```
id                UUID PK
tenant_id         UUID FKÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢Tenant
recipient_phone   VARCHAR NOT NULL
message_type      ENUM: otp | booking_created | booking_cancelled
status            ENUM: sent | failed | pending
provider_response JSONB NULLABLE
created_at        TIMESTAMPTZ NOT NULL
```

---

## API ENDPOINT LÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°STESÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°

TÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼m endpoint'ler: `GET|POST|PUT|DELETE /api/v1/...`
Tenant her request'te subdomain'den resolve edilir.

### Auth
```
POST /auth/user/send-otp          # Public
POST /auth/user/verify-otp        # Public
POST /auth/admin/register         # Public (tek seferlik)
POST /auth/admin/login/otp        # Public
POST /auth/admin/login/password   # Public
POST /auth/logout                 # Cookie
```

### Slots
```
GET /slots?date=YYYY-MM-DD        # User | Admin
GET /slots/week?start=YYYY-MM-DD  # User | Admin
```

### Booking
```
POST   /bookings                  # User ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â atomik iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸lem
GET    /bookings/my               # User
GET    /bookings?date=YYYY-MM-DD  # Admin
DELETE /bookings/{id}             # Admin ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â iptal
```

### Admin Panel
```
GET  /admin/dashboard?date=YYYY-MM-DD   # Admin
GET  /admin/schedule/settings           # Admin
PUT  /admin/schedule/settings           # Admin
POST /admin/schedule/override           # Admin
POST /admin/slots/block                 # Admin
DEL  /admin/slots/block/{id}            # Admin
POST /admin/bookings                    # Admin ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â manuel randevu
```

---

## KRÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°TÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°K BUSINESS RULES

### Randevu OluÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸turma ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ATOMIK
```sql
BEGIN
  SELECT ... FROM bookings
    WHERE tenant_id=? AND slot_time=? AND status='confirmed'
    FOR UPDATE              -- kilitle
  ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ Varsa: ROLLBACK ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ 409

  SELECT ... FROM slot_blocks
    WHERE tenant_id=? AND blocked_at=?
    FOR UPDATE
  ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ Varsa: ROLLBACK ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ 409

  INSERT INTO bookings (...)
COMMIT
```

### OTP KurallarÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±
- SÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼re: 5 dakika
- Max deneme: 3 (sonra is_used=true, geÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ersiz)
- Rate limit: aynÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± numaraya 60sn'de 1 kod
- Hash: bcrypt ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â plain text asla saklanmaz

### Slot Hesaplama
- Slotlar DB'de saklanmaz, her seferinde hesaplanir
- Kaynak: BarberProfile -> DayOverride (varsa) -> SlotBlock -> Booking
- Gecmis slotlar listelenmez
- Ileri tarih limiti tenant bazlidir: `max_booking_days_ahead`
- Varsayilan/Fallback limit: 14
- Kural: bugun + N. gun DAHIL (ornek: N=14 ise bugun + 14 dahil)

### Ileri Tarih Limiti Kurali
- Admin ayarindan secilir: `max_booking_days_ahead` (1-60)
- Ayar kaydi yoksa 14 kabul edilir
- Hem admin hem user "Tarih Secin" listesi bu degerle uretilir
- `too_far_in_future` hatasi dinamik limite gore doner

---

## TENANT MIDDLEWARE

Her request ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸u sÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rayÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± izler:
```
1. Host header ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ subdomain parse
2. DB'de tenant ara
3. Bulunamazsa ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ 404
4. Bulunursa ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€Â¢ request.state.tenant_id set et
5. Devam et
```

**HiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§bir DB sorgusu tenant_id filtresi olmadan ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§alÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸maz.**

---

## BÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°LDÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°RÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°MLER (MVP)

MVP'de SMS sadece OTP iÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§indir.

SMS gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶nderimi her zaman:
- async olmalÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± (background task)
- non-blocking olmalÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±
- hata toleranslÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± olmalÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± (uygulama ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶kmemeli)
- NotificationLog'a yazÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±lmalÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± (baÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸arÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± veya hata)

---

## GÃƒÆ’Ã†â€™Ãƒâ€¦Ã¢â‚¬Å“VENLÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°K KURALLARI

```
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ HTTP-only cookie ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â JS eriÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸imi yok
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ OTP: 3 hatalÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± denemede iptal
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ OTP rate limit: 60sn/numara
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Cookie domain: spesifik subdomain (wildcard .app.com YASAK)
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ TÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼m validation API'de ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â frontend'e gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼venilmez
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ bcrypt: ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸ifre ve OTP hash iÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§in
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Parameterized queries ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â SQL injection yok
ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Tenant izolasyonu: her sorguda tenant_id zorunlu
```

---

## MVP DIÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚ÂI ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â KODLAMA (Sadece DokÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼mante Et)

```
- Randevu oluÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸turuldu SMS'i (mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸teriye)
- KullanÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±cÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â± randevu iptali
- ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°ptal edildi SMS'i (admin'e)
- Ciro takibi (para)
- ÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â°statistik dashboard
- Tema ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶zelleÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸tirme
- SaaS ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¶deme modeli
- Gecikme bildirimi
- Otomatik slot kaydÃƒÆ’Ã¢â‚¬ÂÃƒâ€šÃ‚Â±rma
- CRM mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸teri profilleri
```

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=
DATABASE_URL_SYNC=     # Alembic migration icin sync URL (opsiyonel; yoksa DATABASE_URL kullanilir)
SECRET_KEY=          # min 32 char random string
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
APP_DOMAIN=          # ornek: app.com
ALLOWED_SUBDOMAINS=  # virgulle ayrilmis liste
ENV=                 # development | production
```

---

*Son gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¼ncelleme: v1.0 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â MVP*

