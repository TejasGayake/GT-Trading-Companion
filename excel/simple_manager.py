# ===============================
# excel/simple_manager.py - FIXED VERSION
# ===============================

import xlwings as xw
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import pythoncom
import os

from utils.logger import get_logger
from data.models import TickData, IndicatorData

class SimpleExcelManager:
    """Single-threaded Excel operations with robust COM handling"""
    
    def __init__(self, file_name: str = "Live_Feed_Data.xlsx"):
        self.file_name = file_name
        self.logger = get_logger('SimpleExcelManager')
        
        # Excel objects
        self.app = None
        self.wb = None
        self.sheet_live = None
        self.sheet_inst = None
        self.sheet_alerts = None
        
        # Row mapping
        self.row_map = {}
        self.next_row = 2
        
        # Headers for LIVE sheet
        self.live_headers = [
            "SYMBOL", "TOKEN", "TIME", "LTP", "CHANGE", "%CHANGE",
            "VOLUME", "VOL AVG", "VOL RATIO", "OPEN", "HIGH", "LOW",
            "52W HIGH", "52W LOW", "SMA21", "SMA40", "SMA200", 
            "RSI14",
            "EMA10", "SUPERTREND", "CAM H4", "CAM L4",
            "PREV DAY HIGH", "PREV DAY LOW",
            "VWAP", "SUPPORT", "RESISTANCE", "VOLATILITY", "ALERTS"
        ]
        
        # Headers for INSTRUMENTS sheet
        self.instrument_headers = ["TOKEN", "SYMBOL", "EXCHANGE"]
        
        # Headers for ALERTS sheet
        self.alerts_headers = [
            "SYMBOL", "TOKEN", "TIME", "LTP", "H4", "L4", "CONDITION", "STATUS"
        ]
        
        self.symbol_master = None
        self.symbol_loader = None
        self.com_initialized = False
        self.update_count = 0
        self.last_log_time = time.time()
    
    def set_symbol_master(self, symbol_master):
        self.symbol_master = symbol_master
        self.logger.info("Symbol master set")
    
    def set_symbol_loader(self, symbol_loader):
        self.symbol_loader = symbol_loader
        self.logger.info("Symbol loader set for Excel manager")
    
    def _ensure_com(self):
        try:
            pythoncom.CoInitialize()
            self.com_initialized = True
            return True
        except:
            return False
    
    def initialize(self) -> bool:
        """Initialize Excel connection"""
        try:
            self._ensure_com()
            
            # Start Excel
            self.app = xw.App(visible=True)
            self.app.display_alerts = False
            
            # Open or create workbook
            file_path = Path(self.file_name)
            if file_path.exists():
                self.wb = self.app.books.open(str(file_path))
                self.logger.info(f"Opened existing file: {self.file_name}")
            else:
                self.wb = self.app.books.add()
                self.wb.save(str(file_path))
                self.logger.info(f"Created new file: {self.file_name}")
            
            # Set up sheets
            self._setup_sheets()
            
            # Save once more
            self.wb.save()
            
            self.logger.info("✅ Excel manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Excel initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _setup_sheets(self):
        """Setup Excel sheets - FIXED for duplicate names"""
        try:
            # Get all existing sheet names
            existing_sheets = [s.name for s in self.wb.sheets]
            
            # ========================================================
            # SETUP LIVE SHEET
            # ========================================================
            if "LIVE" in existing_sheets:
                self.sheet_live = self.wb.sheets["LIVE"]
                self.logger.info("Using existing LIVE sheet")
            else:
                # Find first sheet that isn't already used
                for sheet in self.wb.sheets:
                    if sheet.name not in ["Instruments", "alerts"]:
                        sheet.name = "LIVE"
                        self.sheet_live = sheet
                        break
                if not self.sheet_live:
                    self.sheet_live = self.wb.sheets.add("LIVE")
                self.logger.info("Created LIVE sheet")
            
            # ========================================================
            # SETUP INSTRUMENTS SHEET
            # ========================================================
            if "Instruments" in existing_sheets:
                self.sheet_inst = self.wb.sheets["Instruments"]
                self.logger.info("Using existing Instruments sheet")
            else:
                self.sheet_inst = self.wb.sheets.add("Instruments")
                self.logger.info("Created Instruments sheet")
            
            # ========================================================
            # SETUP ALERTS SHEET
            # ========================================================
            if "alerts" in existing_sheets:
                self.sheet_alerts = self.wb.sheets["alerts"]
                self.logger.info("Using existing alerts sheet")
            else:
                self.sheet_alerts = self.wb.sheets.add("alerts")
                self.logger.info("Created alerts sheet")
            
            # Format all sheets
            self._format_live_headers()
            self._format_instrument_headers()
            self._format_alerts_headers()
            self._add_instructions()
            
        except Exception as e:
            self.logger.error(f"Error setting up sheets: {e}")
            raise
    
    def _format_live_headers(self):
        """Format LIVE sheet headers"""
        try:
            # Clear row 1
            self.sheet_live.range("1:1").clear()
            
            # Write headers one by one
            for col_idx, header in enumerate(self.live_headers, start=1):
                cell = self.sheet_live.cells(1, col_idx)
                cell.value = header
                cell.font.bold = True
                cell.color = (0, 100, 200)
                cell.font.color = (255, 255, 255)
            
            self.logger.info(f"LIVE sheet headers formatted")
            
        except Exception as e:
            self.logger.error(f"Error formatting LIVE headers: {e}")
    
    def _format_instrument_headers(self):
        """Format INSTRUMENTS sheet"""
        try:
            self.sheet_inst.range("1:1").clear()
            
            for col_idx, header in enumerate(self.instrument_headers, start=1):
                cell = self.sheet_inst.cells(1, col_idx)
                cell.value = header
                cell.font.bold = True
                cell.color = (0, 100, 200)
                cell.font.color = (255, 255, 255)
            
            # if required  premenent tokens ---> just need to add in below line
            # self.sheet_inst.range("A2").value = 3045 

            self.sheet_inst.autofit()
            
        except Exception as e:
            self.logger.error(f"Error formatting Instruments headers: {e}")
    
    def _format_alerts_headers(self):
        """Format ALERTS sheet"""
        try:
            self.sheet_alerts.range("1:1").clear()
            
            for col_idx, header in enumerate(self.alerts_headers, start=1):
                cell = self.sheet_alerts.cells(1, col_idx)
                cell.value = header
                cell.font.bold = True
                cell.color = (0, 100, 200)
                cell.font.color = (255, 255, 255)
            
            self.sheet_alerts.autofit()
            
        except Exception as e:
            self.logger.error(f"Error formatting alerts headers: {e}")
    
    def _add_instructions(self):
        """Add instructions"""
        try:
            self.sheet_inst.range("E1").value = "INSTRUCTIONS:"
            self.sheet_inst.range("E1").font.bold = True
            self.sheet_inst.range("E1").color = (0, 100, 200)
            self.sheet_inst.range("E1").font.color = (255, 255, 255)
            
            instructions = [
                ["1. Enter TOKEN numbers in column A (e.g., 3045)"],
                ["2. SYMBOL column (B) will be auto-filled"],
                ["3. EXCHANGE column (C) will be auto-filled as 'NSE'"],
                ["4. Multiple tokens: Enter one token per row"],
                ["5. Save the file after adding tokens"]
            ]
            
            for i, instruction in enumerate(instructions, start=2):
                self.sheet_inst.range(f"E{i}").value = instruction
                
        except Exception as e:
            self.logger.error(f"Error adding instructions: {e}")
    
    def _prepare_row_data(self, tick, indicators, alerts):
        """Prepare row data"""
        vol_ratio = 0
        if indicators and indicators.volume_avg and indicators.volume_avg > 0:
            vol_ratio = tick.volume / indicators.volume_avg
        
        row_data = [
            tick.symbol, tick.token, tick.timestamp.strftime("%H:%M:%S"),
            tick.ltp, tick.change, tick.change_percent, tick.volume,
            round(indicators.volume_avg) if indicators and indicators.volume_avg else "",
            round(vol_ratio, 2) if vol_ratio else "",
            tick.open, tick.high, tick.low,
            tick.week_52_high, tick.week_52_low,
            round(indicators.sma21, 2) if indicators and indicators.sma21 else "",
            round(indicators.sma40, 2) if indicators and indicators.sma40 else "",
            round(indicators.sma200, 2) if indicators and indicators.sma200 else "",
            round(indicators.rsi14, 2) if indicators and indicators.rsi14 else "",
            round(indicators.ema10, 2) if indicators and indicators.ema10 else "",
            round(indicators.supertrend, 2) if indicators and indicators.supertrend else "",
            round(indicators.camarilla_h4, 2) if indicators and indicators.camarilla_h4 else "",
            round(indicators.camarilla_l4, 2) if indicators and indicators.camarilla_l4 else "",
            round(indicators.prev_day_high, 2) if indicators and indicators.prev_day_high else "",
            round(indicators.prev_day_low, 2) if indicators and indicators.prev_day_low else "",
            round(indicators.vwap, 2) if indicators and indicators.vwap else "",
            round(indicators.support, 2) if indicators and indicators.support else "",
            round(indicators.resistance, 2) if indicators and indicators.resistance else "",
            round(indicators.volatility * 100, 2) if indicators and indicators.volatility else "",
            ", ".join(alerts) if alerts else ""
        ]
        
        # check length
        if len(row_data) != len(self.live_headers):
            if len(row_data) < len(self.live_headers):
                row_data.extend([''] * (len(self.live_headers) - len(row_data)))
            else:
                row_data = row_data[:len(self.live_headers)]
        
        return row_data

    def fast_update_all_rows(self, all_tokens_data):
        """Update rows"""
        try:
            if not all_tokens_data:
                return
            
            for token, (tick, indicators, alerts) in all_tokens_data.items():
                if token not in self.row_map:
                    self.row_map[token] = self.next_row
                    self.next_row += 1
                    self.logger.debug(f"Created row {self.row_map[token]} for {tick.symbol}")
                
                row = self.row_map[token]
                row_data = self._prepare_row_data(tick, indicators, alerts)
                
                # Write the entire row
                self.sheet_live.range(f"A{row}").value = [row_data]
                
        except Exception as e:
            self.logger.error(f"Update error: {e}")

    def clear_alerts_sheet(self):
        """Clear alerts sheet - FIXED"""
        try:
            if not self.sheet_alerts:
                return
            
            try:
                # Clear rows 2-1000 (safer than using used_range)
                self.sheet_alerts.range("A2:H1000").clear_contents()
            except:
                pass
            
        except Exception as e:
            self.logger.debug(f"Non-critical error clearing alerts: {e}")

    def update_alerts(self, alerts_data):
        """Update alerts sheet"""
        try:
            if not self.sheet_alerts:
                return
            
            self.clear_alerts_sheet()
            
            if not alerts_data:
                return
            
            rows_data = []
            for symbol, token, timestamp, ltp, h4, l4, condition in alerts_data:
                rows_data.append([
                    symbol, token, timestamp.strftime("%H:%M:%S"),
                    ltp, h4, l4, condition, "ACTIVE"
                ])
            
            if rows_data:
                self.sheet_alerts.range("A2").value = rows_data
                
                for i, (_, _, _, _, _, _, condition) in enumerate(alerts_data, start=2):
                    if condition == "ABOVE H4":
                        self.sheet_alerts.range(f"D{i}").color = (200, 255, 200)
                    elif condition == "BELOW L4":
                        self.sheet_alerts.range(f"D{i}").color = (255, 200, 200)
                
                self.logger.info(f"Updated alerts sheet with {len(rows_data)} alerts")
            
        except Exception as e:
            self.logger.error(f"Error updating alerts sheet: {e}")
    
    def get_symbol_for_token(self, token: str) -> str:
        """Get symbol name"""
        try:
            if self.symbol_loader and self.symbol_loader.loaded:
                return self.symbol_loader.get_symbol(token)
        except:
            pass
        return f"TKN-{token}"

    def read_instruments(self) -> List[Tuple[str, int]]:
        """Read tokens from Instruments sheet"""
        try:
            self._ensure_com()
            
            if not self.sheet_inst:
                return []
            
            last_row = self.sheet_inst.cells.last_cell.row
            if last_row < 2:
                return []
            
            token_values = self.sheet_inst.range(f"A2:A{last_row}").value
            instruments = []
            
            if isinstance(token_values, list):
                for i, token in enumerate(token_values, start=2):
                    if token and str(token).strip():
                        clean_token = str(token).strip().split('.')[0]
                        symbol = self.get_symbol_for_token(clean_token)
                        
                        try:
                            self.sheet_inst.range(f"B{i}").value = symbol
                            self.sheet_inst.range(f"C{i}").value = "NSE"
                        except:
                            pass
                        
                        instruments.append((clean_token, 1))
            elif token_values:
                clean_token = str(token_values).strip().split('.')[0]
                instruments.append((clean_token, 1))
            
            if instruments:
                token_list = [t[0] for t in instruments]
                sample_tokens = token_list[:5]
                sample_symbols = [self.get_symbol_for_token(t) for t in sample_tokens]
                self.logger.info(f"Read {len(instruments)} tokens: {dict(zip(sample_tokens, sample_symbols))}")
            
            return instruments
            
        except Exception as e:
            self.logger.error(f"Error reading instruments: {e}")
            return []
    
    def cleanup_removed(self, active_tokens: Set[str]):
        """Clean up removed tokens"""
        try:
            removed = set(self.row_map.keys()) - active_tokens
            for token in removed:
                if token in self.row_map:
                    row = self.row_map[token]
                    last_col = chr(64 + len(self.live_headers))
                    self.sheet_live.range(f"A{row}:{last_col}{row}").clear_contents()
                    del self.row_map[token]
        except Exception as e:
            self.logger.error(f"Error cleaning up: {e}")
    
    def close(self):
        """Close Excel"""
        try:
            if self.wb:
                self.wb.save()
                self.wb.close()
            if self.app:
                self.app.quit()
            self.logger.info("Excel closed")
        except Exception as e:
            self.logger.error(f"Error closing Excel: {e}")