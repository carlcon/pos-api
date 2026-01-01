"""
Celery tasks for report generation.
"""
import os
from datetime import datetime
from celery import shared_task
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML


@shared_task(bind=True)
def generate_report_pdf(self, report_type, report_data, partner_id=None, store_id=None):
    """
    Generate PDF report from report data using WeasyPrint.
    
    Args:
        report_type: Type of report (e.g., 'daily-sales', 'inventory-valuation')
        report_data: Dictionary containing report data
        partner_id: Partner ID for filtering
        store_id: Store ID for filtering
    
    Returns:
        dict: Contains file_path and other metadata
    """
    try:
        # Update task state
        self.update_state(state='PROCESSING', meta={'status': 'Generating PDF...'})
        
        # Debug: print received data
        print(f"=== PDF Generation Debug ===")
        print(f"report_type: {report_type}")
        print(f"report_data keys: {report_data.keys() if report_data else 'None'}")
        print(f"report_data: {report_data}")
        
        # Prepare template context
        summary = format_summary(report_data.get('summary', {}))
        data_sections = extract_data_sections(report_data)
        
        print(f"=== Formatted context ===")
        print(f"summary: {summary}")
        print(f"data_sections keys: {data_sections.keys() if data_sections else 'None'}")
        print(f"data_sections: {data_sections}")
        
        context = {
            'report_title': report_data.get('report_type', 'Report'),
            'generated_at': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
            'period': report_data.get('period'),
            'date': report_data.get('date'),
            'summary': summary,
            'data_sections': data_sections,
        }
        
        # Render HTML template
        html_string = render_to_string('reports/generic_report.html', context)
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{report_type}_{timestamp}.pdf'
        filepath = os.path.join(reports_dir, filename)
        
        # Generate PDF
        HTML(string=html_string).write_pdf(filepath)
        
        # Return relative path for URL construction
        relative_path = os.path.join('reports', filename)
        
        return {
            'status': 'completed',
            'file_path': relative_path,
            'filename': filename,
            'generated_at': datetime.now().isoformat(),
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'status': f'Error: {str(e)}'}
        )
        raise


def format_summary(summary):
    """Format summary values for display."""
    formatted = {}
    for key, value in summary.items():
        # Format key
        display_key = key.replace('_', ' ').title()
        
        # Format value
        if isinstance(value, (int, float)):
            if any(term in key for term in ['revenue', 'value', 'cost', 'price', 'profit', 'amount']) and 'year' not in key:
                formatted[display_key] = f'₱{value:,.2f}'
            elif 'percentage' in key:
                formatted[display_key] = f'{value:.1f}%'
            elif 'year' in key:
                formatted[display_key] = str(int(value))
            else:
                formatted[display_key] = f'{value:,}'
        else:
            formatted[display_key] = str(value)
    
    return formatted


def extract_data_sections(report_data):
    """Extract data sections from report data."""
    sections = {}
    
    # Skip metadata keys
    skip_keys = {'report_type', 'generated_at', 'summary', 'period', 'start_date', 'end_date',
                 'date', 'count', 'page', 'page_size', 'total_pages', 'has_next', 'has_previous'}
    
    for key, value in report_data.items():
        if key in skip_keys:
            continue
            
        if isinstance(value, list) and len(value) > 0:
            # Format list data
            formatted_items = []
            for item in value[:100]:  # Limit to 100 items for PDF
                formatted_item = {}
                for item_key, item_value in item.items():
                    # Skip IDs in display (except if it's the only 'id' field)
                    if item_key == 'id' and len(item) > 1:
                        continue
                    
                    # Format key
                    display_key = item_key.replace('_', ' ').title()
                    
                    # Format value
                    if isinstance(item_value, (int, float)):
                        if any(term in item_key for term in ['price', 'value', 'revenue', 'cost', 'profit', 'amount']) and 'year' not in item_key:
                            formatted_item[display_key] = f'₱{item_value:,.2f}'
                        elif 'percentage' in item_key:
                            formatted_item[display_key] = f'{item_value:.1f}%'
                        elif 'year' in item_key:
                            formatted_item[display_key] = str(int(item_value))
                        else:
                            formatted_item[display_key] = f'{item_value:,}'
                    else:
                        formatted_item[display_key] = str(item_value) if item_value is not None else '-'
                
                formatted_items.append(formatted_item)
            
            if formatted_items:
                sections[key.replace('_', ' ').title()] = formatted_items
    
    return sections


@shared_task
def cleanup_old_reports():
    """Clean up report PDFs older than 7 days."""
    from datetime import timedelta
    import glob
    
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    if not os.path.exists(reports_dir):
        return
    
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for filepath in glob.glob(os.path.join(reports_dir, '*.pdf')):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        if file_mtime < cutoff_date:
            try:
                os.remove(filepath)
            except OSError:
                pass
