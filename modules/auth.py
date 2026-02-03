import streamlit as st
from taiga import TaigaAPI

class TaigaAuth:
    def __init__(self):
        self.api = None
        self.project = None

    def login(self):
        """Authenticate with Taiga API using Streamlit secrets."""
        # Retrieve credentials directly from st.secrets
        username = st.secrets["TAIGA_USERNAME"]
        password = st.secrets["TAIGA_PASSWORD"]
        url = st.secrets["TAIGA_URL"]

        def verify_connection(api_instance):
            """Internal helper to verify the API returned valid data, not HTML."""
            try:
                # The 'me()' method returns a User object representing the logged-in user
                # Calling it serves as a lightweight health check for the connection
                api_instance.me() 
                return True
            except Exception as e:
                err_str = str(e).lower()
                # Check for common firewall/rate-limit indicators in the response
                if "<html>" in err_str or "doctype" in err_str or "bitninja" in err_str:
                    raise Exception(
                        "Access Blocked by Firewall: Taiga is returning an HTML challenge page. "
                        "Your IP might be temporarily rate-limited. Please wait 5-10 minutes."
                    )
                raise e

        try:
            # 1. Try Basic Format (removes /api/v1/ suffix for standard cloud instances)
            base_url = url.replace('/api/v1/', '').rstrip('/')
            self.api = TaigaAPI(host=base_url)
            self.api.auth(username=username, password=password)
            
            if verify_connection(self.api):
                print("✅ Authentication successful (Basic URL)!")
                return True
                
        except Exception as first_err:
            # If blocked by firewall, stop immediately to avoid further flagging
            if "Blocked by Firewall" in str(first_err):
                st.error(str(first_err))
                return False
                
            try:
                # 2. Fallback to Full URL (useful for some self-hosted instances)
                print("🔐 Attempting fallback with full URL...")
                self.api = TaigaAPI(host=url.rstrip('/'))
                self.api.auth(username=username, password=password)
                
                if verify_connection(self.api):
                    print("✅ Authentication successful (Fallback URL)!")
                    return True
            except Exception as final_err:
                error_msg = str(final_err)
                if "<html>" in error_msg.lower():
                    st.error("⚠️ Server returned HTML (Firewall block). Try again in 10 minutes.")
                else:
                    st.error(f"❌ Authentication Failed: {error_msg}")
                return False
            
    def get_project(self):
        if not self.api: return None
        slug = st.secrets["PROJECT_SLUG"]
        self.project = self.api.projects.get_by_slug(slug)
        return self.project

    def get_maps(self):
        if not self.project: return {}
        # Only fetch if not already in memory to save API calls
        if not hasattr(self, '_cached_maps'):
            member_map = {m.id: m.full_name for m in self.project.members}
            self._cached_maps = {'members': member_map}
        return self._cached_maps