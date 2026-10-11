"""
PDF generation service using ReportLab for order receipts.
"""
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_order_invoice_pdf(order_data: dict) -> io.BytesIO:
    """
    Generates a PDF invoice for an order and returns an in-memory BytesIO buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    order = order_data['order']
    items = order_data['items']
    total_amount = order_data['total_amount']

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b')
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12
    )

    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12
    )

    story = []

    # Header Banner
    header_data = [
        [
            Paragraph("<b>GROCERY STORE DBMS</b><br/><font color='#64748b' size='8'>Store Management System • Official Tax Invoice</font>", title_style),
            Paragraph(f"<b>INVOICE #{order['order_id']}</b><br/><font color='#64748b' size='9'>Date: {order['order_date']}<br/>Status: {order.get('status', 'Completed')}</font>", ParagraphStyle('R', parent=subtitle_style, alignment=2))
        ]
    ]
    header_table = Table(header_data, colWidths=[340, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=15))

    # Customer & Payment Info
    cust_data = [
        [
            Paragraph(f"<b>Billed To:</b><br/>{order['customer_name']}<br/>Phone: {order.get('phone') or 'N/A'}<br/>City: {order.get('city') or 'N/A'}", cell_style),
            Paragraph(f"<b>Payment Information:</b><br/>Payment Mode: <b>{order['payment_mode']}</b><br/>Order Status: <b>{order.get('status', 'Completed')}</b><br/>Invoice Date: {order['order_date']}", cell_style)
        ]
    ]
    cust_table = Table(cust_data, colWidths=[270, 270])
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(cust_table)
    story.append(Spacer(1, 15))

    # Items Table
    table_data = [
        [
            Paragraph("<b>#</b>", cell_bold),
            Paragraph("<b>Product Description</b>", cell_bold),
            Paragraph("<b>Category</b>", cell_bold),
            Paragraph("<b>Qty</b>", cell_bold),
            Paragraph("<b>Unit Price</b>", cell_bold),
            Paragraph("<b>Total</b>", cell_bold)
        ]
    ]

    for idx, item in enumerate(items, 1):
        table_data.append([
            Paragraph(str(idx), cell_style),
            Paragraph(f"<b>{item['product_name']}</b>", cell_style),
            Paragraph(item.get('category') or 'General', cell_style),
            Paragraph(str(item['quantity']), cell_style),
            Paragraph(f"Rs. {float(item['unit_price']):.2f}", cell_style),
            Paragraph(f"Rs. {float(item['line_total']):.2f}", cell_bold)
        ])

    # Grand Total Row
    table_data.append([
        "", "", "", "",
        Paragraph("<b>GRAND TOTAL:</b>", ParagraphStyle('GT', parent=cell_bold, alignment=2)),
        Paragraph(f"<b>Rs. {float(total_amount):.2f}</b>", ParagraphStyle('GTV', parent=cell_bold, textColor=colors.HexColor('#16a34a'), fontSize=10))
    ])

    col_widths = [30, 200, 100, 45, 80, 85]
    items_table = Table(table_data, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#334155')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#e2e8f0')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#16a34a')),
        ('LINEABOVE', (0,-1), (-1,-1), 1.0, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f0fdf4')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 20))

    # Footer note
    story.append(Paragraph("<font color='#64748b' size='8'>Thank you for shopping with us! This computer-generated invoice is backed by MySQL transaction integrity and trigger security.</font>", ParagraphStyle('F', alignment=1)))

    doc.build(story)
    buffer.seek(0)
    return buffer
