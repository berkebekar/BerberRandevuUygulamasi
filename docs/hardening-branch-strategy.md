# Hardening Branch Strategy

Bu repo icin profesyonellestirme islemleri `hardening/*` dallarinda yurur.

## Hedef

- Urun gelistirme degisiklikleri ile hardening degisikliklerini ayirmak
- Davranis regressionsuz refactor ve kalite kapilari eklemek

## Kurallar

1. Hardening PR'lari davranis degistirmez.
2. API sozlesmesi degisirse `docs/api-contract.snapshot.md` ayni PR'da guncellenir.
3. PR merge oncesi CI tum zorunlu checkleri gecmelidir.
