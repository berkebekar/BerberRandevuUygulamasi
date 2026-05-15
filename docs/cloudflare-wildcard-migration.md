# Cloudflare Wildcard DNS + Coolify Checklist

Bu checklist `bbsoft.com.tr` tenant subdomain'lerinin deploy tetiklemeden calismasi icindir.

## 1. Cloudflare DNS tasima

Cloudflare'da `bbsoft.com.tr` zone'unu ekleyin ve mevcut kayitlari birebir tasiyin:

| Name | Type | Value | Proxy |
| --- | --- | --- | --- |
| `@` | A | `178.208.187.237` | DNS only |
| `*` | A | `178.208.187.237` | DNS only |
| `api` | A | `178.208.187.237` | DNS only |
| `www` | CNAME | `bbsoft.com.tr` | DNS only |
| `ftp` | A | `77.245.159.230` | DNS only |
| `mail` | A | `77.245.159.230` | DNS only |
| `pop` | A | `77.245.159.230` | DNS only |
| `smtp` | A | `77.245.159.230` | DNS only |
| `@` | MX | `10 mail.bbsoft.com.tr` | DNS only |
| `@` | TXT | `"v=spf1 a mx ip4:77.245.159.230 ~all"` | DNS only |

Kayitlar dogrulandiktan sonra registrar/hosting panelinde nameserver'lari Cloudflare'in verdigi
nameserver'lar ile degistirin.

## 2. Cloudflare API token

Cloudflare'da sadece `bbsoft.com.tr` zone'u icin DNS edit yetkili token olusturun.

Gerekli minimum izinler:

- Zone: `DNS:Edit`
- Zone: `Zone:Read`
- Scope: sadece `bbsoft.com.tr`

Token'i Coolify/Traefik proxy ortam degiskenlerine ekleyin. Coolify wildcard certificate dokumaninda
Cloudflare provider icin gereken env isimlerini kullanin.

## 3. Wildcard SSL

Coolify proxy/Traefik tarafinda Let's Encrypt DNS-01 challenge'i etkinlestirin ve wildcard sertifika
alin:

- Ana domain: `bbsoft.com.tr`
- Wildcard domain: `*.bbsoft.com.tr`
- Challenge: DNS-01
- DNS provider: Cloudflare

Kabul testi:

- `https://random-test.bbsoft.com.tr` sertifika uyarisi vermemeli.

## 4. Wildcard routing

Tenant frontend tek tek domain listesi yerine wildcard host rule ile calismali.

Route hedefleri:

- `api.bbsoft.com.tr` -> backend/API
- `superadmin.bbsoft.com.tr` -> superadmin frontend
- `bbsoft.com.tr` ve `www.bbsoft.com.tr` -> platform/landing
- `{tenant}.bbsoft.com.tr` -> tenant frontend

Tenant frontend icin Traefik rule ornegi:

```text
HostRegexp(`{subdomain:[a-z0-9-]+}.bbsoft.com.tr`)
```

`api` ve `superadmin` daha spesifik router olarak ayri tanimlanmali veya tenant router'dan
haric tutulmalidir.

## 5. App env

Production backend:

```env
APP_DOMAIN=bbsoft.com.tr
SUPERADMIN_HOST=superadmin.bbsoft.com.tr
TENANT_DOMAIN_STRATEGY=wildcard
COOLIFY_INSTANT_DEPLOY_ON_TENANT_CREATE=false
```

Production frontend:

```env
NEXT_PUBLIC_APP_DOMAIN=bbsoft.com.tr
NEXT_PUBLIC_SUPERADMIN_HOST=superadmin.bbsoft.com.tr
```

## 6. Smoke tests

DNS:

- `bbsoft.com.tr`
- `www.bbsoft.com.tr`
- `api.bbsoft.com.tr`
- `superadmin.bbsoft.com.tr`
- `random-test.bbsoft.com.tr`

Uygulama:

- Superadmin login aciliyor.
- Mevcut tenant admin paneli aciliyor.
- Yeni tenant olusturulunca Coolify deploy baslamiyor.
- Yeni tenant subdomain'i deploy beklemeden aciliyor.
