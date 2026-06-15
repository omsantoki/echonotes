import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileAudio, FileText } from 'lucide-react'
import { FileDropZone } from './FileDropZone'
import { Button } from '@/components/ui/Button'
import { useUploadLecture } from '@/hooks/useUploadLecture'
import { ApiRequestError } from '@/lib/http'

// Mirrors the server-side validation in app/ingest.py.
const AUDIO_EXTS = ['.mp3', '.m4a', '.wav', '.flac', '.ogg', '.webm', '.mp4', '.mpeg', '.mpga', '.aac']
const MAX_BYTES = 500 * 1024 * 1024

function ext(name: string): string {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

export function UploadForm({ courseId }: { courseId: string }) {
  const navigate = useNavigate()
  const { mutate, isPending, progress, error } = useUploadLecture(courseId)
  const [title, setTitle] = useState('')
  const [audio, setAudio] = useState<File | null>(null)
  const [slides, setSlides] = useState<File | null>(null)
  const [errors, setErrors] = useState<{ audio?: string; slides?: string; title?: string }>({})

  function validate(): boolean {
    const e: typeof errors = {}
    if (!title.trim()) e.title = 'Give this lecture a title.'
    if (!audio) e.audio = 'Add the lecture audio.'
    else if (!AUDIO_EXTS.includes(ext(audio.name)))
      e.audio = `Unsupported audio type. Use one of ${AUDIO_EXTS.join(', ')}.`
    else if (audio.size > MAX_BYTES) e.audio = 'Audio exceeds the 500 MB limit.'
    if (!slides) e.slides = 'Add the slides PDF.'
    else if (ext(slides.name) !== '.pdf') e.slides = 'Slides must be a PDF.'
    else if (slides.size > MAX_BYTES) e.slides = 'PDF exceeds the 500 MB limit.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  function onSubmit(ev: FormEvent) {
    ev.preventDefault()
    if (!validate() || !audio || !slides) return
    mutate(
      { course_id: courseId, title: title.trim(), audio, slides },
      { onSuccess: (data) => navigate(`/lectures/${data.lecture_id}`) },
    )
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <label htmlFor="title" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Lecture title
        </label>
        <input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Lecture 5 — Photosynthesis"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
        />
        {errors.title && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.title}</p>}
      </div>

      <FileDropZone
        id="audio"
        label="Lecture audio"
        accept="audio/*,video/mp4"
        hint="MP3, M4A, WAV… up to 500 MB. Deleted right after transcription."
        file={audio}
        error={errors.audio}
        onSelect={setAudio}
        icon={<FileAudio className="h-7 w-7" />}
      />

      <FileDropZone
        id="slides"
        label="Slides (PDF)"
        accept="application/pdf,.pdf"
        hint="A single PDF, up to 500 MB."
        file={slides}
        error={errors.slides}
        onSelect={setSlides}
        icon={<FileText className="h-7 w-7" />}
      />

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {error instanceof ApiRequestError ? error.message : 'Upload failed. Please try again.'}
        </p>
      )}

      {isPending && progress < 1 && (
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
          role="progressbar"
          aria-valuenow={Math.round(progress * 100)}
        >
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${Math.round(progress * 100)}%` }}
          />
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          🔒 Your audio is transcribed, then deleted. It is never stored.
        </p>
        <Button type="submit" disabled={isPending}>
          {isPending ? 'Uploading…' : 'Create notes'}
        </Button>
      </div>
    </form>
  )
}
