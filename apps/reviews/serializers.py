"""
Serializers for review management.
Handles serialization of review assignments, reviews, and recommendations.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.reviews.models import (
    ReviewAssignment, Review, ReviewerRecommendation,
    ReviewFormTemplate, ReviewAttachment, ReviewVersion
)
from apps.users.models import Profile
from apps.submissions.models import Submission

CustomUser = get_user_model()


class ReviewerProfileSerializer(serializers.ModelSerializer):
    """Simplified profile serializer for reviewer information."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    verification_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'id', 'user_email', 'full_name', 'display_name',
            'affiliation_name', 'bio', 'expertise_areas',
            'verification_status'
        ]
        read_only_fields = fields


class ReviewAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for review assignments."""
    reviewer_info = ReviewerProfileSerializer(source='reviewer', read_only=True)
    assigned_by_info = ReviewerProfileSerializer(source='assigned_by', read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    submission_id = serializers.UUIDField(source='submission.id', read_only=True)
    submission_number = serializers.CharField(source='submission.submission_number', read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    def get_submission_details(self, obj):
        """Get full submission details for review page."""
        from apps.submissions.serializers import SubmissionSerializer
        return SubmissionSerializer(obj.submission, context=self.context).data
    
    submission_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewAssignment
        fields = [
            'id', 'submission', 'submission_id', 'submission_title', 'submission_number',
            'reviewer', 'reviewer_info',
            'assigned_by', 'assigned_by_info',
            'status', 'status_display', 'invited_at', 'due_date',
            'accepted_at', 'declined_at', 'completed_at',
            'invitation_message', 'decline_reason',
            'review_round', 'days_remaining', 'is_overdue',
            'submission_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'invited_at', 'accepted_at', 'declined_at',
            'completed_at', 'created_at', 'updated_at'
        ]


class ReviewAssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating review assignments."""
    
    class Meta:
        model = ReviewAssignment
        fields = [
            'submission', 'reviewer', 'due_date',
            'invitation_message', 'review_round'
        ]
    
    def validate(self, data):
        """Validate review assignment creation."""
        submission = data.get('submission')
        reviewer = data.get('reviewer')
        review_round = data.get('review_round', 1)
        
        # Check if assignment already exists
        if ReviewAssignment.objects.filter(
            submission=submission,
            reviewer=reviewer,
            review_round=review_round
        ).exists():
            raise serializers.ValidationError(
                "This reviewer is already assigned to this submission for this review round."
            )
        
        # Check if reviewer is verified
        if not reviewer.is_verified():
            raise serializers.ValidationError(
                "Only verified reviewers can be assigned to reviews."
            )
        
        # Check for conflict of interest (same affiliation as author)
        if submission.corresponding_author.affiliation_name and reviewer.affiliation_name:
            if submission.corresponding_author.affiliation_name.lower() == reviewer.affiliation_name.lower():
                raise serializers.ValidationError(
                    "Potential conflict of interest: Reviewer and author share the same affiliation."
                )
        
        return data
    
    def create(self, validated_data):
        """Create review assignment with assigned_by field."""
        validated_data['assigned_by'] = self.context['request'].user.profile
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviews."""
    reviewer_info = ReviewerProfileSerializer(source='reviewer', read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    assignment_id = serializers.UUIDField(source='assignment.id', read_only=True)
    overall_score = serializers.FloatField(read_only=True)
    review_time_days = serializers.IntegerField(read_only=True)
    recommendation_display = serializers.CharField(source='get_recommendation_display', read_only=True)
    confidence_display = serializers.CharField(source='get_confidence_level_display', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'assignment', 'assignment_id',
            'submission', 'submission_title',
            'reviewer', 'reviewer_info',
            'assigned_at', 'due_date', 'submitted_at',
            'recommendation', 'recommendation_display',
            'confidence_level', 'confidence_display',
            'scores', 'overall_score',
            'review_text', 'confidential_comments',
            'attached_files', 'auto_summary',
            'quality_score', 'is_anonymous', 'is_published',
            'review_round', 'revision_round',
            'review_time_days', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'assigned_at', 'due_date', 'submitted_at',
            'auto_summary', 'quality_score', 'review_round',
            'created_at', 'updated_at'
        ]


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/submitting reviews."""
    
    class Meta:
        model = Review
        fields = [
            'id', 'assignment', 'recommendation', 'confidence_level',
            'scores', 'review_text', 'confidential_comments',
            'attached_files', 'is_anonymous'
        ]
        read_only_fields = ['id']
    
    def validate_assignment(self, value):
        """Validate that the assignment belongs to the current user and is accepted."""
        user = self.context['request'].user
        
        if value.reviewer.user != user:
            raise serializers.ValidationError(
                "You can only submit reviews for your own assignments."
            )
        
        if value.status not in ['PENDING', 'ACCEPTED']:
            raise serializers.ValidationError(
                "This assignment is not in a reviewable state."
            )
        
        # Note: Removed OneToOne check to allow multiple reviews per assignment
        # This supports revision rounds where reviewers submit multiple reviews
        
        return value
    
    def validate_scores(self, value):
        """Validate review scores."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Scores must be a dictionary.")
        
        # Validate score values are numeric and within range
        for key, score in value.items():
            if not isinstance(score, (int, float)):
                raise serializers.ValidationError(
                    f"Score for '{key}' must be a number."
                )
            if not (0 <= score <= 10):
                raise serializers.ValidationError(
                    f"Score for '{key}' must be between 0 and 10."
                )
        
        return value
    
    def create(self, validated_data):
        """Create review and initial version."""
        from apps.reviews.models import ReviewVersion
        
        # Create the review
        review = super().create(validated_data)
        
        # Create initial version for audit trail
        ReviewVersion.objects.create(
            review=review,
            version_number=1,
            content_snapshot={
                'recommendation': review.recommendation,
                'confidence_level': review.confidence_level,
                'scores': review.scores,
                'review_text': review.review_text,
                'confidential_comments': review.confidential_comments,
            },
            changes_made="Initial review submission",
            changed_by=review.reviewer
        )
        
        return review


class ReviewerRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for reviewer recommendations."""
    reviewer_info = ReviewerProfileSerializer(source='recommended_reviewer', read_only=True)
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    
    class Meta:
        model = ReviewerRecommendation
        fields = [
            'id', 'submission', 'submission_title',
            'recommended_reviewer', 'reviewer_info',
            'confidence_score', 'reasoning',
            'model_version', 'generated_by',
            'is_used', 'used_at', 'created_at'
        ]
        read_only_fields = fields


class ReviewerExpertiseSerializer(serializers.Serializer):
    """Serializer for reviewer expertise search."""
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=100),
        help_text="List of keywords to match against reviewer expertise"
    )
    min_verification_score = serializers.IntegerField(
        default=0,
        min_value=0,
        max_value=100,
        help_text="Minimum verification auto-score"
    )
    exclude_reviewer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="List of reviewer IDs to exclude"
    )
    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=100,
        help_text="Maximum number of results"
    )


class ReviewInvitationAcceptSerializer(serializers.Serializer):
    """Serializer for accepting review invitations."""
    accept = serializers.BooleanField(
        help_text="True to accept, False to decline"
    )
    decline_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Reason for declining (required if accept=False)"
    )
    
    def validate(self, data):
        """Validate acceptance/decline."""
        if not data.get('accept') and not data.get('decline_reason'):
            raise serializers.ValidationError(
                "decline_reason is required when declining an invitation."
            )
        return data


class ReviewStatisticsSerializer(serializers.Serializer):
    """Serializer for review statistics."""
    total_assignments = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    accepted_assignments = serializers.IntegerField()
    completed_reviews = serializers.IntegerField()
    declined_assignments = serializers.IntegerField()
    overdue_reviews = serializers.IntegerField()
    average_review_time_days = serializers.FloatField()
    recommendations_breakdown = serializers.DictField()
    reviewer_performance = serializers.DictField()
# Append to apps/reviews/serializers.py

"""
Phase 4.2: Review Submission Serializers
"""


class ReviewFormTemplateSerializer(serializers.ModelSerializer):
    """Serializer for review form templates."""
    journal_name = serializers.CharField(source='journal.title', read_only=True, allow_null=True)
    
    class Meta:
        model = ReviewFormTemplate
        fields = [
            'id', 'name', 'description', 'journal', 'journal_name',
            'form_schema', 'scoring_criteria',
            'is_active', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'journal_name', 'created_at', 'updated_at']


class ReviewAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for review file attachments."""
    uploaded_by_name = serializers.CharField(source='uploaded_by.user.get_full_name', read_only=True)
    file_extension = serializers.CharField(source='get_file_extension', read_only=True)
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewAttachment
        fields = [
            'id', 'review', 'file', 'original_filename',
            'file_size', 'mime_type', 'description',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'file_extension', 'download_url'
        ]
        read_only_fields = [
            'id', 'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'file_size', 'mime_type', 'file_extension', 'download_url'
        ]
    
    def get_download_url(self, obj):
        """Generate download URL for the attachment."""
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(
                f'/api/v1/reviews/attachments/{obj.id}/download/'
            )
        return None
    
    def validate_file(self, value):
        """Validate file type and size."""
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size cannot exceed 10MB. Current size: {value.size / 1024 / 1024:.2f}MB"
            )
        
        # Check file extension
        import os
        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type {ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value


class ReviewVersionSerializer(serializers.ModelSerializer):
    """Serializer for review version history."""
    changed_by_name = serializers.CharField(source='changed_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = ReviewVersion
        fields = [
            'id', 'review', 'version_number',
            'content_snapshot', 'changes_made',
            'changed_by', 'changed_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'changed_by_name', 'created_at']


class AnonymousSubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for submission with anonymity support.
    Masks author information based on review type.
    """
    journal_name = serializers.CharField(source='journal.title', read_only=True)
    corresponding_author_name = serializers.SerializerMethodField()
    coauthor_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Submission
        fields = [
            'id', 'journal', 'journal_name', 'title', 'abstract',
            'corresponding_author_name', 'coauthor_names',
            'status', 'submission_number', 'review_type',
            'submitted_at', 'created_at'
        ]
        read_only_fields = fields
    
    def get_corresponding_author_name(self, obj):
        """Get author name with anonymity rules."""
        request = self.context.get('request')
        user = request.user if request else None
        
        # Check if user is reviewer for this submission
        if user and hasattr(user, 'profile'):
            is_reviewer = obj.review_assignments.filter(
                reviewer=user.profile
            ).exists()
            
            # Apply anonymity based on review type
            if is_reviewer:
                if obj.review_type == 'DOUBLE_BLIND':
                    return "[Author name hidden for blind review]"
                elif obj.review_type == 'SINGLE_BLIND':
                    # Reviewer can see author
                    return obj.corresponding_author.user.get_full_name()
            
        # Default: show author (for editors, admins, open review)
        return obj.corresponding_author.user.get_full_name()
    
    def get_coauthor_names(self, obj):
        """Get coauthor names with anonymity rules."""
        request = self.context.get('request')
        user = request.user if request else None
        
        # Check if user is reviewer for this submission
        if user and hasattr(user, 'profile'):
            is_reviewer = obj.review_assignments.filter(
                reviewer=user.profile
            ).exists()
            
            # Apply anonymity based on review type
            if is_reviewer and obj.review_type == 'DOUBLE_BLIND':
                count = obj.coauthors.count()
                if count > 0:
                    return [f"[{count} coauthor(s) - names hidden for blind review]"]
                return []
        
        # Default: show coauthors
        return [co.user.get_full_name() for co in obj.coauthors.all()]


class EnhancedReviewSerializer(serializers.ModelSerializer):
    """
    Enhanced review serializer with attachments and full details.
    """
    reviewer_info = ReviewerProfileSerializer(source='reviewer', read_only=True)
    submission_info = AnonymousSubmissionSerializer(source='submission', read_only=True)
    assigned_by_info = ReviewerProfileSerializer(source='assignment.assigned_by', read_only=True)
    attachments = ReviewAttachmentSerializer(many=True, read_only=True)
    form_template_info = ReviewFormTemplateSerializer(source='form_template', read_only=True)
    overall_score = serializers.FloatField(source='get_overall_score', read_only=True)
    review_time_days = serializers.IntegerField(source='get_review_time_days', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'assignment', 'submission', 'submission_info',
            'reviewer', 'reviewer_info', 'assigned_by_info',
            'review_type', 'form_template', 'form_template_info',
            'assigned_at', 'due_date', 'submitted_at',
            'recommendation', 'confidence_level',
            'scores', 'overall_score', 'review_text',
            'confidential_comments', 'attachments',
            'quality_score', 'is_anonymous', 'is_published',
            'review_time_days', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'submission', 'reviewer', 'assigned_at', 'due_date',
            'submitted_at', 'overall_score', 'review_time_days',
            'created_at', 'updated_at'
        ]


class ReviewSubmitSerializer(serializers.ModelSerializer):
    """
    Serializer for submitting a new review.
    """
    class Meta:
        model = Review
        fields = [
            'assignment', 'review_type', 'form_template',
            'recommendation', 'confidence_level',
            'scores', 'review_text', 'confidential_comments'
        ]
    
    def validate_assignment(self, value):
        """Validate that assignment exists and is accepted."""
        if value.status != 'ACCEPTED':
            raise serializers.ValidationError(
                "Cannot submit review for assignment that is not accepted."
            )
        
        # Note: Removed OneToOne check to allow multiple reviews per assignment
        # This supports revision rounds where reviewers submit multiple reviews
        
        return value
    
    def validate_scores(self, value):
        """Validate that all scores are within valid range (0-10)."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Scores must be a dictionary.")
        
        for key, score in value.items():
            if not isinstance(score, (int, float)):
                raise serializers.ValidationError(
                    f"Score '{key}' must be a number."
                )
            if score < 0 or score > 10:
                raise serializers.ValidationError(
                    f"Score '{key}' must be between 0 and 10. Got: {score}"
                )
        
        return value
    
    def validate_review_text(self, value):
        """Validate minimum review text length."""
        min_length = 100  # Minimum 100 characters
        if len(value.strip()) < min_length:
            raise serializers.ValidationError(
                f"Review text must be at least {min_length} characters. "
                f"Current length: {len(value.strip())}"
            )
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        request = self.context.get('request')
        user = request.user if request else None
        
        # Verify user is the assigned reviewer
        if user and hasattr(user, 'profile'):
            assignment = data.get('assignment')
            if assignment and assignment.reviewer != user.profile:
                raise serializers.ValidationError(
                    "You can only submit reviews for your own assignments."
                )
        
        # Check required scores based on template
        form_template = data.get('form_template')
        if form_template and form_template.scoring_criteria:
            required_criteria = form_template.scoring_criteria.get('required', [])
            scores = data.get('scores', {})
            missing = [c for c in required_criteria if c not in scores]
            if missing:
                raise serializers.ValidationError(
                    f"Missing required score criteria: {', '.join(missing)}"
                )
        
        return data
    
    def create(self, validated_data):
        """Create review and update assignment."""
        assignment = validated_data['assignment']
        
        # Set automatic fields
        validated_data['submission'] = assignment.submission
        validated_data['reviewer'] = assignment.reviewer
        validated_data['assigned_at'] = assignment.invited_at
        validated_data['due_date'] = assignment.due_date
        
        # Get review type from submission if not provided
        if 'review_type' not in validated_data:
            validated_data['review_type'] = assignment.submission.review_type
        
        # Create review
        review = Review.objects.create(**validated_data)
        
        # Create initial version for audit trail
        ReviewVersion.objects.create(
            review=review,
            version_number=1,
            content_snapshot={
                'recommendation': review.recommendation,
                'confidence_level': review.confidence_level,
                'scores': review.scores,
                'review_text': review.review_text,
                'confidential_comments': review.confidential_comments,
            },
            changes_made="Initial review submission",
            changed_by=review.reviewer
        )
        
        return review


# ============================================================================
# PHASE 4.3: EDITORIAL DECISION SERIALIZERS
# ============================================================================
"""
Serializers for Phase 4.3: Editorial Decision Making
Handles decision letters, editorial decisions, and revision rounds.
"""
from rest_framework import serializers



class DecisionLetterTemplateSerializer(serializers.ModelSerializer):
    """Serializer for decision letter templates."""
    journal_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        from apps.reviews.models import DecisionLetterTemplate
        model = DecisionLetterTemplate
        fields = [
            'id', 'name', 'decision_type', 'journal', 'journal_name',
            'subject', 'body', 'description', 'variables_info',
            'is_active', 'is_default', 'created_at', 'updated_at',
            'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'journal_name', 'created_by_name']
    
    def get_journal_name(self, obj):
        """Get journal name."""
        return obj.journal.title if obj.journal else "System Default"
    
    def get_created_by_name(self, obj):
        """Get creator name."""
        if obj.created_by:
            return f"{obj.created_by.user.first_name} {obj.created_by.user.last_name}"
        return None


class EditorialDecisionListSerializer(serializers.ModelSerializer):
    """Serializer for listing editorial decisions."""
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    decided_by_name = serializers.SerializerMethodField()
    decision_type_display = serializers.CharField(source='get_decision_type_display', read_only=True)
    
    class Meta:
        from apps.reviews.models import EditorialDecision
        model = EditorialDecision
        fields = [
            'id', 'submission', 'submission_title', 'decision_type',
            'decision_type_display', 'decided_by', 'decided_by_name',
            'decision_date', 'revision_deadline', 'notification_sent',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_decided_by_name(self, obj):
        """Get editor name."""
        return f"{obj.decided_by.user.first_name} {obj.decided_by.user.last_name}"


class EditorialDecisionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for editorial decisions."""
    submission_info = AnonymousSubmissionSerializer(source='submission', read_only=True)
    decided_by_info = ReviewerProfileSerializer(source='decided_by', read_only=True)
    decision_type_display = serializers.CharField(source='get_decision_type_display', read_only=True)
    letter_template_info = DecisionLetterTemplateSerializer(source='letter_template', read_only=True)
    
    class Meta:
        from apps.reviews.models import EditorialDecision
        model = EditorialDecision
        fields = [
            'id', 'submission', 'submission_info', 'decision_type',
            'decision_type_display', 'decided_by', 'decided_by_info',
            'decision_letter', 'confidential_notes', 'reviews_summary',
            'decision_date', 'revision_deadline', 'letter_template',
            'letter_template_info', 'notification_sent', 'notification_sent_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'submission_info', 'decided_by_info', 'decision_type_display',
            'letter_template_info', 'decision_date', 'notification_sent',
            'notification_sent_at', 'created_at', 'updated_at'
        ]


class EditorialDecisionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating editorial decisions."""
    
    class Meta:
        from apps.reviews.models import EditorialDecision
        model = EditorialDecision
        fields = [
            'id', 'submission', 'decision_type', 'decided_by',
            'decision_letter', 'confidential_notes', 'reviews_summary',
            'revision_deadline', 'letter_template'
        ]
        read_only_fields = ['id']
    
    def validate_submission(self, value):
        """Validate that submission has completed reviews."""
        from apps.reviews.models import Review
        
        # Check if submission has at least one completed review
        review_count = Review.objects.filter(
            submission=value,
            is_published=True
        ).count()
        
        if review_count == 0:
            raise serializers.ValidationError(
                "Cannot make decision: submission has no completed reviews."
            )
        
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        # Require revision deadline for revision decisions
        if data['decision_type'] in ['MINOR_REVISION', 'MAJOR_REVISION']:
            if not data.get('revision_deadline'):
                raise serializers.ValidationError({
                    'revision_deadline': 'Revision deadline is required for revision decisions.'
                })
        
        return data
    
    def create(self, validated_data):
        """Create editorial decision and aggregate review data."""
        from apps.reviews.models import Review, EditorialDecision
        
        submission = validated_data['submission']
        
        # Aggregate review recommendations if not provided
        if not validated_data.get('reviews_summary'):
            reviews = Review.objects.filter(
                submission=submission,
                is_published=True
            )
            
            recommendations_count = {}
            total_score = 0
            review_count = reviews.count()
            
            for review in reviews:
                rec = review.recommendation
                recommendations_count[rec] = recommendations_count.get(rec, 0) + 1
                if review.scores:
                    total_score += sum([v for v in review.scores.values() if isinstance(v, (int, float))])
            
            validated_data['reviews_summary'] = {
                'total_reviews': review_count,
                'recommendations': recommendations_count,
                'average_score': total_score / review_count if review_count > 0 else 0,
            }
        
        # Create decision
        decision = EditorialDecision.objects.create(**validated_data)
        
        return decision


class RevisionRoundListSerializer(serializers.ModelSerializer):
    """Serializer for listing revision rounds."""
    submission_title = serializers.CharField(source='submission.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        from apps.reviews.models import RevisionRound
        model = RevisionRound
        fields = [
            'id', 'submission', 'submission_title', 'round_number',
            'status', 'status_display', 'requested_at', 'deadline',
            'submitted_at', 'is_overdue', 'days_remaining', 'created_at'
        ]
        read_only_fields = fields
    
    def get_is_overdue(self, obj):
        """Check if revision is overdue."""
        return obj.is_overdue()
    
    def get_days_remaining(self, obj):
        """Get days remaining."""
        return obj.days_remaining()


class RevisionRoundDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for revision rounds."""
    submission_info = AnonymousSubmissionSerializer(source='submission', read_only=True)
    editorial_decision_info = EditorialDecisionListSerializer(source='editorial_decision', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    reassigned_reviewers_info = ReviewerProfileSerializer(source='reassigned_reviewers', many=True, read_only=True)
    
    class Meta:
        from apps.reviews.models import RevisionRound
        model = RevisionRound
        fields = [
            'id', 'submission', 'submission_info', 'editorial_decision',
            'editorial_decision_info', 'round_number', 'status', 'status_display',
            'revision_requirements', 'reviewer_comments_included',
            'requested_at', 'deadline', 'submitted_at', 'revised_manuscript',
            'response_letter', 'author_notes', 'reassigned_reviewers',
            'reassigned_reviewers_info', 'is_overdue', 'days_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'submission_info', 'editorial_decision_info', 'status_display',
            'is_overdue', 'days_remaining', 'requested_at', 'created_at', 'updated_at'
        ]
    
    def get_is_overdue(self, obj):
        """Check if revision is overdue."""
        return obj.is_overdue()
    
    def get_days_remaining(self, obj):
        """Get days remaining."""
        return obj.days_remaining()


class RevisionRoundCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating revision rounds."""
    
    class Meta:
        from apps.reviews.models import RevisionRound
        model = RevisionRound
        fields = [
            'id', 'submission', 'editorial_decision', 'round_number',
            'revision_requirements', 'reviewer_comments_included',
            'deadline', 'reassigned_reviewers'
        ]
        read_only_fields = ['id']
    
    def validate_submission(self, value):
        """Validate submission has a revision decision."""
        from apps.reviews.models import EditorialDecision
        
        latest_decision = EditorialDecision.objects.filter(
            submission=value
        ).order_by('-decision_date').first()
        
        if not latest_decision:
            raise serializers.ValidationError(
                "Submission has no editorial decision."
            )
        
        if latest_decision.decision_type not in ['MINOR_REVISION', 'MAJOR_REVISION']:
            raise serializers.ValidationError(
                "Latest decision does not require revision."
            )
        
        return value
    
    def create(self, validated_data):
        """Create revision round."""
        from apps.reviews.models import RevisionRound
        
        # Auto-set round number if not provided
        if 'round_number' not in validated_data:
            last_round = RevisionRound.objects.filter(
                submission=validated_data['submission']
            ).order_by('-round_number').first()
            validated_data['round_number'] = (last_round.round_number + 1) if last_round else 1
        
        # Create revision round
        reassigned_reviewers = validated_data.pop('reassigned_reviewers', [])
        revision_round = RevisionRound.objects.create(**validated_data)
        
        # Add reassigned reviewers
        if reassigned_reviewers:
            revision_round.reassigned_reviewers.set(reassigned_reviewers)
        
        return revision_round


class RevisionSubmissionSerializer(serializers.Serializer):
    """Serializer for submitting revised manuscript."""
    revised_manuscript_id = serializers.UUIDField(
        help_text="UUID of the revised manuscript document"
    )
    response_letter_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="UUID of the response letter document"
    )
    author_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Author's notes about the revision"
    )
    
    def validate_revised_manuscript_id(self, value):
        """Validate revised manuscript exists."""
        from apps.submissions.models import Document
        
        try:
            document = Document.objects.get(id=value)
            if document.document_type not in ['REVISED_MANUSCRIPT', 'MANUSCRIPT']:
                raise serializers.ValidationError(
                    "Document must be of type REVISED_MANUSCRIPT or MANUSCRIPT."
                )
        except Document.DoesNotExist:
            raise serializers.ValidationError("Document not found.")
        
        return value
    
    def validate_response_letter_id(self, value):
        """Validate response letter exists."""
        if not value:
            return value
        
        from apps.submissions.models import Document
        
        try:
            document = Document.objects.get(id=value)
            if document.document_type != 'REVIEWER_RESPONSE':
                raise serializers.ValidationError(
                    "Document must be of type REVIEWER_RESPONSE."
                )
        except Document.DoesNotExist:
            raise serializers.ValidationError("Document not found.")
        
        return value

