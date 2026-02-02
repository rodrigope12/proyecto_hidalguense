"""
PDF Receipt Generator for deliveries
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from typing import Dict, Any
from datetime import datetime
import os


def generate_receipt_pdf(
    order_data: Dict[str, Any],
    client_data: Dict[str, Any],
    output_path: str
) -> str:
    """
    Generate a PDF receipt for a delivery.
    
    Args:
        order_data: Order details from PEDIDOS
        client_data: Client details from CLIENTES
        output_path: Path to save the PDF
    
    Returns:
        Path to the generated PDF
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1a365d')
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#4a5568')
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#718096')
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2d3748')
    )
    
    total_style = ParagraphStyle(
        'Total',
        parent=styles['Heading2'],
        fontSize=16,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#276749')
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("DISTRIBUIDORA DE LÁCTEOS", title_style))
    elements.append(Paragraph("Nota de Entrega", subtitle_style))
    
    # Order info
    order_id = order_data.get('ID_Pedido', 'N/A')
    fecha = order_data.get('Fecha_Ruta', datetime.now().strftime('%Y-%m-%d'))
    timestamp = order_data.get('Timestamp_Entrega', datetime.now().isoformat())
    
    elements.append(Paragraph(f"<b>No. Pedido:</b> {order_id}", value_style))
    elements.append(Paragraph(f"<b>Fecha:</b> {fecha}", value_style))
    elements.append(Spacer(1, 20))
    
    # Client info
    elements.append(Paragraph("DATOS DEL CLIENTE", label_style))
    elements.append(Spacer(1, 5))
    
    client_name = client_data.get('Nombre_Negocio', order_data.get('Nombre_Negocio', 'N/A'))
    client_phone = client_data.get('Telefono', order_data.get('Telefono', 'N/A'))
    
    elements.append(Paragraph(f"<b>{client_name}</b>", value_style))
    elements.append(Paragraph(f"Tel: {client_phone}", value_style))
    elements.append(Spacer(1, 20))
    
    # Product table
    producto = order_data.get('Producto', 'N/A')
    kg_reales = float(order_data.get('Kg_Reales', 0))
    precio = float(order_data.get('Precio_Unitario', 0))
    total = float(order_data.get('Total_Cobrar', kg_reales * precio))
    
    table_data = [
        ['Producto', 'Cantidad (Kg)', 'Precio/Kg', 'Subtotal'],
        [producto, f"{kg_reales:.2f}", f"${precio:.2f}", f"${total:.2f}"]
    ]
    
    table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#4a5568')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Total
    elements.append(Paragraph(f"TOTAL A PAGAR: ${total:.2f}", total_style))
    elements.append(Spacer(1, 40))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#a0aec0')
    )
    
    elements.append(Paragraph(f"Entrega realizada: {timestamp}", footer_style))
    elements.append(Paragraph("¡Gracias por su preferencia!", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    return output_path


def generate_whatsapp_link(
    phone: str,
    order_data: Dict[str, Any],
    drive_folder_id: str = ""
) -> str:
    """
    Generate WhatsApp message link with delivery details.
    Uses search query link for PDF to handle async upload.
    """
    # Clean phone number
    phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "")
    if not phone_clean.startswith("52"):
        phone_clean = "52" + phone_clean
    
    order_id = order_data.get('ID_Pedido', '')
    nombre = order_data.get('Nombre_Negocio', 'Cliente')
    producto = order_data.get('Producto', '')
    kg = order_data.get('Kg_Reales', 0)
    total = order_data.get('Total_Cobrar', 0)
    fecha = order_data.get('Fecha_Ruta', '')
    
    # Build message
    message_lines = [
        f"Hola *{nombre}*. Detalle de entrega:",
        f"📅 Fecha: {fecha}",
        f"🧀 Producto: {producto} | ⚖️ Kg: {kg}",
        f"💰 Total: ${total:.2f}" if isinstance(total, (int, float)) else f"💰 Total: {total}",
        "",
        "📄 *Descargar Nota:*"
    ]
    
    if drive_folder_id:
        # Use search query link for resilient PDF access
        pdf_link = f"https://drive.google.com/drive/folders/{drive_folder_id}?q=name%20contains%20'{order_id}'"
        message_lines.append(pdf_link)
    
    message = "\n".join(message_lines)
    
    # URL encode the message
    import urllib.parse
    encoded_message = urllib.parse.quote(message)
    
    return f"https://wa.me/{phone_clean}?text={encoded_message}"
