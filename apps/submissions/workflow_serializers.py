"""
Serializers for Copyediting and Production workflow management.
Handles copyediting assignments, files, discussions, and production workflow.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .copyediting_models import (
    CopyeditingAssignment, CopyeditingFile, CopyeditingDiscussion,
    CopyeditingMessage, CopyeditingMessageAttachment
)
from .production_models import (
    ProductionAssignment, ProductionFile, ProductionDiscussion,
    ProductionMessage, ProductionMessageAttachment, PublicationSchedule
)
from apps.users.serializers import ProfileSerializer

User = get_user_model()


# ============= COPYEDITING SERIALIZERS =============

class CopyeditingAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for Copyediting Assignment."""
    
    copyeditor = ProfileSerializer(read_only=True)
    copyeditor_id = serializers.UUIDField(write_only=True, required=True)
    assigned_by = ProfileSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = CopyeditingAssignment
        fields = (
            'id', 'submission', 'submission_title', 'copyeditor', 'copyeditor_id',
            'assigned_by', 'status', 'status_display', 'assigned_at',
            'due_date', 'started_at', 'completed_at', 'instructions',
            'completion_notes', 'is_overdue', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'assigned_by', 'assigned_at', 'started_at',
            'completed_at', 'created_at', 'updated_at'
        )
    
    def get_is_overdue(self, obj):
        """Check if assignment is overdue."""
        if obj.status in ['COMPLETED', 'CANCELLED']:
            return False
        return obj.due_date < timezone.now() if obj.due_date else False
    
    def validate_copyeditor_id(self, value):
        """Validate that copyeditor profile exists and has copyeditor role."""
        from apps.users.models import Profile, Role
        try:
            profile = Profile.objects.get(id=value)
            # Check if user has COPY_EDITOR role
            if not profile.roles.filter(name='EDITOR').exists():
                raise serializers.ValidationError(
                    "Selected user does not have COPY_EDITOR role."
                )
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Copyeditor profile does not exist.")
        return value
    
    def validate(self, attrs):
        """Validate assignment data."""
        if 'due_date' in attrs:
            if attrs['due_date'] < timezone.now():
                raise serializers.ValidationError({
                    'due_date': 'Due date cannot be in the past.'
                })
        return attrs
    
    def create(self, validated_data):
        """Create copyediting assignment."""
        # Set assigned_by from request user
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['assigned_by'] = request.user.profile
        
        # Move submission to COPYEDITING status
        submission = validated_data['submission']
        if submission.status == 'ACCEPTED':
            submission.status = 'COPYEDITING'
            submission.save()
        
        return super().create(validated_data)


class CopyeditingAssignmentListSerializer(serializers.ModelSerializer):
    """List serializer for Copyediting Assignments."""
    
    copyeditor = ProfileSerializer(read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    submission_id = serializers.UUIDField(source='submission.id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = CopyeditingAssignment
        fields = (
            'id', 'submission_id', 'submission_title', 'copyeditor',
            'status', 'status_display', 'assigned_at', 'due_date',
            'is_overdue', 'completed_at'
        )
    
    def get_is_overdue(self, obj):
        """Check if assignment is overdue."""
        if obj.status in ['COMPLETED', 'CANCELLED']:
            return False
        return obj.due_date < timezone.now() if obj.due_date else False


class CopyeditingFileSerializer(serializers.ModelSerializer):
    """Serializer for Copyediting Files."""
    
    uploaded_by = ProfileSerializer(read_only=True)
    approved_by = ProfileSerializer(read_only=True)
    last_edited_by = ProfileSerializer(read_only=True)
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CopyeditingFile
        fields = (
            'id', 'assignment', 'submission', 'file_type', 'file_type_display',
            'file', 'file_url', 'original_filename', 'file_size', 'mime_type',
            'version', 'description', 'uploaded_by', 'is_approved',
            'approved_by', 'approved_at', 'last_edited_by', 'last_edited_at',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'uploaded_by', 'file_size', 'mime_type', 'approved_by',
            'approved_at', 'last_edited_by', 'last_edited_at',
            'created_at', 'updated_at'
        )
    
    def get_file_url(self, obj):
        """Get secure file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
    
    def create(self, validated_data):
        """Create copyediting file."""
        # Set uploaded_by from request user
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['uploaded_by'] = request.user.profile
        
        # Extract file info
        file_obj = validated_data.get('file')
        if file_obj:
            validated_data['original_filename'] = file_obj.name
            validated_data['file_size'] = file_obj.size
            validated_data['mime_type'] = file_obj.content_type
        
        return super().create(validated_data)


class CopyeditingMessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Copyediting Message Attachments."""
    
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CopyeditingMessageAttachment
        fields = (
            'id', 'file', 'file_url', 'original_filename',
            'file_size', 'mime_type', 'created_at'
        )
        read_only_fields = ('id', 'file_size', 'mime_type', 'created_at')
    
    def get_file_url(self, obj):
        """Get secure file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class CopyeditingMessageSerializer(serializers.ModelSerializer):
    """Serializer for Copyediting Discussion Messages."""
    
    author = ProfileSerializer(read_only=True)
    attachments = CopyeditingMessageAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = CopyeditingMessage
        fields = (
            'id', 'discussion', 'author', 'message', 'has_attachments',
            'attachments', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'author', 'has_attachments', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        """Create message."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['author'] = request.user.profile
        return super().create(validated_data)


class CopyeditingDiscussionSerializer(serializers.ModelSerializer):
    """Serializer for Copyediting Discussions."""
    
    started_by = ProfileSerializer(read_only=True)
    closed_by = ProfileSerializer(read_only=True)
    participants = ProfileSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    messages = CopyeditingMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CopyeditingDiscussion
        fields = (
            'id', 'assignment', 'submission', 'subject', 'status',
            'status_display', 'started_by', 'participants', 'participant_ids',
            'messages', 'message_count', 'last_message', 'created_at',
            'updated_at', 'closed_at', 'closed_by'
        )
        read_only_fields = (
            'id', 'started_by', 'closed_by', 'created_at', 'updated_at', 'closed_at'
        )
    
    def get_message_count(self, obj):
        """Get total message count."""
        return obj.messages.count()
    
    def get_last_message(self, obj):
        """Get last message info."""
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'author': last_msg.author.user.get_full_name() or last_msg.author.user.email,
                'message': last_msg.message[:100],
                'created_at': last_msg.created_at
            }
        return None
    
    def create(self, validated_data):
        """Create discussion."""
        request = self.context.get('request')
        participant_ids = validated_data.pop('participant_ids', [])
        
        if request and hasattr(request.user, 'profile'):
            validated_data['started_by'] = request.user.profile
        
        discussion = super().create(validated_data)
        
        # Add participants
        if participant_ids:
            from apps.users.models import Profile
            participants = Profile.objects.filter(id__in=participant_ids)
            discussion.participants.set(participants)
        
        # Always add starter as participant
        if request and hasattr(request.user, 'profile'):
            discussion.participants.add(request.user.profile)
        
        return discussion


class CopyeditingDiscussionListSerializer(serializers.ModelSerializer):
    """List serializer for Copyediting Discussions."""
    
    started_by = ProfileSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CopyeditingDiscussion
        fields = (
            'id', 'subject', 'status', 'status_display', 'started_by',
            'message_count', 'last_message_at', 'created_at', 'updated_at'
        )
    
    def get_message_count(self, obj):
        """Get total message count."""
        return obj.messages.count()
    
    def get_last_message_at(self, obj):
        """Get last message timestamp."""
        last_msg = obj.messages.order_by('-created_at').first()
        return last_msg.created_at if last_msg else obj.created_at


# ============= PRODUCTION SERIALIZERS =============

class ProductionAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for Production Assignment."""
    
    production_assistant = ProfileSerializer(read_only=True)
    production_assistant_id = serializers.UUIDField(write_only=True, required=True)
    assigned_by = ProfileSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductionAssignment
        fields = (
            'id', 'submission', 'submission_title', 'production_assistant',
            'production_assistant_id', 'assigned_by', 'status', 'status_display',
            'assigned_at', 'due_date', 'started_at', 'completed_at',
            'instructions', 'completion_notes', 'is_overdue',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'assigned_by', 'assigned_at', 'started_at',
            'completed_at', 'created_at', 'updated_at'
        )
    
    def get_is_overdue(self, obj):
        """Check if assignment is overdue."""
        if obj.status in ['COMPLETED', 'CANCELLED']:
            return False
        return obj.due_date < timezone.now() if obj.due_date else False
    
    def validate_production_assistant_id(self, value):
        """Validate that production assistant profile exists and has appropriate role."""
        from apps.users.models import Profile, Role
        try:
            profile = Profile.objects.get(id=value)
            # Check if user has EDITOR role
            if not profile.roles.filter(name__in=['EDITOR']).exists():
                raise serializers.ValidationError(
                    "Selected user does not have EDITOR role."
                )
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Production assistant profile does not exist.")
        return value
    
    def validate(self, attrs):
        """Validate assignment data."""
        if 'due_date' in attrs:
            if attrs['due_date'] < timezone.now():
                raise serializers.ValidationError({
                    'due_date': 'Due date cannot be in the past.'
                })
        return attrs
    
    def create(self, validated_data):
        """Create production assignment."""
        # Set assigned_by from request user
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['assigned_by'] = request.user.profile
        
        # Move submission to IN_PRODUCTION status
        submission = validated_data['submission']
        if submission.status == 'COPYEDITING':
            submission.status = 'IN_PRODUCTION'
            submission.save()
        
        return super().create(validated_data)


class ProductionAssignmentListSerializer(serializers.ModelSerializer):
    """List serializer for Production Assignments."""
    
    production_assistant = ProfileSerializer(read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    submission_id = serializers.UUIDField(source='submission.id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductionAssignment
        fields = (
            'id', 'submission_id', 'submission_title', 'production_assistant',
            'status', 'status_display', 'assigned_at', 'due_date',
            'is_overdue', 'completed_at'
        )
    
    def get_is_overdue(self, obj):
        """Check if assignment is overdue."""
        if obj.status in ['COMPLETED', 'CANCELLED']:
            return False
        return obj.due_date < timezone.now() if obj.due_date else False


class ProductionFileSerializer(serializers.ModelSerializer):
    """Serializer for Production Files (Galleys)."""
    
    uploaded_by = ProfileSerializer(read_only=True)
    approved_by = ProfileSerializer(read_only=True)
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    galley_format_display = serializers.CharField(source='get_galley_format_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductionFile
        fields = (
            'id', 'assignment', 'submission', 'file_type', 'file_type_display',
            'galley_format', 'galley_format_display', 'file', 'file_url',
            'original_filename', 'file_size', 'mime_type', 'label', 'version',
            'description', 'uploaded_by', 'is_published', 'published_at',
            'is_approved', 'approved_by', 'approved_at', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'uploaded_by', 'file_size', 'mime_type', 'original_filename',
            'approved_by', 'approved_at', 'published_at', 'created_at', 'updated_at'
        )
    
    def get_file_url(self, obj):
        """Get secure file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
    
    def create(self, validated_data):
        """Create production file."""
        # Set uploaded_by from request user
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['uploaded_by'] = request.user.profile
        
        # Extract file info
        file_obj = validated_data.get('file')
        if file_obj:
            validated_data['original_filename'] = file_obj.name
            validated_data['file_size'] = file_obj.size
            validated_data['mime_type'] = file_obj.content_type
        
        return super().create(validated_data)


class ProductionMessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Production Message Attachments."""
    
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductionMessageAttachment
        fields = (
            'id', 'file', 'file_url', 'original_filename',
            'file_size', 'mime_type', 'created_at'
        )
        read_only_fields = ('id', 'file_size', 'mime_type', 'created_at')
    
    def get_file_url(self, obj):
        """Get secure file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class ProductionMessageSerializer(serializers.ModelSerializer):
    """Serializer for Production Discussion Messages."""
    
    author = ProfileSerializer(read_only=True)
    attachments = ProductionMessageAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductionMessage
        fields = (
            'id', 'discussion', 'author', 'message', 'has_attachments',
            'attachments', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'author', 'has_attachments', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        """Create message."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['author'] = request.user.profile
        return super().create(validated_data)


class ProductionDiscussionSerializer(serializers.ModelSerializer):
    """Serializer for Production Discussions."""
    
    started_by = ProfileSerializer(read_only=True)
    closed_by = ProfileSerializer(read_only=True)
    participants = ProfileSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    messages = ProductionMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProductionDiscussion
        fields = (
            'id', 'assignment', 'submission', 'subject', 'status',
            'status_display', 'started_by', 'participants', 'participant_ids',
            'messages', 'message_count', 'last_message', 'created_at',
            'updated_at', 'closed_at', 'closed_by'
        )
        read_only_fields = (
            'id', 'started_by', 'closed_by', 'created_at', 'updated_at', 'closed_at'
        )
    
    def get_message_count(self, obj):
        """Get total message count."""
        return obj.messages.count()
    
    def get_last_message(self, obj):
        """Get last message info."""
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'author': last_msg.author.user.get_full_name() or last_msg.author.user.email,
                'message': last_msg.message[:100],
                'created_at': last_msg.created_at
            }
        return None
    
    def create(self, validated_data):
        """Create discussion."""
        request = self.context.get('request')
        participant_ids = validated_data.pop('participant_ids', [])
        
        if request and hasattr(request.user, 'profile'):
            validated_data['started_by'] = request.user.profile
        
        discussion = super().create(validated_data)
        
        # Add participants
        if participant_ids:
            from apps.users.models import Profile
            participants = Profile.objects.filter(id__in=participant_ids)
            discussion.participants.set(participants)
        
        # Always add starter as participant
        if request and hasattr(request.user, 'profile'):
            discussion.participants.add(request.user.profile)
        
        return discussion


class ProductionDiscussionListSerializer(serializers.ModelSerializer):
    """List serializer for Production Discussions."""
    
    started_by = ProfileSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProductionDiscussion
        fields = (
            'id', 'subject', 'status', 'status_display', 'started_by',
            'message_count', 'last_message_at', 'created_at', 'updated_at'
        )
    
    def get_message_count(self, obj):
        """Get total message count."""
        return obj.messages.count()
    
    def get_last_message_at(self, obj):
        """Get last message timestamp."""
        last_msg = obj.messages.order_by('-created_at').first()
        return last_msg.created_at if last_msg else obj.created_at


class PublicationScheduleSerializer(serializers.ModelSerializer):
    """Serializer for Publication Schedule."""
    
    scheduled_by = ProfileSerializer(read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PublicationSchedule
        fields = (
            'id', 'submission', 'submission_title', 'status', 'status_display',
            'scheduled_date', 'published_date', 'volume', 'issue', 'year',
            'doi', 'pages', 'scheduled_by', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'scheduled_by', 'published_date', 'created_at', 'updated_at'
        )
    
    def validate_scheduled_date(self, value):
        """Validate scheduled date."""
        if value < timezone.now():
            raise serializers.ValidationError("Scheduled date cannot be in the past.")
        return value
    
    def create(self, validated_data):
        """Create publication schedule."""
        # Set scheduled_by from request user
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['scheduled_by'] = request.user.profile
        
        # Move submission to SCHEDULED status
        submission = validated_data['submission']
        if submission.status == 'IN_PRODUCTION':
            submission.status = 'SCHEDULED'
            submission.save()
        
        return super().create(validated_data)
