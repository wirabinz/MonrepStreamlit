# modules/visualizer.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.ticker import MaxNLocator, FuncFormatter

class TaigaVisualizer:
    def __init__(self, df, month=None, year=None):
        # Apply modern Apple-like styling globally
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        plt.rcParams['axes.edgecolor'] = '#f0f0f0'
        plt.rcParams['axes.labelcolor'] = '#333333'
        plt.rcParams['text.color'] = '#333333'
        plt.rcParams['font.family'] = 'sans-serif'
        
        # 1. Konversi ke datetime agar bisa difilter
        if 'Created Date' in df.columns:
            df['Created Date'] = pd.to_datetime(df['Created Date'])
            if year:
                df = df[df['Created Date'].dt.year == year]
            if month:
                target_months = self._parse_month_input(month)
                df = df[df['Created Date'].dt.month.isin(target_months)]

        # Filter awal untuk mengecualikan data "Not specified"
        self.df = df[
            (df['Project Type'] != "Not specified") & 
            (df['Work Type'] != "Not specified") &
            (df['Priority'] != "Not specified")
        ].copy()
        
        self.target_statuses = ['To Do', 'In progress', 'Peer Review', 'Need Approval', 'Approved']
        self._prepare_data()

    def _parse_month_input(self, month):
        if isinstance(month, int): return [month]
        if isinstance(month, list): return month
        if isinstance(month, str) and 'to' in month.lower():
            parts = month.lower().split('to')
            return list(range(int(parts[0]), int(parts[1]) + 1))
        return []

    def _clean_text(self, text):
        if pd.isna(text) or text == "": return text
        return str(text).replace('_', ' ').title()

    def _duration_to_minutes(self, duration_str):
        if pd.isna(duration_str) or duration_str in ["0m", "", "Not specified"]:
            return 0
        total = 0
        parts = str(duration_str).split()
        for part in parts:
            if 'd' in part: total += int(part.replace('d', '')) * 9 * 60
            elif 'h' in part: total += int(part.replace('h', '')) * 60
            elif 'm' in part: total += int(part.replace('m', ''))
        return total

    def _format_mins_to_hm(self, x, pos=None):
        hours = int(x // 60)
        minutes = int(x % 60)
        return f"{hours}h {minutes}m"

    def _format_mins_to_dhm(self, x):
        """1 Day = 9 Office Hours (540 minutes)"""
        mins_in_day = 540 
        
        days = int(x // mins_in_day)
        remaining_mins_after_days = x % mins_in_day
        
        rem_hours = int(remaining_mins_after_days // 60)
        rem_mins = int(remaining_mins_after_days % 60)
        
        res = []
        if days > 0: res.append(f"{days}d")
        if rem_hours > 0: res.append(f"{rem_hours}h")
        res.append(f"{rem_mins}m")
        return " ".join(res)

    def _prepare_data(self):
        self.df['Assigned To'] = self.df['Assigned To'].apply(self._clean_text)
        self.df['Project Type'] = self.df['Project Type'].apply(self._clean_text)
        self.df['Work Type'] = self.df['Work Type'].apply(self._clean_text)
        self.df['Points'] = pd.to_numeric(self.df['Points'], errors='coerce').fillna(1).replace(0, 1)
        if 'Project' in self.df.columns:
            self.df['Project'] = self.df['Project'].apply(self._clean_text)

        for status in self.target_statuses:
            col_mins = f'{status}_mins'
            if status in self.df.columns:
                self.df[col_mins] = self.df[status].apply(self._duration_to_minutes)
            else:
                self.df[col_mins] = 0
        
        self.df['Mins_Per_Unit'] = self.df['In progress_mins'] / self.df['Points']

    def _apply_modern_style(self, ax):
        sns.despine(ax=ax, left=True, bottom=True)
        ax.grid(True, axis='x', linestyle='--', alpha=0.3)
        ax.tick_params(colors='#666666', labelsize=10)

    def _add_labels(self, ax, is_horizontal=False, is_time=False):
        for p in ax.patches:
            val = p.get_width() if is_horizontal else p.get_height()
            if val <= 0 or np.isnan(val): continue
            label = self._format_mins_to_hm(val) if is_time else f'{val:.0f}'
            if is_horizontal:
                ax.annotate(label, (p.get_width(), p.get_y() + p.get_height() / 2.),
                            ha='left', va='center', xytext=(8, 0), textcoords='offset points', color='#555555')
            else:
                ax.annotate(label, (p.get_x() + p.get_width() / 2., p.get_height()),
                            ha='center', va='bottom', xytext=(0, 8), textcoords='offset points', color='#555555')

    def plot_status_distribution(self):
        plt.figure(figsize=(10, 5))
        ax = sns.countplot(data=self.df, y='Status', hue='Status', palette='pastel', legend=False)
        self._add_labels(ax, is_horizontal=True)
        self._apply_modern_style(ax)
        plt.title('Status Distribusi', pad=20, weight='bold')
        

    def plot_priority_pie(self):
        plt.figure(figsize=(7, 7))
        
        # 1. Define colors and get counts
        p_colors = {'urgent': '#ff6b6b', 'moderate': '#ffd93d', 'low': '#6bcb77'}
        p_counts = self.df['Priority'].value_counts()
        total_cards = len(self.df) # Total ID/Card counts

        # 2. Create the donut chart
        # We hide the labels on the wedges to use the legend instead
        plt.pie(p_counts, labels=None, autopct='%1.1f%%', startangle=140,
                colors=[p_colors.get(x, '#eee') for x in p_counts.index], 
                pctdistance=0.85, wedgeprops={'edgecolor': 'white', 'linewidth': 3})
        
        # 3. Add the center circle and "Total Kartu" text
        center_circle = plt.Circle((0,0), 0.70, fc='white')
        plt.gca().add_artist(center_circle)
        
        # Display Total Kartu in the center
        plt.text(0, 0, f'Total Kartu\n{total_cards}', ha='center', va='center', 
                 weight='bold', fontsize=14, color='#333333')

        # 4. Create a custom legend showing numbers
        # Format: "Urgent (5)"
        legend_labels = [f'{self._clean_text(idx)} ({p_counts[idx]})' for idx in p_counts.index]
        plt.legend(legend_labels, title="Prioritas", loc="center left", 
                   bbox_to_anchor=(1, 0, 0.5, 1), frameon=False)

        plt.title('Prioritas Pekerjaan', weight='bold', pad=20)
        

    def show_performance_table(self):
        perf = self.df.groupby('Assigned To').agg({
            'ID': 'count',
            'Points': 'sum',
            'In progress_mins': 'sum'
        }).rename(columns={'ID': 'Jumlah Kartu', 'Points': 'Total Unit Pekerjaan'})

        # New Days Hours Minutes Format
        perf['Total Durasi In Progress'] = perf['In progress_mins'].apply(self._format_mins_to_dhm)
        perf['Efisiensi (Waktu/Unit)'] = (perf['In progress_mins'] / perf['Total Unit Pekerjaan']).apply(self._format_mins_to_hm)
        
        perf['Tipe Proyek'] = self.df.groupby('Assigned To')['Project Type'].apply(lambda x: ', '.join(x.unique()))
        perf['Tipe Pekerjaan'] = self.df.groupby('Assigned To')['Work Type'].apply(lambda x: ', '.join(x.unique()))
        
        # Drop raw minutes before display
        display_df = perf.drop(columns=['In progress_mins'])
        
        print("\n📊 LAPORAN PERFORMA PERSONIL")
        # display(display_df.sort_values('Total Unit Pekerjaan', ascending=False))

    def plot_priority_mix_stacked(self):
        plt.figure(figsize=(12, 6))
        mix = self.df.groupby(['Assigned To', 'Priority'])['Points'].sum().unstack().fillna(0)
        available_cols = [c for c in ['low', 'moderate', 'urgent'] if c in mix.columns]
        mix = mix[available_cols]
        color_map = {'low': '#6bcb77', 'moderate': '#ffd93d', 'urgent': '#ff6b6b'}
        
        ax = mix.plot(kind='barh', stacked=True, ax=plt.gca(), 
                      color=[color_map[c] for c in available_cols], edgecolor='white', linewidth=1)
        
        self._apply_modern_style(plt.gca())
        plt.title('Komposisi Prioritas per Personil', pad=20, weight='bold')
        plt.legend(title='Priority', bbox_to_anchor=(1.05, 1), loc='upper left', frameon=False)
        

    def plot_efficiency_by_priority(self):
            """Menampilkan rata-rata waktu per unit berdasarkan prioritas dengan gaya modern"""
            plt.figure(figsize=(10, 5))
            
            # Mengambil rata-rata menit per unit dan diurutkan berdasarkan prioritas
            eff_data = self.df.groupby('Priority')['Mins_Per_Unit'].mean().reindex(['urgent', 'moderate', 'low']).dropna()
            
            # Palet warna Apple-like
            p_colors = {'urgent': '#ff6b6b', 'moderate': '#ffd93d', 'low': '#6bcb77'}
            
            ax = sns.barplot(x=eff_data.index, y=eff_data.values, hue=eff_data.index, 
                             palette=p_colors, legend=False)
            
            # Tambahkan label waktu (Hh Mm) di atas bar
            self._add_labels(ax, is_time=True)
            
            # Terapkan gaya modern dan format sumbu Y
            self._apply_modern_style(ax)
            ax.yaxis.set_major_formatter(FuncFormatter(self._format_mins_to_hm))
            
            plt.title('Rata-rata Waktu per Unit Pekerjaan', pad=20, weight='bold')
            plt.ylabel('Durasi (Jam & Menit)')
            
    
    def plot_bottleneck_analysis(self):
        """Analisis Bottleneck untuk setiap fase proses"""
        plt.figure(figsize=(12, 5))
        
        # Menghitung rata-rata waktu untuk setiap status target
        avg_times = [self.df[f'{s}_mins'].mean() for s in self.target_statuses]
        
        # Menggunakan warna biru muda yang bersih (Apple-style)
        ax = plt.gca()
        bars = ax.bar(self.target_statuses, avg_times, color='#74b9ff', edgecolor='white', linewidth=1)
        
        # Tambahkan label waktu di atas bar
        for bar in bars:
            yval = bar.get_height()
            if yval > 0:
                ax.text(bar.get_x() + bar.get_width()/2, yval + 5, 
                        self._format_mins_to_hm(yval), 
                        va='bottom', ha='center', color='#555555', fontsize=9)
        
        # Terapkan gaya modern dan format sumbu Y
        self._apply_modern_style(ax)
        ax.yaxis.set_major_formatter(FuncFormatter(self._format_mins_to_hm))
        
        plt.title('Analisis Bottleneck: Rata-rata Waktu per Fase', pad=20, weight='bold')
        plt.ylabel('Durasi (Jam & Menit)')
        plt.xticks(rotation=0) # Tetap horizontal agar bersih
        

    def plot_total_work_units(self):
        """The New Graph: Plotting 'Total Unit Pekerjaan' per Personnel"""
        plt.figure(figsize=(10, 6))
        summary = self.df.groupby('Assigned To')['Points'].sum().sort_values()
        ax = sns.barplot(x=summary.values, y=summary.index, hue=summary.index, palette='pastel', legend=False)
        self._add_labels(ax, is_horizontal=True)
        self._apply_modern_style(ax)
        plt.title('Total Unit Pekerjaan (Poin) per Personil', pad=20, weight='bold')
        plt.xlabel('Jumlah Unit Pekerjaan')
        

    def plot_connection_heatmap(self):
        """Visualizing the relationship between Project Type and Work Type"""
        plt.figure(figsize=(12, 8))
        
        # Create the pivot table for the heatmap
        pivot_df = self.df.pivot_table(
            index='Work Type', 
            columns='Project Type', 
            values='Subject', 
            aggfunc='count'
        ).fillna(0)
        
        # Plot using a clean, modern color map
        sns.heatmap(
            pivot_df, 
            annot=True, 
            fmt=".0f", 
            cmap="YlGnBu", 
            cbar=False, 
            linewidths=.5, 
            annot_kws={"size": 10}
        )
        
        plt.title('Koneksi: Tipe Proyek vs Tipe Pekerjaan', pad=20, weight='bold')
        plt.xlabel('Tipe Proyek', labelpad=10)
        plt.ylabel('Tipe Pekerjaan', labelpad=10)
        
        # Modern cleanup: Remove tick marks
        plt.tick_params(axis='both', which='both', length=0)

    def plot_project_assignment_matrix(self):
        """
        Horizontal Bar Chart: Optimized for long project names and 
        compact vertical space (narrower vertically).
        """
        if 'Project' not in self.df.columns:
            return None, None 

        # 1. Prepare and Sort Data
        report_df = self.df[['Project', 'Subject', 'Assigned To', 'Status']].copy()
        
        # Robust replacement for "Various Projects"
        report_df['Project'] = report_df['Project'].replace({
            'Not specified': 'Various Projects',
            'not specified': 'Various Projects',
            'Not Specified': 'Various Projects'
        })

        status_order = ['To Do', 'In progress', 'Peer Review', 'Need Approval','Approved', 'Submitted']
        report_df['Status'] = pd.Categorical(report_df['Status'], categories=status_order, ordered=True)
        
        # 2. Setup Plotting (Horizontal and Narrow)
        n_projects = len(report_df['Project'].unique())
        # Compact vertical scaling: multiplier reduced to 0.45 for a narrower profile
        fig_height = max(3, n_projects * 0.45) 
        
        fig = plt.figure(figsize=(12, fig_height))
        
        # Use y='Project' for horizontal layout to accommodate long names
        ax = sns.countplot(
            data=report_df, 
            y='Project', 
            hue='Status', 
            hue_order=status_order, 
            palette='pastel'
        )

        # 3. Horizontal Annotations (Labels next to dots/bars)
        for p in ax.patches:
            width = p.get_width()
            if width > 0:
                ax.annotate(f'{int(width)}', 
                            (width, p.get_y() + p.get_height() / 2.), 
                            ha='left', va='center', 
                            xytext=(5, 0), textcoords='offset points',
                            fontsize=9, color='#555555', weight='semibold')

        self._apply_modern_style(ax)
        
        # Cleanup for Apple-style: focus on labels instead of axis lines
        ax.xaxis.set_visible(False) 
        sns.despine(left=False, bottom=True)
        
        plt.title('Card Volume per Project & Status', pad=15, weight='bold', fontsize=12)
        plt.ylabel('')
        plt.legend(title='Status', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False, fontsize=9)
        plt.tight_layout()

        # --- PART B: Return values (Exact match for app.py) ---
        return fig, report_df
    
    def plot_personnel_bottleneck_comparison(self):
        """Analisis Bottleneck per Personil dalam satu grafik"""
        # Maintain your existing logic...
        plt.figure(figsize=(14, 7))
        status_cols = [f'{s}_mins' for s in self.target_statuses]
        melted_df = self.df.melt(
            id_vars=['Assigned To'], 
            value_vars=status_cols, 
            var_name='Status', 
            value_name='Minutes'
        )
        melted_df['Status'] = melted_df['Status'].str.replace('_mins', '')
        
        ax = sns.barplot(
            data=melted_df, 
            x='Assigned To', 
            y='Minutes', 
            hue='Status', 
            hue_order=self.target_statuses,
            palette='pastel',
            errorbar=None
        )
        
        self._apply_modern_style(ax)
        ax.yaxis.set_major_formatter(FuncFormatter(self._format_mins_to_hm))
        
        plt.title('Perbandingan Bottleneck Antar Personil (Rata-rata Waktu)', pad=25, weight='bold')
        plt.ylabel('Durasi (Jam & Menit)')
        plt.xlabel('Nama Personil')
        plt.xticks(rotation=45)
        plt.legend(title='Fase Kerja', bbox_to_anchor=(1.05, 1), loc='upper left', frameon=False)
        plt.tight_layout()
        
        return plt.gcf() # RETURN instead of plt.show()

    def plot_bottleneck_heatmap(self):
        """Efficiency Heatmap: Rata-rata menit per Unit Poin (Minutes per Point)."""
        # Maintain your existing logic...
        plt.figure(figsize=(14, 8))
        status_cols = [f'{s}_mins' for s in self.target_statuses]
        agg_data = self.df.groupby('Assigned To').agg({
            'Points': 'sum',
            **{col: 'sum' for col in status_cols}
        })
        
        efficiency_data = pd.DataFrame(index=agg_data.index)
        for s in self.target_statuses:
            efficiency_data[s] = agg_data[f'{s}_mins'] / agg_data['Points'].replace(0, 1)
        
        ax = sns.heatmap(
            efficiency_data, 
            annot=True, 
            fmt=".1f", 
            cmap="coolwarm", 
            cbar_kws={'label': 'Menit per Unit Poin'},
            linewidths=0.5,
            annot_kws={"size": 10}
        )
        
        for text in ax.texts:
            try:
                val = float(text.get_text())
                if val > 0:
                    text.set_text(self._format_mins_to_hm(val))
                else:
                    text.set_text("-")
            except ValueError:
                continue

        plt.title('Heatmap Efisiensi: Waktu per Unit Pekerjaan ', pad=25, weight='bold', fontsize=16)
        plt.xlabel('Fase Kerja', labelpad=15)
        plt.ylabel('Nama Personil', labelpad=15)
        plt.tick_params(axis='both', which='both', length=0)
        plt.tight_layout()
        
        return plt.gcf() # RETURN instead of plt.show()