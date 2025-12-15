from django.contrib import admin
from .models import Submission, AuthorContribution, Document, DocumentVersion, Comment
from .copyediting_models import (
    CopyeditingAssignment, CopyeditingFile, CopyeditingDiscussion,
    CopyeditingMessage, CopyeditingMessageAttachment
)
from .production_models import (
    ProductionAssignment, ProductionFile, ProductionDiscussion,
    ProductionMessage, ProductionMessageAttachment, PublicationSchedule
)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'journal', 'status', 'doi', 'corresponding_author', 'submitted_at', 'created_at')
    list_filter = ('status', 'journal', 'created_at')
    search_fields = ('title', 'submission_number', 'abstract', 'doi')
    date_hierarchy = 'created_at'


@admin.register(AuthorContribution)
class AuthorContributionAdmin(admin.ModelAdmin):
    list_display = ('submission', 'profile', 'order', 'contrib_role')
    list_filter = ('contrib_role',)
    search_fields = ('submission__title', 'profile__user__email')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'submission', 'created_by', 'created_at')
    list_filter = ('document_type', 'created_at')
    search_fields = ('title', 'submission__title')


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'created_by', 'is_current', 'created_at')
    list_filter = ('is_current', 'created_at')
    search_fields = ('document__title', 'change_summary')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'document_version', 'comment_type', 'resolved', 'created_at')
    list_filter = ('comment_type', 'resolved', 'created_at')
    search_fields = ('text', 'author__user__email')


# Copyediting Models
@admin.register(CopyeditingAssignment)
class CopyeditingAssignmentAdmin(admin.ModelAdmin):
    list_display = ('submission', 'copyeditor', 'status', 'assigned_at', 'due_date', 'completed_at')
    list_filter = ('status', 'assigned_at', 'due_date')
    search_fields = ('submission__title', 'copyeditor__user__email')
    date_hierarchy = 'assigned_at'


@admin.register(CopyeditingFile)
class CopyeditingFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'file_type', 'assignment', 'uploaded_by', 'is_approved', 'created_at')
    list_filter = ('file_type', 'is_approved', 'created_at')
    search_fields = ('original_filename', 'assignment__submission__title')


@admin.register(CopyeditingDiscussion)
class CopyeditingDiscussionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'assignment', 'status', 'started_by', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'assignment__submission__title')


@admin.register(CopyeditingMessage)
class CopyeditingMessageAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'author', 'has_attachments', 'created_at')
    list_filter = ('has_attachments', 'created_at')
    search_fields = ('message', 'author__user__email')


# Production Models
@admin.register(ProductionAssignment)
class ProductionAssignmentAdmin(admin.ModelAdmin):
    list_display = ('submission', 'production_assistant', 'status', 'assigned_at', 'due_date', 'completed_at')
    list_filter = ('status', 'assigned_at', 'due_date')
    search_fields = ('submission__title', 'production_assistant__user__email')
    date_hierarchy = 'assigned_at'


@admin.register(ProductionFile)
class ProductionFileAdmin(admin.ModelAdmin):
    list_display = ('label', 'file_type', 'galley_format', 'assignment', 'is_published', 'is_approved', 'created_at')
    list_filter = ('file_type', 'galley_format', 'is_published', 'is_approved', 'created_at')
    search_fields = ('label', 'original_filename', 'assignment__submission__title')


@admin.register(ProductionDiscussion)
class ProductionDiscussionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'assignment', 'status', 'started_by', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'assignment__submission__title')


@admin.register(ProductionMessage)
class ProductionMessageAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'author', 'has_attachments', 'created_at')
    list_filter = ('has_attachments', 'created_at')
    search_fields = ('message', 'author__user__email')


@admin.register(PublicationSchedule)
class PublicationScheduleAdmin(admin.ModelAdmin):
    list_display = ('submission', 'status', 'scheduled_date', 'published_date', 'volume', 'issue', 'year')
    list_filter = ('status', 'year', 'scheduled_date')
    search_fields = ('submission__title', 'doi', 'volume', 'issue')
