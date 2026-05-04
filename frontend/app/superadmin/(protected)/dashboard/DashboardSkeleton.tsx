function SkeletonBlock({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-xl bg-zinc-800/70 ${className}`} />
}

export default function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5">
        <SkeletonBlock className="h-4 w-36" />
        <SkeletonBlock className="mt-3 h-3 w-60" />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SkeletonBlock className="h-28" />
        <SkeletonBlock className="h-28" />
        <SkeletonBlock className="h-28" />
        <SkeletonBlock className="h-28" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <SkeletonBlock className="h-[320px]" />
        <SkeletonBlock className="h-[320px]" />
        <SkeletonBlock className="h-[320px]" />
      </div>

      <SkeletonBlock className="h-[280px]" />
    </div>
  )
}
