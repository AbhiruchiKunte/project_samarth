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

    def _extract_crop_year_from_column(_self, col_name):
        """Extracts crop and year from the complex crop production column names."""
        
        # Extract year (prefer the start year for fiscal years, e.g., 2009-10 -> 2009)
        year_match = re.search(r'(\d{4})[ -]?(\d{2})?', col_name)
        year = year_match.group(1) if year_match else None
        
        # Clean up superfluous phrases and keep the main crop/commodity part
        # Including removal of 'P' which stands for Provisional in some headers
        cleaned = re.sub(r'-\d{4}-\d{2}|-\d{4}|(Production is Thausand Toones)|\(Th. tonnes\)|\(000 Bales\)|- Total|- Total\*|- Total\*\*|- Total\*\*\*|\(Mn.Kg\)|\(MT\)|(P)', '', col_name, flags=re.IGNORECASE).strip()

        # Split by hyphen and try to find the actual crop name
        parts = cleaned.split('-')
        
        crop_name = None
        for part in reversed(parts):
            p = part.strip()
            # Avoid terms that indicate categories or units
            if p and not re.search(r'food grains|cereals|pulses|oilseeds|total|prod|tons', p, re.IGNORECASE):
                crop_name = p
                break
        
        if not crop_name:
             # Fallback to match specific keywords if heuristic fails
             crop_name_match = re.search(r'(rice|wheat|jowar|bajra|maize|ragi|millets|barley|gram|tur|urad|moong|groundnut|sesamum|rapeseed|linseed|castor seed|cotton|jute|mesta|tea|coffee|rubber|banana|sugarcane|tobacco|potato|pepper|chillies|ginger|coconut|turmeric|nigerseed|soyabean|sunflower|safflower|guarseed|sanhemp)', cleaned, re.IGNORECASE)
             if crop_name_match:
                 crop_name = crop_name_match.group(0)

        # Final cleanup and title case
        if crop_name:
             crop_name = re.sub(r'[^a-zA-Z\s]', '', crop_name).strip()
             crop_name = re.sub(r'seed|seeds', '', crop_name, flags=re.IGNORECASE).strip()
        
        return {'crop': crop_name.title() if crop_name else None, 'year': year}

    @st.cache_data
    def _process_crop_data(_self, df: pd.DataFrame) -> pd.DataFrame:
        """Helper to transform wide crop data into long format (melt operation)."""
        if df is None or df.empty:
            return pd.DataFrame()
            
        id_vars = ['State_Name'] 

        # Melt the dataframe from wide to long format
        df_long = df.melt(
            id_vars=id_vars,
            var_name='Original_Column',
            value_name='Production'
        )
        
        # Drop rows where production is NA 
        df_long = df_long.dropna(subset=['Production'])
        
        # Extract Crop and Year from the original column name
        extracted_data = df_long['Original_Column'].apply(_self._extract_crop_year_from_column)
        
        df_long['Crop'] = extracted_data.apply(lambda x: x.get('crop'))
        df_long['Year'] = extracted_data.apply(lambda x: x.get('year'))
        
        # Drop rows where extraction failed 
        df_long.dropna(subset=['Crop', 'Year'], inplace=True)
        
        # Convert Year to integer and filter out Total/Summation columns
        df_long['Year'] = pd.to_numeric(df_long['Year'], errors='coerce').astype('Int64', errors='ignore')
        
        sum_keywords = ['total', 'food grains', 'oilseeds', 'total cereals', 'total pulses', 'cereals total', 'pulses total']
        df_long = df_long[~df_long['Crop'].str.lower().str.contains('|'.join(sum_keywords), na=False)]
        
        # Keep essential columns
        return df_long[['State_Name', 'Year', 'Crop', 'Production']].copy()

    @st.cache_data
    def load_crop_data(_self) -> pd.DataFrame:
        """Load, clean, and process crop production dataset"""
        try:
            file_path = _self.data_dir / "crop_production.csv"
            df = pd.read_csv(file_path)
            
            # Identify and rename the state column robustly (original name is 'State/ UT Name')
            state_col_candidates = [c for c in df.columns if 'State' in c or 'st_name' in c.lower()]
            if not state_col_candidates:
                raise ValueError("Could not find a clear State column in crop data.")
            state_col_name = state_col_candidates[0]
            df.rename(columns={state_col_name: 'State_Name'}, inplace=True)
            
            # Replace various NA representations
            df = df.replace(['NA', 'na', 'N/A', '#', '-', ''], np.nan)
            
            # Convert crop columns to numeric
            non_numeric_cols = [c for c in df.columns if c not in ['State_Name']]
            for col in non_numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['State_Name'] = df['State_Name'].str.strip()
            
            # Process to long format
            df_processed = _self._process_crop_data(df)
            
            _self.crop_df = df_processed
            return df_processed
            
        except Exception as e:
            st.error(f"❌ Error loading crop data: {str(e)}. Please check your CSV file.")
            return pd.DataFrame()
    
    @st.cache_data
    def load_rainfall_data(_self) -> pd.DataFrame:
        """Load and clean rainfall dataset"""
        # Original columns: State, District, Date, Year, Month, Avg_rainfall, Agency_name
        try:
            file_path = _self.data_dir / "rainfall_data.csv"
            
            try:
                df = pd.read_csv(file_path)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin-1')
            
            # Clean column names (lowercase with underscores)
            df.columns = df.columns.str.strip().str.lower().str.replace(r"[^\w\s]", "", regex=True).str.replace(r"\s+", "_", regex=True)
            
            # Rename for consistency in analytics module
            if 'avg_rainfall' in df.columns:
                 df.rename(columns={'avg_rainfall': 'rainfall'}, inplace=True) # Used 'rainfall' in analytics
            
            # Replace NA values
            df = df.replace(['NA', 'na', 'N/A', '#', '-', ''], np.nan)
            
            # Convert numeric columns
            for col in df.columns:
                if col not in ['state', 'district', 'date', 'agency_name']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            _self.rainfall_df = df
            return df
            
        except FileNotFoundError:
            st.warning("⚠️ Rainfall data not found. Some features will be limited.")
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"⚠️ Error loading rainfall data: {str(e)}")
            return pd.DataFrame()
    
    def get_available_states(self) -> List[str]:
        """Get list of available states from processed crop data"""
        if self.crop_df is not None and 'State_Name' in self.crop_df.columns:
            states = self.crop_df['State_Name'].dropna().unique().tolist()
            return sorted([s for s in states if s.lower() not in ['all-india', 'others']])
        if self.rainfall_df is not None and 'state' in self.rainfall_df.columns:
            states = self.rainfall_df['state'].dropna().unique().tolist()
            return sorted([s for s in states if s.lower() not in ['all-india', 'others']])
        return []
    
    def get_available_years(self) -> List[str]:
        """Extract available years from processed crop data"""
        if self.crop_df is None or 'Year' not in self.crop_df.columns:
            return []
        
        years = self.crop_df['Year'].dropna().unique()
        return sorted([str(y) for y in years])
    
    def get_available_crops(self) -> List[str]:
        """Extract unique crop names from processed crop data"""
        if self.crop_df is None or 'Crop' not in self.crop_df.columns:
            return []
        
        crops = self.crop_df['Crop'].dropna().unique().tolist()
        return sorted(list(set(crops)))