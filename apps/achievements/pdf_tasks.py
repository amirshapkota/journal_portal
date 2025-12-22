"""
Celery task for generating certificate PDFs.
"""

from celery import shared_task
from django.core.files.base import ContentFile
from django.conf import settings
import os
from .models import Certificate
from .pdf_generator import generate_certificate_pdf


@shared_task(name='apps.achievements.tasks.generate_certificate_pdf_task')
def generate_certificate_pdf_task(certificate_id):
    """
    Background task to generate PDF for a certificate.
    
    Args:
        certificate_id: UUID of the certificate
        
    Returns:
        dict: Status and file URL
    """
    try:
        certificate = Certificate.objects.get(id=certificate_id)
        
        # Skip if already generated
        if certificate.pdf_generated and certificate.file_url:
            return {
                'status': 'already_generated',
                'certificate_id': str(certificate.id),
                'file_url': certificate.file_url
            }
        
        # Generate PDF
        pdf_buffer = generate_certificate_pdf(certificate)
        
        # Create filename
        filename = f"certificate_{certificate.certificate_number}.pdf"
        
        # Save to media storage
        from django.core.files.storage import default_storage
        file_path = f"certificates/{certificate.recipient.id}/{filename}"
        
        # Save file
        saved_path = default_storage.save(file_path, ContentFile(pdf_buffer.read()))
        
        # Update certificate
        certificate.file_url = default_storage.url(saved_path)
        certificate.pdf_generated = True
        certificate.save(update_fields=['file_url', 'pdf_generated'])
        
        return {
            'status': 'success',
            'certificate_id': str(certificate.id),
            'file_url': certificate.file_url,
            'certificate_number': certificate.certificate_number
        }
        
    except Certificate.DoesNotExist:
        return {
            'status': 'error',
            'message': f'Certificate {certificate_id} not found'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'certificate_id': str(certificate_id)
        }


@shared_task(name='apps.achievements.tasks.generate_all_missing_pdfs')
def generate_all_missing_pdfs():
    """
    Background task to generate PDFs for all certificates that don't have them.
    
    Returns:
        dict: Summary of PDF generation
    """
    certificates_without_pdf = Certificate.objects.filter(pdf_generated=False)
    total = certificates_without_pdf.count()
    
    if total == 0:
        return {
            'status': 'success',
            'message': 'All certificates already have PDFs',
            'total': 0,
            'generated': 0
        }
    
    generated = 0
    errors = []
    
    for certificate in certificates_without_pdf:
        try:
            result = generate_certificate_pdf_task(certificate.id)
            if result['status'] == 'success':
                generated += 1
        except Exception as e:
            errors.append({
                'certificate_id': str(certificate.id),
                'error': str(e)
            })
    
    return {
        'status': 'success',
        'message': f'Generated {generated} PDFs out of {total} certificates',
        'total': total,
        'generated': generated,
        'errors': errors if errors else None
    }
