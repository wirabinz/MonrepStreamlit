import streamlit as st
from taiga import TaigaAPI

class TaigaAuth:
    def __init__(self):
        self.api = None
        self.project = None

    def login(self):
        """Authenticate with Taiga API - Optimized for Streamlit"""
        try:
            # Use Streamlit secrets instead of external Config class
            url = st.secrets["TAIGA_URL"]
            username = st.secrets["TAIGA_USERNAME"]
            password = st.secrets["TAIGA_PASSWORD"]

            # 1. Try Basic Auth (No /api/v1/ suffix)
            base_url = url.split('/api/v1')[0].rstrip('/')
            print(f"🔐 Trying URL: {base_url}")
            
            self.api = TaigaAPI(host=base_url)
            self.api.auth(username=username, password=password)
            
            # Verify authentication by attempting a small request
            self.api.me.get() 
            print("✅ Authentication successful!")
            return True

        except Exception as e:
            # Fallback to standard auth if basic fails
            return self._try_standard_auth(url, username, password)

    def _try_standard_auth(self, url, username, password):
        """Standard fallback with full URL"""
        try:
            print("🔐 Trying standard authentication...")
            host_url = url.rstrip('/')
            self.api = TaigaAPI(host=host_url)
            self.api.auth(username=username, password=password)
            self.api.me.get() # Verification
            return True
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
            return False

    def get_project(self):
        if not self.api: return None
        slug = st.secrets["PROJECT_SLUG"]
        self.project = self.api.projects.get_by_slug(slug)
        return self.project

    def get_maps(self):
        if not self.project: return {}
        member_map = {m.id: m.full_name for m in self.project.members}
        return {'members': member_map}