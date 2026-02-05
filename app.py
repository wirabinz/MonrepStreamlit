import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
import time

# Ensure modules folder is in path
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "modules"))
if module_path not in sys.path:
    sys.path.append(module_path)

from auth import TaigaAuth
from fetcher import TaigaFetcher
from visualizer import TaigaVisualizer

st.set_page_config(page_title="Taiga Monitor Report", layout="wide")

# Shared, cross-session cooldown state
@st.cache_resource
def blocked_state():
    return {"until": 0}

# --- CONNECTION CACHING ---
@st.cache_resource(ttl=3600)
def init_connection():
    # Check shared cooldown to avoid spamming the API
    if blocked_state()["until"] > time.time():
        return None, None, None

    auth = TaigaAuth()
    try:
        if auth.login():
            project = auth.get_project()
            maps = auth.get_maps()
            return auth.api, project, maps
    except Exception as e:
        if "<html>" in str(e).lower() or "waiting for the redirection" in str(e).lower():
            blocked_state()["until"] = time.time() + 900
        init_connection.clear()
    return None, None, None

# --- DATA FETCHING ---
def fetch_fresh_data(api, project, maps):
    """Pulls new data with extreme caution."""
    fetcher = TaigaFetcher(api, project, maps)
    try:
        # Brief pause to 'cool down' before the first API call
        time.sleep(2)
        return fetcher.get_all_stories()
    except Exception as e:
        if "firewall_blocked" in str(e).lower() or "<html>" in str(e).lower():
            st.error("Firewall redirection detected.")
            st.info("The server is challenging the connection. Please close this tab and wait 15 minutes.")
            blocked_state()["until"] = time.time() + 900
            st.stop()

        st.cache_resource.clear()
        st.rerun()

def main():
    st.title("📊 Taiga Engineering Performance Dashboard")

    api, project, maps = init_connection()
    
    if api:
        st.sidebar.success(f"Connected to: {project.name}")
        
        # --- NEW: MANUAL SYNC STRATEGY ---
        st.sidebar.header("🔄 Data Management")
        
        # 1. Initialize session state for data if it doesn't exist
        if 'df_raw' not in st.session_state:
            st.session_state['df_raw'] = None

        # 2. Add Sync Button
        if st.sidebar.button("Sync Data from Taiga"):
            with st.spinner("Fetching data safely (this may take a minute)..."):
                # Call the fetcher directly (make sure your fetcher has the 1.0s sleep!)
                new_data = fetch_fresh_data(api, project, maps)
                st.session_state['df_raw'] = new_data
                st.sidebar.success("✅ Data Synced!")

        # 3. Check if we have data to display
        if st.session_state['df_raw'] is None:
            st.warning("No data loaded. Please click 'Sync Data from Taiga' in the sidebar to begin.")
            st.stop()
        
        # Use the data stored in session state
        df_raw = st.session_state['df_raw']
        # --- END SYNC STRATEGY ---

        # Filters in Sidebar
        st.sidebar.header("Filters")
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
                plt.clf() 
            with col2:
                st.subheader("Prioritas Pekerjaan")
                viz.plot_priority_pie()
                st.pyplot(plt.gcf())
                plt.clf()

            st.markdown("---")
            st.header("📌 Project Assignment Matrix")
            fig, report_df = viz.plot_project_assignment_matrix()
            if fig:
                st.pyplot(fig)
                plt.clf()
                st.subheader("📋 Project Assignment Details")
                projects = report_df['Project'].unique()
                for project_name in projects:
                    with st.expander(f"Project: {project_name}"):
                        group = report_df[report_df['Project'] == project_name]
                        st.table(group[['Subject', 'Assigned To', 'Status']].sort_values('Status'))
            else:
                st.warning("⚠️ 'Project' column missing. Click 'Sync Data' to refresh.")

        with tab2:
            st.header("Efficiency, Bottleneck & Work Connections")
            st.subheader("Koneksi: Tipe Proyek vs Tipe Pekerjaan")
            viz.plot_connection_heatmap()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf() 
            st.markdown("---")
            st.subheader("Efficiency by Priority")
            viz.plot_efficiency_by_priority()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf()
            st.markdown("---")
            st.subheader("Bottleneck Analysis (Avg Time per Phase)")
            viz.plot_bottleneck_analysis()
            st.pyplot(plt.gcf(), use_container_width=True)
            plt.clf()

        with tab3:
            st.header("Personnel Performance & Velocity")
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
            st.dataframe(perf.drop(columns=['In progress_mins']).sort_values('Total Unit Pekerjaan', ascending=False), use_container_width=True)
            
            st.markdown("---")
            st.subheader("🌡️ Heatmap Efisiensi (Waktu per Poin)")
            fig_heatmap = viz.plot_bottleneck_heatmap()
            st.pyplot(fig_heatmap, use_container_width=True)
            plt.clf()

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
        st.error("🛑 **Access Temporarily Blocked by Taiga Firewall.**")
        st.info("Please wait at least 15 minutes. The firewall detected too many requests.")
        st.stop()

if __name__ == "__main__":
    main()
