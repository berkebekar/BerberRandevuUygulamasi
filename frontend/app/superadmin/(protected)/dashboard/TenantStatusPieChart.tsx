"use client"

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

type Props = {
  active: number
  inactive: number
  deleted: number
}

const COLORS = ["#22c55e", "#f59e0b", "#ef4444"]

export default function TenantStatusPieChart({ active, inactive, deleted }: Props) {
  const data = [
    { name: "Aktif", value: active },
    { name: "Pasif", value: inactive },
    { name: "Silinmis", value: deleted },
  ]
  const hasData = data.some((item) => item.value > 0)

  return (
    <article className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-zinc-100">Tenant Durum Dagilimi</h2>
        <p className="text-xs text-zinc-400">Aktif / pasif / silinmis tenantlar</p>
      </div>

      {!hasData ? (
        <div className="flex h-[260px] items-center justify-center rounded-lg border border-dashed border-zinc-700 text-sm text-zinc-500">
          Dagilim verisi bulunamadi.
        </div>
      ) : (
        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} innerRadius={45}>
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", borderRadius: 8 }}
                labelStyle={{ color: "#e4e4e7" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {data.map((entry, idx) => (
          <div key={entry.name} className="rounded-lg border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-xs">
            <div className="flex items-center gap-2 text-zinc-300">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
              <span>{entry.name}</span>
            </div>
            <p className="mt-1 font-semibold text-zinc-100">{entry.value}</p>
          </div>
        ))}
      </div>
    </article>
  )
}
