"""
Barcode generation and label printing utilities
"""
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from django.http import HttpResponse


def generate_barcode_image(barcode_value, barcode_type='code128'):
    """
    Generate barcode image
    
    Args:
        barcode_value: The value to encode
        barcode_type: Type of barcode (code128, ean13, etc.)
    
    Returns:
        BytesIO object containing barcode image
    """
    # Get barcode class
    try:
        barcode_class = barcode.get_barcode_class(barcode_type)
    except:
        barcode_class = barcode.get_barcode_class('code128')
    
    # Generate barcode
    barcode_instance = barcode_class(barcode_value, writer=ImageWriter())
    
    # Save to BytesIO
    buffer = BytesIO()
    barcode_instance.write(buffer)
    buffer.seek(0)
    
    return buffer


def generate_product_label_pdf(product, label_size='2x1'):
    """
    Generate PDF with product barcode labels
    
    Args:
        product: Product instance
        label_size: Label size ('2x1' for 2"x1", '3x2' for 3"x2")
    
    Returns:
        HttpResponse with PDF
    """
    buffer = BytesIO()
    
    # Set label dimensions based on size
    if label_size == '3x2':
        label_width = 3 * inch
        label_height = 2 * inch
    else:  # Default 2x1
        label_width = 2 * inch
        label_height = 1 * inch
    
    # Create PDF
    p = canvas.Canvas(buffer, pagesize=(label_width, label_height))
    
    # Generate barcode if product has one
    if product.barcode:
        try:
            barcode_img = generate_barcode_image(product.barcode)
            barcode_reader = ImageReader(barcode_img)
            
            # Position barcode
            barcode_width = label_width - 0.2 * inch
            barcode_height = 0.5 * inch
            barcode_x = 0.1 * inch
            barcode_y = label_height - barcode_height - 0.15 * inch
            
            p.drawImage(barcode_reader, barcode_x, barcode_y, 
                       width=barcode_width, height=barcode_height, 
                       preserveAspectRatio=True, mask='auto')
        except Exception as e:
            # If barcode generation fails, just show text
            pass
    
    # Product name (truncate if too long)
    p.setFont("Helvetica-Bold", 8 if label_size == '2x1' else 10)
    product_name = product.name[:30] + '...' if len(product.name) > 30 else product.name
    p.drawString(0.1 * inch, 0.35 * inch if label_size == '2x1' else 0.5 * inch, product_name)
    
    # SKU
    p.setFont("Helvetica", 7 if label_size == '2x1' else 9)
    p.drawString(0.1 * inch, 0.22 * inch if label_size == '2x1' else 0.35 * inch, f"SKU: {product.sku}")
    
    # Price
    p.setFont("Helvetica-Bold", 8 if label_size == '2x1' else 10)
    p.drawString(0.1 * inch, 0.1 * inch if label_size == '2x1' else 0.2 * inch, 
                f"${product.selling_price}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="label_{product.sku}.pdf"'
    
    return response


def generate_multiple_labels_pdf(products, label_size='2x1', labels_per_page=6):
    """
    Generate PDF with multiple product labels on a single page
    
    Args:
        products: List of Product instances
        label_size: Label size ('2x1' or '3x2')
        labels_per_page: Number of labels per page
    
    Returns:
        HttpResponse with PDF
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Set label dimensions
    if label_size == '3x2':
        label_width = 3 * inch
        label_height = 2 * inch
    else:
        label_width = 2 * inch
        label_height = 1 * inch
    
    # Calculate layout
    labels_per_row = int((8.5 * inch) / label_width)
    labels_per_col = int((11 * inch) / label_height)
    labels_per_page = labels_per_row * labels_per_col
    
    margin_x = (8.5 * inch - (labels_per_row * label_width)) / 2
    margin_y = (11 * inch - (labels_per_col * label_height)) / 2
    
    for idx, product in enumerate(products):
        # Calculate position
        page_idx = idx % labels_per_page
        row = page_idx // labels_per_row
        col = page_idx % labels_per_row
        
        x = margin_x + (col * label_width)
        y = 11 * inch - margin_y - ((row + 1) * label_height)
        
        # Draw barcode if available
        if product.barcode:
            try:
                barcode_img = generate_barcode_image(product.barcode)
                barcode_reader = ImageReader(barcode_img)
                
                p.drawImage(barcode_reader, 
                           x + 0.1 * inch, 
                           y + label_height - 0.6 * inch,
                           width=label_width - 0.2 * inch, 
                           height=0.4 * inch,
                           preserveAspectRatio=True, 
                           mask='auto')
            except:
                pass
        
        # Product info
        p.setFont("Helvetica-Bold", 8 if label_size == '2x1' else 10)
        product_name = product.name[:25] + '...' if len(product.name) > 25 else product.name
        p.drawString(x + 0.1 * inch, y + 0.35 * inch if label_size == '2x1' else y + 0.5 * inch, 
                    product_name)
        
        p.setFont("Helvetica", 7 if label_size == '2x1' else 9)
        p.drawString(x + 0.1 * inch, y + 0.22 * inch if label_size == '2x1' else y + 0.35 * inch, 
                    f"SKU: {product.sku}")
        
        p.setFont("Helvetica-Bold", 8 if label_size == '2x1' else 10)
        p.drawString(x + 0.1 * inch, y + 0.1 * inch if label_size == '2x1' else y + 0.2 * inch,
                    f"${product.selling_price}")
        
        # New page if needed
        if (idx + 1) % labels_per_page == 0 and idx + 1 < len(products):
            p.showPage()
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="product_labels.pdf"'
    
    return response
