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
# --- In app.py ---
import streamlit as st
from modules.auth import TaigaAuth

# Use @st.cache_resource for objects that shouldn't be duplicated (sessions/connections)
# Added ttl=3600 to force a refresh every hour in case of silent token expiry
@st.cache_resource(ttl=86400) 
def init_connection():
    auth = TaigaAuth()
    try:
        if auth.login():
            # Get the resources you'll use throughout the app
            project = auth.get_project()
            maps = auth.get_maps()
            return auth.api, project, maps
    except Exception as e:
        # Catch errors where the API might return an HTML login page instead of JSON
        st.error(f"Authentication session error: {e}")
        # Programmatically clear this function's cache so it retries next time
        init_connection.clear()
    return None, None, None

# Usage in your main app flow:


api, project, maps = init_connection()

if api is None:
    st.error("🛑 **Access Temporarily Blocked by Taiga Firewall.**")
    st.info("The server thinks the app is a bot. Please wait at least 15 minutes before refreshing. "
            "I have updated the fetcher to be slower to prevent this in the future.")
    st.stop()

@st.cache_data(ttl=600)
def load_data(_api, _project, _maps):
    # If the API token is dead, this call will fail. 
    # Because we added a TTL to init_connection, _api should be fresh.
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

            st.markdown("---")
            st.header("📌 Project Assignment Matrix")

            # Call the new method
            fig, report_df = viz.plot_project_assignment_matrix()

            if fig:
                # Display the Card Volume Graph
                st.pyplot(fig)
                plt.clf()

                # Display the Individual Project Tables in an Expander or List
                st.subheader("📋 Project Assignment Details")
                
                # Group by Project and show tables
                projects = report_df['Project'].unique()
                for project_name in projects:
                    with st.expander(f"Project: {project_name}"):
                        group = report_df[report_df['Project'] == project_name]
                        # Sort by status order defined previously
                        st.table(group[['Subject', 'Assigned To', 'Status']].sort_values('Status'))
            else:
                st.warning("⚠️ 'Project' column missing. Please clear cache and re-fetch data.")


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
            
            # --- NEW: Efficiency Heatmap ---
            st.markdown("---")
            st.subheader("🌡️ Heatmap Efisiensi (Waktu per Poin)")
            st.info("Heatmap ini menunjukkan rata-rata waktu yang dihabiskan per 1 unit poin pekerjaan.")
            fig_heatmap = viz.plot_bottleneck_heatmap()
            st.pyplot(fig_heatmap, use_container_width=True)
            plt.clf()

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