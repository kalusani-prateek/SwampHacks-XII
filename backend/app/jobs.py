"""Background refresh schedule (APScheduler, running inside the web process)."""
import atexit
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from .services import briefings, ingest

log = logging.getLogger(__name__)


def start_jobs(app):
    scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
    )

    def in_app(fn):
        """Run a job inside the app context and log (not crash on) failures."""
        def job():
            with app.app_context():
                try:
                    fn()
                except Exception:
                    log.exception("Job %s failed", fn.__name__)
        return job

    now = datetime.now(timezone.utc)
    cfg = app.config

    def add(fn, start_in_seconds, **interval):
        scheduler.add_job(in_app(fn), "interval", id=fn.__name__,
                          next_run_time=now + timedelta(seconds=start_in_seconds), **interval)

    # Staggered first runs so startup isn't one burst of requests.
    add(ingest.refresh_weather, 2, minutes=cfg["WEATHER_REFRESH_MINUTES"])
    add(ingest.refresh_nws, 20, minutes=10)
    add(ingest.refresh_rivers, 40, minutes=30)
    add(ingest.refresh_fires, 60, minutes=60)
    add(ingest.refresh_wildlife, 90, hours=12)
    if cfg["LIGHTNING_SOURCE"] == "glm":
        add(ingest.refresh_lightning, 10, seconds=cfg["LIGHTNING_POLL_SECONDS"])
    else:
        add(ingest.rescore_lightning_sites, 60, minutes=1)
    add(briefings.run_due, 120, minutes=5)

    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    log.info("Background jobs started (lightning source: %s)", cfg["LIGHTNING_SOURCE"])
    return scheduler
