from fpdf import FPDF
import matplotlib.pyplot as plt
import os
from datetime import datetime
import io
from typing import List, Dict, Any
from .file_cleanup import FileCleanupManager

# Get the absolute paths
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
LOGO_PATH = os.path.join(ASSETS_DIR, 'opal_logo.png')

# Clean professional color scheme
COLORS = {
    'primary': {'r': 0, 'g': 82, 'b': 156},      # Dark Blue
    'secondary': {'r': 45, 'g': 55, 'b': 72},    # Dark Gray
    'text': {'r': 50, 'g': 50, 'b': 50},         # Near Black
    'light_gray': {'r': 240, 'g': 240, 'b': 240},# Light Gray
    'medium_gray': {'r': 200, 'g': 200, 'b': 200},# Medium Gray
    'white': {'r': 255, 'g': 255, 'b': 255}      # White
}

# Violation type colors
VIOLATION_COLORS = {
    'SPEED_HIGH': '#CC0000',      # Dark Red
    'SPEED_MEDIUM': '#FF6600',    # Orange
    'SPEED_LOW': '#FFCC00',       # Yellow
    'HARSH_ACCELERATION': '#9933CC', # Purple
    'HARD_BRAKING': '#3366FF',    # Blue
    'CRASH_DETECTION': '#990000', # Dark Red
    'DEFAULT': '#666666'          # Gray
}

class CleanReportPDF(FPDF):
    """Simple, clean PDF report generator"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 20, 15)
        
        # Add fonts
        self.add_font('Roboto', '', os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'), uni=True)
        self.add_font('Roboto', 'B', os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'), uni=True)
    
    def header(self):
        """Simple professional header with logo and title"""
        # Add logo if exists
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, 15, 12, 22)
            
        # Add blue header line
        self.set_draw_color(**COLORS['primary'])
        self.set_line_width(0.5)
        self.line(15, 38, 195, 38)
        
        # Title
        self.set_font('Roboto', 'B', 16)
        self.set_text_color(**COLORS['primary'])
        self.set_xy(40, 15)
        self.cell(0, 10, 'Driver Safety Report', 0, 1, 'L')
        
        # Subtitle with date
        self.set_font('Roboto', '', 10)
        self.set_text_color(**COLORS['secondary'])
        self.set_xy(40, 25)
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'L')
        
        # Add space after header
        self.ln(20)

    def footer(self):
        """Simple footer with page number"""
        self.set_y(-20)
        
        # Add line
        self.set_draw_color(**COLORS['medium_gray'])
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        
        # Add page number
        self.set_font('Roboto', '', 8)
        self.set_text_color(**COLORS['secondary'])
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')

    def add_title(self, title):
        """Add a section title"""
        self.set_font('Roboto', 'B', 14)
        self.set_text_color(**COLORS['primary'])
        self.cell(0, 10, title, 0, 1, 'L')
        
        # Add underline
        self.set_draw_color(**COLORS['primary'])
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)

    def add_subtitle(self, subtitle):
        """Add a subsection title"""
        self.set_font('Roboto', 'B', 12)
        self.set_text_color(**COLORS['secondary'])
        self.cell(0, 10, subtitle, 0, 1, 'L')
        self.ln(2)
        
    def add_info_row(self, label, value):
        """Add a label-value pair with consistent formatting"""
        self.set_font('Roboto', 'B', 10)
        self.set_text_color(**COLORS['secondary'])
        self.cell(60, 8, label, 0, 0, 'L')
        
        self.set_font('Roboto', '', 10)
        self.set_text_color(**COLORS['text'])
        self.cell(0, 8, str(value), 0, 1, 'L')

    def add_table(self, headers, data):
        """Add a clean, professional table"""
        # Set up widths based on headers
        col_widths = [40, 30, 60, 50]
        if len(col_widths) != len(headers):
            col_widths = [180 / len(headers)] * len(headers)
        
        # Headers
        self.set_font('Roboto', 'B', 10)
        self.set_fill_color(**COLORS['light_gray'])
        self.set_text_color(**COLORS['secondary'])
        
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
        self.ln()
        
        # Data rows
        self.set_font('Roboto', '', 10)
        self.set_text_color(**COLORS['text'])
        
        fill = False
        for row in data:
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 8, str(cell), 1, 0, 'L', fill)
            self.ln()
            fill = not fill  # Alternate row colors

def create_clean_chart(data: Dict[str, int], title: str, chart_type: str = 'bar') -> bytes:
    """Create clean, professional charts with minimal styling"""
    # Reset any previous styling
    plt.rcdefaults()
    plt.style.use('default')
    
    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    if chart_type == 'bar':
        # Create bar chart
        colors = [VIOLATION_COLORS.get(key, VIOLATION_COLORS['DEFAULT']) for key in data.keys()]
        bars = ax.bar(range(len(data)), list(data.values()), color=colors)
        
        # Configure axes
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels(list(data.keys()), rotation=45, ha='right')
        
        # Add values on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{int(height)}', ha='center', va='bottom', fontsize=9)
    
    elif chart_type == 'pie':
        # Create pie chart
        colors = [VIOLATION_COLORS.get(key, VIOLATION_COLORS['DEFAULT']) for key in data.keys()]
        ax.pie(
            data.values(),
            labels=data.keys(),
            colors=colors,
            autopct='%1.1f%%',
            startangle=90
        )
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Add title
    ax.set_title(title, pad=15, fontsize=12, fontweight='bold')
    
    # Clean up chart
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # Save to memory
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    plt.close(fig)
    
    return buf.getvalue()

def generate_driver_report(trend_data: List[Dict[str, Any]], 
                         period_info: Dict[str, Any] = None,
                         output_dir: str = "reports",
                         cleanup_minutes: int = 30) -> str:
    """Generate a clean, professional driver violations report"""
    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/driver_violations_{timestamp}.pdf"
    
    # Initialize PDF
    pdf = CleanReportPDF()
    pdf.set_title("Driver Safety Analysis Report")
    pdf.set_author("Opal Analytics System")
    
    # Create first page
    pdf.add_page()
    
    # Handle empty data case
    if not trend_data:
        pdf.add_title("No Violations Found")
        pdf.ln(5)
        
        pdf.set_font('Roboto', '', 10)
        summary_text = "No violation data was found for the specified period."
        
        if period_info:
            start_date = period_info.get('start_date', 'Unknown')
            end_date = period_info.get('end_date', 'Unknown')
            driver_id = period_info.get('driver_uuid', 'All Drivers')
            
            pdf.add_info_row("Period Start:", start_date)
            pdf.add_info_row("Period End:", end_date)
            pdf.add_info_row("Driver ID:", driver_id)
        
        pdf.output(filename)
        
        # Schedule cleanup
        FileCleanupManager.get_instance().schedule_cleanup(filename, cleanup_minutes)
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
    high_risk_count = len([d for d in driver_reports.values() 
                        if sum(r['total_violations'] for r in d) > 10])
    
    # Add report title and summary
    pdf.add_title("Executive Summary")
    pdf.ln(2)
    
    # Add period info
    period_text = f"{trend_data[0]['time_period']} to {trend_data[-1]['time_period']}"
    pdf.add_info_row("Report Period:", period_text)
    pdf.ln(5)
    
    # Add key metrics
    pdf.add_info_row("Total Drivers:", total_drivers)
    pdf.add_info_row("Total Violations:", total_violations)
    pdf.add_info_row("High Risk Drivers:", high_risk_count)
    pdf.ln(5)
    
    # Fleet Overview
    pdf.add_subtitle("Fleet Overview")
    
    # Generate fleet-wide statistics
    all_violations = {}
    for driver_uuid, reports in driver_reports.items():
        for report in reports:
            for v_type, count in report.get("violation_types", {}).items():
                all_violations[v_type] = all_violations.get(v_type, 0) + count
    
    # Add fleet chart
    if all_violations:
        chart_image = create_clean_chart(
            all_violations,
            "Violation Distribution by Type",
            'pie'
        )
        pdf.image(io.BytesIO(chart_image), x=30, w=150)
    
    # Individual Driver Reports
    for driver_uuid, reports in driver_reports.items():
        pdf.add_page()
        sample_report = reports[0]
        driver_name = sample_report.get('driver_name', 'Unknown')
        
        # Driver header
        pdf.add_title(f"Driver: {driver_name}")
        
        # Driver statistics
        total_violations = sum(r["total_violations"] for r in reports)
        high_severity = sum(r.get("high_severity_count", 0) for r in reports)
        
        pdf.add_info_row("Total Violations:", total_violations)
        pdf.add_info_row("High Severity Incidents:", high_severity)
        pdf.ln(5)
        
        # Violation chart
        pdf.add_subtitle("Violation Distribution")
        
        violation_types = {}
        for report in reports:
            for v_type, count in report.get("violation_types", {}).items():
                violation_types[v_type] = violation_types.get(v_type, 0) + count
        
        if violation_types:
            chart_image = create_clean_chart(
                violation_types,
                f"Violations by Type - {driver_name}",
                'bar'
            )
            pdf.image(io.BytesIO(chart_image), x=15, w=180)
        
        # Recommendations
        pdf.add_subtitle("Safety Recommendations")
        latest_report = max(reports, key=lambda x: x["time_period"])
        pdf.set_font('Roboto', '', 10)
        pdf.multi_cell(0, 6, latest_report.get("action", "No specific recommendations"))
        pdf.ln(5)
        
        # Violation details table
        pdf.add_subtitle("Violation Details")
        
        # Table headers
        headers = ["Date", "Count", "Top Type", "Severity"]
        
        # Table data
        table_data = []
        for report in sorted(reports, key=lambda x: x["time_period"]):
            severity = "High" if report.get("high_severity_count", 0) > 0 else "Normal"
            table_data.append([
                report['time_period'], 
                str(report['total_violations']), 
                report['top_type'], 
                severity
            ])
        
        pdf.add_table(headers, table_data)
    
    # Output the PDF
    pdf.output(filename)
    
    # Schedule cleanup
    FileCleanupManager.get_instance().schedule_cleanup(filename, cleanup_minutes)
    
    return filename

def generate_fleet_report(trend_data: List[Dict[str, Any]], output_dir: str = "reports") -> str:
    """Generate PDF report for entire fleet"""
    pass
