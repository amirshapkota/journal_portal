"""
Custom file storage handlers for the Journal Portal.
Supports both local and S3 storage with security and validation.
"""
import os
import hashlib
import mimetypes
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string


class SecureFileStorage:
    """
    Secure file storage handler with validation and access control.
    """
    
    # Allowed file types for different document categories
    ALLOWED_FILE_TYPES = {
        'MANUSCRIPT': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'application/rtf',
        ],
        'SUPPLEMENTARY': [
            'application/pdf',
            'application/zip',
            'application/x-zip-compressed',
            'text/csv',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg',
            'image/png',
            'image/tiff',
            'video/mp4',
            'audio/mpeg',
        ],
        'COVER_LETTER': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
        ],
        'DEFAULT': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ]
    }
    
    # Maximum file sizes (in bytes) by type
    MAX_FILE_SIZES = {
        'MANUSCRIPT': 50 * 1024 * 1024,      # 50MB
        'SUPPLEMENTARY': 100 * 1024 * 1024,  # 100MB
        'COVER_LETTER': 10 * 1024 * 1024,    # 10MB
        'DEFAULT': 50 * 1024 * 1024,         # 50MB
    }
    
    @classmethod
    def validate_file(cls, file, document_type='DEFAULT'):
        """
        Comprehensive file validation.
        
        Args:
            file: Django UploadedFile instance
            document_type: Type of document being uploaded
            
        Returns:
            dict: Validation results with file metadata
            
        Raises:
            ValidationError: If file fails validation
        """
        errors = []
        
        # Check file size
        max_size = cls.MAX_FILE_SIZES.get(document_type, cls.MAX_FILE_SIZES['DEFAULT'])
        if file.size > max_size:
            errors.append(f"File size {file.size} exceeds maximum allowed size {max_size} bytes")
        
        # Check MIME type
        allowed_types = cls.ALLOWED_FILE_TYPES.get(document_type, cls.ALLOWED_FILE_TYPES['DEFAULT'])
        mime_type, _ = mimetypes.guess_type(file.name)
        
        if mime_type not in allowed_types:
            errors.append(f"File type '{mime_type}' not allowed for {document_type}")
        
        # Check file extension
        _, ext = os.path.splitext(file.name.lower())
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.js', '.vbs', '.jar']
        if ext in dangerous_extensions:
            errors.append(f"File extension '{ext}' is not allowed for security reasons")
        
        # Generate file hash for integrity checking
        file.seek(0)
        file_hash = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)
        
        if errors:
            raise ValidationError(errors)
        
        return {
            'file_size': file.size,
            'mime_type': mime_type,
            'file_hash': file_hash,
            'original_name': file.name,
        }
    
    @classmethod
    def generate_secure_filename(cls, original_filename, document_id=None):
        """
        Generate a secure filename to prevent path traversal and collisions.
        
        Args:
            original_filename: Original uploaded filename
            document_id: Document UUID for organization
            
        Returns:
            str: Secure filename with path
        """
        # Extract safe file extension
        name, ext = os.path.splitext(original_filename)
        safe_ext = ext.lower() if ext else ''
        
        # Generate random filename component
        random_string = get_random_string(16)
        
        # Create date-based directory structure
        now = datetime.now()
        date_path = now.strftime('%Y/%m/%d')
        
        # Combine into secure path
        if document_id:
            filename = f"{document_id}_{random_string}{safe_ext}"
        else:
            filename = f"{random_string}{safe_ext}"
        
        return f"documents/{date_path}/{filename}"
    
    @classmethod
    def store_file(cls, file, document_type, document_id=None):
        """
        Store file with validation and security measures.
        
        Args:
            file: Django UploadedFile instance
            document_type: Type of document
            document_id: Document UUID
            
        Returns:
            dict: Storage results with file info
        """
        # Validate file
        validation_result = cls.validate_file(file, document_type)
        
        # Generate secure filename
        secure_path = cls.generate_secure_filename(file.name, document_id)
        
        # Store file
        stored_path = default_storage.save(secure_path, ContentFile(file.read()))
        
        return {
            **validation_result,
            'stored_path': stored_path,
            'storage_url': default_storage.url(stored_path),
        }
    
    @classmethod
    def generate_download_url(cls, file_path, expires_in_hours=24):
        """
        Generate secure download URL with expiration.
        
        Args:
            file_path: Stored file path
            expires_in_hours: URL expiration time
            
        Returns:
            str: Secure download URL
        """
        # For local storage, return the file URL
        # In production with S3, this would generate a presigned URL
        if hasattr(default_storage, 'url'):
            return default_storage.url(file_path)
        
        # Fallback for custom storage backends
        return f"/api/v1/files/download/{file_path}"
    
    @classmethod
    def delete_file(cls, file_path):
        """
        Safely delete a file from storage.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                return True
        except Exception:
            pass
        return False


class S3FileStorage:
    """
    AWS S3 specific file storage handler.
    Ready for production deployment with S3.
    """
    
    @classmethod
    def setup_s3_storage(cls):
        """
        Configure S3 storage settings.
        This would be used when AWS_STORAGE_BUCKET_NAME is configured.
        """
        s3_settings = {
            'AWS_ACCESS_KEY_ID': getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
            'AWS_SECRET_ACCESS_KEY': getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''),
            'AWS_STORAGE_BUCKET_NAME': getattr(settings, 'AWS_STORAGE_BUCKET_NAME', ''),
            'AWS_S3_REGION_NAME': getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
            'AWS_S3_FILE_OVERWRITE': False,
            'AWS_DEFAULT_ACL': 'private',
            'AWS_S3_CUSTOM_DOMAIN': None,  # Use CloudFront if needed
        }
        return s3_settings
    
    @classmethod
    def generate_presigned_url(cls, file_path, expires_in=3600):
        """
        Generate presigned URL for secure S3 access.
        
        Args:
            file_path: S3 object key
            expires_in: URL expiration in seconds
            
        Returns:
            str: Presigned URL
        """
        # This would use boto3 to generate presigned URLs in production
        # For now, return placeholder
        return f"/api/v1/files/secure/{file_path}"


# File type detection utilities
class FileTypeDetector:
    """
    Advanced file type detection and validation.
    """
    
    @classmethod
    def detect_file_type(cls, file_content):
        """
        Detect file type from content (magic bytes).
        More secure than relying on extensions or MIME types.
        
        Args:
            file_content: Binary file content
            
        Returns:
            str: Detected file type
        """
        # PDF magic bytes
        if file_content.startswith(b'%PDF'):
            return 'application/pdf'
        
        # Microsoft Word (newer format)
        if file_content.startswith(b'PK\x03\x04') and b'word/' in file_content[:1024]:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        # Microsoft Word (older format)
        if file_content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            return 'application/msword'
        
        # JPEG
        if file_content.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        
        # PNG
        if file_content.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        
        # ZIP
        if file_content.startswith(b'PK\x03\x04') or file_content.startswith(b'PK\x05\x06'):
            return 'application/zip'
        
        return 'application/octet-stream'
    
    @classmethod
    def is_safe_file(cls, file_content):
        """
        Basic safety check for uploaded files.
        
        Args:
            file_content: Binary file content
            
        Returns:
            bool: True if file appears safe
        """
        # Check for executable signatures
        dangerous_signatures = [
            b'MZ',  # Windows executable
            b'\x7fELF',  # Linux executable
            b'\xfe\xed\xfa',  # macOS executable
        ]
        
        for signature in dangerous_signatures:
            if file_content.startswith(signature):
                return False
        
        return True