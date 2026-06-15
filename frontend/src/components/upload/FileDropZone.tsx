import { useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

export function FileDropZone({
  id,
  label,
  accept,
  hint,
  file,
  error,
  onSelect,
  icon,
}: {
  id: string
  label: string
  accept: string
  hint: string
  file: File | null
  error?: string
  onSelect: (file: File | null) => void
  icon: ReactNode
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const f = e.dataTransfer.files?.[0]
          if (f) onSelect(f)
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-7 text-center transition-colors',
          dragging
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10'
            : 'border-slate-300 hover:border-brand-400 dark:border-slate-700',
          error && 'border-red-400 dark:border-red-500/60',
        )}
      >
        <span className="text-slate-400">{icon}</span>
        {file ? (
          <div className="text-sm">
            <p className="font-medium text-slate-800 dark:text-slate-100">{file.name}</p>
            <p className="text-xs text-slate-500">{(file.size / (1024 * 1024)).toFixed(1)} MB · click to replace</p>
          </div>
        ) : (
          <div className="text-sm text-slate-500 dark:text-slate-400">
            <span className="font-medium text-brand-600 dark:text-brand-400">Click to upload</span> or
            drag and drop
            <p className="mt-0.5 text-xs">{hint}</p>
          </div>
        )}
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => onSelect(e.target.files?.[0] ?? null)}
        />
      </div>
      {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}
