from django.contrib import admin
from .models import Journal, JournalStaff, Section, Category, ResearchType, Area


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ('title', 'short_name', 'publisher', 'is_active', 'is_accepting_submissions')
    list_filter = ('is_active', 'is_accepting_submissions', 'created_at')
    search_fields = ('title', 'short_name', 'publisher')


@admin.register(JournalStaff)
class JournalStaffAdmin(admin.ModelAdmin):
    list_display = ('profile', 'journal', 'role', 'is_active', 'start_date')
    list_filter = ('role', 'is_active', 'journal')
    search_fields = ('profile__user__email', 'journal__title')


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'journal', 'section_editor', 'order', 'is_active')
    list_filter = ('is_active', 'journal')
    search_fields = ('name', 'code', 'description')
    ordering = ('journal', 'order', 'name')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'section', 'order', 'is_active')
    list_filter = ('is_active', 'section__journal')
    search_fields = ('name', 'code', 'description')
    ordering = ('section', 'order', 'name')


@admin.register(ResearchType)
class ResearchTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'order', 'is_active')
    list_filter = ('is_active', 'category__section__journal')
    search_fields = ('name', 'code', 'description')
    ordering = ('category', 'order', 'name')


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'research_type', 'order', 'is_active')
    list_filter = ('is_active', 'research_type__category__section__journal')
    search_fields = ('name', 'code', 'description', 'keywords')
    ordering = ('research_type', 'order', 'name')
