"use client"

import { useMemo, useState } from "react"

type VirtualizedListProps<T> = {
  items: T[]
  height: number
  rowHeight: number
  overscan?: number
  className?: string
  getKey?: (item: T, index: number) => string
  renderItem: (item: T, index: number) => React.ReactNode
}

export default function VirtualizedList<T>({
  items,
  height,
  rowHeight,
  overscan = 5,
  className,
  getKey,
  renderItem,
}: VirtualizedListProps<T>) {
  const [scrollTop, setScrollTop] = useState(0)

  const { startIndex, offsetY, visibleItems } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan)
    const end = Math.min(items.length, Math.ceil((scrollTop + height) / rowHeight) + overscan)
    return {
      startIndex: start,
      offsetY: start * rowHeight,
      visibleItems: items.slice(start, end),
    }
  }, [height, items, overscan, rowHeight, scrollTop])

  const totalHeight = items.length * rowHeight

  return (
    <div
      className={className}
      style={{ height, overflowY: "auto", position: "relative" }}
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
    >
      <div style={{ height: totalHeight, position: "relative" }}>
        <div style={{ position: "absolute", top: offsetY, left: 0, right: 0 }}>
          {visibleItems.map((item, index) => {
            const originalIndex = startIndex + index
            const key = getKey ? getKey(item, originalIndex) : String(originalIndex)
            return (
              <div key={key} style={{ height: rowHeight }}>
                {renderItem(item, originalIndex)}
              </div>
            )
          })}
        </div>
      </div>
      {items.length === 0 && (
        <div className="flex h-full items-center justify-center text-sm text-zinc-500">Kayit bulunamadi.</div>
      )}
    </div>
  )
}
