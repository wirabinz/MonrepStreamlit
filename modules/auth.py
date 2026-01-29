import streamlit as st
from taiga import TaigaAPI

class TaigaAuth:
    def __init__(self):
        self.api = None
        self.project = None
        
    def login(self):
        """Authenticate with Taiga API using Streamlit secrets with firewall protection."""
        # Using Streamlit Secrets instead of Config class
        username = st.secrets["TAIGA_USERNAME"]
        password = st.secrets["TAIGA_PASSWORD"]
        url = st.secrets["TAIGA_URL"]
    
        def verify_connection(api_instance):
            """Internal helper to verify the API returned valid data, not HTML."""
            try:
                # A simple lightweight call to verify the token and response format
                api_instance.me.get()
                return True
            except Exception as e:
                err_str = str(e).lower()
                if "<html>" in err_str or "doctype" in err_str or "bitninja" in err_str:
                    raise Exception(
                        "Access Blocked by Firewall: Taiga is returning an HTML challenge page. "
                        "Your IP might be temporarily rate-limited. Please wait 5-10 minutes."
                    )
                raise e
    
        try:
            # Try basic format first (standard for api.taiga.io)
            base_url = url.replace('/api/v1/', '').rstrip('/')
            self.api = TaigaAPI(host=base_url)
            self.api.auth(username=username, password=password)
            
            # Verify that we actually have a JSON connection
            if verify_connection(self.api):
                return True
                
        except Exception as first_attempt_error:
            # If the first attempt failed due to a firewall block, don't try the second one immediately
            if "Blocked by Firewall" in str(first_attempt_error):
                st.error(str(first_attempt_error))
                return False
                
            try:
                # Fallback to the full URL suffix if the first way failed
                self.api = TaigaAPI(host=url.rstrip('/'))
                self.api.auth(username=username, password=password)
                
                if verify_connection(self.api):
                    return True
            except Exception as e:
                # Handle the error message for the UI
                error_msg = str(e)
                if "<html>" in error_msg.lower() or "bitninja" in error_msg.lower():
                    st.error("⚠️ Authentication Failed: The server returned an HTML block page (Firewall/Rate Limit).")
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
        member_map = {m.id: m.full_name for m in self.project.members}
        return {'members': member_map}