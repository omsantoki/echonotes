import { useState } from 'react'
import { Sparkles, Zap } from 'lucide-react'
import { useAsk } from '@/hooks/useAsk'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorState } from '@/components/ui/ErrorState'
import { SearchResults } from '@/components/search/SearchResults'

/**
 * "Ask your notes" — type a question, get an LLM answer grounded in this course's notes.
 * A "cached" badge appears when the semantic cache served the answer (a near-duplicate
 * of an earlier question), making the optimization visible.
 */
export function AskPanel({ courseId }: { courseId: string }) {
  const [question, setQuestion] = useState('')
  const ask = useAsk(courseId)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = question.trim()
    if (q.length > 1) ask.mutate(q)
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-brand-600" />
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Ask your notes</h2>
      </div>

      <form onSubmit={submit} className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. When is the project due? Explain backpropagation."
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
        />
        <Button type="submit" disabled={ask.isPending || question.trim().length < 2}>
          {ask.isPending ? <Spinner className="h-4 w-4" /> : 'Ask'}
        </Button>
      </form>

      {ask.isError && (
        <div className="mt-3">
          <ErrorState message={(ask.error as Error)?.message} />
        </div>
      )}

      {ask.data && (
        <div className="mt-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Answer</span>
            {ask.data.cached && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">
                <Zap className="h-3 w-3" />
                cached
              </span>
            )}
          </div>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700 dark:text-slate-200">
            {ask.data.answer}
          </p>

          {ask.data.sources.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Sources</p>
              <SearchResults results={ask.data.sources} />
            </div>
          )}
        </div>
      )}
    </section>
  )
}
