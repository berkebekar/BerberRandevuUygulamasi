"use client"

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

type Point = { label: string; value: number }

type Props = {
  points: Point[]
}

export default function HourlyBookingBar({ points }: Props) {
  const data = points.map((p) => ({ hour: p.label, value: p.value }))

  return (
    <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">Saatlik Yogunluk</h2>
        <p className="text-xs text-zinc-400 mt-1">
          Hangi saatlerde daha fazla randevu alındigini gosterir. En yuksek cubuklar en yogun saatlerini isaret eder; musterilerin seni ne zaman tercih ettigini anlayabilirsin.
        </p>
      </div>

      {data.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center rounded-lg border border-dashed border-zinc-700 text-sm text-zinc-500">
          Bu donemde randevu bulunamadi.
        </div>
      ) : (
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
              <XAxis dataKey="hour" stroke="#a1a1aa" tick={{ fontSize: 11 }} />
              <YAxis stroke="#a1a1aa" allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", borderRadius: 8 }}
                formatter={(value: number) => [`${value} randevu`, "Saat"]}
              />
              <Bar dataKey="value" fill="#38bdf8" radius={[4, 4, 0, 0]} maxBarSize={36} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
