"use client"

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

type Props = {
  completed: number
  noShow: number
  cancelled: number
}

const SLICES = [
  { key: "Tamamlanan", color: "#4ade80" },
  { key: "Gelmeyen", color: "#f59e0b" },
  { key: "Iptal", color: "#f87171" },
]

export default function BookingStatusDonut({ completed, noShow, cancelled }: Props) {
  const data = [
    { name: "Tamamlanan", value: completed },
    { name: "Gelmeyen", value: noShow },
    { name: "Iptal", value: cancelled },
  ].filter((d) => d.value > 0)

  const total = completed + noShow + cancelled

  return (
    <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">Randevu Durumu Dagilimi</h2>
        <p className="text-xs text-zinc-400 mt-1">
          Secilen donemde randevularin kacinin tamamlandigini, kacinin iptal veya gelmedi olarak kapandigini gosterir.
        </p>
      </div>

      {total === 0 ? (
        <div className="flex h-[200px] items-center justify-center rounded-lg border border-dashed border-zinc-700 text-sm text-zinc-500">
          Bu donemde randevu bulunamadi.
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          <div className="h-[200px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  dataKey="value"
                  paddingAngle={2}
                >
                  {data.map((entry) => {
                    const slice = SLICES.find((s) => s.key === entry.name)
                    return <Cell key={entry.name} fill={slice?.color ?? "#71717a"} />
                  })}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", borderRadius: 8 }}
                  formatter={(value: number, name: string) => [`${value} randevu`, name]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-2">
            {SLICES.map((s) => {
              const val = data.find((d) => d.name === s.key)?.value ?? 0
              const pct = total > 0 ? ((val / total) * 100).toFixed(0) : "0"
              return (
                <div key={s.key} className="flex items-center gap-1.5 text-xs text-zinc-300">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                  {s.key} — {val} (%{pct})
                </div>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}
