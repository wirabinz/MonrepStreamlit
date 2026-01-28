
# modules/processor.py
import pandas as pd
import holidays
from datetime import datetime, timedelta, timezone
import pytz
import streamlit as st

class TaigaProcessor:
    def __init__(self):
        # Access secrets directly instead of using Config class
        self.local_tz = pytz.timezone(st.secrets["TIMEZONE"])
        self.holidays = self._load_holidays()
    
    def _load_holidays(self):
        current_year = datetime.now().year
        years = [current_year-1, current_year, current_year + 1]
        
        holiday_dates = []
        for year in years:
            # Access country code from secrets
            country_holidays = holidays.CountryHoliday(st.secrets["COUNTRY_CODE"], years=[year])
            holiday_dates.extend(list(country_holidays.keys()))
        
        return set(holiday_dates)
    
    def analyze_time(self, history_entries):
        """Analyze time spent in each status, handling reversions correctly"""
        target_statuses = ['To Do','In progress', 'Peer Review', 'Need Approval', 'Approved']
        durations_minutes = {status: 0 for status in target_statuses}
        
        if not history_entries:
            return {status: "0m" for status in target_statuses}
        
        # 1. Sort history chronologically
        status_changes = []
        for entry in history_entries:
            v_diff = entry.get('values_diff', {})
            if 'status' in v_diff:
                status_changes.append({
                    'Date': pd.to_datetime(entry.get('created_at')),
                    'To': v_diff['status'][1]
                })
        
        if not status_changes:
            return {status: "0m" for status in target_statuses}
        
        df_h = pd.DataFrame(status_changes).sort_values('Date').reset_index(drop=True)
        
        # 2. Use a "Pointer" logic to calculate intervals between changes
        for i in range(len(df_h)):
            current_status = df_h.iloc[i]['To']
            start_time = df_h.iloc[i]['Date']
            
            # Determine the end of this specific interval
            if i + 1 < len(df_h):
                end_time = df_h.iloc[i+1]['Date']
            else:
                # If it's the current status, calculate up to right now
                end_time = datetime.now(timezone.utc)
                
            # 3. Add to the accumulator ONLY if it's one of our tracked statuses
            if current_status in durations_minutes:
                interval_mins = self._calculate_office_minutes(start_time, end_time)
                # Use max(0, ...) to safety-guard against any clock drift/API anomalies
                durations_minutes[current_status] += max(0, interval_mins)
                
        # 4. Format the final accumulated totals
        return {s: self._format_duration(durations_minutes[s]) for s in target_statuses}
    
    def _calculate_office_minutes(self, start_utc, end_utc):
        if pd.isna(start_utc) or pd.isna(end_utc) or start_utc >= end_utc:
            return 0
        
        start_local = start_utc.astimezone(self.local_tz)
        end_local = end_utc.astimezone(self.local_tz)
        total_minutes = 0
        current_day = start_local.date()
        
        while current_day <= end_local.date():
            if current_day.weekday() < 5 and current_day not in self.holidays:
                # Use secrets for office hours
                work_start = self.local_tz.localize(
                    datetime.combine(current_day, datetime.min.time().replace(
                        hour=int(st.secrets["OFFICE_HOURS_START_HOUR"]), 
                        minute=int(st.secrets["OFFICE_HOURS_START_MIN"])
                    ))
                )
                work_end = self.local_tz.localize(
                    datetime.combine(current_day, datetime.min.time().replace(
                        hour=int(st.secrets["OFFICE_HOURS_END_HOUR"]), 
                        minute=int(st.secrets["OFFICE_HOURS_END_MIN"])
                    ))
                )
                
                overlap_start = max(start_local, work_start)
                overlap_end = min(end_local, work_end)
                
                if overlap_end > overlap_start:
                    total_minutes += (overlap_end - overlap_start).total_seconds() / 60
            current_day += timedelta(days=1)
        return total_minutes
    
    def _format_duration(self, minutes):
        """Format minutes to readable string (1 day = 9 hours)"""
        if minutes == 0:
            return "0m"
        
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours >= 9:
            days = hours // 9
            rem_hours = hours % 9
            return f"{days}d {rem_hours}h {mins}m"
        
        return f"{hours}h {mins}m"


# # modules/processor.py
# import pandas as pd
# import holidays
# from datetime import datetime, timedelta, timezone
# import pytz
# from config import Config

# class TaigaProcessor:
#     def __init__(self):
#         self.local_tz = pytz.timezone(Config.TIMEZONE)
#         self.holidays = self._load_holidays()
    
#     def _load_holidays(self):
#         """Load holidays"""
#         current_year = datetime.now().year
#         years = [current_year, current_year + 1]
        
#         holiday_dates = []
#         for year in years:
#             country_holidays = holidays.CountryHoliday(Config.COUNTRY_CODE, years=[year])
#             holiday_dates.extend(list(country_holidays.keys()))
        
#         return set(holiday_dates)
    
#     def analyze_time(self, history_entries):
#         """Analyze time spent in each status"""
#         if not history_entries:
#             return pd.DataFrame()
        
#         # Extract status changes
#         status_changes = []
#         for entry in history_entries:
#             v_diff = entry.get('values_diff', {})
#             if 'status' in v_diff:
#                 status_changes.append({
#                     'Date': pd.to_datetime(entry.get('created_at')),
#                     'From': v_diff['status'][0],
#                     'To': v_diff['status'][1]
#                 })
        
#         if not status_changes:
#             return pd.DataFrame()
        
#         df = pd.DataFrame(status_changes).sort_values('Date')
        
#         # Calculate durations
#         results = []
#         target_statuses = ['In progress', 'Peer Review', 'Need Approval', 'Approved']
        
#         for status in target_statuses:
#             total_minutes = 0
#             status_entries = df[df['To'] == status].index
            
#             for idx in status_entries:
#                 start = df.iloc[idx]['Date']
#                 end = df.iloc[idx + 1]['Date'] if idx + 1 < len(df) else datetime.now(timezone.utc)
#                 total_minutes += self._calculate_office_minutes(start, end)
            
#             results.append({
#                 'Status': status,
#                 'Total Minutes': total_minutes,
#                 'Formatted': self._format_duration(total_minutes)
#             })
        
#         return pd.DataFrame(results)
    
#     def _calculate_office_minutes(self, start_utc, end_utc):
#         """Calculate office minutes between two timestamps"""
#         if pd.isna(start_utc) or pd.isna(end_utc) or start_utc >= end_utc:
#             return 0
        
#         # Convert to local time
#         start_local = start_utc.astimezone(self.local_tz)
#         end_local = end_utc.astimezone(self.local_tz)
        
#         total_minutes = 0
#         current_day = start_local.date()
#         end_day = end_local.date()
        
#         while current_day <= end_day:
#             # Check if it's a workday
#             if current_day.weekday() < 5 and current_day not in self.holidays:
#                 # Define office hours for this day
#                 work_start = self.local_tz.localize(
#                     datetime.combine(current_day, datetime.min.time().replace(hour=Config.OFFICE_START))
#                 )
#                 work_end = self.local_tz.localize(
#                     datetime.combine(current_day, datetime.min.time().replace(hour=Config.OFFICE_END))
#                 )
                
#                 # Calculate overlap
#                 overlap_start = max(start_local, work_start)
#                 overlap_end = min(end_local, work_end)
                
#                 if overlap_end > overlap_start:
#                     total_minutes += (overlap_end - overlap_start).total_seconds() / 60
            
#             current_day += timedelta(days=1)
        
#         return total_minutes
    
#     def _format_duration(self, minutes):
#         """Format minutes to readable string"""
#         if minutes == 0:
#             return "0m"
        
#         hours = int(minutes // 60)
#         mins = int(minutes % 60)
        
#         if hours >= 9:
#             days = hours // 9
#             rem_hours = hours % 9
#             return f"{days}d {rem_hours}h {mins}m"
        
#         return f"{hours}h {mins}m"
    
#     def get_status_history(self, history_entries):
#         """Get chronological status history"""
#         if not history_entries:
#             return pd.DataFrame()
        
#         history_list = []
#         for entry in history_entries:
#             v_diff = entry.get('values_diff', {})
#             if 'status' in v_diff:
#                 history_list.append({
#                     'Date': entry.get('created_at'),
#                     'User': entry.get('user', {}).get('name', 'System'),
#                     'From': v_diff['status'][0],
#                     'To': v_diff['status'][1]
#                 })
        
#         if history_list:
#             df = pd.DataFrame(history_list)
#             df['Date'] = pd.to_datetime(df['Date'])
#             return df.sort_values('Date')
        
#         return pd.DataFrame()