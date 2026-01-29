import streamlit as st
from taiga import TaigaAPI

class TaigaAuth:
    def __init__(self):
        self.api = None
        self.project = None
        
    # modules/auth.py

def login(self):
    username = st.secrets["TAIGA_USERNAME"]
    password = st.secrets["TAIGA_PASSWORD"]
    
    # Logic to ensure the URL is always just the base domain
    raw_url = st.secrets["TAIGA_URL"]
    base_url = raw_url.replace('/api/v1/', '').rstrip('/')
    
    try:
        # We manually use the base_url. 
        # The library will add /api/v1/ internally.
        self.api = TaigaAPI(host=base_url)
        self.api.auth(username=username, password=password)
        
        # Verify it's actually JSON and not an error page
        self.api.me.get() 
        return True
    except Exception as e:
        st.error(f"❌ Authentication Failed: {e}")
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