import re
import streamlit as st
from modules.data_loader import DataLoader
from modules.nlu import NLUEngine
from modules.analytics import compare_rainfall_and_production, district_extrema_for_crop
from modules.utils import get_citations


def load_data():
    # Initialize with data directory path
    loader = DataLoader("data")
    crop_df = loader.load_crop_data()
    rain_df = loader.load_rainfall_data()
    return crop_df, rain_df, loader


# helper: find a likely column name in a dataframe based on keywords
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
        col = _find_col(df, ["state", "st_name", "state_name"])
        if col:
            vals = df[col].dropna().astype(str).unique().tolist()
            candidates.update(vals)

    # direct substring match (case-insensitive)
    for s in candidates:
        if s.strip() and s.lower() in query_l:
            states.add(s)

    # fallback: match if all words of state appear in query (handles "Tamil Nadu")
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

    col = _find_col(crop_df, ["crop", "commodity", "crop_name", "produce"])
    if not col:
        return []

    candidates = crop_df[col].dropna().astype(str).unique().tolist()
    for c in candidates:
        if c.strip() and c.lower() in query_l:
            crops.add(c)

    return list(crops)


def _detect_years_from_query(query):
    # look for phrases like "last 5 years", "for 3 years" etc.
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


def process_query(query, crop_df, rain_df, loader):
    nlu_engine = NLUEngine(loader)
    parsed = nlu_engine.parse_query(query)

    # Validate parsed result
    if not isinstance(parsed, dict):
        st.error("Invalid query format. Please try one of the sample queries above.")
        return False

    # If NLU didn't detect states/crops/years, try lightweight data-driven extraction
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

    st.write("#### 🧠 Detected Parameters:")
    st.json(parsed)

    # Handle comparison and trend queries
    if parsed.get("type") in ["comparison", "trend"]:
        if parsed.get("states") and len(parsed["states"]) >= 2:
            state1, state2 = parsed["states"][:2]
            crop = parsed.get("crops", [None])[0]
            n_years = parsed.get("limit", 5)

            answer = compare_rainfall_and_production(crop_df, rain_df, state1, state2, crop, n_years)

            if answer:
                for res in answer:
                    st.subheader(f"📍 {res['state']}")
                    st.write(f"**Average Rainfall:** {res['avg_rainfall']:.2f} mm")
                    if res.get('top_crops'):
                        st.write(f"**Top Crops:** {', '.join(res['top_crops'])}")
            else:
                st.warning("No data found for the specified states and parameters.")
        else:
            st.warning("Please mention at least two states to compare. (Try sample queries shown above.)")

    # Handle ranking queries
    elif parsed.get("type") in ["ranking_high", "ranking_low"]:
        if parsed.get("states") and len(parsed["states"]) >= 2 and parsed.get("crops"):
            state1, state2 = parsed["states"][:2]
            crop = parsed["crops"][0]
            result = district_extrema_for_crop(crop_df, state1, state2, crop)

            if result:
                st.success(
                    f"🌿 In **{result['state_x']}**, district **{result['max_district']}** "
                    f"had the highest production of **{crop.title()}** "
                    f"({result['max_production']:,} tons) in {result['year']}.\n\n"
                    f"🌾 In **{result['state_y']}**, district **{result['min_district']}** "
                    f"had the lowest production ({result['min_production']:,} tons)."
                )
            else:
                st.error("No sufficient data found for that crop or states.")
        else:
            st.warning("Please specify two states and a crop name.")

    else:
        st.info("Try asking questions about comparing rainfall and crop production between states, or finding highest/lowest producing districts for specific crops.")

    return True


def main():
    st.set_page_config(page_title="Project Samarth", layout="wide")
    st.title("🌾 Project Samarth — Intelligent Q&A System for India's Agriculture & Climate")
    st.markdown("### Ask data-driven questions about Indian agriculture using natural language.")

    # Add sample queries section
    st.markdown("### 📝 Sample Queries:")
    st.markdown("""
    - Compare the average annual rainfall in Maharashtra and Tamil Nadu for the last 5 years
    - Compare rainfall between Karnataka and Kerala for last 3 years
    - Which districts have highest and lowest production of rice in Gujarat and Maharashtra?
    - Compare production of wheat between Uttar Pradesh and Punjab
    - Show rainfall trend in Bihar and West Bengal for last 5 years
    """)

    query = st.text_input("💬 Enter your question:")

    if st.button("🔍 Get Answer") and query:
        try:
            crop_df, rain_df, loader = load_data()
            process_query(query, crop_df, rain_df, loader)

            st.markdown("### 📚 Data Sources")
            for c in get_citations():
                st.write(f"- {c}")

        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
            st.error("Please try rephrasing your question or check if the states and crops mentioned are in our database.")


if __name__ == "__main__":
    main()
