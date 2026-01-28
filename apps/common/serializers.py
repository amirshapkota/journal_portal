"""
Serializers for common app models.
"""
from rest_framework import serializers
from .models import ActivityLog, VerificationTicket, Concept, Embedding, AnomalyEvent, Award


class ActivityLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ActivityLog model.
    Provides detailed information about system events for admin monitoring.
    """
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True, allow_null=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    actor_type_display = serializers.CharField(source='get_actor_type_display', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'user_id',
            'user_email',
            'actor_type',
            'actor_type_display',
            'action_type',
            'action_type_display',
            'resource_type',
            'resource_type_display',
            'resource_id',
            'metadata',
            'ip_address',
            'user_agent',
            'session_id',
            'created_at',
        ]
        read_only_fields = fields


class VerificationTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for VerificationTicket model.
    """
    profile_name = serializers.CharField(source='profile.get_full_name', read_only=True)
    requested_role_display = serializers.CharField(source='get_requested_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = VerificationTicket
        fields = [
            'id',
            'profile',
            'profile_name',
            'requested_role',
            'requested_role_display',
            'status',
            'status_display',
            'evidence',
            'ml_score',
            'ml_reasoning',
            'reviewed_by',
            'reviewed_at',
            'review_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'ml_score', 'ml_reasoning']


class ConceptSerializer(serializers.ModelSerializer):
    """
    Serializer for Concept model.
    """
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    
    class Meta:
        model = Concept
        fields = [
            'id',
            'name',
            'description',
            'provider',
            'provider_display',
            'external_id',
            'parent_concept',
            'metadata',
            'usage_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'usage_count']


class AnomalyEventSerializer(serializers.ModelSerializer):
    """
    Serializer for AnomalyEvent model.
    """
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AnomalyEvent
        fields = [
            'id',
            'event_type',
            'event_type_display',
            'severity',
            'severity_display',
            'resource_type',
            'resource_id',
            'anomaly_score',
            'evidence',
            'detector_name',
            'detector_version',
            'detection_confidence',
            'is_handled',
            'handled_by',
            'handled_by_name',
            'handled_at',
            'resolution_notes',
            'is_false_positive',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AwardSerializer(serializers.ModelSerializer):
    """
    Serializer for Award model.
    """
    profile_name = serializers.CharField(source='profile.get_full_name', read_only=True)
    badge_type_display = serializers.CharField(source='get_badge_type_display', read_only=True)
    awarded_by_name = serializers.CharField(source='awarded_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Award
        fields = [
            'id',
            'profile',
            'profile_name',
            'badge_type',
            'badge_type_display',
            'title',
            'description',
            'criteria_met',
            'evidence',
            'points_value',
            'is_public',
            'awarded_by',
            'awarded_by_name',
            'auto_awarded',
            'awarded_at',
        ]
        read_only_fields = ['id', 'awarded_at']


# ============================================================================
# PUBLIC API SERIALIZERS FOR PUBLISHED SUBMISSIONS
# ============================================================================

class PublicAuthorSerializer(serializers.Serializer):
    """Public serializer for author information on published articles."""
    id = serializers.UUIDField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    affiliation_name = serializers.CharField(read_only=True, allow_blank=True)
    orcid_id = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    order = serializers.IntegerField(read_only=True)
    contrib_role = serializers.CharField(read_only=True)
    
    class Meta:
        fields = ['id', 'display_name', 'affiliation_name', 'orcid_id', 'order', 'contrib_role']


class PublicJournalSerializer(serializers.Serializer):
    """Public serializer for journal information."""
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    short_name = serializers.CharField(read_only=True)
    publisher = serializers.CharField(read_only=True, allow_blank=True)
    issn_print = serializers.CharField(read_only=True, allow_blank=True)
    issn_online = serializers.CharField(read_only=True, allow_blank=True)
    website_url = serializers.URLField(read_only=True, allow_blank=True)
    
    class Meta:
        fields = ['id', 'title', 'short_name', 'publisher', 'issn_print', 'issn_online', 'website_url']


class PublicDocumentSerializer(serializers.Serializer):
    """Public serializer for published document information."""
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    document_type = serializers.CharField(read_only=True)
    file_name = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    # Note: file URLs would need appropriate public access handling
    # For now, we'll include placeholder for file access
    download_url = serializers.SerializerMethodField()
    
    def get_download_url(self, obj):
        """Generate download URL for public access."""
        request = self.context.get('request')
        if request and obj.original_file:
            # This would need to be a public endpoint
            return request.build_absolute_uri(f'/api/public/publications/documents/{obj.id}/download/')
        return None
    
    class Meta:
        fields = ['id', 'title', 'document_type', 'file_name', 'file_size', 'created_at', 'download_url']


class PublicationDetailSerializer(serializers.Serializer):
    """
    Comprehensive public serializer for published submissions.
    Provides complete publication details including journal, authors, and documents.
    Designed for integration with platforms like ResearchGate, Google Scholar, etc.
    """
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    abstract = serializers.CharField(read_only=True)
    submission_number = serializers.CharField(read_only=True)
    doi = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    
    # Journal information
    journal = PublicJournalSerializer(read_only=True)
    
    # Publication details (volume, issue, pages, year)
    publication_details = serializers.SerializerMethodField()
    
    # Publication dates
    submitted_at = serializers.DateTimeField(read_only=True)
    published_date = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Article type
    article_type = serializers.SerializerMethodField()
    
    # Taxonomy information
    section = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()
    
    # Authors
    authors = serializers.SerializerMethodField()
    corresponding_author = PublicAuthorSerializer(read_only=True)
    
    # Contact information for corresponding author
    corresponding_author_email = serializers.SerializerMethodField()
    
    # Documents
    documents = serializers.SerializerMethodField()
    
    # Metadata (funding, conflicts of interest, etc.)
    metadata = serializers.SerializerMethodField()
    
    # Citation information
    citation = serializers.SerializerMethodField()
    
    # License information
    license_info = serializers.SerializerMethodField()
    
    def get_section(self, obj):
        """Get section and taxonomy information."""
        if obj.section:
            section_data = {
                'name': obj.section.name,
                'code': obj.section.code,
            }
            
            if obj.category:
                section_data['category'] = {
                    'name': obj.category.name,
                    'code': obj.category.code,
                }
                
                if obj.research_type:
                    section_data['research_type'] = {
                        'name': obj.research_type.name,
                        'code': obj.research_type.code,
                    }
                    
                    if obj.area:
                        section_data['area'] = {
                            'name': obj.area.name,
                            'code': obj.area.code,
                            'keywords': obj.area.keywords if hasattr(obj.area, 'keywords') else []
                        }
            
            return section_data
        return None
    
    def get_keywords(self, obj):
        """Extract keywords from metadata."""
        if obj.metadata_json and 'keywords' in obj.metadata_json:
            return obj.metadata_json['keywords']
        return []
    
    def get_publication_details(self, obj):
        """
        Get publication details (volume, issue, pages, year) from PublicationSchedule.
        Essential for academic citations and platforms like ResearchGate.
        """
        try:
            from apps.submissions.models.production.models import PublicationSchedule
            schedule = PublicationSchedule.objects.filter(
                submission=obj,
                status='PUBLISHED'
            ).first()
            
            if schedule:
                return {
                    'volume': schedule.volume,
                    'issue': schedule.issue,
                    'year': schedule.year,
                    'pages': schedule.pages,
                    'published_date': schedule.published_date,
                }
        except:
            pass
        
        # Fallback to basic info if no publication schedule
        return {
            'volume': '',
            'issue': '',
            'year': obj.submitted_at.year if obj.submitted_at else obj.created_at.year,
            'pages': '',
            'published_date': obj.updated_at if obj.status == 'PUBLISHED' else None,
        }
    
    def get_published_date(self, obj):
        """
        Get the actual publication date.
        Tries PublicationSchedule first, falls back to updated_at for published submissions.
        """
        try:
            from apps.submissions.models.production.models import PublicationSchedule
            schedule = PublicationSchedule.objects.filter(
                submission=obj,
                status='PUBLISHED'
            ).first()
            
            if schedule and schedule.published_date:
                return schedule.published_date
        except:
            pass
        
        # Fallback to updated_at for published status
        if obj.status == 'PUBLISHED':
            return obj.updated_at
        return None
    
    def get_article_type(self, obj):
        """
        Get article type from research_type taxonomy.
        Important for categorization in academic databases.
        """
        if obj.research_type:
            return {
                'code': obj.research_type.code,
                'name': obj.research_type.name,
                'description': obj.research_type.description if hasattr(obj.research_type, 'description') else '',
            }
        return None
    
    def get_corresponding_author_email(self, obj):
        """
        Provide corresponding author email for contact.
        Only if author has made it publicly available in metadata.
        """
        # Check if email is marked as public in metadata
        if obj.metadata_json and 'corresponding_author_email' in obj.metadata_json:
            return obj.metadata_json['corresponding_author_email']
        
        # For public API, only return if explicitly set in metadata
        # Don't automatically expose user email
        return None
    
    def get_authors(self, obj):
        """Get all authors with their contributions ordered."""
        from apps.submissions.models.models import AuthorContribution
        
        contributions = AuthorContribution.objects.filter(
            submission=obj
        ).select_related('profile').order_by('order')
        
        authors_data = []
        for contrib in contributions:
            authors_data.append({
                'id': str(contrib.profile.id),
                'display_name': contrib.profile.display_name or contrib.profile.get_full_name(),
                'affiliation_name': contrib.profile.affiliation_name,
                'orcid_id': contrib.profile.orcid_id,
                'order': contrib.order,
                'contrib_role': contrib.contrib_role,
            })
        
        return authors_data
    
    def get_documents(self, obj):
        """Get published documents (final versions, manuscripts)."""
        from apps.submissions.models.models import Document
        
        # Only include manuscript and final version documents for public view
        public_doc_types = ['MANUSCRIPT', 'FINAL_VERSION']
        docs = Document.objects.filter(
            submission=obj,
            document_type__in=public_doc_types
        ).order_by('-created_at')
        
        serializer = PublicDocumentSerializer(docs, many=True, context=self.context)
        return serializer.data
    
    def get_metadata(self, obj):
        """Get safe public metadata."""
        public_metadata = {}
        
        if obj.metadata_json:
            # Only include safe public fields
            safe_fields = [
                'keywords',
                'funding',
                'acknowledgments',
                'subject_areas',
                'conflicts_of_interest',
                'ethics_statement',
                'data_availability',
                'author_contributions',
                'supplementary_materials',
                'competing_interests',
                'references',  # Bibliography/References
                'abbreviations',
            ]
            for field in safe_fields:
                if field in obj.metadata_json:
                    public_metadata[field] = obj.metadata_json[field]
        
        return public_metadata
    
    def get_citation(self, obj):
        """
        Generate citation information in multiple formats.
        Essential for ResearchGate and other academic platforms.
        """
        # Get publication details
        pub_details = self.get_publication_details(obj)
        
        # Get all authors
        authors_list = self.get_authors(obj)
        
        # Format author names for citation
        if authors_list:
            if len(authors_list) == 1:
                authors_citation = authors_list[0]['display_name']
            elif len(authors_list) == 2:
                authors_citation = f"{authors_list[0]['display_name']} and {authors_list[1]['display_name']}"
            else:
                # First author et al.
                authors_citation = f"{authors_list[0]['display_name']} et al."
        else:
            authors_citation = "Unknown"
        
        # Basic citation components
        citation_data = {
            'authors': authors_citation,
            'year': pub_details.get('year'),
            'title': obj.title,
            'journal': obj.journal.title,
            'volume': pub_details.get('volume'),
            'issue': pub_details.get('issue'),
            'pages': pub_details.get('pages'),
            'doi': obj.doi,
            
            # Formatted citations
            'apa': self._format_apa_citation(obj, authors_citation, pub_details),
            'mla': self._format_mla_citation(obj, authors_citation, pub_details),
            'chicago': self._format_chicago_citation(obj, authors_citation, pub_details),
            'bibtex': self._format_bibtex_citation(obj, authors_list, pub_details),
        }
        
        return citation_data
    
    def _format_apa_citation(self, obj, authors, pub_details):
        """Format APA style citation."""
        parts = [authors]
        
        year = pub_details.get('year')
        if year:
            parts.append(f"({year}).")
        
        parts.append(f"{obj.title}.")
        parts.append(f"<i>{obj.journal.title}</i>")
        
        vol_issue = []
        if pub_details.get('volume'):
            vol_issue.append(f"<i>{pub_details['volume']}</i>")
        if pub_details.get('issue'):
            vol_issue.append(f"({pub_details['issue']})")
        
        if vol_issue:
            parts.append(''.join(vol_issue) + ',')
        
        if pub_details.get('pages'):
            parts.append(f"{pub_details['pages']}.")
        
        if obj.doi:
            parts.append(f"https://doi.org/{obj.doi}")
        
        return ' '.join(parts)
    
    def _format_mla_citation(self, obj, authors, pub_details):
        """Format MLA style citation."""
        parts = [f'{authors}.']
        parts.append(f'"{obj.title}."')
        parts.append(f'<i>{obj.journal.title}</i>')
        
        vol_info = []
        if pub_details.get('volume'):
            vol_info.append(f"vol. {pub_details['volume']}")
        if pub_details.get('issue'):
            vol_info.append(f"no. {pub_details['issue']}")
        
        if vol_info:
            parts.append(', '.join(vol_info) + ',')
        
        year = pub_details.get('year')
        if year:
            parts.append(f"{year},")
        
        if pub_details.get('pages'):
            parts.append(f"pp. {pub_details['pages']}.")
        
        if obj.doi:
            parts.append(f"doi:{obj.doi}.")
        
        return ' '.join(parts)
    
    def _format_chicago_citation(self, obj, authors, pub_details):
        """Format Chicago style citation."""
        parts = [f'{authors}.']
        parts.append(f'"{obj.title}."')
        parts.append(f'<i>{obj.journal.title}</i>')
        
        vol_issue_parts = []
        if pub_details.get('volume'):
            vol_issue_parts.append(pub_details['volume'])
        if pub_details.get('issue'):
            vol_issue_parts.append(f"no. {pub_details['issue']}")
        
        if vol_issue_parts:
            parts.append(', '.join(vol_issue_parts))
        
        year = pub_details.get('year')
        if year:
            parts.append(f"({year}):")
        
        if pub_details.get('pages'):
            parts.append(f"{pub_details['pages']}.")
        
        if obj.doi:
            parts.append(f"https://doi.org/{obj.doi}.")
        
        return ' '.join(parts)
    
    def _format_bibtex_citation(self, obj, authors_list, pub_details):
        """Format BibTeX citation entry."""
        # Generate citation key (FirstAuthorYear)
        first_author_last = authors_list[0]['display_name'].split()[-1] if authors_list else 'Unknown'
        year = pub_details.get('year', '')
        citation_key = f"{first_author_last}{year}"
        
        # Format author names for BibTeX
        bibtex_authors = ' and '.join([a['display_name'] for a in authors_list])
        
        bibtex_lines = [
            f"@article{{{citation_key},",
            f'  author = {{{bibtex_authors}}},',
            f'  title = {{{obj.title}}},',
            f'  journal = {{{obj.journal.title}}},',
        ]
        
        if pub_details.get('year'):
            bibtex_lines.append(f"  year = {{{pub_details['year']}}},")
        if pub_details.get('volume'):
            bibtex_lines.append(f"  volume = {{{pub_details['volume']}}},")
        if pub_details.get('issue'):
            bibtex_lines.append(f"  number = {{{pub_details['issue']}}},")
        if pub_details.get('pages'):
            bibtex_lines.append(f"  pages = {{{pub_details['pages']}}},")
        if obj.doi:
            bibtex_lines.append(f"  doi = {{{obj.doi}}},")
        if obj.journal.issn_online:
            bibtex_lines.append(f"  issn = {{{obj.journal.issn_online}}},")
        
        bibtex_lines.append("}")
        
        return '\n'.join(bibtex_lines)
    
    def get_license_info(self, obj):
        """
        Get licensing information for the publication.
        Important for open access and reuse permissions.
        """
        if obj.metadata_json and 'license' in obj.metadata_json:
            return obj.metadata_json['license']
        
        # Default to typical academic license if not specified
        return {
            'type': 'All Rights Reserved',
            'url': '',
            'description': 'Copyright held by the authors and/or publisher. Contact for permissions.',
        }
    
    class Meta:
        fields = [
            'id', 'title', 'abstract', 'submission_number', 'doi',
            'journal', 'publication_details', 'submitted_at', 'published_date',
            'created_at', 'updated_at', 'article_type', 'section', 'keywords',
            'authors', 'corresponding_author', 'corresponding_author_email',
            'documents', 'metadata', 'citation', 'license_info'
        ]
