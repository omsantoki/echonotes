"""Celery application — the distributed task queue for the lecture pipeline.

The lecture pipeline (transcribe → slides → align → merge → refine → diagrams → embed)
is slow and CPU-heavy. Running it inside the API request would time out the HTTP call and
starve the web process. Instead the upload endpoint enqueues a task here and returns 202;
a SEPARATE worker pool (`celery -A app.worker worker`) pulls tasks from Redis and runs
them, so the API stays responsive and workers scale independently.

Redis is both the broker (the durable message bus the API pushes onto and workers pull
from) and the result backend (task state). In local dev / tests `task_always_eager` makes
`.delay()` run the task INLINE in the calling process — no Redis, no worker, no broker —
so everything works with zero extra infrastructure and the suite stays hermetic.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

_settings = get_settings()

# A blank REDIS_URL would make Celery unhappy even in eager mode, so fall back to a
# harmless in-memory broker URL; eager mode never actually touches it.
_broker = _settings.redis_url or "memory://"
_backend = _settings.redis_url or "cache+memory://"

celery_app = Celery("echonotes", broker=_broker, backend=_backend)
celery_app.conf.update(
    task_always_eager=_settings.task_always_eager,   # true (dev/test) → run inline
    task_eager_propagates=True,                       # surface eager-task errors to the caller
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,                              # re-deliver if a worker dies mid-task
    worker_prefetch_multiplier=1,                     # one heavy task at a time per worker
    task_track_started=True,
)

# Import the task module so Celery registers the tasks. Done at the bottom to avoid a
# circular import (tasks.py imports celery_app from here).
from app import tasks  # noqa: E402,F401
