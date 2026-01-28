# modules/fetcher.py
import pandas as pd
from concurrent.futures import ThreadPoolExecutor # New import for speed
from modules.processor import TaigaProcessor

class TaigaFetcher:
    def __init__(self, api, project, maps):
        self.api = api
        self.project = project
        self.maps = maps
        self.processor = TaigaProcessor()

        # Fetch all statuses once at the start
        project_statuses = self.api.user_story_statuses.list(project=self.project.id)
        self.status_map = {s.id: s.name for s in project_statuses}
    
    def fetch_single_story_data(self, story):
        """Helper function to fetch history and extract data for one story."""
        # This part runs in parallel for multiple stories
        history_entries = self.api.history.user_story.get(story.id)
        return self._extract_story_data(story, history_entries)

    def get_all_stories(self):
        """Get all user stories as DataFrame using parallel fetching."""
        stories = self.api.user_stories.list(project=self.project.id, pagination=False)
        
        # Use ThreadPoolExecutor to fetch history for stories in parallel
        # Adjust max_workers based on your internet/server capacity (5-10 is usually safe)
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(self.fetch_single_story_data, stories))
        
        return pd.DataFrame(results)
    
    def _extract_story_data(self, story, history_entries):
        """Extract story data with clean integer points (default 1)"""
        tags = getattr(story, 'tags', []) or []
        
        # 1. Extract Tag Categories
        priority = self._extract_tag(tags, 'priority')
        project_type = self._extract_tag(tags, 'project')
        work_type = self._extract_tag(tags, 'work')
        
        # 2. Get durations from processor
        durations = self.processor.analyze_time(history_entries)
        
        # 3. IMPROVED POINTS EXTRACTION
        # Get raw total points, defaulting to None to catch unassigned stories
        raw_points = getattr(story, 'total_points', None)
        
        if raw_points is None:
            # Default to 1 if point is None or Not Assigned
            real_points = 1
        else:
            try:
                # Convert to float first (to handle strings like "1.0"), then to int
                real_points = int(float(raw_points))
                # If the value is 0 (often Taiga's default for "Closed" points), default to 1
                if real_points == 0:
                    real_points = 1
            except (ValueError, TypeError):
                real_points = 1

        # 4. Extract assigned users
        assigned_ids = getattr(story, 'assigned_users', []) or []
        assigned_names = [self.maps['members'].get(u_id, f"User:{u_id}") for u_id in assigned_ids]
        
        result = {
            'ID': getattr(story, 'id', None),
            'Ref': f"#{getattr(story, 'ref', 'N/A')}",
            'Subject': getattr(story, 'subject', 'No Subject'),
            'Status': self._get_status_name(story),
            'Created Date': getattr(story, 'created_date', None),
            'Assigned To': ', '.join(assigned_names) if assigned_names else 'Unassigned',
            'Priority': priority,
            'Project Type': project_type,
            'Work Type': work_type,
            'Points': real_points  # Now returns a clean integer
        }
        
        result.update(durations)
        return result

    def _extract_tag(self, tags, category):
        """Corrected tag extraction with category scoping"""
        if not tags:
            return "Not specified"

        priority_keywords = {'urgent', 'moderate', 'low'}
        WORK_COLOR = '#51CFD3'
        PROJECT_COLOR = '#5178D3'

        for tag in tags:
            if tag is None: continue
            
            if isinstance(tag, list) and len(tag) >= 2:
                label = str(tag[0])
                color = str(tag[1]).upper() 
                
                if category == 'priority' and label.lower() in priority_keywords:
                    return label.lower()
                elif category == 'project' and color == PROJECT_COLOR:
                    return label
                elif category == 'work' and color == WORK_COLOR:
                    return label
            else:
                tag_str = str(tag).lower()
                if f"{category.lower()}:" in tag_str:
                    parts = str(tag).split(':', 1)
                    return parts[1].strip() if len(parts) > 1 else str(tag).strip()
        return "Not specified"

    def _get_status_name(self, story):
        """Improved status name extraction using pre-loaded status_map."""
        status_info = getattr(story, 'status_extra', None)
        if status_info and status_info.get('name'):
            return status_info.get('name')
            
        status_id = getattr(story, 'status', None)
        return self.status_map.get(status_id, f"Unknown ID: {status_id}")