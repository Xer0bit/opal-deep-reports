from fpdf import FPDF
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
from typing import List, Dict, Any
import io

# Get the absolute paths
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
LOGO_PATH = os.path.join(ASSETS_DIR, 'opal_logo.png')

# Professional color scheme
COLORS = {
    'primary': {'r': 51, 'g': 51, 'b': 51},      # Dark Gray
    'secondary': {'r': 85, 'g': 85, 'b': 85},    # Medium Gray
    'accent': {'r': 128, 'g': 128, 'b': 128},    # Light Gray
    'warning': {'r': 220, 'g': 53, 'b': 69},     # Alert Red
    'success': {'r': 40, 'g': 167, 'b': 69},     # Success Green
    'text': {'r': 33, 'g': 37, 'b': 41},         # Dark Text
    'light': {'r': 242, 'g': 242, 'b': 242}      # Background Gray
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
        self.set_auto_page_break(auto=True, margin=15)
        
        # Add fonts with absolute paths
        self.add_font('Roboto', '', os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'), uni=True)
        self.add_font('Roboto', 'B', os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'), uni=True)
        
    def header(self):
        # Modern grayscale header
        self.set_fill_color(**COLORS['primary'])
        self.rect(0, 0, self.w, 35, 'F')
        
        # Add logo if exists - centered
        if os.path.exists(LOGO_PATH):
            # Calculate center position
            logo_width = 40
            x_pos = (self.w - logo_width) / 2
            self.image(LOGO_PATH, x_pos, 8, logo_width)
        
        # Title text
        self.set_font('Roboto', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 35, 'Opal - Violation trends Driver Safety', 0, 1, 'C')  # Increased from 21 to 35
        
        self.set_font('Roboto', 'B', 14)
        self.cell(0, 10, '', 0, 1, 'C')
        self.ln(15)  # Increased from 10 to 15

    def footer(self):
        self.set_y(-20)
        self.set_font('Roboto', '', 8)
        self.set_text_color(**COLORS['text'])
        
        # Add horizontal line
        self.set_draw_color(**COLORS['light'])
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        
        # Footer text
        self.cell(0, 15, f'Page {self.page_no()} | Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Roboto', 'B', 14)
        self.set_fill_color(**COLORS['secondary'])
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(5)

    def section_title(self, title):
        self.set_font('Roboto', 'B', 12)
        self.set_text_color(**COLORS['accent'])
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

def create_modern_chart(data: Dict[str, int], title: str, chart_type: str = 'bar') -> bytes:
    # Use a basic style that works across versions
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    
    # Manual styling for consistent look
    ax.set_facecolor('#F8F9FA')
    fig.patch.set_facecolor('#FFFFFF')
    
    # Add grid manually
    ax.grid(True, linestyle='--', alpha=0.3, color='#666666', axis='y')
    
    if chart_type == 'bar':
        # Assign colors based on violation type
        colors = [VIOLATION_COLORS.get(key, VIOLATION_COLORS['DEFAULT']) 
                 for key in data.keys()]
        
        bars = ax.bar(range(len(data)), list(data.values()), color=colors)
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels(list(data.keys()), rotation=45, ha='right')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom',
                   color='#333333',
                   fontweight='bold',
                   fontsize=9)
            
    elif chart_type == 'pie':
        colors = [VIOLATION_COLORS.get(key, VIOLATION_COLORS['DEFAULT']) 
                 for key in data.keys()]
        
        wedges, texts, autotexts = ax.pie(
            data.values(), 
            labels=data.keys(),
            colors=colors,
            autopct='%1.1f%%',
            textprops={'color': "#333333", 'fontsize': 9},
            wedgeprops={'edgecolor': 'white', 'linewidth': 2}
        )
        ax.axis('equal')
    
    # Style updates
    ax.set_title(title, pad=20, fontsize=12, fontweight='bold', color='#333333')
    if chart_type == 'bar':
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#CCCCCC')
        ax.spines['left'].set_color('#CCCCCC')
        ax.tick_params(colors='#666666')
    
    plt.tight_layout()
    
    # Save with white background
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300,
                facecolor='white', edgecolor='none')
    plt.close()
    
    return buf.getvalue()

def generate_driver_report(trend_data: List[Dict[str, Any]], 
                         period_info: Dict[str, Any] = None,
                         output_dir: str = "reports") -> str:
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
    
    # Executive Summary Page
    pdf.add_page()
    pdf.chapter_title("Executive Summary")
    
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
    
    # Continue with normal report generation for non-empty data
    # Group data by driver
    driver_reports = {}
    for item in trend_data:
        driver_uuid = item.get("driver_uuid", "Unknown")
        if driver_uuid not in driver_reports:
            driver_reports[driver_uuid] = []
        driver_reports[driver_uuid].append(item)
    
    # Executive Summary Page
    pdf.add_page()
    pdf.chapter_title("Executive Summary")
    total_drivers = len(driver_reports)
    total_violations = sum(sum(r["total_violations"] for r in reports) 
                         for reports in driver_reports.values())
    
    pdf.set_font('Roboto', '', 10)
    period_text = (f"Period: {trend_data[0]['time_period']} to {trend_data[-1]['time_period']}"
                  if trend_data else "No period data available")
    
    pdf.multi_cell(0, 10, f"""
    This report analyzes driving behavior and safety patterns across {total_drivers} drivers.
    Total violations recorded: {total_violations}
    {period_text}
    """)
    
    # Generate Fleet-wide Statistics
    all_violations = {}
    high_risk_drivers = []
    
    for driver_uuid, reports in driver_reports.items():
        sample_report = reports[0]
        driver_total = sum(r["total_violations"] for r in reports)
        if driver_total > 10:
            high_risk_drivers.append({
                "name": sample_report.get("driver_name", "Unknown"),
                "violations": driver_total
            })
        
        for report in reports:
            for v_type, count in report.get("violation_types", {}).items():
                all_violations[v_type] = all_violations.get(v_type, 0) + count
    
    # Add Fleet-wide Violation Chart
    chart_image = create_modern_chart(
        all_violations,
        "Violation Distribution",
        'pie'
    )
    pdf.image(io.BytesIO(chart_image), x=10, w=190)
    
    # Individual Driver Reports
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
    return filename

def generate_fleet_report(trend_data: List[Dict[str, Any]], output_dir: str = "reports") -> str:
    """Generate PDF report for entire fleet"""
    pass
