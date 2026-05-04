"use client"

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

type Point = { label: string; value: number }

type Props = {
  points: Point[]
}

function shortDayLabel(isoDate: string): string {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
    timeZone: "Europe/Istanbul",
  })
}

export default function DailyBookingBar({ points }: Props) {
  const data = points.map((p) => ({ day: shortDayLabel(p.label), value: p.value }))

  return (
    <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">Gunluk Randevu Sayisi</h2>
        <p className="text-xs text-zinc-400 mt-1">
          Her gune ait toplam randevu sayisi. Hangi gunlerin daha yogun oldugunu gorup takvimini buna gore duzenliyebilirsin.
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
              <XAxis dataKey="day" stroke="#a1a1aa" tick={{ fontSize: 11 }} />
              <YAxis stroke="#a1a1aa" allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", borderRadius: 8 }}
                formatter={(value: number) => [`${value} randevu`, "Randevu"]}
              />
              <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
