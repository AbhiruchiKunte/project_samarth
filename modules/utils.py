import re
import pandas as pd

# ---------------------------
# 🔹 Basic Utility Functions
# ---------------------------

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame column names (lowercase + underscores)."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)
        .str.replace(r"\s+", "_", regex=True)
    )
    return df


def parse_column_name(name: str) -> str:
    """Normalize a column name string."""
    return re.sub(r"[^a-zA-Z0-9_]", "", name.strip().lower().replace(" ", "_"))


# ---------------------------
# 🔹 Citation Function
# ---------------------------

def get_citations() -> list:
    """
    Return a list of dataset sources used in Project Samarth.
    Modify this to include your actual file names or dataset titles.
    """
    citations = [
        "Crop Production Statistics - Ministry of Agriculture & Farmers Welfare (data.gov.in)",
        "Rainfall Data - India Meteorological Department (IMD) (data.gov.in)",
    ]
    return citations


# ---------------------------
# 🔹 Helper for safe data extraction
# ---------------------------

def safe_extract(df: pd.DataFrame, column: str, default=None):
    """Safely extract a column from DataFrame."""
    if column in df.columns:
        return df[column]
    return default


# ---------------------------
# 🔹 Debug helper
# ---------------------------

def print_debug(title: str, obj):
    """Print debug info (optional logging helper)."""
    print(f"\n=== {title} ===")
    if isinstance(obj, pd.DataFrame):
        print(obj.head())
    else:
        print(obj)
