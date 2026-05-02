"use client"

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { SuperAdminTrendPoint } from "./types"

type Props = {
  points: SuperAdminTrendPoint[]
}

export default function BookingTrendChart({ points }: Props) {
  const hasData = points.length > 0

  return (
    <article className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-zinc-100">Aylik Booking Trendi</h2>
        <p className="text-xs text-zinc-400">Son 6 ay booking sayisi</p>
      </div>

      {!hasData ? (
        <div className="flex h-[260px] items-center justify-center rounded-lg border border-dashed border-zinc-700 text-sm text-zinc-500">
          Trend verisi bulunamadi.
        </div>
      ) : (
        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
              <XAxis dataKey="month" stroke="#a1a1aa" />
              <YAxis stroke="#a1a1aa" allowDecimals={false} />
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", borderRadius: 8 }}
                labelStyle={{ color: "#e4e4e7" }}
              />
              <Line type="monotone" dataKey="count" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </article>
  )
}
