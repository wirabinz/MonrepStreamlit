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

# --- CONNECTION CACHING ---
@st.cache_resource(ttl=3600) # Reduced to 1 hour to stay safe with token expiry
def init_connection():
    auth = TaigaAuth()
    try:
        if auth.login():
            project = auth.get_project()
            maps = auth.get_maps()
            # Double check the connection works before returning
            auth.api.me() 
            return auth.api, project, maps
    except Exception as e:
        # If we see the HTML robot page or a 401, clear cache instantly
        init_connection.clear()
        return None, None, None

# --- DATA FETCHING ---
def fetch_fresh_data(api, project, maps):
    """Pulls new data, but first verifies the session is still alive."""
    try:
        # Step 1: "Heartbeat" check - try a tiny API call
        api.me() 
    except Exception:
        # Step 2: If heartbeat fails, the token is likely expired.
        # Clear the connection cache and force the user to re-run
        st.cache_resource.clear()
        st.error("🔄 **Session Expired.** Re-authenticating... Please click 'Sync' again.")
        st.rerun()

    fetcher = TaigaFetcher(api, project, maps)
    return fetcher.get_all_stories()

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