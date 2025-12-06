import logging
import sys
from config import ARCHIVE_AFTER_HOURS
from database import db

# Configure logging so we can see output in GitHub Actions
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def run_maintenance():
    """
    Initiates the maintenance process using the centralized database instance.
    """
    logging.info("🧹 Maintenance script initiated.")
    
    # Check if DB is connected
    if not db.client:
        logging.error("❌ Database client not initialized. Check credentials.")
        sys.exit(1)

    try:
        logging.info(f"⏳ Archiving picks older than {ARCHIVE_AFTER_HOURS} hours...")
        # Call the correct method on the db instance
        db.archive_old_picks(ARCHIVE_AFTER_HOURS)
        logging.info("✅ Maintenance script finished successfully.")
    except Exception as e:
        logging.error(f"❌ Maintenance failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_maintenance()
