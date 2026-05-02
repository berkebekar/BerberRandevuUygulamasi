import type { SuperAdminRecentActivityItem } from "./types"

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Istanbul",
  })
}

export default function RecentActivityTimeline({ items }: { items: SuperAdminRecentActivityItem[] }) {
  return (
    <article className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-zinc-100">Son Aktiviteler</h2>
        <p className="text-xs text-zinc-400">Son 10 olay</p>
      </div>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-zinc-700 px-4 py-8 text-center text-sm text-zinc-500">
          Gosterilecek aktivite bulunamadi.
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((item, index) => (
            <li key={`${item.source}-${item.type}-${item.created_at}-${index}`} className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-zinc-100">{item.title}</p>
                  {item.description && <p className="mt-1 text-xs text-zinc-400">{item.description}</p>}
                </div>
                <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-[10px] uppercase tracking-wide text-zinc-300">
                  {item.source}
                </span>
              </div>
              <p className="mt-2 text-xs text-zinc-500">{formatDateTime(item.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}
