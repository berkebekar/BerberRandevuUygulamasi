type Props = {
  message: string
  onRetry: () => void
}

export default function DashboardErrorState({ message, onRetry }: Props) {
  return (
    <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-5">
      <h2 className="text-sm font-semibold text-red-200">Dashboard su an yuklenemedi</h2>
      <p className="mt-2 text-sm text-red-100">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-lg border border-red-300/40 px-3 py-2 text-sm font-medium text-red-100 hover:bg-red-400/10"
      >
        Tekrar dene
      </button>
    </div>
  )
}
