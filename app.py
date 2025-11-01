import re
import streamlit as st
from modules.data_loader import DataLoader
from modules.nlu import NLUEngine
from modules.analytics import compare_rainfall_and_production, district_extrema_for_crop
from modules.utils import get_citations


# --- Helper functions (kept local to app.py) ---

def _find_col(df, keywords):
    for c in df.columns:
        lc = c.lower()
        if any(k in lc for k in keywords):
            return c
    return None

def _detect_states_from_query(query, rain_df, crop_df):
    query_l = query.lower()
    states = set()

    # gather candidate state names from dataframes
    candidates = set()
    for df in (rain_df, crop_df):
        if df is None:
            continue
        col = _find_col(df, ["state", "st_name", "state_name", "state_ut_name"])
        if col:
            vals = df[col].dropna().astype(str).unique().tolist()
            candidates.update(vals)

    for s in candidates:
        if s.strip() and s.lower() in query_l:
            states.add(s)

    if not states:
        for s in candidates:
            words = [w for w in s.lower().split() if w]
            if words and all(w in query_l for w in words):
                states.add(s)

    return list(states)

def _detect_crops_from_query(query, crop_df):
    query_l = query.lower()
    crops = set()
    if crop_df is None:
        return []

    col = 'Crop'
    if col not in crop_df.columns:
        return []

    candidates = crop_df[col].dropna().astype(str).unique().tolist()
    for c in candidates:
        if c.strip() and c.lower() in query_l:
            crops.add(c)

    return list(crops)

def _detect_years_from_query(query):
    m = re.search(r"last\s+(\d+)\s+years?", query, re.IGNORECASE)
    if not m:
        m = re.search(r"for\s+the\s+last\s+(\d+)\s+years?", query, re.IGNORECASE)
    if not m:
        m = re.search(r"(\d+)\s+years?", query, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

# --- Main App Logic ---

def load_data():
    loader = DataLoader("data")
    crop_df = loader.load_crop_data()
    rain_df = loader.load_rainfall_data()
    return crop_df, rain_df, loader


def process_query(query, crop_df, rain_df, loader, explicit_params):
    nlu_engine = NLUEngine(loader)
    parsed = nlu_engine.parse_query(query)

    if not isinstance(parsed, dict):
        st.error("Invalid query format. Please try one of the sample queries.")
        return False

    # --- Parameter Overrides/Fallback ---
    
    # 1. Apply explicit parameters if provided
    states = [explicit_params['state1'], explicit_params['state2']]
    if all(states):
        parsed['states'] = states
    
    if explicit_params['crop'] is not None:
         parsed['crops'] = [explicit_params['crop']]
    
    if explicit_params['n_years'] is not None:
        parsed['limit'] = explicit_params['n_years']

    # 2. Fallback to data-driven detection only if missing after explicit check
    if not parsed.get("states") or len(parsed.get("states", [])) < 2:
        detected_states = _detect_states_from_query(query, rain_df, crop_df)
        if detected_states:
            parsed["states"] = detected_states

    if not parsed.get("crops"):
        detected_crops = _detect_crops_from_query(query, crop_df)
        if detected_crops:
            parsed["crops"] = detected_crops

    if not parsed.get("limit"):
        detected_years = _detect_years_from_query(query)
        if detected_years:
            parsed["limit"] = detected_years
            
    with st.expander("🧠 Detected Parameters (for debugging)"):
         st.json(parsed)

    # Handle comparison and trend queries
    if parsed.get("type") in ["comparison", "trend"]:
        if parsed.get("states") and len(parsed["states"]) >= 2:
            state1, state2 = parsed["states"][:2]
            crop = parsed.get("crops", [None])[0]
            n_years = parsed.get("limit", 5)

            if crop is None:
                st.warning(f"No specific crop detected. Displaying Average Rainfall and Top Crops for the last {n_years} years.")

            try:
                answer = compare_rainfall_and_production(crop_df, rain_df, state1, state2, crop, n_years)
            except Exception as e:
                st.error(f"Error during comparison analysis: {e}")
                return False

            if answer:
                st.subheader(f"📊 Comparison of {state1.title()} vs. {state2.title()} over the last {n_years} years:")
                
                cols = st.columns(2)
                
                # Display State 1 Results
                res1 = answer[0]
                with cols[0]:
                    st.markdown(f"#### 🟡 {res1['state']} Highlights")
                    st.metric(label="Avg. Annual Rainfall (mm)", value=res1['avg_rainfall'])
                    
                    if crop and res1.get('avg_crop_production') and res1['avg_crop_production'] != 'N/A':
                        st.metric(label=f"Avg. Production of {crop.title()} (Th. Tonnes)", value=res1['avg_crop_production'])
                    
                    if res1.get('top_crops'):
                        st.markdown(f"**Top Crops (Total Production):**")
                        for crop_name, prod in res1['top_crops'].items():
                             st.markdown(f"&nbsp; &nbsp; - **{crop_name}**: {prod}")

                # Display State 2 Results
                res2 = answer[1]
                with cols[1]:
                    st.markdown(f"#### 🟢 {res2['state']} Highlights")
                    st.metric(label="Avg. Annual Rainfall (mm)", value=res2['avg_rainfall'])
                    if crop and res2.get('avg_crop_production') and res2['avg_crop_production'] != 'N/A':
                        st.metric(label=f"Avg. Production of {crop.title()} (Th. Tonnes)", value=res2['avg_crop_production'])
                    if res2.get('top_crops'):
                        st.markdown(f"**Top Crops (Total Production):**")
                        for crop_name, prod in res2['top_crops'].items():
                            st.markdown(f"&nbsp; &nbsp; - **{crop_name}**: {prod}")
            else:
                st.warning("No data found for the specified states and parameters.")
        else:
            st.warning("Please mention at least two states to compare.")

    # Handle ranking queries (MODIFIED LOGIC for state-level extremes)
    elif parsed.get("type") in ["ranking_high", "ranking_low"]:
        if parsed.get("states") and len(parsed["states"]) >= 2 and parsed.get("crops"):
            state1, state2 = parsed["states"][:2]
            crop = parsed["crops"][0]
            
            try:
                result = district_extrema_for_crop(crop_df, state1, state2, crop)
            except Exception as e:
                st.error(f"Error during ranking analysis: {e}")
                return False

            if result:
                st.subheader(f"📈 Production Extremes for {result['crop']}")
                
                col_max, col_min = st.columns(2)
                
                with col_max:
                    st.success(
                        f"**Highest Production** in **{result['state_x']}** for {result['crop']} was recorded in **{result['max_year']}** "
                        f"at **{result['max_production']:,}** Th. Tonnes."
                    )
                with col_min:
                    st.info(
                        f"**Lowest Production** in **{result['state_y']}** for {result['crop']} was recorded in **{result['min_year']}** "
                        f"at **{result['min_production']:,}** Th. Tonnes."
                    )

                st.caption(f"⚠️ Data Note: The crop data is available at the state level. The results reflect the highest/lowest production **year** for the crop in each state.")
            else:
                st.error("No sufficient data found for that crop or states.")
        else:
            st.warning("Please specify two states and a crop name.")

    else:
        st.info("Try asking questions about comparing rainfall and crop production between states, or finding the years with the highest/lowest production for specific crops.")

    return True


def main():
    # Set the page configuration for a wider layout
    st.set_page_config(page_title="Project Samarth", layout="wide", initial_sidebar_state="auto")
    
    # Custom CSS for modern, clean styling (Deep Green/Orange palette)
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f0f4f0; /* Very light sage background */
            color: #1f1f1f;
        }
        h1, h2, h3, h4 {
            color: #1a4314; /* Deep Forest Green */
            font-family: 'Helvetica Neue', sans-serif;
        }
        h1 {
            border-bottom: 2px solid #b3c99f;
            padding-bottom: 10px;
        }
        .stButton>button {
            background-color: #f79927; /* Vibrant Orange */
            color: white;
            font-weight: bold;
            border-radius: 8px;
            border: 1px solid #c97c1d;
            padding: 10px 20px;
        }
        .stMetric {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 8px rgba(26, 67, 20, 0.1);
            margin-bottom: 15px;
        }
        .stSelectbox, .stTextInput, .stSlider {
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #b3c99f;
            background-color: #ffffff;
        }
        .stSuccess, .stInfo {
            padding: 15px;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Data Loading (for initial state/crop lists) ---
    try:
        crop_df, rain_df, loader = load_data()
        available_states = [None] + loader.get_available_states()
        available_crops = [None] + loader.get_available_crops()
        
        # Determine initial selection indices
        default_state1_idx = available_states.index("Maharashtra") if "Maharashtra" in available_states else 0
        default_state2_idx = available_states.index("Tamil Nadu") if "Tamil Nadu" in available_states else 0
        default_crop_idx = available_crops.index("Rice") if "Rice" in available_crops else 0

    except Exception:
        # Fallback if loading fails instantly
        available_states = [None, "Maharashtra", "Tamil Nadu", "Gujarat", "Punjab", "Karnataka", "Kerala"]
        available_crops = [None, "Rice", "Wheat", "Jowar", "Bajra", "Maize", "Cotton", "Sugarcane"]
        default_state1_idx, default_state2_idx, default_crop_idx = 1, 2, 1
        crop_df, rain_df, loader = None, None, None
        st.warning("Could not load full data for dropdowns. Using fallback lists.")
        
    # --- UI Start ---
    st.title("🌾 Project Samarth — Intelligent Q&A System for India's Agriculture & Climate")
    st.markdown("### Agricultural Insights through Natural Language & Data Analysis.")
    st.markdown("---")

    # 1. Input Section
    st.header("1. 🗣️ Query Input")
    query = st.text_input("Ask your full question here (e.g., 'Compare rainfall between Karnataka and Kerala for last 3 years'):", key="nl_query")
    
    # 2. Explicit Parameter Input (mimicking the categorical layout from the image)
    with st.container(border=True):
        st.header("2. ⚙️ Explicit Parameter Selection")
        st.markdown("*(Optional: Use these selectors to ensure specific states/crops are targeted.)*")

        col_left, col_mid, col_right = st.columns(3)
        
        with col_left:
             st.subheader("📍 States for Comparison")
             state1 = st.selectbox("Select State 1:", available_states, key="state1_select", index=default_state1_idx)
             state2 = st.selectbox("Select State 2:", available_states, key="state2_select", index=default_state2_idx)

        with col_mid:
             st.subheader("🍚 Crop / Commodity")
             crop_selected = st.selectbox("Select Crop:", available_crops, key="crop_select", index=default_crop_idx)
             st.markdown("*(Select 'None' for general comparison)*")

        with col_right:
             st.subheader("📅 Timeframe")
             n_years = st.slider("Select Last N Years:", min_value=2, max_value=10, value=5, key="years_slider")
             st.caption(f"Results will use the last **{n_years}** years of available data.")
    
    st.markdown("---")
    
    # Collate explicit parameters
    explicit_params = {
        'state1': state1,
        'state2': state2,
        'crop': crop_selected,
        'n_years': n_years
    }
    
    submit_button = st.button("🚀 Analyze Data", use_container_width=True)

    # --- Execution Logic ---
    if submit_button and (query or (state1 and state2)):
        
        # Fallback to generate NL query from selections if the NL text input is empty
        if not query and state1 and state2:
            crop_text = crop_selected if crop_selected else 'all crops'
            query = f"Compare {crop_text} production and rainfall between {state1} and {state2} for the last {n_years} years"
            st.caption(f"Using generated query: '{query}'")
        
        if not query:
             st.error("Please enter a query or select two states and a crop/timeframe.")
             return

        st.markdown("## 🔍 Analysis Results")
        with st.spinner("Analyzing agricultural and climate data..."):
            try:
                # Ensure data is loaded (this is cached so it's fast on subsequent runs)
                if crop_df is None or rain_df is None or loader is None:
                    crop_df, rain_df, loader = load_data()
                    if crop_df.empty or rain_df.empty:
                        st.error("❌ Critical Error: Data files are empty or unreadable.")
                        return

                process_query(query, crop_df, rain_df, loader, explicit_params)
        
            except Exception as e:
                st.error(f"⚠️ An unexpected error occurred during analysis: {str(e)}")
                st.error("Please check your input values (especially state/crop spellings in the NL query) and try again.")
        
        # --- Footer ---
        st.markdown("---")
        st.markdown("#### 📚 Data Sources")
        for c in get_citations():
            st.caption(f"- {c}")

if __name__ == "__main__":
    main()