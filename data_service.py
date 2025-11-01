import os
from dotenv import load_dotenv
import pandas as pd
import requests
from pathlib import Path
import re
from typing import Dict, Any
import streamlit as st 

load_dotenv()

# Directory for storing CSV files
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

RAINFALL_CSV = DATA_DIR / "rainfall_data.csv"
CROP_CSV = DATA_DIR / "crop_production.csv"

# Resource IDs and download URLs
RAINFALL_RESOURCE_ID = os.getenv("RAINFALL_RESOURCE_ID")
CROP_PRODUCTION_RESOURCE_ID = os.getenv("CROP_PRODUCTION_RESOURCE_ID")

# Direct download URLs (CSV format - more reliable)
RAINFALL_DOWNLOAD_URL = f"https://data.gov.in/api/datastore/resource.json?resource_id={RAINFALL_RESOURCE_ID}&format=csv&limit=50000"
CROP_DOWNLOAD_URL = f"https://data.gov.in/api/datastore/resource.json?resource_id={CROP_PRODUCTION_RESOURCE_ID}&format=csv&limit=50000"


def download_csv_with_retry(url: str, output_path: Path, max_retries: int = 3, timeout: int = 60) -> bool:
    """
    Download CSV with retry logic and longer timeout
    """
    if not RAINFALL_RESOURCE_ID or not CROP_PRODUCTION_RESOURCE_ID:
        print("⚠ Error: Resource IDs are missing from environment variables.")
        return False
        
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}: Downloading from {url[:100]}...")
            response = requests.get(url, timeout=timeout, stream=True)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✓ Successfully downloaded to {output_path}")
                return True
            else:
                print(f"✗ HTTP {response.status_code}: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"✗ Timeout on attempt {attempt + 1}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    return False


def download_datasets_if_missing() -> bool:
    """
    Download datasets if they don't exist locally
    """
    if not RAINFALL_CSV.exists():
        print(f"\n[Downloading Rainfall Data]")
        if not download_csv_with_retry(RAINFALL_DOWNLOAD_URL, RAINFALL_CSV):
            print("⚠ Failed to download rainfall data. Using manual download instructions below.")
            print(f"Please download manually from:")
            print(f"https://data.gov.in/resource/daily-district-wise-rainfall-data")
            print(f"Save as: {RAINFALL_CSV}")
            return False
    
    if not CROP_CSV.exists():
        print(f"\n[Downloading Crop Production Data]")
        if not download_csv_with_retry(CROP_DOWNLOAD_URL, CROP_CSV):
            print("⚠ Failed to download crop data. Using manual download instructions below.")
            print(f"Please download manually from:")
            print(f"https://data.gov.in/resource/state-ut-wise-production-principal-crops-2009-10-2015-16")
            print(f"Save as: {CROP_CSV}")
            return False
    
    return True


# Caching is crucial for performance in Streamlit, even when reading local files
@st.cache_data
def get_rainfall_data() -> pd.DataFrame:
    """
    Load rainfall data from CSV file
    """
    if not RAINFALL_CSV.exists():
        if not download_datasets_if_missing():
            return pd.DataFrame()
    
    try:
        df = pd.read_csv(RAINFALL_CSV)
        
        # Convert numeric columns
        for col in df.columns:
            if 'year' in col.lower() or 'rain' in col.lower():
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error loading rainfall CSV: {e}")
        return pd.DataFrame()


@st.cache_data
def get_crop_data() -> pd.DataFrame:
    """
    Load crop production data from CSV file
    """
    if not CROP_CSV.exists():
        if not download_datasets_if_missing():
            return pd.DataFrame()
    
    try:
        df = pd.read_csv(CROP_CSV)
        
        # Convert all numeric columns (except state name)
        for col in df.columns:
            if col != 'State/ UT Name' and 'state' not in col.lower() and 'name' not in col.lower():
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error loading crop CSV: {e}")
        return pd.DataFrame()


def compare_average_rainfall(state_x: str, state_y: str, last_n_years: int = 5) -> Dict[str, Any]:
    """
    Compare average rainfall between two states
    """
    df = get_rainfall_data()
    
    if df.empty:
        return {
            "error": "No rainfall data available",
            "suggestion": "Please ensure data files are in the 'data' folder and resource IDs are correct.",
            "download_link": "https://data.gov.in/resource/daily-district-wise-rainfall-data"
        }
    
    # Find relevant columns (case-insensitive)
    state_col = next((c for c in df.columns if 'state' in c.lower()), None)
    year_col = next((c for c in df.columns if 'year' in c.lower()), None)
    rain_col = next((c for c in df.columns if 'rain' in c.lower() or 'avg' in c.lower()), None)
    
    if not all([state_col, year_col, rain_col]):
        return {
            "error": "Required columns not found in dataset. Check column headers.",
            "available_columns": list(df.columns),
        }
    
    # Standardize data for filtering
    df[state_col] = df[state_col].astype(str).str.strip() 
    df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
    
    valid_years = df[year_col].dropna()
    if len(valid_years) == 0:
        return {"error": "No valid year data found in the rainfall dataset."}
    
    years = sorted(valid_years.unique())[-last_n_years:]
    
    # Filter data
    state_x_l = state_x.lower().strip()
    state_y_l = state_y.lower().strip()
    
    df_x = df[(df[state_col].str.lower() == state_x_l) & (df[year_col].isin(years))]
    df_y = df[(df[state_col].str.lower() == state_y_l) & (df[year_col].isin(years))]
    
    if df_x.empty and df_y.empty:
        return {"error": f"No data found for both states: {state_x} and {state_y}."}
    
    # Calculate yearly aggregated rainfall for plotting
    yearly_x = df_x.groupby(year_col)[rain_col].sum().reset_index()
    yearly_y = df_y.groupby(year_col)[rain_col].sum().reset_index()

    # Rename columns and combine for plot (Year, Rainfall, State)
    yearly_x['State'] = state_x.title()
    yearly_y['State'] = state_y.title()
    
    # Standardize column names for the final yearly DF
    yearly_x.rename(columns={year_col: 'Year', rain_col: 'Rainfall (mm)'}, inplace=True)
    yearly_y.rename(columns={year_col: 'Year', rain_col: 'Rainfall (mm)'}, inplace=True)

    # Combine the two dataframes
    yearly_data = pd.concat([yearly_x, yearly_y])

    # Calculate average
    avg_x = df_x[rain_col].mean()
    avg_y = df_y[rain_col].mean()
    
    return {
        "state_x": state_x.title(),
        "state_y": state_y.title(),
        "avg_rainfall_x": round(avg_x, 2) if pd.notna(avg_x) else None,
        "avg_rainfall_y": round(avg_y, 2) if pd.notna(avg_y) else None,
        "years_analyzed": list(map(int, years)),
        "data_source": f"Rainfall data from data.gov.in resource {RAINFALL_RESOURCE_ID}",
        "yearly_data": yearly_data # ADDED FOR PLOTTING
    }


def top_crops_in_state(state: str, top_m: int = 3, last_n_years: int = 5) -> Dict[str, Any]:
    """
    Get top crops by production in a state.
    """
    df = get_crop_data()
    
    if df.empty:
        return {
            "error": "No crop production data available",
            "suggestion": "Please ensure data files are in the 'data' folder and resource IDs are correct.",
            "download_link": "https://data.gov.in/resource/state-ut-wise-production-principal-crops-2009-10-2015-16"
        }
    
    # Find state name column
    state_col = next((c for c in df.columns if 'state' in c.lower() or 'name' in c.lower()), None)
    
    if not state_col:
        return {"error": "State column not found in crop production dataset."}
    
    # Standardize state column
    df[state_col] = df[state_col].astype(str).str.strip() 
    
    # Filter for the requested state (case-insensitive)
    df_state = df[df[state_col].str.lower() == state.lower().strip()]
    
    if df_state.empty:
        return {"error": f"No data found for state: {state.title()}"}
    
    crop_totals = {}
    max_year_in_data = 2015 
    
    # Process each column
    for col in df.columns:
        if col == state_col:
            continue
            
        # Extract year
        year_match = None
        year_re = re.search(r'(\d{4})[ -]?(\d{2})?', col)
        if year_re:
            try:
                year_match = int(year_re.group(1))
            except:
                pass

        # Apply year filter
        if year_match and last_n_years:
            min_year = max_year_in_data - last_n_years + 1
            if year_match < min_year:
                continue
        
        # Extract and clean crop name (robustly)
        crop_name = col
        
        # Clean up production indicators
        crop_name = re.sub(r'-\(Production.*$|-\(Th\. tonnes\)|-\(000.*$', '', crop_name)
        
        # Remove year suffix if present
        if year_match:
            crop_name = re.sub(r'-\d{4}(-\d{2})?$', '', crop_name)
        
        # Clean up prefixes
        crop_name = re.sub(r'Food grains \(cereals\)-|Food grains\(pulses\)-|Oilseeds-', '', crop_name)
        
        # Final cleanup
        crop_name = crop_name.strip('-').strip()
        
        if not crop_name or crop_name.lower() in ['state', 'name', 'total', 'all-india', 'all india', 'crop']:
            continue
        
        # Get production value
        try:
            value = df_state[col].iloc[0]
            if pd.notna(value) and value not in ['NA', '#']:
                value = float(value)
                if value > 0:
                    crop_totals[crop_name] = crop_totals.get(crop_name, 0) + value
        except:
            continue
    
    if not crop_totals:
        return {"error": f"No valid crop production data found for {state.title()} in the last {last_n_years} years."}
    
    # Sort crops by total production and get top M
    sorted_crops = sorted(crop_totals.items(), key=lambda x: x[1], reverse=True)
    top_crops = sorted_crops[:top_m]
    
    # Format results
    results = [
        {
            "crop": crop,
            "total_production": round(production, 2),
            "unit": "Thousand Tonnes"
        }
        for crop, production in top_crops
    ]
    
    return {
        "state": state.title(),
        "period": f"Last {last_n_years} years (up to {max_year_in_data})",
        "top_crops": results,
        "data_source": f"Crop production data from data.gov.in resource {CROP_PRODUCTION_RESOURCE_ID}"
    }

if __name__ == "__main__":
    download_datasets_if_missing()