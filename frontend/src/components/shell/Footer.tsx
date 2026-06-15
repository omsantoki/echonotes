export function Footer() {
  return (
    <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
      <p className="mx-auto max-w-xl px-4">
        EchoNotes merges what was <span className="font-medium text-spoken">said</span> with what
        was on the <span className="font-medium text-slides">slides</span>. Audio is transcribed,
        then deleted — never stored.
      </p>
    </footer>
  )
}
