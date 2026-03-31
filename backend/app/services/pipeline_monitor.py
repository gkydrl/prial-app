"""
Pipeline monitoring: her job'ın başlangıç/bitiş/hata durumunu DB'ye kaydeder.
Kullanım:
    @monitored_job("akakce_enrichment_full")
    async def daily_enrichment_full():
        ...
        return stats_dict

Veya wrapper ile:
    await run_monitored("job_name", some_coroutine())
"""
from __future__ import annotations

import functools
import time
import traceback
from datetime import datetime, timezone

from app.database import AsyncSessionLocal
from app.models.pipeline_run import PipelineRun


async def run_monitored(job_name: str, coro) -> dict | None:
    """
    Bir coroutine'i monitörlü olarak çalıştırır.
    Başlangıç/bitiş/hata durumunu pipeline_runs tablosuna kaydeder.
    """
    start = time.time()

    async with AsyncSessionLocal() as db:
        run = PipelineRun(
            job_name=job_name,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        run_id = run.id

    result = None
    try:
        result = await coro
        duration = int(time.time() - start)

        async with AsyncSessionLocal() as db:
            run = await db.get(PipelineRun, run_id)
            if run:
                run.status = "ok"
                run.finished_at = datetime.now(timezone.utc)
                run.duration_seconds = duration
                run.stats = result if isinstance(result, dict) else None
                await db.commit()

        print(f"[pipeline_monitor] {job_name} tamamlandı ({duration}s)", flush=True)

    except Exception as e:
        duration = int(time.time() - start)
        error_msg = f"{type(e).__name__}: {e}"
        tb = traceback.format_exc()

        async with AsyncSessionLocal() as db:
            run = await db.get(PipelineRun, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.duration_seconds = duration
                run.error = f"{error_msg}\n{tb}"[-2000:]  # Max 2000 char
                await db.commit()

        print(f"[pipeline_monitor] {job_name} HATA ({duration}s): {error_msg}", flush=True)
        # Hatayı yutma, yukarıya ilet
        raise

    return result


def monitored_job(job_name: str):
    """
    Decorator: async fonksiyonu otomatik olarak monitörlü yapar.

    @monitored_job("daily_enrichment_full")
    async def daily_enrichment_full():
        ...
        return {"ok": 5, "error": 1}
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await run_monitored(
                job_name,
                func(*args, **kwargs),
            )
        return wrapper
    return decorator


async def get_recent_runs(limit: int = 50) -> list[dict]:
    """Son N pipeline çalışmasını döner (admin dashboard için)."""
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PipelineRun)
            .order_by(PipelineRun.started_at.desc())
            .limit(limit)
        )
        runs = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "job_name": r.job_name,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_seconds": r.duration_seconds,
            "stats": r.stats,
            "error": r.error[:200] if r.error else None,
            "credits_used": r.credits_used,
        }
        for r in runs
    ]


async def get_pipeline_health() -> dict:
    """
    Pipeline sağlık özeti: her job'ın son çalışma durumu,
    ortalama süre, başarı oranı.
    """
    from sqlalchemy import select, func, case, and_
    from datetime import timedelta

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    async with AsyncSessionLocal() as db:
        # Her job için son 7 gün istatistikleri
        result = await db.execute(
            select(
                PipelineRun.job_name,
                func.count().label("total"),
                func.count(case((PipelineRun.status == "ok", 1))).label("success"),
                func.count(case((PipelineRun.status == "failed", 1))).label("failed"),
                func.avg(PipelineRun.duration_seconds).label("avg_duration"),
                func.max(PipelineRun.started_at).label("last_run"),
            )
            .where(PipelineRun.started_at >= seven_days_ago)
            .group_by(PipelineRun.job_name)
        )
        rows = result.all()

    jobs = {}
    all_ok = True
    for row in rows:
        success_rate = (row.success / row.total * 100) if row.total > 0 else 0
        if success_rate < 80:
            all_ok = False
        jobs[row.job_name] = {
            "total_runs": row.total,
            "success": row.success,
            "failed": row.failed,
            "success_rate": round(success_rate, 1),
            "avg_duration_seconds": round(row.avg_duration) if row.avg_duration else None,
            "last_run": row.last_run.isoformat() if row.last_run else None,
        }

    return {
        "status": "healthy" if all_ok else "degraded",
        "period": "7d",
        "jobs": jobs,
    }
