# File: ./maintenance.py
import logging
from config import ARCHIVE_PENDING_PICKS_AFTER_HOURS
from database import run_maintenance_archive

def run_maintenance():
    """
    Initiates the maintenance process using the centralized database function
    and configuration settings.
    """
    logging.info("Maintenance script initiated.")
    run_maintenance_archive(ARCHIVE_PENDING_PICKS_AFTER_HOURS)
    logging.info("Maintenance script finished.")

if __name__ == "__main__":
    run_maintenance()