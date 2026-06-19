"""Celery tasks — run the lecture pipeline on a worker, with real durability.

`run_pipeline` (app/pipeline.py) does the work and is idempotent: it skips an
already-finished lecture and clears partial output before reprocessing. It re-raises
only *transient* errors (network blips), which this task retries with backoff; permanent
failures are recorded on the lecture inside `run_pipeline` and never reach a retry.

If transient retries are exhausted, `on_failure` records the failure and removes the
stored uploads, so no raw audio survives even when every attempt fails (Art. IV).
"""

from __future__ import annotations

from celery import Task

from app import store
from app.models import LectureStatus
from app.pipeline import _TRANSIENT, run_pipeline
from app.worker import celery_app


class _ProcessLectureTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Reached only when transient retries are exhausted (or an unexpected error
        # propagates). Record the terminal failure and clean up the stored uploads.
        lecture_id = args[0] if args else kwargs.get("lecture_id")
        if not lecture_id:
            return
        store.update_lecture(lecture_id, status=LectureStatus.failed,
                             progress=f"Failed after repeated retries: {exc}")
        store.delete_uploads(lecture_id)


@celery_app.task(
    name="process_lecture",
    base=_ProcessLectureTask,
    bind=True,
    max_retries=3,
    autoretry_for=_TRANSIENT,        # transient errors bubble up from run_pipeline
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def process_lecture(self, lecture_id: str, course_id: str, audio_name: str,
                    pdf_name: str) -> None:
    run_pipeline(lecture_id, course_id, audio_name, pdf_name)
