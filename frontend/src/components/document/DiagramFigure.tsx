import { useState } from 'react'
import { ImageOff } from 'lucide-react'
import type { Segment } from '@/types/api'
import { resolveAssetUrl } from '@/lib/assets'
import { renderInline } from '@/lib/markdown'

export function DiagramFigure({ seg }: { seg: Segment }) {
  const src = resolveAssetUrl(seg.image_ref)
  const caption = (seg.text ?? '').trim() || 'Diagram'
  const [errored, setErrored] = useState(false)

  return (
    <figure className="my-7">
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-1.5 font-sans text-xs font-medium text-diagram dark:border-slate-800 dark:text-violet-300">
          <span className="inline-block h-2 w-2 rounded-full bg-diagram" />
          Diagram
        </div>
        {src && !errored ? (
          <img
            src={src}
            alt={caption}
            loading="lazy"
            onError={() => setErrored(true)}
            className="mx-auto block max-h-[28rem] w-full object-contain p-3"
          />
        ) : (
          <div className="flex items-center justify-center gap-2 px-4 py-10 font-sans text-sm text-slate-400">
            <ImageOff className="h-4 w-4" />
            Image unavailable
          </div>
        )}
      </div>
      <figcaption className="mt-2 text-center font-sans text-sm text-slate-500 dark:text-slate-400">
        {renderInline(caption)}
      </figcaption>
    </figure>
  )
}
