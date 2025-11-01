import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path
import re
from typing import List

class DataLoader:
    """Load and preprocess agriculture and climate datasets"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.crop_df = None
        self.rainfall_df = None
    
    @st.cache_data
    def load_crop_data(_self) -> pd.DataFrame:
        """Load and clean crop production dataset"""
        try:
            file_path = _self.data_dir / "crop_production.csv"
            df = pd.read_csv(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Replace various NA representations
            df = df.replace(['NA', 'na', 'N/A', '#', '-', ''], np.nan)
            
            # Convert numeric columns
            numeric_cols = df.columns[1:]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Rename first column
            df.rename(columns={df.columns[0]: 'State'}, inplace=True)
            df['State'] = df['State'].str.strip()
            
            _self.crop_df = df
            return df
            
        except Exception as e:
            st.error(f"❌ Error loading crop data: {str(e)}")
            return None
    
    @st.cache_data
    def load_rainfall_data(_self) -> pd.DataFrame:
        """Load and clean rainfall dataset"""
        try:
            file_path = _self.data_dir / "rainfall_data.csv"
            
            # Try reading with different encodings
            try:
                df = pd.read_csv(file_path)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin-1')
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Common rainfall data column names
            if 'State' not in df.columns and 'STATE' in df.columns:
                df.rename(columns={'STATE': 'State'}, inplace=True)
            
            # Replace NA values
            df = df.replace(['NA', 'na', 'N/A', '#', '-', ''], np.nan)
            
            # Convert numeric columns
            for col in df.columns:
                if col != 'State' and col != 'District':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            _self.rainfall_df = df
            return df
            
        except FileNotFoundError:
            st.warning("⚠️ Rainfall data not found. Some features will be limited.")
            return None
        except Exception as e:
            st.warning(f"⚠️ Error loading rainfall data: {str(e)}")
            return None
    
    def get_available_states(self) -> List[str]:
        """Get list of available states"""
        if self.crop_df is not None:
            return sorted(self.crop_df['State'].unique().tolist())
        return []
    
    def get_available_years(self) -> List[str]:
        """Extract available years from column names"""
        if self.crop_df is None:
            return []
        
        years = set()
        for col in self.crop_df.columns[1:]:
            year_match = re.search(r'(\d{4})', col)
            if year_match:
                years.add(year_match.group(1))
        
        return sorted(list(years))
    
    def get_available_crops(self) -> List[str]:
        """Extract unique crop names from columns"""
        if self.crop_df is None:
            return []
        
        from modules.utils import parse_column_name
        
        crops = set()
        for col in self.crop_df.columns[1:]:
            info = parse_column_name(col)
            if info['crop']:
                crops.add(info['crop'])
        
        return sorted(list(crops))
