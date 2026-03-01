/**
 * components/OTPInput.tsx — 6 haneli OTP giriş bileşeni.
 *
 * Her hane ayrı bir input kutusu.
 * Kullanıcı bir hane girince odak otomatik sonraki kutuya geçer.
 * Backspace basılınca önceki kutuya döner.
 * Paste (yapıştır) desteği: 6 haneli kodu bir anda yapıştırabilir.
 */

"use client"

import { useRef, useState } from "react"

interface OTPInputProps {
  // 6 haneli OTP tamamlandığında üst bileşene bildir
  onComplete: (otp: string) => void
  disabled?: boolean
}

export default function OTPInput({ onComplete, disabled }: OTPInputProps) {
  // Her kutunun değerini ayrı ayrı tut — 6 elemanlı dizi
  const [digits, setDigits] = useState<string[]>(Array(6).fill(""))
  // Her input için ref tutuyoruz — programatik odak için
  const refs = useRef<(HTMLInputElement | null)[]>([])

  function handleChange(index: number, value: string) {
    // Sadece tek rakam kabul et
    const digit = value.replace(/\D/g, "").slice(-1)

    const newDigits = [...digits]
    newDigits[index] = digit
    setDigits(newDigits)

    // Hane doluysa sonraki kutuya geç
    if (digit && index < 5) {
      refs.current[index + 1]?.focus()
    }

    // Tüm haneler doluysa üst bileşeni bildir
    const otp = newDigits.join("")
    if (newDigits.every((d) => d !== "")) {
      onComplete(otp)
    }
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent) {
    // Backspace: mevcut kutu boşsa önceki kutuya git ve onu temizle
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      refs.current[index - 1]?.focus()
      const newDigits = [...digits]
      newDigits[index - 1] = ""
      setDigits(newDigits)
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault()
    // Yapıştırılan metinden sadece rakamları al, 6 ile sınırla
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6)
    if (!pasted) return

    const newDigits = [...digits]
    for (let i = 0; i < pasted.length; i++) {
      newDigits[i] = pasted[i]
    }
    setDigits(newDigits)

    // Odağu doldurulmuş son haneden sonrakine taşı
    const nextIndex = Math.min(pasted.length, 5)
    refs.current[nextIndex]?.focus()

    // 6 hane doluysa bildir
    if (pasted.length === 6) {
      onComplete(pasted)
    }
  }

  return (
    <div className="flex gap-2 justify-center" onPaste={handlePaste}>
      {digits.map((digit, i) => (
        <input
          key={i}
          ref={(el) => { refs.current[i] = el }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digit}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          disabled={disabled}
          className={`
            w-11 h-12 text-center text-lg font-semibold rounded-lg border
            outline-none transition-all
            ${digit ? "border-zinc-200 bg-zinc-800" : "border-zinc-700 bg-zinc-900"}
            focus:ring-2 focus:ring-zinc-200 focus:border-transparent
            disabled:bg-zinc-950 disabled:text-zinc-500 disabled:cursor-not-allowed
          `}
        />
      ))}
    </div>
  )
}



