import app as billing_app


def test_scheduler_disabled_via_env_returns_none(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    assert billing_app._start_background_scheduler() is None


def test_scheduler_enabled_registers_all_jobs(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    scheduler = billing_app._start_background_scheduler()
    try:
        assert scheduler is not None
        job_ids = {job.id for job in scheduler.get_jobs()}
        assert job_ids == {
            "retry_failed_notifications", "check_expiry", "purge_old_location_logs",
        }
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def test_scheduler_jobs_use_configured_intervals(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("RETRY_NOTIFICATIONS_INTERVAL_MINUTES", "7")
    monkeypatch.setenv("CHECK_EXPIRY_INTERVAL_MINUTES", "13")
    monkeypatch.setenv("PURGE_LOCATION_LOGS_INTERVAL_MINUTES", "999")
    scheduler = billing_app._start_background_scheduler()
    try:
        jobs = {job.id: job for job in scheduler.get_jobs()}
        assert jobs["retry_failed_notifications"].trigger.interval.total_seconds() == 7 * 60
        assert jobs["check_expiry"].trigger.interval.total_seconds() == 13 * 60
        assert jobs["purge_old_location_logs"].trigger.interval.total_seconds() == 999 * 60
    finally:
        scheduler.shutdown(wait=False)


def test_scheduled_retry_job_calls_retry_failed_notifications(monkeypatch, db_path):
    calls = []
    monkeypatch.setattr(
        billing_app.models, "retry_failed_notifications", lambda path: calls.append(path) or 0
    )
    billing_app._run_scheduled_retry_failed_notifications()
    assert calls == [billing_app.get_db_path()]


def test_scheduled_expiry_job_calls_scan_and_notify(monkeypatch, db_path):
    calls = []
    monkeypatch.setattr(
        billing_app.models, "scan_and_notify_expired_subscriptions",
        lambda path: calls.append(path) or 0,
    )
    billing_app._run_scheduled_check_expiry()
    assert calls == [billing_app.get_db_path()]


def test_scheduled_purge_job_calls_purge_old_location_logs(monkeypatch, db_path):
    calls = []
    monkeypatch.setattr(
        billing_app.models, "purge_old_location_logs", lambda path: calls.append(path) or 0
    )
    billing_app._run_scheduled_purge_old_location_logs()
    assert calls == [billing_app.get_db_path()]


def test_scheduled_jobs_swallow_exceptions(monkeypatch, db_path, caplog):
    import logging

    caplog.set_level(logging.ERROR, logger="app")

    def _boom(path):
        raise RuntimeError("boom")

    monkeypatch.setattr(billing_app.models, "retry_failed_notifications", _boom)
    billing_app._run_scheduled_retry_failed_notifications()  # phải không raise ra ngoài

    monkeypatch.setattr(billing_app.models, "scan_and_notify_expired_subscriptions", _boom)
    billing_app._run_scheduled_check_expiry()  # phải không raise ra ngoài

    monkeypatch.setattr(billing_app.models, "purge_old_location_logs", _boom)
    billing_app._run_scheduled_purge_old_location_logs()  # phải không raise ra ngoài
