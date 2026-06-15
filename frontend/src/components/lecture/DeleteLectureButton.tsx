import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useDeleteLecture } from '@/hooks/useLecture'

export function DeleteLectureButton({
  lectureId,
  title,
}: {
  lectureId: string
  title?: string
}) {
  const [confirm, setConfirm] = useState(false)
  const navigate = useNavigate()
  const del = useDeleteLecture()

  return (
    <>
      <Button variant="secondary" size="sm" onClick={() => setConfirm(true)}>
        <Trash2 className="h-4 w-4" />
        Delete
      </Button>
      <ConfirmDialog
        open={confirm}
        title="Delete lecture?"
        message={`${title ? `"${title}"` : 'This lecture'} and its notes will be permanently deleted. This can't be undone.`}
        confirmLabel="Delete lecture"
        loading={del.isPending}
        error={del.isError ? (del.error as Error).message : undefined}
        onConfirm={() => del.mutate(lectureId, { onSuccess: () => navigate('/app') })}
        onClose={() => setConfirm(false)}
      />
    </>
  )
}
