from fpdf import FPDF
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
from typing import List, Dict, Any
import io
from .file_cleanup import FileCleanupManager

# Get the absolute paths
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
LOGO_PATH = os.path.join(ASSETS_DIR, 'opal_logo.png')

# Update color scheme with modern colors
COLORS = {
    'primary': {'r': 41, 'g': 128, 'b': 185},     # Modern Blue
    'secondary': {'r': 52, 'g': 152, 'b': 219},   # Light Blue
    'accent': {'r': 46, 'g': 204, 'b': 113},      # Green
    'warning': {'r': 231, 'g': 76, 'b': 60},      # Red
    'success': {'r': 46, 'g': 204, 'b': 113},     # Green
    'text': {'r': 52, 'g': 73, 'b': 94},          # Dark Blue-Gray
    'light': {'r': 236, 'g': 240, 'b': 241},      # Light Gray
    'highlight': {'r': 155, 'g': 89, 'b': 182}    # Purple
}

# Violation type colors
VIOLATION_COLORS = {
    'SPEED_HIGH': '#DC3545',    # Red for high severity
    'SPEED_MEDIUM': '#FD7E14',  # Orange for medium severity
    'SPEED_LOW': '#FFC107',     # Yellow for low severity
    'DEFAULT': '#6C757D'        # Gray for others
}

class ModernReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)  # Increased margin
        self.set_margins(left=20, top=25, right=20)     # Better margins
        
        # Add fonts with absolute paths
        self.add_font('Roboto', '', os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'), uni=True)
        self.add_font('Roboto', 'B', os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'), uni=True)
        
    def header(self):
        # Gradient-style header
        self.set_fill_color(**COLORS['primary'])
        self.rect(0, 0, self.w, 30, 'F')
        self.set_fill_color(**COLORS['secondary'])
        self.rect(0, 30, self.w, 2, 'F')  # Accent line
        
        # Logo
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, 15, 5, 20)
            
        # Title
        self.set_font('Roboto', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(25)  # Space after logo
        self.cell(0, 30, 'Driver Safety Report', 0, 1, 'L')

    def footer(self):
        self.set_y(-25)
        self.set_font('Roboto', '', 8)
        self.set_text_color(**COLORS['text'])
        
        # Modern footer with multiple elements
        self.set_fill_color(**COLORS['light'])
        self.rect(0, self.get_y(), self.w, 25, 'F')
        
        # Footer content
        self.set_y(-20)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(0, 10, f'Generated: {current_date}', 0, 0, 'L')
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')

    def chapter_title(self, title):
        self.set_font('Roboto', 'B', 16)
        self.set_fill_color(**COLORS['primary'])
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, title, 0, 1, 'L', 1)
        self.ln(10)

    def section_title(self, title):
        self.set_font('Roboto', 'B', 14)
        self.set_text_color(**COLORS['primary'])
        self.cell(0, 10, '□ ' + title, 0, 1, 'L')  # Added modern bullet point
        self.ln(5)

    def stat_box(self, label, value, fill_color=None):
        """Add a modern stat box"""
        original_fill = self.get_fill_color()
        
        if fill_color:
            self.set_fill_color(**fill_color)
        else:
            self.set_fill_color(**COLORS['light'])
            
        self.rect(self.get_x(), self.get_y(), 90, 25, 'F')
        
        # Label
        self.set_font('Roboto', '', 10)
        self.set_text_color(**COLORS['text'])
        self.set_xy(self.get_x() + 5, self.get_y() + 5)
        self.cell(80, 6, label, 0, 2, 'L')
        
        # Value
        self.set_font('Roboto', 'B', 12)
        self.cell(80, 10, str(value), 0, 0, 'L')
        
        # Reset fill color
        self.set_fill_color(**original_fill)
        self.ln(30)

def create_modern_chart(data: Dict[str, int], title: str, chart_type: str = 'bar') -> bytes:
    # Use a built-in style that works better
    plt.style.use('bmh')  # Changed from seaborn to bmh style
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    
    # Set background colors
    ax.set_facecolor('#ffffff')
    fig.patch.set_facecolor('#ffffff')
    
    # Enhanced grid styling
    ax.yaxis.grid(True, linestyle='--', alpha=0.7, color='#cccccc')
    ax.xaxis.grid(False)
    
    if chart_type == 'bar':
        # Assign colors based on violation type with enhanced styling
        colors = [VIOLATION_COLORS.get(key, VIOLATION_COLORS['DEFAULT']) 
                 for key in data.keys()]
        
        bars = ax.bar(range(len(data)), list(data.values()), color=colors)
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels(list(data.keys()), rotation=45, ha='right')
        
        # Enhanced bar labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height):,}',  # Added thousands separator
                   ha='center', va='bottom',
                   color='#333333',
                   fontweight='bold',
                   fontsize=9,
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
            
            # Add gradient effect
            bar.set_alpha(0.85)
            
    elif chart_type == 'pie':
        # Enhanced pie chart styling
        colors = [VIOLATION_COLORS.get(key, VIOLATION_COLORS['DEFAULT']) 
                 for key in data.keys()]
        
        wedges, texts, autotexts = ax.pie(
            data.values(), 
            labels=data.keys(),
            colors=colors,
            autopct='%1.1f%%',
            textprops={'color': "#333333", 'fontsize': 9},
            wedgeprops={'edgecolor': 'white', 'linewidth': 2, 'alpha': 0.85}
        )
        
        # Enhance pie chart text
        plt.setp(autotexts, weight="bold")
        plt.setp(texts, weight="bold")
        ax.axis('equal')
    
    # Enhanced title styling
    ax.set_title(title, pad=20, fontsize=14, fontweight='bold', 
                 color=(COLORS['text']['r']/255,
                        COLORS['text']['g']/255,
                        COLORS['text']['b']/255))
    
    if chart_type == 'bar':
        # Clean up bar chart spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(True)
        ax.spines['left'].set_visible(True)
        ax.spines['bottom'].set_color('#cccccc')
        ax.spines['left'].set_color('#cccccc')
        ax.tick_params(colors='#666666', grid_alpha=0.3)
    
    plt.tight_layout()
    
    # Save with enhanced quality
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300,
                facecolor='white', edgecolor='none',
                pad_inches=0.2)
    plt.close()
    
    return buf.getvalue()

def generate_driver_report(trend_data: List[Dict[str, Any]], 
                         period_info: Dict[str, Any] = None,
                         output_dir: str = "reports",
                         cleanup_minutes: int = 30) -> str:
    """
    Generate PDF report for driver violations
    Args:
        trend_data: List of violation trend data
        period_info: Optional period information for empty reports
        output_dir: Output directory for the report
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/driver_violations_{timestamp}.pdf"
    
    pdf = ModernReportPDF()
    pdf.set_title("Driver Safety Analysis Report")
    pdf.set_author("Opal Analytics System")
    
    # First page with executive summary
    pdf.add_page()
    
    if not trend_data:
        pdf.set_font('Roboto', '', 10)
        summary_text = "No violations found for the specified period.\n\n"
        
        if period_info:
            start_date = period_info.get('start_date', 'Unknown')
            end_date = period_info.get('end_date', 'Unknown')
            driver_id = period_info.get('driver_uuid', 'All Drivers')
            
            summary_text += f"""
            Period: {start_date} to {end_date}
            Driver ID: {driver_id}
            """
        
        pdf.multi_cell(0, 10, summary_text)
        pdf.output(filename)
        return filename

    # Group data by driver
    driver_reports = {}
    for item in trend_data:
        driver_uuid = item.get("driver_uuid", "Unknown")
        if driver_uuid not in driver_reports:
            driver_reports[driver_uuid] = []
        driver_reports[driver_uuid].append(item)
    
    # Executive Summary
    total_drivers = len(driver_reports)
    total_violations = sum(sum(r["total_violations"] for r in reports) 
                         for reports in driver_reports.values())
    
    # Report Header
    pdf.chapter_title("Executive Summary")
    pdf.ln(5)
    
    # Summary Statistics
    pdf.set_font('Roboto', 'B', 12)
    pdf.set_text_color(**COLORS['text'])
    period_text = f"Report Period: {trend_data[0]['time_period']} to {trend_data[-1]['time_period']}"
    pdf.cell(0, 10, period_text, ln=True)
    
    pdf.set_font('Roboto', '', 10)
    summary_text = f"""
Total Drivers Analyzed: {total_drivers}
Total Violations: {total_violations}
High Risk Drivers: {len([d for d in driver_reports.values() if sum(r['total_violations'] for r in d) > 10])}
"""
    for line in summary_text.strip().split('\n'):
        pdf.cell(0, 8, line.strip(), ln=True)
    
    pdf.ln(5)
    
    # Fleet Overview Section
    pdf.section_title("Fleet Overview")
    
    # Generate and add Fleet-wide Statistics
    all_violations = {}
    for driver_uuid, reports in driver_reports.items():
        for report in reports:
            for v_type, count in report.get("violation_types", {}).items():
                all_violations[v_type] = all_violations.get(v_type, 0) + count
    
    # Add Fleet-wide Violation Chart on first page
    if all_violations:
        chart_image = create_modern_chart(
            all_violations,
            "Fleet-wide Violation Distribution",
            'pie'
        )
        pdf.image(io.BytesIO(chart_image), x=15, w=180)  # Adjusted position and width
    
    # Individual Driver Reports (starting from page 2)
    for driver_uuid, reports in driver_reports.items():
        pdf.add_page()
        sample_report = reports[0]
        
        # Driver Header
        pdf.chapter_title(f"Driver Analysis: {sample_report.get('driver_name', 'Unknown')}")
        
        # Driver Statistics
        total_violations = sum(r["total_violations"] for r in reports)
        high_severity = sum(r.get("high_severity_count", 0) for r in reports)
        
        pdf.section_title("Key Statistics")
        pdf.set_font('Roboto', '', 10)
        pdf.cell(0, 10, f"Total Violations: {total_violations}", ln=True)
        pdf.cell(0, 10, f"High Severity Incidents: {high_severity}", ln=True)
        
        # Violation Types Chart
        violation_types = {}
        for report in reports:
            for v_type, count in report.get("violation_types", {}).items():
                violation_types[v_type] = violation_types.get(v_type, 0) + count
        
        pdf.section_title("Violation Distribution")
        chart_image = create_modern_chart(
            violation_types,
            f"Violation Types - {sample_report.get('driver_name', 'Unknown')}",
            'bar'
        )
        pdf.image(io.BytesIO(chart_image), x=10, w=190)
        
        # Recommendations
        pdf.section_title("Safety Recommendations")
        latest_report = max(reports, key=lambda x: x["time_period"])
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 10, latest_report.get("action", "No specific recommendations"))
        

        # Table headers
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(40, 10, "Date", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Violations", 1, 0, 'C', 1)
        pdf.cell(60, 10, "Top Violation", 1, 0, 'C', 1)
        pdf.cell(60, 10, "Severity", 1, 1, 'C', 1)
        
        for report in sorted(reports, key=lambda x: x["time_period"]):
            pdf.cell(40, 10, report['time_period'], 1)
            pdf.cell(30, 10, str(report['total_violations']), 1)
            pdf.cell(60, 10, report['top_type'], 1)
            pdf.cell(60, 10, "High" if report.get("high_severity_count", 0) > 0 else "Normal", 1)
            pdf.ln()
    
    pdf.output(filename)
    
    # Schedule cleanup
    cleanup_manager = FileCleanupManager.get_instance()
    cleanup_manager.schedule_cleanup(filename, cleanup_minutes)
    
    return filename

def generate_fleet_report(trend_data: List[Dict[str, Any]], output_dir: str = "reports") -> str:
    """Generate PDF report for entire fleet"""
    pass
