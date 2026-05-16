# ===============================
# test_excel.py - Test Excel Initialization
# ===============================

import xlwings as xw
import time
from utils.logger import get_logger


self.logger.debug("Testing Excel initialization...")

try:
    # Start Excel
    app = xw.App(visible=True)
    self.logger.info("✅ Excel App created")
    
    # Add workbook
    wb = app.books.add()
    self.logger.info("✅ Workbook added")
    
    # Rename sheet
    sheet = wb.sheets[0]
    sheet.name = "TEST"
    self.logger.info("✅ Sheet renamed")
    
    # Add some data
    sheet.range("A1").value = ["Test", "Data"]
    sheet.range("A1:B1").font.bold = True
    self.logger.info("✅ Data added")
    
    # Save
    wb.save("test_output.xlsx")
    self.logger.info("✅ File saved")
    
    # Keep open for 5 seconds
    self.logger.debug("Excel window should be visible with data...")
    time.sleep(5)
    
    # Close
    wb.close()
    app.quit()
    self.logger.info("✅ Excel closed properly")
    
except Exception as e:
    self.logger.error(f"❌ Error: {e}")