import pandas as pd
import numpy as np

# -------------------------------
# 1️⃣ Compare Rainfall & Production
# -------------------------------
def compare_rainfall_and_production(crop_df, rain_df, state1, state2, crop, n_years):
    """
    Compares average rainfall and top crops for two states over the last N years.
    """
    crop_df.columns = crop_df.columns.str.strip().str.lower()
    rain_df.columns = rain_df.columns.str.strip().str.lower()

    crop_state_col = "state_name" if "state_name" in crop_df.columns else "state"
    crop_year_col = "crop_year" if "crop_year" in crop_df.columns else "year"
    crop_prod_col = "production" if "production" in crop_df.columns else "prod"

    rain_state_col = "state" if "state" in rain_df.columns else crop_state_col
    rain_year_col = "year"
    rain_val_col = "annual_rainfall_mm" if "annual_rainfall_mm" in rain_df.columns else "rainfall"

    crop_df[crop_year_col] = pd.to_numeric(crop_df[crop_year_col], errors='coerce')
    rain_df[rain_year_col] = pd.to_numeric(rain_df[rain_year_col], errors='coerce')

    # Get recent N years
    all_years = sorted(crop_df[crop_year_col].dropna().unique())
    if len(all_years) < n_years:
        n_years = len(all_years)
    recent_years = all_years[-n_years:]

    result = []
    for state in [state1, state2]:
        rainfall_data = rain_df[
            (rain_df[rain_state_col].str.lower() == state.lower()) &
            (rain_df[rain_year_col].isin(recent_years))
        ]
        avg_rainfall = rainfall_data[rain_val_col].astype(float).mean() if not rainfall_data.empty else np.nan

        crop_data = crop_df[
            (crop_df[crop_state_col].str.lower() == state.lower()) &
            (crop_df[crop_year_col].isin(recent_years))
        ]

        if crop_data.empty:
            top_crops_dict = {"No data": 0}
        else:
            top_crops = crop_data.groupby("crop")[crop_prod_col].sum().sort_values(ascending=False).head(3)
            top_crops_dict = top_crops.to_dict()

        result.append({
            "state": state.title(),
            "avg_rainfall": round(avg_rainfall, 2) if not np.isnan(avg_rainfall) else "N/A",
            "top_crops": top_crops_dict
        })
    return result


# -------------------------------
# 2️⃣ District Extremes for Crop
# -------------------------------
def district_extrema_for_crop(crop_df, state_x, state_y, crop):
    """
    Finds the district with highest production of a given crop in one state
    and the district with the lowest in another state for the latest year.
    """
    crop_df.columns = crop_df.columns.str.strip().str.lower()
    crop_state_col = "state_name" if "state_name" in crop_df.columns else "state"
    crop_district_col = "district_name" if "district_name" in crop_df.columns else "district"
    crop_year_col = "crop_year" if "crop_year" in crop_df.columns else "year"
    crop_prod_col = "production" if "production" in crop_df.columns else "prod"

    latest_year = crop_df[crop_year_col].max()

    data_x = crop_df[
        (crop_df[crop_state_col].str.lower() == state_x.lower()) &
        (crop_df["crop"].str.lower() == crop.lower()) &
        (crop_df[crop_year_col] == latest_year)
    ]

    data_y = crop_df[
        (crop_df[crop_state_col].str.lower() == state_y.lower()) &
        (crop_df["crop"].str.lower() == crop.lower()) &
        (crop_df[crop_year_col] == latest_year)
    ]

    if data_x.empty or data_y.empty:
        return None

    max_district_x = data_x.loc[data_x[crop_prod_col].idxmax()]
    min_district_y = data_y.loc[data_y[crop_prod_col].idxmin()]

    return {
        "state_x": state_x.title(),
        "max_district": max_district_x[crop_district_col].title(),
        "max_production": float(max_district_x[crop_prod_col]),
        "state_y": state_y.title(),
        "min_district": min_district_y[crop_district_col].title(),
        "min_production": float(min_district_y[crop_prod_col]),
        "year": int(latest_year)
    }
