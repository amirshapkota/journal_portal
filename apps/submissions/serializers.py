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
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = (
            'id', 'title', 'document_type', 'document_type_display',
            'description', 'created_by', 'file_name', 'file_size', 'file_url',
            'last_edited_by', 'last_edited_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_by', 'file_name', 'file_size', 
                           'last_edited_by', 'last_edited_at', 'created_at', 'updated_at')
    
    def get_file_url(self, obj):
        """Generate absolute URL for the original file."""
        if obj.original_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.original_file.url)
            return obj.original_file.url
        return None


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


class ReviewAssignmentBasicSerializer(serializers.ModelSerializer):
    """Basic serializer for review assignments in submission details."""
    reviewer_name = serializers.CharField(source='reviewer.display_name', read_only=True)
    reviewer_email = serializers.CharField(source='reviewer.user.email', read_only=True)
    reviewer_affiliation = serializers.CharField(source='reviewer.affiliation_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        from apps.reviews.models import ReviewAssignment
        model = ReviewAssignment
        fields = [
            'id', 'reviewer', 'reviewer_name', 'reviewer_email', 'reviewer_affiliation',
            'assigned_by', 'assigned_by_name', 'status', 'status_display',
            'invited_at', 'due_date', 'accepted_at', 'declined_at', 'completed_at',
            'decline_reason', 'review_round', 'is_overdue', 'days_remaining'
        ]
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_days_remaining(self, obj):
        return obj.days_remaining()


class SubmissionSerializer(serializers.ModelSerializer):
    """Comprehensive Submission serializer."""
    
    journal = JournalListSerializer(read_only=True)
    journal_id = serializers.UUIDField(write_only=True)
    corresponding_author = ProfileSerializer(read_only=True)
    author_contributions = AuthorContributionSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    review_assignments = ReviewAssignmentBasicSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    review_type_display = serializers.CharField(source='get_review_type_display', read_only=True)
    
    # Taxonomy fields
    section = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    research_type = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    
    # Write-only IDs for taxonomy
    section_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    research_type_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    area_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Submission
        fields = (
            'id', 'journal', 'journal_id', 'title', 'abstract',
            'section', 'section_id', 'category', 'category_id',
            'research_type', 'research_type_id', 'area', 'area_id',
            'corresponding_author', 'author_contributions', 'documents',
            'review_assignments', 'status', 'status_display', 
            'submission_number', 'review_type', 'review_type_display', 
            'metadata_json', 'compliance_score', 
            'created_at', 'submitted_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'corresponding_author', 'submission_number',
            'compliance_score', 'submitted_at', 'created_at', 'updated_at'
        )
    
    def get_section(self, obj):
        """Get section details with full hierarchy."""
        if obj.section:
            section_data = {
                'id': str(obj.section.id),
                'name': obj.section.name,
                'code': obj.section.code,
                'description': obj.section.description
            }
            
            # Add category if it exists
            if obj.category and obj.category.section_id == obj.section.id:
                section_data['category'] = {
                    'id': str(obj.category.id),
                    'name': obj.category.name,
                    'code': obj.category.code,
                    'description': obj.category.description
                }
                
                # Add research_type if it exists
                if obj.research_type and obj.research_type.category_id == obj.category.id:
                    section_data['category']['research_type'] = {
                        'id': str(obj.research_type.id),
                        'name': obj.research_type.name,
                        'code': obj.research_type.code,
                        'description': obj.research_type.description
                    }
                    
                    # Add area if it exists
                    if obj.area and obj.area.research_type_id == obj.research_type.id:
                        section_data['category']['research_type']['area'] = {
                            'id': str(obj.area.id),
                            'name': obj.area.name,
                            'code': obj.area.code,
                            'description': obj.area.description,
                            'keywords': obj.area.keywords
                        }
            
            return section_data
        return None
    
    def get_category(self, obj):
        """Get category details - not needed when using tree structure."""
        return None
    
    def get_research_type(self, obj):
        """Get research type details - not needed when using tree structure."""
        return None
    
    def get_area(self, obj):
        """Get area details - not needed when using tree structure."""
        return None
    
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
        """Create submission with corresponding author and taxonomy."""
        # Extract taxonomy IDs
        section_id = validated_data.pop('section_id', None)
        category_id = validated_data.pop('category_id', None)
        research_type_id = validated_data.pop('research_type_id', None)
        area_id = validated_data.pop('area_id', None)
        
        # Set corresponding author from request user
        user = self.context['request'].user
        corresponding_author_profile = None
        if hasattr(user, 'profile'):
            validated_data['corresponding_author'] = user.profile
            corresponding_author_profile = user.profile
        else:
            raise serializers.ValidationError(
                "User must have a profile to create submissions."
            )
        
        # Set taxonomy relationships
        from apps.journals.models import Section, Category, ResearchType, Area
        
        if section_id:
            try:
                validated_data['section'] = Section.objects.get(id=section_id)
            except Section.DoesNotExist:
                raise serializers.ValidationError({"section_id": "Section does not exist."})
        
        if category_id:
            try:
                validated_data['category'] = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError({"category_id": "Category does not exist."})
        
        if research_type_id:
            try:
                validated_data['research_type'] = ResearchType.objects.get(id=research_type_id)
            except ResearchType.DoesNotExist:
                raise serializers.ValidationError({"research_type_id": "ResearchType does not exist."})
        
        if area_id:
            try:
                validated_data['area'] = Area.objects.get(id=area_id)
            except Area.DoesNotExist:
                raise serializers.ValidationError({"area_id": "Area does not exist."})
        
        # Create the submission
        submission = super().create(validated_data)
        
        # Automatically create AuthorContribution for the corresponding author
        if corresponding_author_profile:
            AuthorContribution.objects.create(
                submission=submission,
                profile=corresponding_author_profile,
                order=1,
                contrib_role='FIRST',
                contribution_details={},
                has_agreed=True  # Corresponding author implicitly agrees
            )
        
        # Create AuthorContribution records for co-authors from metadata_json
        self._create_coauthor_contributions(submission)
        
        return submission
    
    def _create_coauthor_contributions(self, submission):
        """Create AuthorContribution records from metadata_json co_authors."""
        from apps.users.models import CustomUser, Profile
        
        metadata = submission.metadata_json or {}
        co_authors = metadata.get('co_authors', [])
        
        if not co_authors:
            return
        
        # Start order from 2 (order 1 is corresponding author)
        current_order = 2
        
        for co_author_data in co_authors:
            email = co_author_data.get('email')
            name = co_author_data.get('name', '')
            orcid = co_author_data.get('orcid', '')
            institution = co_author_data.get('institution', '')
            affiliation_ror_id = co_author_data.get('affiliation_ror_id', '')
            
            if not email:
                # Skip co-authors without email
                continue
            
            # Try to find existing user by email
            try:
                user = CustomUser.objects.get(email=email)
                profile = user.profile
            except CustomUser.DoesNotExist:
                # Create a new user for the co-author
                name_parts = name.split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                user = CustomUser.objects.create(
                    email=email,
                    username=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.set_unusable_password()
                user.save()
                
                # Create profile for the new user
                profile = Profile.objects.create(
                    user=user,
                    display_name=name,
                    orcid_id=orcid if orcid else None,
                    affiliation_name=institution,
                    affiliation_ror_id=affiliation_ror_id
                )
            
            # Create AuthorContribution if it doesn't already exist
            AuthorContribution.objects.get_or_create(
                submission=submission,
                profile=profile,
                defaults={
                    'order': current_order,
                    'contrib_role': 'CO_AUTHOR',
                    'contribution_details': {
                        'contribution_role': co_author_data.get('contribution_role', 'Co-Author'),
                        'institution': institution,
                        'orcid': orcid,
                        'affiliation_ror_id': affiliation_ror_id
                    },
                    'has_agreed': False
                }
            )
            
            current_order += 1
    
    def update(self, instance, validated_data):
        """Update submission with taxonomy."""
        # Extract taxonomy IDs
        section_id = validated_data.pop('section_id', None)
        category_id = validated_data.pop('category_id', None)
        research_type_id = validated_data.pop('research_type_id', None)
        area_id = validated_data.pop('area_id', None)
        
        # Update taxonomy relationships
        from apps.journals.models import Section, Category, ResearchType, Area
        
        if section_id is not None:
            if section_id:
                try:
                    instance.section = Section.objects.get(id=section_id)
                except Section.DoesNotExist:
                    raise serializers.ValidationError({"section_id": "Section does not exist."})
            else:
                instance.section = None
        
        if category_id is not None:
            if category_id:
                try:
                    instance.category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    raise serializers.ValidationError({"category_id": "Category does not exist."})
            else:
                instance.category = None
        
        if research_type_id is not None:
            if research_type_id:
                try:
                    instance.research_type = ResearchType.objects.get(id=research_type_id)
                except ResearchType.DoesNotExist:
                    raise serializers.ValidationError({"research_type_id": "ResearchType does not exist."})
            else:
                instance.research_type = None
        
        if area_id is not None:
            if area_id:
                try:
                    instance.area = Area.objects.get(id=area_id)
                except Area.DoesNotExist:
                    raise serializers.ValidationError({"area_id": "Area does not exist."})
            else:
                instance.area = None
        
        # Update the submission
        submission = super().update(instance, validated_data)
        
        # Update AuthorContribution records for co-authors if metadata_json changed
        if 'metadata_json' in validated_data:
            # Remove existing co-author contributions (keep corresponding author)
            AuthorContribution.objects.filter(
                submission=submission,
                contrib_role__in=['CO_AUTHOR', 'SENIOR', 'LAST']
            ).delete()
            
            # Recreate co-author contributions from updated metadata
            self._create_coauthor_contributions(submission)
        
        return submission


class SubmissionListSerializer(serializers.ModelSerializer):
    """Lightweight Submission serializer for list views."""
    
    journal_name = serializers.SerializerMethodField()
    corresponding_author_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_count = serializers.SerializerMethodField()
    review_assignment_count = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    # Taxonomy fields
    section = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    research_type = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    
    class Meta:
        model = Submission
        fields = (
            'id', 'title', 'journal_name', 'corresponding_author_name',
            'status', 'status_display', 'submission_number', 'document_count',
            'review_assignment_count', 'review_count',
            'section', 'category', 'research_type', 'area',
            'created_at', 'submitted_at', 'updated_at'
        )
    
    def get_journal_name(self, obj):
        """Get journal name safely."""
        return obj.journal.title if obj.journal else None
    
    def get_corresponding_author_name(self, obj):
        """Get corresponding author name safely."""
        if obj.corresponding_author:
            return obj.corresponding_author.display_name or f"{obj.corresponding_author.user.first_name} {obj.corresponding_author.user.last_name}".strip() or obj.corresponding_author.user.email
        return None
    
    def get_document_count(self, obj):
        """Get document count for submission."""
        return obj.documents.count()
    
    def get_review_assignment_count(self, obj):
        """Get count of review assignments for this submission."""
        return obj.review_assignments.filter(status__in=['PENDING', 'ACCEPTED']).count()
    
    def get_review_count(self, obj):
        """Get count of completed reviews for this submission."""
        return obj.reviews.filter(is_published=True).count()
    
    def get_section(self, obj):
        """Get section details with full hierarchy."""
        if obj.section:
            section_data = {
                'id': str(obj.section.id),
                'name': obj.section.name,
                'code': obj.section.code,
                'description': obj.section.description
            }
            
            # Add category if it exists
            if obj.category and obj.category.section_id == obj.section.id:
                section_data['category'] = {
                    'id': str(obj.category.id),
                    'name': obj.category.name,
                    'code': obj.category.code,
                    'description': obj.category.description
                }
                
                # Add research_type if it exists
                if obj.research_type and obj.research_type.category_id == obj.category.id:
                    section_data['category']['research_type'] = {
                        'id': str(obj.research_type.id),
                        'name': obj.research_type.name,
                        'code': obj.research_type.code,
                        'description': obj.research_type.description
                    }
                    
                    # Add area if it exists
                    if obj.area and obj.area.research_type_id == obj.research_type.id:
                        section_data['category']['research_type']['area'] = {
                            'id': str(obj.area.id),
                            'name': obj.area.name,
                            'code': obj.area.code,
                            'description': obj.area.description,
                            'keywords': obj.area.keywords
                        }
            
            return section_data
        return None
    
    def get_category(self, obj):
        """Get category details - not needed when using tree structure."""
        return None
    
    def get_research_type(self, obj):
        """Get research type details - not needed when using tree structure."""
        return None
    
    def get_area(self, obj):
        """Get area details - not needed when using tree structure."""
        return None


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
        document_type = validated_data.get('document_type')
        
        # Create document first
        document = Document.objects.create(
            submission=submission,
            created_by=user.profile,
            **validated_data
        )
        
        # Anonymize file if required by journal settings
        from apps.submissions.utils import DocumentAnonymizer
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from io import BytesIO
        
        anonymized_content, was_anonymized = DocumentAnonymizer.anonymize_file(file, submission)
        
        # If anonymized, create a new file object with anonymized content
        if was_anonymized:
            anonymized_file = InMemoryUploadedFile(
                BytesIO(anonymized_content),
                field_name='file',
                name=file.name,
                content_type=file.content_type,
                size=len(anonymized_content),
                charset=file.charset
            )
            file_to_store = anonymized_file
        else:
            file_to_store = file
        
        # Store file securely
        try:
            from apps.common.storage import SecureFileStorage
            storage_result = SecureFileStorage.store_file(
                file_to_store,
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
                change_summary="Initial upload" + (" (anonymized)" if was_anonymized else ""),
                is_current=True,
                metadata={'anonymized': was_anonymized} if was_anonymized else {}
            )
            
            # Set current version and also populate SuperDoc fields
            document.current_version = version
            document.original_file = version.file
            document.file_name = version.file_name
            document.file_size = version.file_size
            document.save()
            
            # Handle revision workflow
            if document_type == 'REVISED_MANUSCRIPT' and submission.status == 'REVISION_REQUIRED':
                # Update submission status to REVISED
                submission.status = 'REVISED'
                submission.save()
                
                # Clear old reviews (mark as superseded) so reviewers can review again
                # Keep the reviewer assignments (status stays ACCEPTED)
                from apps.reviews.models import Review
                Review.objects.filter(
                    submission=submission
                ).update(
                    is_published=False  # Mark old reviews as not current
                )
            
        except Exception as e:
            # Clean up document if file storage fails
            document.delete()
            raise serializers.ValidationError(f"File storage failed: {str(e)}")
        
        return document