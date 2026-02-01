"""Scheduler — runs all ingestion scripts on a weekly schedule with diff detection and notifications.

Usage:
    python scripts/scheduler.py          # run once then exit
    python scripts/scheduler.py --daemon  # run on schedule continuously
"""
import argparse
import importlib
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import SCHEDULER_INTERVAL_HOURS
from db_utils import init_db, setup_logging
from run_logger import start_run, finish_run, fail_run
from diff_detector import take_snapshot, detect_changes
from notifier import notify_changes, notify_failure

logger = setup_logging("scheduler")

# Scripts to run in order
SCRIPTS = [
    ("ingest_nrc_reactors", "ingest_nrc_reactors"),
    ("ingest_decommissioning", "ingest_decommissioning"),
    ("ingest_usaspending", "ingest_usaspending"),
    ("ingest_trust_funds", "ingest_trust_funds"),
    ("ingest_nrc_events", "ingest_nrc_events"),
]


def run_all():
    """Execute all ingestion scripts with logging, diff detection, and notifications."""
    init_db()
    logger.info("Starting scheduled ingestion run")

    all_changes = []

    for script_name, module_name in SCRIPTS:
        run_id = start_run(script_name)
        logger.info("Running %s (run_id=%d)...", script_name, run_id)

        # Snapshot before
        snapshot = take_snapshot()

        try:
            mod = importlib.import_module(module_name)
            mod.main()

            # Detect changes
            changes = detect_changes(snapshot, run_id)
            all_changes.extend(changes)
            if changes:
                logger.info("  %d change(s) detected", len(changes))

            finish_run(run_id, processed=0, inserted=0, updated=0)
            logger.info("  %s completed successfully", script_name)

        except Exception as e:
            error_msg = traceback.format_exc()
            fail_run(run_id, error_msg)
            logger.error("  %s FAILED: %s", script_name, e)
            notify_failure(script_name, error_msg)

    # Send consolidated change notification
    if all_changes:
        notify_changes(all_changes)
        logger.info("Total changes detected: %d", len(all_changes))

    logger.info("Scheduled run complete")


def run_daemon():
    """Run on a repeating schedule using APScheduler."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler()
    scheduler.add_job(run_all, "interval", hours=SCHEDULER_INTERVAL_HOURS, id="nuclear_ingest")

    # Run immediately on start
    logger.info("Running initial ingestion...")
    run_all()

    logger.info("Scheduler started — running every %d hours", SCHEDULER_INTERVAL_HOURS)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


def main():
    parser = argparse.ArgumentParser(description="Nuclear DB ingestion scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run continuously on schedule")
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    else:
        run_all()


if __name__ == "__main__":
    main()
