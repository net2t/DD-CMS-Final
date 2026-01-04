"""
Dynamic Dashboard Generator - Auto-Create Google Sheets Dashboard

Generates comprehensive dashboards from scraping data with:
- Run statistics and trends
- Profile state breakdown
- Phase 2 eligibility tracking
- Performance metrics
- Error analysis

Usage:
    from utils.dashboard_generator import DashboardGenerator
    
    dashboard = DashboardGenerator(sheets_manager)
    dashboard.create_or_update(stats, profiles_data)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import Counter

from utils.ui import log_msg


class DashboardGenerator:
    """
    Generate dynamic dashboards from scraping data.
    
    This class creates comprehensive dashboards in Google Sheets
    with statistics, trends, and visualizations.
    
    Example:
        >>> from utils.sheets_manager import SheetsManager
        >>> from utils.dashboard_generator import DashboardGenerator
        >>> 
        >>> sheets = SheetsManager()
        >>> dashboard = DashboardGenerator(sheets)
        >>> 
        >>> # After scraping run
        >>> dashboard.create_or_update(stats, profiles_data)
    """
    
    def __init__(self, sheets_manager):
        """
        Initialize dashboard generator.
        
        Args:
            sheets_manager: SheetsManager instance
        """
        self.sheets = sheets_manager
    
    def create_or_update(
        self,
        stats: Dict[str, Any],
        mode: str,
        duration: float,
        start_time: datetime,
        end_time: datetime
    ):
        """
        Create or update dashboard with latest data.
        
        Args:
            stats: Scraping statistics
            mode: Run mode (online/target/test)
            duration: Run duration in seconds
            start_time: Run start time
            end_time: Run end time
        
        Example:
            >>> stats = {
            ...     'success': 45,
            ...     'failed': 5,
            ...     'new': 30,
            ...     'updated': 15,
            ...     'phase2_ready': 40,
            ...     'phase2_not_eligible': 5
            ... }
            >>> dashboard.create_or_update(stats, 'target', 300, start, end)
        """
        log_msg("Generating dashboard data...", "INFO")
        
        # Generate dashboard sections
        summary = self._generate_summary(stats, mode, duration)
        profile_breakdown = self._analyze_profiles()
        phase2_analysis = self._analyze_phase2_eligibility()
        recent_trends = self._generate_recent_trends()
        
        # Update dashboard sheet
        self._update_dashboard_sheet(
            summary,
            profile_breakdown,
            phase2_analysis,
            recent_trends,
            start_time,
            end_time
        )
        
        log_msg("✅ Dashboard updated successfully", "OK")
    
    def _generate_summary(
        self,
        stats: Dict[str, Any],
        mode: str,
        duration: float
    ) -> Dict[str, Any]:
        """Generate run summary section."""
        return {
            'mode': mode.upper(),
            'total_processed': stats.get('success', 0) + stats.get('failed', 0),
            'success_count': stats.get('success', 0),
            'failure_count': stats.get('failed', 0),
            'success_rate': self._calculate_rate(
                stats.get('success', 0),
                stats.get('success', 0) + stats.get('failed', 0)
            ),
            'new_profiles': stats.get('new', 0),
            'updated_profiles': stats.get('updated', 0),
            'unchanged_profiles': stats.get('unchanged', 0),
            'duration_seconds': duration,
            'duration_formatted': self._format_duration(duration),
            'avg_time_per_profile': (
                duration / (stats.get('success', 0) + stats.get('failed', 0))
                if (stats.get('success', 0) + stats.get('failed', 0)) > 0
                else 0
            )
        }
    
    def _analyze_profiles(self) -> Dict[str, Any]:
        """Analyze profile states from Profiles sheet."""
        try:
            # Get all profiles
            all_data = self.sheets.profiles_ws.get_all_values()
            
            if len(all_data) <= 1:
                return {'error': 'No profile data'}
            
            headers = all_data[0]
            rows = all_data[1:]
            
            # Find status column
            try:
                status_idx = headers.index('STATUS')
            except ValueError:
                return {'error': 'STATUS column not found'}
            
            # Count statuses
            statuses = [
                row[status_idx].strip().upper()
                for row in rows
                if len(row) > status_idx and row[status_idx].strip()
            ]
            
            status_counts = Counter(statuses)
            
            # Calculate totals
            total = len(statuses)
            
            return {
                'total': total,
                'verified': status_counts.get('VERIFIED', 0),
                'unverified': status_counts.get('UNVERIFIED', 0),
                'banned': status_counts.get('BANNED', 0),
                'normal': status_counts.get('NORMAL', 0),
                'verified_rate': self._calculate_rate(
                    status_counts.get('VERIFIED', 0), total
                ),
                'banned_rate': self._calculate_rate(
                    status_counts.get('BANNED', 0), total
                )
            }
        
        except Exception as e:
            log_msg(f"Error analyzing profiles: {e}", "ERROR")
            return {'error': str(e)}
    
    def _analyze_phase2_eligibility(self) -> Dict[str, Any]:
        """Analyze Phase 2 eligibility from Profiles sheet."""
        try:
            all_data = self.sheets.profiles_ws.get_all_values()
            
            if len(all_data) <= 1:
                return {'error': 'No profile data'}
            
            headers = all_data[0]
            rows = all_data[1:]
            
            # Find Phase 2 column
            try:
                phase2_idx = headers.index('PHASE 2')
            except ValueError:
                return {'error': 'PHASE 2 column not found'}
            
            # Count eligibility
            phase2_values = [
                row[phase2_idx].strip()
                for row in rows
                if len(row) > phase2_idx and row[phase2_idx].strip()
            ]
            
            ready_count = sum(1 for v in phase2_values if 'ready' in v.lower())
            not_eligible_count = sum(1 for v in phase2_values if 'not eligible' in v.lower())
            total = len(phase2_values)
            
            return {
                'total': total,
                'ready': ready_count,
                'not_eligible': not_eligible_count,
                'ready_rate': self._calculate_rate(ready_count, total)
            }
        
        except Exception as e:
            log_msg(f"Error analyzing Phase 2 eligibility: {e}", "ERROR")
            return {'error': str(e)}
    
    def _generate_recent_trends(self) -> Dict[str, Any]:
        """Analyze recent trends from Dashboard sheet."""
        try:
            dashboard_data = self.sheets.dashboard_ws.get_all_values()
            
            if len(dashboard_data) <= 1:
                return {'error': 'No dashboard history'}
            
            # Get last 10 runs (excluding header)
            recent_runs = dashboard_data[1:11]  # Rows 2-11
            
            if not recent_runs:
                return {'error': 'No run history'}
            
            # Extract metrics (assuming standard column order)
            try:
                success_values = [int(row[3]) for row in recent_runs if len(row) > 3 and row[3].isdigit()]
                failed_values = [int(row[4]) for row in recent_runs if len(row) > 4 and row[4].isdigit()]
                
                avg_success = sum(success_values) / len(success_values) if success_values else 0
                avg_failed = sum(failed_values) / len(failed_values) if failed_values else 0
                
                return {
                    'runs_analyzed': len(recent_runs),
                    'avg_success': avg_success,
                    'avg_failed': avg_failed,
                    'total_success': sum(success_values),
                    'total_failed': sum(failed_values)
                }
            
            except Exception:
                return {'error': 'Unable to parse dashboard data'}
        
        except Exception as e:
            log_msg(f"Error analyzing trends: {e}", "ERROR")
            return {'error': str(e)}
    
    def _update_dashboard_sheet(
        self,
        summary: Dict,
        profile_breakdown: Dict,
        phase2_analysis: Dict,
        recent_trends: Dict,
        start_time: datetime,
        end_time: datetime
    ):
        """Update Dashboard sheet with formatted data."""
        
        # Build dashboard content
        dashboard_rows = []
        
        # === HEADER ===
        dashboard_rows.append(['=== DAMADAM SCRAPER DASHBOARD ==='])
        dashboard_rows.append(['Generated:', datetime.now().strftime('%d-%b-%y %I:%M %p')])
        dashboard_rows.append([''])
        
        # === RUN SUMMARY ===
        dashboard_rows.append(['🎯 LATEST RUN SUMMARY'])
        dashboard_rows.append(['─' * 50])
        dashboard_rows.append(['Mode:', summary['mode']])
        dashboard_rows.append(['Duration:', summary['duration_formatted']])
        dashboard_rows.append(['Start Time:', start_time.strftime('%d-%b-%y %I:%M %p')])
        dashboard_rows.append(['End Time:', end_time.strftime('%d-%b-%y %I:%M %p')])
        dashboard_rows.append([''])
        dashboard_rows.append(['Total Processed:', summary['total_processed']])
        dashboard_rows.append(['✅ Success:', f"{summary['success_count']} ({summary['success_rate']:.1%})"])
        dashboard_rows.append(['❌ Failed:', summary['failure_count']])
        dashboard_rows.append(['🆕 New:', summary['new_profiles']])
        dashboard_rows.append(['🔄 Updated:', summary['updated_profiles']])
        dashboard_rows.append(['💤 Unchanged:', summary['unchanged_profiles']])
        dashboard_rows.append([''])
        dashboard_rows.append(['Avg Time/Profile:', f"{summary['avg_time_per_profile']:.2f}s"])
        dashboard_rows.append([''])
        
        # === PROFILE BREAKDOWN ===
        dashboard_rows.append(['📊 PROFILE STATUS BREAKDOWN'])
        dashboard_rows.append(['─' * 50])
        if 'error' not in profile_breakdown:
            dashboard_rows.append(['Total Profiles:', profile_breakdown['total']])
            dashboard_rows.append([''])
            dashboard_rows.append(['Verified:', f"{profile_breakdown['verified']} ({profile_breakdown['verified_rate']:.1%})"])
            dashboard_rows.append(['Unverified:', profile_breakdown['unverified']])
            dashboard_rows.append(['Banned:', f"{profile_breakdown['banned']} ({profile_breakdown['banned_rate']:.1%})"])
            dashboard_rows.append(['Normal:', profile_breakdown['normal']])
        else:
            dashboard_rows.append(['Error:', profile_breakdown['error']])
        dashboard_rows.append([''])
        
        # === PHASE 2 ELIGIBILITY ===
        dashboard_rows.append(['🚩 PHASE 2 ELIGIBILITY'])
        dashboard_rows.append(['─' * 50])
        if 'error' not in phase2_analysis:
            dashboard_rows.append(['Total Analyzed:', phase2_analysis['total']])
            dashboard_rows.append([''])
            dashboard_rows.append(['✅ Ready:', f"{phase2_analysis['ready']} ({phase2_analysis['ready_rate']:.1%})"])
            dashboard_rows.append(['⛔ Not Eligible:', phase2_analysis['not_eligible']])
            dashboard_rows.append([''])
            dashboard_rows.append(['Note: Ready = Profiles with < 100 posts'])
        else:
            dashboard_rows.append(['Error:', phase2_analysis['error']])
        dashboard_rows.append([''])
        
        # === RECENT TRENDS ===
        dashboard_rows.append(['📈 RECENT TRENDS (Last 10 Runs)'])
        dashboard_rows.append(['─' * 50])
        if 'error' not in recent_trends:
            dashboard_rows.append(['Runs Analyzed:', recent_trends['runs_analyzed']])
            dashboard_rows.append([''])
            dashboard_rows.append(['Avg Success/Run:', f"{recent_trends['avg_success']:.1f}"])
            dashboard_rows.append(['Avg Failed/Run:', f"{recent_trends['avg_failed']:.1f}"])
            dashboard_rows.append(['Total Success:', recent_trends['total_success']])
            dashboard_rows.append(['Total Failed:', recent_trends['total_failed']])
        else:
            dashboard_rows.append(['Error:', recent_trends['error']])
        dashboard_rows.append([''])
        
        # Write to new Dashboard tab
        try:
            # Create or get Dashboard Summary sheet
            try:
                summary_sheet = self.sheets.spreadsheet.worksheet('Dashboard Summary')
            except:
                summary_sheet = self.sheets.spreadsheet.add_worksheet(
                    title='Dashboard Summary',
                    rows=100,
                    cols=5
                )
            
            # Clear existing content
            summary_sheet.clear()
            
            # Update with new dashboard
            summary_sheet.update('A1', dashboard_rows)
            
            # Apply formatting
            # (Format first column bold, use Quantico font)
            summary_sheet.format('A:A', {
                'textFormat': {'bold': True, 'fontFamily': 'Quantico'}
            })
            summary_sheet.format('B:B', {
                'textFormat': {'fontFamily': 'Quantico'}
            })
            
            log_msg("Dashboard Summary sheet updated", "OK")
        
        except Exception as e:
            log_msg(f"Error updating Dashboard Summary sheet: {e}", "ERROR")
    
    @staticmethod
    def _calculate_rate(numerator: int, denominator: int) -> float:
        """Calculate percentage rate safely."""
        return numerator / denominator if denominator > 0 else 0.0
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


class TrendAnalyzer:
    """
    Analyze trends over time from historical data.
    
    Provides insights into scraping performance trends,
    error patterns, and profile state changes.
    """
    
    def __init__(self, sheets_manager):
        """Initialize trend analyzer."""
        self.sheets = sheets_manager
    
    def analyze_success_rate_trend(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze success rate trend over time.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with trend data
        """
        try:
            # Get dashboard history
            dashboard_data = self.sheets.dashboard_ws.get_all_values()
            
            if len(dashboard_data) <= 1:
                return {'error': 'No history data'}
            
            # Parse runs (skip header)
            runs = dashboard_data[1:]
            
            # Calculate success rates
            success_rates = []
            for row in runs[:min(len(runs), days * 4)]:  # ~4 runs per day
                if len(row) > 4:
                    try:
                        success = int(row[3])
                        total = int(row[2])
                        if total > 0:
                            rate = success / total
                            success_rates.append(rate)
                    except:
                        continue
            
            if not success_rates:
                return {'error': 'No valid data'}
            
            # Calculate trend
            avg_rate = sum(success_rates) / len(success_rates)
            recent_avg = sum(success_rates[:5]) / min(5, len(success_rates))
            
            trend = "improving" if recent_avg > avg_rate else "declining"
            
            return {
                'average_rate': avg_rate,
                'recent_rate': recent_avg,
                'trend': trend,
                'data_points': len(success_rates)
            }
        
        except Exception as e:
            return {'error': str(e)}


# Convenience function
def generate_dashboard(sheets_manager, stats, mode, duration, start_time, end_time):
    """
    Quick dashboard generation.
    
    Example:
        >>> from utils.dashboard_generator import generate_dashboard
        >>> generate_dashboard(sheets, stats, 'target', 300, start, end)
    """
    dashboard = DashboardGenerator(sheets_manager)
    dashboard.create_or_update(stats, mode, duration, start_time, end_time)
