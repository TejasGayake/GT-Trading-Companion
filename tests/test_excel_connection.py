# ===============================
# test_excel_connection.py - Test Excel Connection
# ===============================

import time
from excel.simple_manager import SimpleExcelManager
from utils.logger import get_logger

logger = get_logger('Test')

def test_excel():
    """Test Excel connection stability"""
    logger.info("Testing Excel connection...")
    
    excel = SimpleExcelManager()
    if not excel.initialize():
        logger.error("Failed to initialize Excel")
        return
    
    logger.info("Excel initialized successfully")
    
    # Test reading
    for i in range(10):
        tokens = excel.read_instruments()
        logger.info(f"Read {len(tokens)} tokens (attempt {i+1})")
        time.sleep(2)
    
    excel.close()
    logger.info("Test complete")

if __name__ == "__main__":
    test_excel()