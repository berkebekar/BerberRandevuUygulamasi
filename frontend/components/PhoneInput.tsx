/**
 * components/PhoneInput.tsx — Türkiye telefon numarası giriş bileşeni.
 *
 * +90 öneki sabit gösterilir, kullanıcı sadece 10 haneli numarayı girer.
 * Backend'e "+90XXXXXXXXXX" formatında gönderilir.
 */

"use client"

import { useState } from "react"

interface PhoneInputProps {
  // Kullanıcı numarayı değiştirdiğinde üst bileşene "+90XXXXXXXXXX" formatında bildir
  onChange: (fullPhone: string) => void
  disabled?: boolean
}

export default function PhoneInput({ onChange, disabled }: PhoneInputProps) {
  // Kullanıcının girdiği 10 haneli kısım (ör: "5321234567")
  const [value, setValue] = useState("")

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    // Sadece rakam kabul et, maksimum 10 hane
    const digits = e.target.value.replace(/\D/g, "").slice(0, 10)
    setValue(digits)
    // Üst bileşene tam format olarak bildir
    onChange(digits.length > 0 ? `+90${digits}` : "")
  }

  return (
    <div className="flex items-center border border-zinc-700 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-zinc-200 focus-within:border-transparent transition-all">
      {/* +90 sabit prefix — kullanıcı değiştiremez */}
      <span className="px-3 py-3 bg-zinc-800 text-zinc-400 text-sm font-medium border-r border-zinc-700 select-none">
        +90
      </span>
      <input
        type="tel"
        inputMode="numeric"
        placeholder="5XX XXX XX XX"
        value={value}
        onChange={handleChange}
        disabled={disabled}
        className="flex-1 px-3 py-3 text-sm outline-none bg-zinc-900 disabled:bg-zinc-950 disabled:text-zinc-500"
      />
    </div>
  )
}


