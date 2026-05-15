import Image from "next/image"

type TenantUnavailableProps = {
  message?: string
}

export default function TenantUnavailable({
  message = "Bu adreste aktif isletme bulunamadi.",
}: TenantUnavailableProps) {
  return (
    <main className="min-h-[100dvh] bg-zinc-950 px-4 py-10 flex items-center justify-center">
      <section className="w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl border border-zinc-800 bg-white p-2 shadow-sm">
          <Image
            src="/icon.svg"
            alt="BBSoft"
            width={40}
            height={40}
            priority
          />
        </div>
        <h1 className="text-xl font-semibold text-zinc-100">Isletme bulunamadi</h1>
        <p className="mt-2 text-sm leading-6 text-zinc-400">{message}</p>
        <a
          href="https://bbsoft.com.tr"
          className="mt-5 inline-flex items-center justify-center rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-200 transition-colors hover:border-zinc-400 hover:text-white"
        >
          bbsoft.com.tr
        </a>
      </section>
    </main>
  )
}
