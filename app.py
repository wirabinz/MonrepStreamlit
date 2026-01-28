import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# Ensure modules folder is in path
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "modules"))
if module_path not in sys.path:
    sys.path.append(module_path)

from auth import TaigaAuth
from fetcher import TaigaFetcher
from visualizer import TaigaVisualizer

st.set_page_config(page_title="Taiga Monitor Report", layout="wide")

# --- DATA CACHING ---
@st.cache_resource
def init_connection():
    auth = TaigaAuth()
    if auth.login():
        project = auth.get_project()
        maps = auth.get_maps()
        return auth.api, project, maps
    return None, None, None

@st.cache_data(ttl=600)
def load_data(_api, _project, _maps):
    fetcher = TaigaFetcher(_api, _project, _maps)
    return fetcher.get_all_stories()

def main():
    st.title("📊 Taiga Engineering Performance Dashboard")

    api, project, maps = init_connection()
    
    if api:
        st.sidebar.success(f"Connected to: {project.name}")
        
        # Load Data
        with st.spinner("Fetching data from Taiga..."):
            df_raw = load_data(api, project, maps)
        
        # Filters in Sidebar
        st.sidebar.header("Filters")
        # Set default to Jan-Jan (1to1) and Year 2026 as per your Jupyter notebook
        month_val = st.sidebar.slider("Month Range", 1, 12, (1, 1))
        month_filter = f"{month_val[0]}to{month_val[1]}"
        
        # Initialize Visualizer
        viz = TaigaVisualizer(df_raw, month=month_filter, year=2026)

        # --- UI LAYOUT ---
        tab1, tab2, tab3 = st.tabs(["Overview", "Efficiency & Bottleneck", "Performance Analysis"])

        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Status Distribution")
                viz.plot_status_distribution()
                st.pyplot(plt.gcf())
                plt.clf() # Clear figure for next plot
            with col2:
                st.subheader("Prioritas Pekerjaan")
                viz.plot_priority_pie()
                st.pyplot(plt.gcf())
                plt.clf()

        with tab2:
            st.header("Efficiency, Bottleneck & Work Connections")
            
            # 1. Heatmap: Relationship between Project Type and Work Type
            st.subheader("Koneksi: Tipe Proyek vs Tipe Pekerjaan")
            viz.plot_connection_heatmap()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf()  # Clear the figure for the next plot
            
            st.markdown("---")
            
            # 2. Efficiency by Priority
            st.subheader("Efficiency by Priority")
            viz.plot_efficiency_by_priority()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf()
            
            st.markdown("---")
            
            # 3. Bottleneck Analysis
            st.subheader("Bottleneck Analysis (Avg Time per Phase)")
            viz.plot_bottleneck_analysis()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf()

        with tab3:
            st.header("Personnel Performance & Velocity")

            # Calculate performance metrics
            perf = viz.df.groupby('Assigned To').agg({
                'ID': 'count',
                'Points': 'sum',
                'In progress_mins': 'sum'
            }).rename(columns={'ID': 'Jumlah Kartu', 'Points': 'Total Unit Pekerjaan'})

            perf['Total Durasi In Progress'] = perf['In progress_mins'].apply(viz._format_mins_to_dhm)
            perf['Efisiensi (Waktu/Unit)'] = (perf['In progress_mins'] / perf['Total Unit Pekerjaan']).apply(viz._format_mins_to_hm)

            perf['Tipe Proyek'] = viz.df.groupby('Assigned To')['Project Type'].apply(lambda x: ', '.join(x.unique()))
            perf['Tipe Pekerjaan'] = viz.df.groupby('Assigned To')['Work Type'].apply(lambda x: ', '.join(x.unique()))

            st.subheader("📊 Laporan Performa Personil")
            # Streamlit natively handles the display of dataframes
            st.dataframe(perf.drop(columns=['In progress_mins']).sort_values('Total Unit Pekerjaan', ascending=False), use_container_width=True)

            # 2. Velocity & Mix Prioritas (Stacked vertically for larger view)
            st.markdown("---")
            st.subheader("Priority Mix per Personnel")
            viz.plot_priority_mix_stacked()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf()
            
            st.markdown("---")
            st.subheader("Total Work Units (Points)")
            viz.plot_total_work_units()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf()

    else:
        st.error("Could not establish connection. Check your environment variables file.")

if __name__ == "__main__":
    main()