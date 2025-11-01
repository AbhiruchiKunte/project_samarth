# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
# Note: data_service.py must still contain 'import streamlit as st' for @st.cache_data to work.
from data_service import compare_average_rainfall, top_crops_in_state

def apply_custom_css():
    """Apply custom CSS for a modern, consistent UI with identical text & number inputs."""

    ORANGE_BORDER = "#f79927"
    ORANGE_SHADOW = "rgba(247, 153, 39, 0.4)"

    st.markdown(
        f"""
        <style>
        /* -------------------- GENERAL PAGE STYLING -------------------- */
        .stApp {{
            background-color: #f0f4f0; /* Light Green/Gray background */
        }}
        h1, h2, h3, h4 {{
            color: #1a4314;
            font-family: 'Helvetica Neue', sans-serif;
        }}

        /* -------------------- BUTTON STYLING -------------------- */
        .stButton>button {{
            background-color: #38761d;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            border: 1px solid #275213;
            padding: 10px 20px;
            transition: all 0.2s ease;
        }}
        .stButton>button:hover {{
            background-color: #6aa84f;
            border-color: #38761d;
        }}

        /* -------------------- METRIC STYLING -------------------- */
        .stMetric {{
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 15px;
            border-left: 5px solid #38761d;
        }}

        /* -------------------- TABS STYLING -------------------- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 20px;
        }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 18px;
            font-weight: 600;
            color: #1a4314;
        }}

        /* -------------------- FIX COLUMN GAPS -------------------- */
        .stContainer div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {{
            gap: 0px !important;
        }}
        .stContainer div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div {{
            padding: 0 !important;
            margin: 0 !important;
        }}

        /* -------------------- IDENTICAL TEXT + NUMBER INPUT STYLING -------------------- */
        /* Make both inputs share exact same look */
        .stTextInput div[data-baseweb="input"],
        [data-testid="stNumberInput"] div[data-baseweb="input"] {{
            border: 1px solid {ORANGE_BORDER} !important;
            border-radius: 0.5rem !important;
            box-shadow: none !important;
            transition: none !important;
            background-color: white !important;
        }}

        /* Keep same border color always */
        .stTextInput div[data-baseweb="input"]:focus-within,
        .stTextInput div[data-baseweb="input"]:hover,
        [data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stNumberInput"] div[data-baseweb="input"]:hover {{
            border-color: {ORANGE_BORDER} !important;
            box-shadow: none !important;
        }}

        /* Remove center divider line between number and +/- buttons */
        [data-testid="stNumberInput"] div[data-baseweb="input"] > div:first-child {{
            border-right: none !important;
        }}

        /* Make +/- buttons blend in naturally inside the box */
        [data-testid="stNumberInput"] button {{
            border: none !important;
            background: transparent !important;
            color: #333 !important;
            font-weight: 600 !important;
            margin: 0 !important;
        }}
        [data-testid="stNumberInput"] button:hover {{
            color: {ORANGE_BORDER} !important;
        }}

        /* Keep the +/- buttons inline without splitting border */
        [data-testid="stNumberInput"] > div {{
            border: none !important;
        }}

        /* -------------------- HIDE SIDEBAR -------------------- */
        [data-testid="stSidebar"],
        [data-testid="stSidebarContent"] {{
            display: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )



# --- PLOTTING FUNCTIONS ---

def plot_rainfall_proportion(res):
    """Generates and displays a pie chart for the proportional average rainfall."""
    avg_x = res['avg_rainfall_x']
    avg_y = res['avg_rainfall_y']
    state_x = res['state_x']
    state_y = res['state_y']

    if avg_x is None or avg_y is None:
        st.info("Cannot plot Pie Chart: Average rainfall data missing for one or both states.")
        return

    data = {
        'State': [state_x, state_y],
        'Avg. Rainfall (mm)': [avg_x, avg_y]
    }
    df = pd.DataFrame(data)
    
    if df['Avg. Rainfall (mm)'].sum() <= 0:
        st.info("Cannot plot Pie Chart: Sum of average rainfall is zero or negative.")
        return

    fig = px.pie(
        df, 
        values='Avg. Rainfall (mm)', 
        names='State', 
        title='Proportional Average Rainfall Contribution',
        color_discrete_sequence=["#261aaa", "#3a68cb"]
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=False, margin=dict(t=50, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)


def plot_crop_ranking(crops_data: list, state: str):
    """Generates and displays a bar chart for crop production ranking."""
    if not crops_data:
        st.warning("Cannot plot: No crop data found for ranking.")
        return
        
    df = pd.DataFrame(crops_data)
    df.rename(columns={'total_production': 'Production (Th. Tonnes)', 'crop': 'Crop'}, inplace=True)

    fig = px.bar(
        df, 
        y='Crop', 
        x='Production (Th. Tonnes)', 
        color='Crop',
        title=f'Top Crop Production in {state}',
        orientation='h', 
        color_discrete_sequence=px.colors.qualitative.Safe 
    )
    fig.update_layout(
        showlegend=False, 
        yaxis={'categoryorder':'total ascending', 'title': 'Crop'},
        xaxis_title='Production (Thousand Tonnes)',
        plot_bgcolor='#ffffff',
        margin=dict(t=50, b=10, l=10, r=10)
    )
    fig.update_traces(hovertemplate='%{y}: %{x:,.0f} Th. Tonnes<extra></extra>')
    st.plotly_chart(fig, use_container_width=True)

# --- DISPLAY FUNCTIONS ---

def display_rainfall_results(res):
    """Displays rainfall comparison results (Metrics and Pie Chart only)."""
    if "error" in res:
        st.error(res['error'])
        if 'suggestion' in res:
            st.info(f"Suggestion: {res['suggestion']}")
        return
        
    st.markdown(f"### ☔ Comparison Period: {res['years_analyzed'][0]} - {res['years_analyzed'][-1]}")
    
    # 1. Display Metrics
    col_x, col_y = st.columns(2)
    
    avg_x = res['avg_rainfall_x']
    avg_y = res['avg_rainfall_y']

    # Calculate Delta Safely
    delta_x, delta_y = None, None
    delta_color_x, delta_color_y = "off", "off"
    
    if avg_x is not None and avg_y is not None:
        if avg_x > avg_y:
            delta_x = "Higher"
            delta_color_x = "normal"
            delta_y = "Lower"
            delta_color_y = "inverse"
        elif avg_x < avg_y:
            delta_x = "Lower"
            delta_color_x = "inverse"
            delta_y = "Higher"
            delta_color_y = "normal"
        else:
            delta_x = "Equal"
            delta_y = "Equal"

    # State X Result
    with col_x:
        st.markdown(f"#### 🟢 {res['state_x']}")
        if avg_x is not None:
            st.metric(
                label="Avg. Annual Rainfall (mm)", 
                value=f"{avg_x:,.2f}",
                delta=delta_x,
                delta_color=delta_color_x
            )
        else:
            st.info("Rainfall data N/A for this state.")

    # State Y Result
    with col_y:
        st.markdown(f"#### 🟡 {res['state_y']}")
        if avg_y is not None:
            st.metric(
                label="Avg. Annual Rainfall (mm)", 
                value=f"{avg_y:,.2f}",
                delta=delta_y,
                delta_color=delta_color_y
            )
        else:
            st.info("Rainfall data N/A for this state.")
            
    # 2. Display Pie Chart 
    st.markdown("---")
    st.markdown("#### 🥧 Average Rainfall Proportion")
    plot_rainfall_proportion(res)
    
    st.caption(f"Source: {res['data_source']}")


def display_crop_results(res):
    """Displays top crops results and graph."""
    if "error" in res:
        st.error(res['error'])
        if 'suggestion' in res:
            st.info(f"Suggestion: {res['suggestion']}")
        return
        
    st.markdown(f"### 🍚 Top {len(res['top_crops'])} Crops in {res['state']} ")
    st.caption(f"Period Analyzed: {res['period']}")
    
    # Display metrics 
    cols = st.columns(min(len(res['top_crops']), 3)) 
    for i, crop_data in enumerate(res['top_crops'][:3]):
        with cols[i]:
            st.metric(
                label=crop_data['crop'].title(),
                value=f"{crop_data['total_production']:,.0f}",
                help=f"Total production over the period in {crop_data['unit']}",
            )
            st.markdown(f"<p style='font-size: 12px; color: gray;'>{crop_data['unit']}</p>", unsafe_allow_html=True)
            
    st.markdown("---")
    st.markdown("#### 📊 Production Ranking")
    plot_crop_ranking(res.get('top_crops'), res['state'])

    st.caption(f"Source: {res['data_source']}")


# --- Main Application ---

apply_custom_css()
st.set_page_config(page_title="Project Samarth - Live Q&A", layout='wide')
st.title("🌾 Project Samarth: Agricultural Data Insights")
st.markdown("### Powered by Data from data.gov.in")

# Use tabs for a cleaner, more organized interface
tab1, tab2 = st.tabs(["💧 Rainfall Comparison", "🌱 Crop Production Ranking"])

with tab1:
    st.header("Compare Average Rainfall 🌧️")
    with st.container(border=True):
        st.markdown("Analyze the average rainfall between two selected states over a recent period.")
        
        col_input_1, col_input_2, col_input_3 = st.columns([1.5, 1.5, 1])
        
        with col_input_1:
            sx = st.text_input("State X Name:", "Maharashtra", key="compare_sx")
        
        with col_input_2:
            sy = st.text_input("State Y Name:", "Kerala", key="compare_sy")

        with col_input_3:
            n = st.number_input("Last N Years:", 1, 20, 5, key="compare_last_n_years_t1")

        if st.button("🚀 Analyze Rainfall", key="btn_rainfall_analysis", use_container_width=True):
            if sx and sy and n:
                st.subheader("Analysis Results")
                with st.spinner(f"Fetching and analyzing rainfall data for {sx} vs {sy} over {n} years..."):
                    res = compare_average_rainfall(sx, sy, last_n_years=n)
                    display_rainfall_results(res)
            else:
                st.warning("Please provide valid inputs for both states and number of years.")


with tab2:
    st.header("Top Crops by Production 📈")
    with st.container(border=True):
        st.markdown("Identify the top producing crops in a single state over a recent period.")
        
        col_input_1, col_input_2, col_input_3 = st.columns([2, 1, 1])
        
        with col_input_1:
            state = st.text_input("State Name:", "Punjab", key="crops_state_name")
        
        with col_input_2:
            m = st.number_input("Top M Crops:", 1, 10, 3, key="crops_top_m")

        with col_input_3:
            y = st.number_input("Last N Years:", 1, 20, 5, key="crops_last_n_years_t2")

        if st.button("🚀 Find Top Crops", key="btn_crop_analysis", use_container_width=True):
            if state and m and y:
                st.subheader("Analysis Results")
                with st.spinner(f"Fetching and analyzing crop production data for {state} over {y} years..."):
                    res = top_crops_in_state(state, top_m=m, last_n_years=y)
                    display_crop_results(res)
            else:
                st.warning("Please provide valid inputs for state, top crops, and number of years.")


st.markdown("---")
st.caption("Disclaimer: Data is sourced from data.gov.in. Results are based on the latest available data in the specified resource files (currently up to ~2015/2016 for crop data).")