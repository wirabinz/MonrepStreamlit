import streamlit as st
from taiga import TaigaAPI

class TaigaAuth:
    def __init__(self):
        self.api = None
        self.project = None
        
    def login(self):
        # Using Streamlit Secrets instead of Config class
        username = st.secrets["TAIGA_USERNAME"]
        password = st.secrets["TAIGA_PASSWORD"]
        url = st.secrets["TAIGA_URL"]

        try:
            # Try basic format first (fastest for api.taiga.io)
            base_url = url.replace('/api/v1/', '').rstrip('/')
            self.api = TaigaAPI(host=base_url)
            self.api.auth(username=username, password=password)
            return True
        except Exception:
            try:
                self.api = TaigaAPI(host=url.rstrip('/'))
                self.api.auth(username=username, password=password)
                return True
            except Exception as e:
                st.error(f"Authentication Failed: {e}")
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