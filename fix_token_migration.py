from app.core.database import execute_query
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_fcm_token_columns():
    try:
        # 1. Update drivers table
        logger.info("Updating drivers table fcm_token column...")
        # Check if fcm_token is already TEXT or similar. 
        # Alter to TEXT (no index needed usually on token string)
        execute_query("ALTER TABLE drivers MODIFY fcm_token TEXT")
        logger.info("✅ drivers.fcm_token altered to TEXT")

        # 2. Update fcm_tokens (parents/students) table
        logger.info("Updating fcm_tokens table...")
        
        # First, drop the unique index on fcm_token because it limits length and may be redundant
        try:
            execute_query("DROP INDEX uniq_fcm_token ON fcm_tokens")
            logger.info("✅ Dropped index uniq_fcm_token")
        except Exception as e:
            logger.warning(f"Could not drop index (maybe doesn't exist): {e}")

        # Alter fcm_token to TEXT
        execute_query("ALTER TABLE fcm_tokens MODIFY fcm_token TEXT NOT NULL")
        logger.info("✅ fcm_tokens.fcm_token altered to TEXT")

        # 3. Ensure login_requests table exists with TEXT
        execute_query("""
            CREATE TABLE IF NOT EXISTS login_requests (
                request_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                user_type ENUM('parent', 'driver', 'admin') NOT NULL,
                new_fcm_token TEXT NOT NULL,
                status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        logger.info("✅ login_requests table verified")

    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    fix_fcm_token_columns()
