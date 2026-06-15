import { Download } from 'lucide-react'
import { api } from '@/lib/api'
import { buttonClasses } from '@/components/ui/Button'

export function ExportMenu({ lectureId }: { lectureId: string }) {
  return (
    <div className="flex items-center gap-2">
      <a
        href={api.exportLectureUrl(lectureId, 'md')}
        className={buttonClasses('secondary', 'sm')}
        download
      >
        <Download className="h-4 w-4" />
        Markdown
      </a>
      <a
        href={api.exportLectureUrl(lectureId, 'html')}
        className={buttonClasses('secondary', 'sm')}
        download
      >
        <Download className="h-4 w-4" />
        HTML
      </a>
    </div>
  )
}
