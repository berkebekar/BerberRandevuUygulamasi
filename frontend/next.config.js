/**
 * next.config.js — Next.js uygulama konfigürasyonu.
 *
 * rewrites: "/api/v1/..." yollarını backend sunucusuna yönlendirir.
 * Bu sayede frontend ve backend farklı portlarda çalışsa bile
 * CORS (Cross-Origin) sorunu yaşanmaz; tarayıcı aynı origin sanır.
 */

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        // "/api/v1/" ile başlayan tüm istekleri backend'e yönlendir
        source: "/api/v1/:path*",
        // BACKEND_URL ortam değişkeni yoksa local Docker adresini kullan
        destination: `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
