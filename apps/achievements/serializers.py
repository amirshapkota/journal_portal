"""
Serializers for achievements app.
"""
from rest_framework import serializers
from .models import Badge, UserBadge, Award, Leaderboard, Certificate
from apps.users.serializers import ProfileSerializer
from apps.journals.serializers import JournalListSerializer


class BadgeSerializer(serializers.ModelSerializer):
    """Serializer for Badge model."""
    
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    badge_type_display = serializers.CharField(source='get_badge_type_display', read_only=True)
    
    class Meta:
        model = Badge
        fields = (
            'id', 'name', 'description', 'badge_type', 'badge_type_display',
            'level', 'level_display', 'criteria', 'icon_url', 'icon_color',
            'points', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserBadgeSerializer(serializers.ModelSerializer):
    """Serializer for UserBadge model."""
    
    badge = BadgeSerializer(read_only=True)
    profile = ProfileSerializer(read_only=True)
    journal = JournalListSerializer(read_only=True)
    
    class Meta:
        model = UserBadge
        fields = (
            'id', 'profile', 'badge', 'earned_at', 'year',
            'journal', 'achievement_data', 'is_featured'
        )
        read_only_fields = ('id', 'earned_at')


class AwardSerializer(serializers.ModelSerializer):
    """Serializer for Award model."""
    
    award_type_display = serializers.CharField(source='get_award_type_display', read_only=True)
    recipient = ProfileSerializer(read_only=True)
    journal = JournalListSerializer(read_only=True)
    
    class Meta:
        model = Award
        fields = (
            'id', 'title', 'description', 'award_type', 'award_type_display',
            'year', 'journal', 'discipline', 'country', 'recipient',
            'citation', 'metrics', 'certificate_generated', 'certificate_url',
            'announced_at'
        )
        read_only_fields = ('id', 'announced_at')


class LeaderboardSerializer(serializers.ModelSerializer):
    """Serializer for Leaderboard model."""
    
    profile = ProfileSerializer(read_only=True)
    journal = JournalListSerializer(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    
    class Meta:
        model = Leaderboard
        fields = (
            'id', 'profile', 'category', 'category_display', 'period',
            'period_display', 'journal', 'field', 'country', 'rank',
            'score', 'metrics', 'period_start', 'period_end', 'calculated_at'
        )
        read_only_fields = ('id', 'calculated_at')


class CertificateSerializer(serializers.ModelSerializer):
    """Serializer for Certificate model."""
    
    recipient = ProfileSerializer(read_only=True)
    journal = JournalListSerializer(read_only=True)
    award = AwardSerializer(read_only=True)
    badge = UserBadgeSerializer(read_only=True)
    certificate_type_display = serializers.CharField(source='get_certificate_type_display', read_only=True)
    
    class Meta:
        model = Certificate
        fields = (
            'id', 'recipient', 'certificate_type', 'certificate_type_display',
            'title', 'description', 'award', 'badge', 'journal',
            'certificate_number', 'issued_date', 'file_url', 'pdf_generated',
            'template_name', 'custom_data', 'verification_code',
            'is_public', 'created_at'
        )
        read_only_fields = ('id', 'certificate_number', 'verification_code', 'created_at')
