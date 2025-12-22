"""
Certificate PDF Generator

Generates professional certificate PDFs with verification codes and QR codes.
"""

from io import BytesIO
from datetime import datetime
from django.conf import settings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode


class CertificatePDFGenerator:
    """
    Generates professional certificate PDFs.
    """
    
    def __init__(self, certificate):
        """
        Initialize the PDF generator with a certificate instance.
        
        Args:
            certificate: Certificate model instance
        """
        self.certificate = certificate
        self.width, self.height = landscape(A4)
        self.buffer = BytesIO()
        
    def _create_qr_code(self, data):
        """
        Create a QR code image for verification.
        
        Args:
            data: String to encode in QR code
            
        Returns:
            BytesIO buffer containing QR code image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        return qr_buffer
    
    def _draw_border(self, canvas_obj):
        """
        Draw decorative border around certificate.
        
        Args:
            canvas_obj: ReportLab canvas object
        """
        # Outer border
        canvas_obj.setStrokeColor(colors.HexColor('#1e40af'))  # Blue
        canvas_obj.setLineWidth(3)
        canvas_obj.rect(20*mm, 20*mm, self.width - 40*mm, self.height - 40*mm)
        
        # Inner border
        canvas_obj.setStrokeColor(colors.HexColor('#60a5fa'))  # Light blue
        canvas_obj.setLineWidth(1)
        canvas_obj.rect(25*mm, 25*mm, self.width - 50*mm, self.height - 50*mm)
        
        # Decorative corners
        canvas_obj.setStrokeColor(colors.HexColor('#fbbf24'))  # Gold
        canvas_obj.setLineWidth(2)
        corner_size = 15*mm
        
        # Top-left corner
        canvas_obj.line(20*mm, self.height - 20*mm, 20*mm + corner_size, self.height - 20*mm)
        canvas_obj.line(20*mm, self.height - 20*mm, 20*mm, self.height - 20*mm - corner_size)
        
        # Top-right corner
        canvas_obj.line(self.width - 20*mm, self.height - 20*mm, self.width - 20*mm - corner_size, self.height - 20*mm)
        canvas_obj.line(self.width - 20*mm, self.height - 20*mm, self.width - 20*mm, self.height - 20*mm - corner_size)
        
        # Bottom-left corner
        canvas_obj.line(20*mm, 20*mm, 20*mm + corner_size, 20*mm)
        canvas_obj.line(20*mm, 20*mm, 20*mm, 20*mm + corner_size)
        
        # Bottom-right corner
        canvas_obj.line(self.width - 20*mm, 20*mm, self.width - 20*mm - corner_size, 20*mm)
        canvas_obj.line(self.width - 20*mm, 20*mm, self.width - 20*mm, 20*mm + corner_size)
    
    def _add_watermark(self, canvas_obj):
        """
        Add subtle watermark to certificate.
        
        Args:
            canvas_obj: ReportLab canvas object
        """
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 60)
        canvas_obj.setFillColor(colors.Color(0.95, 0.95, 0.95, alpha=0.3))
        canvas_obj.translate(self.width / 2, self.height / 2)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(0, 0, 'CERTIFIED')
        canvas_obj.restoreState()
    
    def generate(self):
        """
        Generate the certificate PDF.
        
        Returns:
            BytesIO buffer containing the PDF
        """
        # Create PDF
        pdf = SimpleDocTemplate(
            self.buffer,
            pagesize=landscape(A4),
            rightMargin=30*mm,
            leftMargin=30*mm,
            topMargin=30*mm,
            bottomMargin=30*mm,
        )
        
        # Container for elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=36,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=18,
            textColor=colors.HexColor('#374151'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica',
        )
        
        recipient_style = ParagraphStyle(
            'RecipientStyle',
            parent=styles['Normal'],
            fontSize=28,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        )
        
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica',
            leading=20,
        )
        
        citation_style = ParagraphStyle(
            'CitationStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique',
            leftIndent=50,
            rightIndent=50,
        )
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#9ca3af'),
            alignment=TA_CENTER,
            fontName='Helvetica',
        )
        
        # Header - Certificate Type
        cert_type_map = {
            'AWARD': 'Certificate of Award',
            'BADGE': 'Certificate of Achievement',
            'RECOGNITION': 'Certificate of Recognition',
            'PARTICIPATION': 'Certificate of Participation',
        }
        cert_type_text = cert_type_map.get(self.certificate.certificate_type, 'Certificate')
        elements.append(Paragraph(cert_type_text, title_style))
        elements.append(Spacer(1, 10*mm))
        
        # Presentation text
        elements.append(Paragraph('This certificate is proudly presented to', subtitle_style))
        elements.append(Spacer(1, 5*mm))
        
        # Recipient name
        recipient_name = self.certificate.recipient.display_name
        elements.append(Paragraph(f'<b>{recipient_name}</b>', recipient_style))
        elements.append(Spacer(1, 10*mm))
        
        # Award/Badge title
        elements.append(Paragraph(f'<b>{self.certificate.title}</b>', body_style))
        elements.append(Spacer(1, 5*mm))
        
        # Description
        if self.certificate.description:
            elements.append(Paragraph(self.certificate.description, body_style))
            elements.append(Spacer(1, 5*mm))
        
        # Citation (if available)
        citation = None
        if self.certificate.award and self.certificate.award.citation:
            citation = self.certificate.award.citation
        elif self.certificate.custom_data and 'citation' in self.certificate.custom_data:
            citation = self.certificate.custom_data['citation']
        
        if citation:
            elements.append(Paragraph(f'"{citation}"', citation_style))
            elements.append(Spacer(1, 8*mm))
        else:
            elements.append(Spacer(1, 10*mm))
        
        # Journal info (if available)
        if self.certificate.journal:
            journal_text = f'Issued by {self.certificate.journal.title}'
            elements.append(Paragraph(journal_text, body_style))
            elements.append(Spacer(1, 5*mm))
        
        # Date and certificate number
        issued_date = self.certificate.issued_date.strftime('%B %d, %Y')
        cert_info = f'Issued on {issued_date} | Certificate No: {self.certificate.certificate_number}'
        elements.append(Paragraph(cert_info, body_style))
        elements.append(Spacer(1, 8*mm))
        
        # QR Code and Verification
        verification_url = f"{settings.FRONTEND_URL}/certificates/verify?code={self.certificate.verification_code}"
        qr_buffer = self._create_qr_code(verification_url)
        qr_image = Image(qr_buffer, width=60, height=60)
        
        # Create table for QR code and verification text
        qr_data = [
            [qr_image, Paragraph(f'<b>Verification Code:</b> {self.certificate.verification_code}<br/>'
                                f'Scan QR code or visit:<br/>'
                                f'{settings.FRONTEND_URL}/certificates/verify', footer_style)]
        ]
        
        qr_table = Table(qr_data, colWidths=[70, 400])
        qr_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(qr_table)
        elements.append(Spacer(1, 5*mm))
        
        # Footer disclaimer
        disclaimer = 'This is an official certificate. Verify authenticity using the verification code above.'
        elements.append(Paragraph(disclaimer, footer_style))
        
        # Build PDF with custom canvas for borders and watermark
        def add_page_decorations(canvas_obj, doc):
            canvas_obj.saveState()
            self._add_watermark(canvas_obj)
            self._draw_border(canvas_obj)
            canvas_obj.restoreState()
        
        pdf.build(elements, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
        
        # Get PDF data
        self.buffer.seek(0)
        return self.buffer
    
    def save_to_file(self, file_path):
        """
        Generate and save PDF to file.
        
        Args:
            file_path: Path where to save the PDF
            
        Returns:
            File path where PDF was saved
        """
        pdf_buffer = self.generate()
        
        with open(file_path, 'wb') as f:
            f.write(pdf_buffer.read())
        
        return file_path


def generate_certificate_pdf(certificate):
    """
    Convenience function to generate certificate PDF.
    
    Args:
        certificate: Certificate model instance
        
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = CertificatePDFGenerator(certificate)
    return generator.generate()
