import pandas as pd
import numpy as np

# -------------------------------
# 1️⃣ Compare Rainfall & Production
# -------------------------------
def compare_rainfall_and_production(crop_df, rain_df, state1, state2, crop, n_years):
    """
    Compares average rainfall and top crops for two states over the last N years.
    Expects crop_df in long format (State_Name, Year, Crop, Production)
    Expects rain_df to have columns state, year, and rainfall 
    """
    
    # --- Standardized Column Names (Must match new DataLoader output) ---
    crop_state_col = "State_Name"
    crop_year_col = "Year"
    crop_prod_col = "Production"
    
    rain_state_col = "state"
    rain_year_col = "year"
    rain_val_col = "rainfall" 

    # Prepare for matching
    state1_l, state2_l = state1.lower(), state2.lower()
    crop_l = crop.lower() if crop else None
    
    # Ensure year column is numeric
    if rain_year_col in rain_df.columns:
        rain_df[rain_year_col] = pd.to_numeric(rain_df[rain_year_col], errors='coerce').astype('Int64', errors='ignore')
    if crop_year_col in crop_df.columns:
        crop_df[crop_year_col] = pd.to_numeric(crop_df[crop_year_col], errors='coerce').astype('Int64', errors='ignore')

    # Determine the latest N years available in crop data (primary data source)
    all_years = sorted(crop_df[crop_year_col].dropna().unique())
    if len(all_years) < 2:
        return None
        
    n_years = min(n_years, len(all_years))
    recent_years = all_years[-n_years:]

    result = []
    for state, state_l in [(state1, state1_l), (state2, state2_l)]:
        
        # 1. Rainfall Calculation (Average over recent N years)
        rainfall_data = rain_df[
            (rain_df[rain_state_col].str.lower() == state_l) &
            (rain_df[rain_year_col].isin(recent_years))
        ].copy() 
        
        # Calculate Total Annual Rainfall from daily/monthly averages, then average the yearly totals
        yearly_rainfall = rainfall_data.groupby(rain_year_col)[rain_val_col].sum()
        avg_rainfall = yearly_rainfall.mean() if not yearly_rainfall.empty else np.nan

        # 2. Crop Production Data (Top crops over recent N years)
        crop_data = crop_df[
            (crop_df[crop_state_col].str.lower() == state_l) &
            (crop_df[crop_year_col].isin(recent_years))
        ].copy()

        top_crops_dict = {}
        avg_crop_prod = None

        if not crop_data.empty:
            crop_data.dropna(subset=[crop_prod_col], inplace=True) 
            
            # Top 3 crops by total production over the period
            top_crops_series = crop_data.groupby('Crop')[crop_prod_col].sum().sort_values(ascending=False).head(3)
            # Format output crop production for display
            top_crops_dict = {
                k: f"{v:,.0f} Th. Tonnes" 
                for k, v in top_crops_series.items()
            }
            
            # Calculate average production of the specific requested crop
            if crop_l and crop_data['Crop'].str.lower().str.contains(crop_l, na=False).any():
                specific_crop_data = crop_data[crop_data['Crop'].str.lower().str.contains(crop_l, na=False)]
                # Calculate average of the production column directly
                avg_crop_prod = specific_crop_data[crop_prod_col].mean()
            

        result.append({
            "state": state.title(),
            "avg_rainfall": f"{avg_rainfall:.2f} mm" if not np.isnan(avg_rainfall) else "N/A",
            "top_crops": top_crops_dict,
            "avg_crop_production": f"{avg_crop_prod:,.2f} Th. Tonnes" if avg_crop_prod is not None else "N/A"
        })
    return result


# -------------------------------
# 2️⃣ District Extremes for Crop (MODIFIED TO FIND STATE-LEVEL YEAR EXTREMA)
# -------------------------------
def district_extrema_for_crop(crop_df, state_x, state_y, crop):
    """
    MODIFIED: Finds the year with the highest production of a given crop in state X
    and the year with the lowest production of the same crop in state Y across all available years.
    """
    
    # --- Standardized Column Names ---
    crop_state_col = "State_Name"
    crop_year_col = "Year"
    crop_prod_col = "Production"

    state_x_l, state_y_l = state_x.lower(), state_y.lower()
    crop_l = crop.lower()
    
    # Filter for the specific crop
    data_crop = crop_df[crop_df['Crop'].str.lower() == crop_l].copy()

    if data_crop.empty:
        return None

    # Filter data for each state
    data_x = data_crop[data_crop[crop_state_col].str.lower() == state_x_l].copy()
    data_y = data_crop[data_crop[crop_state_col].str.lower() == state_y_l].copy()
    
    # Group by year to find the total state production for this crop in each year
    grouped_x = data_x.groupby(crop_year_col)[crop_prod_col].sum().reset_index()
    grouped_y = data_y.groupby(crop_year_col)[crop_prod_col].sum().reset_index()

    if grouped_x.empty or grouped_y.empty:
        return None

    # Find year with max production in state X
    max_row_x = grouped_x.loc[grouped_x[crop_prod_col].idxmax()]
    
    # Find year with min production in state Y
    min_row_y = grouped_y.loc[grouped_y[crop_prod_col].idxmin()]

    return {
        "state_x": state_x.title(),
        "max_year": int(max_row_x[crop_year_col]),
        "max_production": float(max_row_x[crop_prod_col]),
        "state_y": state_y.title(),
        "min_year": int(min_row_y[crop_year_col]),
        "min_production": float(min_row_y[crop_prod_col]),
        "crop": crop.title()
    }