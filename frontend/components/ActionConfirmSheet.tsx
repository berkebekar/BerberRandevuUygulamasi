/**
 * components/ActionConfirmSheet.tsx — Kritik islemler icin mobil uyumlu onay sheet'i.
 *
 * Bu bilesen, admin tarafinda yanlis tiklamayi azaltmak icin
 * ekrana alttan acilan bir onay penceresi gosterir.
 */

"use client"

interface ActionConfirmSheetProps {
  open: boolean
  title: string
  description: string
  confirmText: string
  cancelText?: string
  isLoading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ActionConfirmSheet({
  open,
  title,
  description,
  confirmText,
  cancelText = "Vazgec",
  isLoading = false,
  onConfirm,
  onCancel,
}: ActionConfirmSheetProps) {
  // Kapaliysa hic render etme
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50">
      {/* Arka plan karartmasi — sheet disina tiklanirsa kapat */}
      <button
        aria-label="Kapat"
        className="absolute inset-0 bg-black/70"
        onClick={onCancel}
      />

      {/* Alt panel */}
      <div className="absolute bottom-0 left-0 right-0 bg-zinc-900 rounded-t-2xl border-t border-zinc-800 p-4 max-w-lg mx-auto">
        <div className="w-10 h-1 bg-zinc-700 rounded-full mx-auto mb-3" />
        <h3 className="text-base font-semibold text-zinc-100">{title}</h3>
        <p className="text-sm text-zinc-400 mt-1">{description}</p>

        <div className="grid grid-cols-2 gap-3 mt-4">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="py-3 rounded-lg border border-zinc-700 text-sm font-medium text-zinc-300 disabled:opacity-50"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="py-3 rounded-lg bg-red-600 text-white text-sm font-medium disabled:opacity-50"
          >
            {isLoading ? "Isleniyor..." : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}



