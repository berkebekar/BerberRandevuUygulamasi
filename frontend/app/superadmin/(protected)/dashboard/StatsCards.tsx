import type { SuperAdminOverviewResponse } from "./types"

function formatCount(value: number): string {
  return new Intl.NumberFormat("tr-TR").format(value)
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

export default function StatsCards({ overview }: { overview: SuperAdminOverviewResponse }) {
  const cards = [
    {
      label: "Tenant Sayisi",
      value: formatCount(overview.tenants.total),
      helper: `${overview.tenants.active} aktif / ${overview.tenants.inactive} pasif / ${overview.tenants.deleted} silinmis`,
    },
    {
      label: "User Sayisi",
      value: formatCount(overview.users.total),
      helper: "Platform genelinde toplam kullanici",
    },
    {
      label: "Bu Ay Booking",
      value: formatCount(overview.bookings.this_month_total),
      helper: "Aylik toplam randevu",
    },
    {
      label: "Iptal Orani",
      value: formatPercent(overview.cancel.this_month_cancel_rate),
      helper: `${formatCount(overview.cancel.this_month_cancelled)} iptal`,
    },
  ]

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <article key={card.label} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">{card.label}</p>
          <p className="mt-2 text-2xl font-bold text-zinc-100">{card.value}</p>
          <p className="mt-1 text-xs text-zinc-400">{card.helper}</p>
        </article>
      ))}
    </section>
  )
}
