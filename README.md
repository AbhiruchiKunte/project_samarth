# 🌾 Project Samarth: Agricultural Data Insights

Project Samarth is an interactive web application built using **Streamlit** that provides quick, data-driven insights into India's agriculture sector. It allows users to compare rainfall trends and identify top-producing crops across various states.

The application adheres to a clean, modular structure, separating the user interface (`app.py`) from the core data processing and fetching logic (`data_service.py`).

## ✨ Features

The application is divided into two main tabs, each offering a specific analysis:

### 1. 💧 Rainfall Comparison
* **Purpose:** Compares the average annual rainfall between any two selected states (State X and State Y).
* **Analysis:** Calculates and displays the average rainfall in millimeters (mm) for the selected states over the last **N** years.
* **Visualization:** Uses a Pie Chart (Plotly) to show the proportional average rainfall contribution between the two states.

### 2. 🌱 Crop Production Ranking
* **Purpose:** Identifies the top producing crops in a single selected state.
* **Analysis:** Aggregates the total production for various crops over the last **N** years and ranks the **Top M** crops.
* **Visualization:** Presents the ranking using a Bar Chart (Plotly), showing production in Thousand Tonnes.

---

## 💾 Data Source and Disclaimer

The application uses open data resources provided by the Government of India via **data.gov.in**.

* **Rainfall Data Source:** Daily district-wise rainfall data.
* **Crop Data Source:** State/UT-wise production of principal crops (e.g., 2009-10 to 2015-16 data is expected based on the links in `data_service.py`).

Results are based on the latest available data in the specified resource files (the code notes that crop data is currently up to ~2015/2016).*

---
## 🚀 Live Demo

[**Live Project Link**](https://project--samarth.streamlit.app/)
