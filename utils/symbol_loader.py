# ===============================
# utils/symbol_loader.py - For CSV File
# ===============================

import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from utils.logger import get_logger

class SymbolLoader:
    """Load symbol mappings from CSV file"""

    def __init__(self, csv_path: str = "symbol_mapping.csv"):
        self.csv_path = Path(csv_path)
        self.logger = get_logger('SymbolLoader')
        self.token_to_symbol: Dict[str, str] = {}
        self.loaded = False

    def _find_csv(self) -> Optional[Path]:
        """Try multiple locations to find the symbol CSV"""
        candidates = [
            self.csv_path,
            self.csv_path.parent / "New folder" / "symbol_mapping.csv",
            self.csv_path.parent / "instrument_master.csv",
        ]

        for path in candidates:
            if path.exists():
                return path
        return None

    def load(self) -> bool:
        """Load symbols from CSV file"""
        try:
            csv_file = self._find_csv()
            if not csv_file:
                self.logger.error(f"Symbol file not found. Tried: {self.csv_path}")
                return False

            # Read CSV file
            df = pd.read_csv(csv_file)
            self.logger.info(f"Loading symbols from: {csv_file}")

            # Support both formats
            if 'TOKEN' in df.columns and 'SYMBOL' in df.columns:
                # Standard format: TOKEN,SYMBOL
                df['TOKEN'] = df['TOKEN'].astype(str).str.strip()
                df['SYMBOL'] = df['SYMBOL'].astype(str).str.strip()
                self.token_to_symbol = dict(zip(df['TOKEN'], df['SYMBOL']))
            elif 'angel_token' in df.columns and 'base_symbol' in df.columns:
                # instrument_master format: angel_token, base_symbol
                df['angel_token'] = df['angel_token'].astype(str).str.strip()
                df['base_symbol'] = df['base_symbol'].astype(str).str.strip()
                # Add -EQ suffix to match expected format
                self.token_to_symbol = {
                    row['angel_token']: f"{row['base_symbol']}-EQ"
                    for _, row in df.iterrows()
                }
            else:
                self.logger.error(f"Unsupported CSV format. Columns: {list(df.columns)}")
                return False

            self.logger.info(f"[OK] Loaded {len(self.token_to_symbol)} symbol mappings from CSV")
            self.logger.debug(f"First 5 mappings: {list(self.token_to_symbol.items())[:5]}")

            self.loaded = True
            return True

        except Exception as e:
            self.logger.error(f"Error loading symbols: {e}")
            return False
    # ========================================
    ''' def get_symbol(self, token: str) -> str:
        """Get symbol for token"""
        clean_token = str(token).split('.')[0]
        return self.token_to_symbol.get(clean_token, f"TKN-{clean_token}") '''
     
    def get_symbol(self, token: str) -> str:
        """Get symbol for token"""
        clean_token = str(token).split('.')[0]
        symbol = self.token_to_symbol.get(clean_token)

        # Debug print
        if symbol:
            self.logger.debug(f"CSV lookup: {token} → {symbol}")
        else:
            self.logger.info(f"[NOT FOUND] CSV lookup: {clean_token} -> NOT FOUND")

        return symbol if symbol else f"TKN-{clean_token}" 
    # ========================================
    
    def get_all_tokens(self) -> list:
        """Get list of all tokens"""
        return list(self.token_to_symbol.keys())
    
    def add_token(self, token: str, symbol: str):
        """Add a new token to the mapping"""
        clean_token = str(token).split('.')[0]
        self.token_to_symbol[clean_token] = symbol
        self.logger.info(f"✅ Added token {clean_token} -> {symbol}")
    
    def save(self, csv_path: Optional[str] = None):
        """Save mappings back to CSV"""
        save_path = csv_path or self.csv_path
        try:
            import pandas as pd
            data = [{"TOKEN": t, "SYMBOL": s} for t, s in self.token_to_symbol.items()]
            df = pd.DataFrame(data)
            df.to_csv(save_path, index=False)
            self.logger.info(f"✅ Saved {len(data)} mappings to {save_path}")
        except Exception as e:
            self.logger.error(f"Error saving CSV: {e}")
