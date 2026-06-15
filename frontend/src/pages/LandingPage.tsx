import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  FileText,
  Layers,
  Mic,
  Image as ImageIcon,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { buttonClasses } from '@/components/ui/Button'

export function LandingPage() {
  return (
    <div className="overflow-hidden">
      {/* Hero */}
      <section className="relative">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -top-40 -z-10 transform-gpu blur-3xl"
        >
          <div className="mx-auto aspect-[1155/678] w-[72rem] max-w-full bg-gradient-to-tr from-brand-300 to-violet-300 opacity-20 dark:opacity-10" />
        </div>

        <div className="mx-auto max-w-4xl px-4 pb-16 pt-20 text-center sm:px-6 sm:pt-28">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300">
            <Sparkles className="h-3.5 w-3.5 text-brand-500" />
            Honest, explainable lecture notes
          </span>
          <h1 className="mt-6 font-serif text-4xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-6xl">
            The notes your slides forgot.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
            EchoNotes merges what your lecturer <span className="font-semibold text-spoken">said</span>{' '}
            with what was on the <span className="font-semibold text-slides">slides</span> — into one
            flowing, source-labeled study document. The spoken-only insights that never made it onto
            a slide are highlighted, with the reasoning shown.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link to="/app" className={buttonClasses('primary', 'lg')}>
              Get started
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#how" className={buttonClasses('secondary', 'lg')}>
              See how it works
            </a>
          </div>
          <p className="mt-4 text-xs text-slate-400 dark:text-slate-500">
            No sign-up to try · Your audio is transcribed, then deleted
          </p>
        </div>

        <MergeIllustration />
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto max-w-5xl scroll-mt-20 px-4 py-20 sm:px-6">
        <h2 className="text-center font-serif text-3xl font-bold text-slate-900 dark:text-white">
          How it works
        </h2>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          <Step
            n={1}
            icon={<Layers className="h-6 w-6" />}
            title="Upload audio + slides"
            body="Drop in the lecture recording and the slide deck. EchoNotes transcribes the audio and reads every slide."
          />
          <Step
            n={2}
            icon={<Sparkles className="h-6 w-6" />}
            title="We merge them"
            body="Spoken explanations are aligned to the right slide, diagrams are preserved, and everything is woven into one narrative."
          />
          <Step
            n={3}
            icon={<FileText className="h-6 w-6" />}
            title="Study with confidence"
            body="Read source-labeled notes, see what was only said aloud, and export to Markdown or HTML."
          />
        </div>
      </section>

      {/* Principles */}
      <section className="border-y border-slate-200 bg-white/50 py-20 dark:border-slate-800 dark:bg-slate-900/40">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <h2 className="text-center font-serif text-3xl font-bold text-slate-900 dark:text-white">
            Built to be trusted
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <Feature
              icon={<Mic className="h-5 w-5 text-spoken" />}
              title="Spoken-only, surfaced"
              body="The insights said aloud but absent from the slides are highlighted with a ★ — the part most notes lose."
            />
            <Feature
              icon={<ShieldCheck className="h-5 w-5 text-emerald-600" />}
              title="Explainable by design"
              body="Every highlight reveals why it's there. No black box, no chatbot theatre."
            />
            <Feature
              icon={<ImageIcon className="h-5 w-5 text-diagram" />}
              title="Diagrams preserved"
              body="Figures from the slides stay in place, in context, with captions."
            />
            <Feature
              icon={<Search className="h-5 w-5 text-slides" />}
              title="A course that grows"
              body="Notes persist per course and search across lectures, so each one builds on the last."
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-3xl px-4 py-24 text-center sm:px-6">
        <h2 className="font-serif text-3xl font-bold text-slate-900 dark:text-white">
          Turn your next lecture into notes you can trust.
        </h2>
        <Link to="/app" className={buttonClasses('primary', 'lg', 'mt-8')}>
          Get started
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </div>
  )
}

function MergeIllustration() {
  return (
    <div className="mx-auto max-w-4xl px-4 pb-8 sm:px-6">
      <div className="grid items-center gap-4 sm:grid-cols-[1fr_auto_1fr]">
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slides">
            <FileText className="h-4 w-4" /> Slides
          </div>
          <div className="h-2 w-3/4 rounded bg-slate-100 dark:bg-slate-800" />
          <div className="h-2 w-full rounded bg-slate-100 dark:bg-slate-800" />
          <div className="h-2 w-5/6 rounded bg-slate-100 dark:bg-slate-800" />
        </div>
        <div className="flex justify-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-white shadow-md">
            <Sparkles className="h-5 w-5" />
          </span>
        </div>
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-spoken">
            <Mic className="h-4 w-4" /> Spoken
          </div>
          <div className="h-2 w-full rounded bg-amber-100 dark:bg-amber-500/20" />
          <div className="h-2 w-2/3 rounded bg-amber-100 dark:bg-amber-500/20" />
          <div className="h-2 w-4/5 rounded bg-slate-100 dark:bg-slate-800" />
        </div>
      </div>
      <div className="mt-4 rounded-2xl border border-brand-200 bg-gradient-to-b from-brand-50 to-white p-6 shadow-sm dark:border-brand-900/50 dark:from-brand-500/10 dark:to-slate-900">
        <div className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-brand-700 dark:text-brand-300">
          <FileText className="h-4 w-4" /> One merged study document
        </div>
        <p className="font-serif text-[1.05rem] leading-relaxed text-slate-700 dark:text-slate-200">
          Photosystem II contains P680, named for its peak absorption at 680 nm.{' '}
          <mark className="rounded-[3px] bg-spoken-soft px-1 text-slate-900 dark:bg-amber-400/20 dark:text-amber-50">
            Water is split into oxygen, hydrogen ions, and electrons{' '}
            <span className="font-bold text-spoken dark:text-amber-300">★</span>
          </mark>{' '}
          — a detail the lecturer added that never appeared on a slide.
        </p>
      </div>
    </div>
  )
}

function Step({
  n,
  icon,
  title,
  body,
}: {
  n: number
  icon: ReactNode
  title: string
  body: string
}) {
  return (
    <div className="relative rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <span className="absolute right-5 top-5 font-serif text-4xl font-bold text-slate-100 dark:text-slate-800">
        {n}
      </span>
      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
        {icon}
      </span>
      <h3 className="mt-4 font-semibold text-slate-900 dark:text-white">{title}</h3>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{body}</p>
    </div>
  )
}

function Feature({
  icon,
  title,
  body,
}: {
  icon: ReactNode
  title: string
  body: string
}) {
  return (
    <div>
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 dark:bg-slate-800">
        {icon}
      </span>
      <h3 className="mt-4 font-semibold text-slate-900 dark:text-white">{title}</h3>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{body}</p>
    </div>
  )
}
