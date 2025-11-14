"""
Serializers for Submission management.
Handles submission CRUD, author management, and document upload.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Submission, AuthorContribution, Document, DocumentVersion, Comment
from apps.users.serializers import ProfileSerializer
from apps.journals.serializers import JournalListSerializer

User = get_user_model()


class AuthorContributionSerializer(serializers.ModelSerializer):
    """Serializer for Author Contribution management."""
    
    profile = ProfileSerializer(read_only=True)
    profile_id = serializers.UUIDField(write_only=True)
    contrib_role_display = serializers.CharField(source='get_contrib_role_display', read_only=True)
    
    class Meta:
        model = AuthorContribution
        fields = (
            'id', 'profile', 'profile_id', 'order', 'contrib_role',
            'contrib_role_display', 'contribution_details', 'has_agreed',
            'agreed_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate_profile_id(self, value):
        """Validate that profile exists."""
        from apps.users.models import Profile
        try:
            Profile.objects.get(id=value)
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Profile does not exist.")
        return value


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Serializer for Document Version."""
    
    created_by = ProfileSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentVersion
        fields = (
            'id', 'version_number', 'change_summary', 'file', 'file_url',
            'file_name', 'file_size', 'is_current', 'immutable_flag',
            'created_by', 'created_at'
        )
        read_only_fields = (
            'id', 'version_number', 'file_size', 'file_hash',
            'created_by', 'created_at'
        )
    
    def get_file_url(self, obj):
        """Get secure file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document management."""
    
    created_by = ProfileSerializer(read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    last_edited_by = ProfileSerializer(read_only=True)
    
    class Meta:
        model = Document
        fields = (
            'id', 'title', 'document_type', 'document_type_display',
            'description', 'created_by', 'file_name', 'file_size',
            'last_edited_by', 'last_edited_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_by', 'file_name', 'file_size', 
                           'last_edited_by', 'last_edited_at', 'created_at', 'updated_at')


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Document Comments."""
    
    author = ProfileSerializer(read_only=True)
    resolved_by = ProfileSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    comment_type_display = serializers.CharField(source='get_comment_type_display', read_only=True)
    
    class Meta:
        model = Comment
        fields = (
            'id', 'author', 'comment_type', 'comment_type_display', 'text',
            'location', 'resolved', 'resolved_by', 'resolved_at',
            'parent_comment', 'replies', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'author', 'resolved_by', 'resolved_at',
            'created_at', 'updated_at'
        )
    
    def get_replies(self, obj):
        """Get comment replies."""
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []


class SubmissionSerializer(serializers.ModelSerializer):
    """Comprehensive Submission serializer."""
    
    journal = JournalListSerializer(read_only=True)
    journal_id = serializers.UUIDField(write_only=True)
    corresponding_author = ProfileSerializer(read_only=True)
    author_contributions = AuthorContributionSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Submission
        fields = (
            'id', 'journal', 'journal_id', 'title', 'abstract',
            'corresponding_author', 'author_contributions', 'documents',
            'status', 'status_display', 'submission_number', 'metadata_json',
            'compliance_score', 'created_at', 'submitted_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'corresponding_author', 'submission_number',
            'compliance_score', 'submitted_at', 'created_at', 'updated_at'
        )
    
    def validate_journal_id(self, value):
        """Validate that journal exists and is accepting submissions."""
        from apps.journals.models import Journal
        try:
            journal = Journal.objects.get(id=value)
            if not journal.is_accepting_submissions:
                raise serializers.ValidationError(
                    "This journal is not currently accepting submissions."
                )
            return value
        except Journal.DoesNotExist:
            raise serializers.ValidationError("Journal does not exist.")
    
    def create(self, validated_data):
        """Create submission with corresponding author."""
        # Set corresponding author from request user
        user = self.context['request'].user
        if hasattr(user, 'profile'):
            validated_data['corresponding_author'] = user.profile
        else:
            raise serializers.ValidationError(
                "User must have a profile to create submissions."
            )
        
        return super().create(validated_data)


class SubmissionListSerializer(serializers.ModelSerializer):
    """Lightweight Submission serializer for list views."""
    
    journal_name = serializers.CharField(source='journal.title', read_only=True)
    corresponding_author_name = serializers.CharField(
        source='corresponding_author.display_name', 
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Submission
        fields = (
            'id', 'title', 'journal_name', 'corresponding_author_name',
            'status', 'status_display', 'submission_number', 'document_count',
            'created_at', 'submitted_at', 'updated_at'
        )
    
    def get_document_count(self, obj):
        """Get document count for submission."""
        return obj.documents.count()


class SubmissionStatusUpdateSerializer(serializers.Serializer):
    """Serializer for submission status updates."""
    
    status = serializers.ChoiceField(choices=Submission.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate_status(self, value):
        """Validate status transition."""
        submission = self.context.get('submission')
        if not submission:
            return value
        
        current_status = submission.status
        
        # Define allowed transitions
        allowed_transitions = {
            'DRAFT': ['SUBMITTED', 'WITHDRAWN'],
            'SUBMITTED': ['UNDER_REVIEW', 'WITHDRAWN', 'REJECTED'],
            'UNDER_REVIEW': ['REVISION_REQUIRED', 'ACCEPTED', 'REJECTED'],
            'REVISION_REQUIRED': ['REVISED', 'WITHDRAWN'],
            'REVISED': ['UNDER_REVIEW', 'ACCEPTED', 'REJECTED'],
            'ACCEPTED': ['PUBLISHED'],
            'REJECTED': [],  # Final state
            'WITHDRAWN': [],  # Final state  
            'PUBLISHED': []  # Final state
        }
        
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {value}"
            )
        
        return value


class AddAuthorSerializer(serializers.Serializer):
    """Serializer for adding authors to submissions."""
    
    profile_id = serializers.UUIDField()
    contrib_role = serializers.ChoiceField(choices=AuthorContribution.CONTRIBUTION_ROLE_CHOICES)
    order = serializers.IntegerField(min_value=1)
    contribution_details = serializers.JSONField(required=False, default=dict)
    
    def validate_profile_id(self, value):
        """Validate that profile exists."""
        from apps.users.models import Profile
        try:
            return Profile.objects.get(id=value)
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Profile does not exist.")
    
    def validate(self, attrs):
        """Validate that author isn't already on this submission."""
        profile = attrs['profile_id']
        submission = self.context['submission']
        
        existing = AuthorContribution.objects.filter(
            submission=submission,
            profile=profile
        ).exists()
        
        if existing:
            raise serializers.ValidationError(
                "This author is already part of the submission."
            )
        
        # Check order conflicts
        order = attrs['order']
        order_exists = AuthorContribution.objects.filter(
            submission=submission,
            order=order
        ).exists()
        
        if order_exists:
            raise serializers.ValidationError(
                f"Author order {order} is already taken."
            )
        
        return attrs


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for document uploads."""
    
    file = serializers.FileField()
    
    class Meta:
        model = Document
        fields = ('title', 'document_type', 'description', 'file')
    
    def validate_file(self, value):
        """Validate uploaded file using secure file storage."""
        if not value:
            raise serializers.ValidationError("File is required")
        
        # Use SecureFileStorage validation
        try:
            from apps.common.storage import SecureFileStorage
            document_type = self.initial_data.get('document_type', 'DEFAULT')
            SecureFileStorage.validate_file(value, document_type)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        
        return value
    
    def create(self, validated_data):
        """Create document with initial version using secure file storage."""
        file = validated_data.pop('file')
        submission = self.context['submission']
        user = self.context['request'].user
        
        # Create document first
        document = Document.objects.create(
            submission=submission,
            created_by=user.profile,
            **validated_data
        )
        
        # Store file securely
        try:
            from apps.common.storage import SecureFileStorage
            storage_result = SecureFileStorage.store_file(
                file,
                document.document_type,
                str(document.id)
            )
            
            # Create initial version with secure storage info
            version = DocumentVersion.objects.create(
                document=document,
                version_number=1,
                file=storage_result['stored_path'],
                file_name=storage_result['original_name'],
                file_size=storage_result['file_size'],
                file_hash=storage_result['file_hash'],
                created_by=user.profile,
                change_summary="Initial upload",
                is_current=True
            )
            
            # Set current version
            document.current_version = version
            document.save()
            
        except Exception as e:
            # Clean up document if file storage fails
            document.delete()
            raise serializers.ValidationError(f"File storage failed: {str(e)}")
        
        return document