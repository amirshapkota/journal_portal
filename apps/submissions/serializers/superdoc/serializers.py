"""
SuperDoc Integration Serializers.
Simple serializers for document creation and metadata.
"""

from rest_framework import serializers
from ...models.models import Document, Submission
from apps.users.models import Profile


class SuperDocCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new SuperDoc documents.
    """
    file = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = Document
        fields = [
            'id', 'submission', 'title', 'document_type', 
            'description', 'file', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        file = validated_data.pop('file', None)
        
        # Create document
        document = Document.objects.create(
            **validated_data,
            created_by=self.context['request'].user.profile
        )
        
        # Handle file upload if provided
        if file:
            document.original_file = file
            document.file_name = file.name
            document.file_size = file.size
            document.save()
        
        return document


class SuperDocMetadataSerializer(serializers.ModelSerializer):
    """
    Serializer for document metadata (read-only).
    """
    created_by_name = serializers.CharField(source='created_by.display_name', read_only=True)
    last_edited_by_name = serializers.CharField(source='last_edited_by.display_name', read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'submission', 'submission_title', 'title', 
            'document_type', 'description', 'file_name', 'file_size',
            'file_url', 'created_by', 'created_by_name', 'last_edited_by', 
            'last_edited_by_name', 'last_edited_at', 
            'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_file_url(self, obj):
        """Generate absolute URL for the original file."""
        if obj.original_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.original_file.url)
            return obj.original_file.url
        return None
