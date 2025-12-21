"""
Admin configuration for achievements app.
"""
from django.contrib import admin
from .models import Badge, UserBadge, Award, Leaderboard, Certificate


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'badge_type', 'level', 'points', 'is_active', 'created_at']
    list_filter = ['badge_type', 'level', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-points', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'badge_type', 'level')
        }),
        ('Requirements', {
            'fields': ('criteria', 'points', 'icon', 'color')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['profile', 'badge', 'year', 'journal', 'earned_at', 'is_featured']
    list_filter = ['year', 'is_featured', 'earned_at']
    search_fields = ['profile__user__email', 'badge__name']
    readonly_fields = ['earned_at']
    raw_id_fields = ['profile', 'journal']
    date_hierarchy = 'earned_at'
    
    fieldsets = (
        ('Badge Information', {
            'fields': ('profile', 'badge', 'year')
        }),
        ('Context', {
            'fields': ('journal', 'achievement_data', 'notes')
        }),
        ('Settings', {
            'fields': ('is_featured', 'earned_at')
        }),
    )


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ['title', 'award_type', 'recipient', 'year', 'journal', 'announced_at']
    list_filter = ['award_type', 'year', 'discipline', 'country']
    search_fields = ['title', 'recipient__user__email', 'journal__title']
    readonly_fields = ['announced_at']
    raw_id_fields = ['recipient', 'journal']
    date_hierarchy = 'announced_at'
    
    fieldsets = (
        ('Award Details', {
            'fields': ('title', 'description', 'award_type', 'year')
        }),
        ('Recipient', {
            'fields': ('recipient', 'journal', 'discipline', 'country')
        }),
        ('Recognition', {
            'fields': ('citation', 'metrics', 'amount', 'certificate_generated')
        }),
        ('Metadata', {
            'fields': ('announced_at',)
        }),
    )


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['profile', 'category', 'rank', 'score', 'period', 'journal', 'calculated_at']
    list_filter = ['category', 'period', 'field', 'country']
    search_fields = ['profile__user__email', 'journal__title']
    readonly_fields = ['calculated_at']
    raw_id_fields = ['profile', 'journal']
    ordering = ['category', 'period', 'rank']
    
    fieldsets = (
        ('Ranking Information', {
            'fields': ('profile', 'category', 'rank', 'score')
        }),
        ('Context', {
            'fields': ('period', 'journal', 'field', 'country')
        }),
        ('Metrics', {
            'fields': ('metrics', 'calculated_at')
        }),
    )


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'recipient', 'certificate_type', 'title', 'issued_date', 'is_public']
    list_filter = ['certificate_type', 'issued_date', 'is_public']
    search_fields = ['certificate_number', 'verification_code', 'recipient__user__email', 'title']
    readonly_fields = ['certificate_number', 'verification_code', 'issued_date']
    raw_id_fields = ['recipient', 'journal', 'award', 'badge']
    date_hierarchy = 'issued_date'
    
    fieldsets = (
        ('Certificate Information', {
            'fields': ('certificate_number', 'verification_code', 'certificate_type', 'title', 'description')
        }),
        ('Recipient & Context', {
            'fields': ('recipient', 'journal', 'award', 'badge')
        }),
        ('Document', {
            'fields': ('pdf_file', 'issued_date', 'is_public')
        }),
        ('Additional Data', {
            'fields': ('custom_data',),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make certificate number and verification code readonly after creation."""
        if obj:
            return self.readonly_fields + ['certificate_type', 'recipient']
        return self.readonly_fields
