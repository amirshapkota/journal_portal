"""
Management command to create default review form templates.
Run with: python manage.py seed_review_forms
"""
from django.core.management.base import BaseCommand
from apps.reviews.models import ReviewFormTemplate
from apps.journals.models import Journal


class Command(BaseCommand):
    help = 'Create default review form templates for journals'

    def handle(self, *args, **options):
        """Create default review form templates."""
        
        # Standard review form schema
        standard_form = {
            'name': 'Standard Peer Review Form',
            'description': 'Comprehensive peer review form with standard academic criteria',
            'journal': None,  # System-wide default
            'form_schema': {
                'sections': [
                    {
                        'title': 'Manuscript Quality Assessment',
                        'fields': [
                            {
                                'name': 'originality',
                                'label': 'Originality',
                                'type': 'score',
                                'min': 0,
                                'max': 10,
                                'required': True,
                                'description': 'How original and novel is this research?'
                            },
                            {
                                'name': 'methodology',
                                'label': 'Methodology',
                                'type': 'score',
                                'min': 0,
                                'max': 10,
                                'required': True,
                                'description': 'Are the methods sound and appropriate?'
                            },
                            {
                                'name': 'significance',
                                'label': 'Significance',
                                'type': 'score',
                                'min': 0,
                                'max': 10,
                                'required': True,
                                'description': 'How significant is the contribution to the field?'
                            },
                            {
                                'name': 'clarity',
                                'label': 'Clarity of Presentation',
                                'type': 'score',
                                'min': 0,
                                'max': 10,
                                'required': True,
                                'description': 'Is the manuscript well-written and clearly presented?'
                            },
                            {
                                'name': 'references',
                                'label': 'References',
                                'type': 'score',
                                'min': 0,
                                'max': 10,
                                'required': True,
                                'description': 'Are the references appropriate and comprehensive?'
                            }
                        ]
                    }
                ]
            },
            'scoring_criteria': {
                'required': ['originality', 'methodology', 'significance', 'clarity', 'references'],
                'ranges': {
                    'min': 0,
                    'max': 10
                },
                'scoring_guide': {
                    '9-10': 'Outstanding',
                    '7-8': 'Very Good',
                    '5-6': 'Adequate',
                    '3-4': 'Below Standard',
                    '0-2': 'Unacceptable'
                }
            },
            'is_active': True,
            'is_default': True
        }
        
        # Create system-wide default
        template, created = ReviewFormTemplate.objects.update_or_create(
            name=standard_form['name'],
            journal=None,
            defaults=standard_form
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created: {standard_form['name']}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Updated: {standard_form['name']}")
            )
        
        # Create journal-specific templates for existing journals
        journals = Journal.objects.all()
        
        for journal in journals:
            journal_template = standard_form.copy()
            journal_template['name'] = f'Standard Review Form - {journal.title}'
            journal_template['description'] = f'Standard review form for {journal.title}'
            journal_template['journal'] = journal
            journal_template['is_default'] = True
            
            template, created = ReviewFormTemplate.objects.update_or_create(
                name=journal_template['name'],
                journal=journal,
                defaults=journal_template
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created: {journal_template['name']}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Updated: {journal_template['name']}")
                )
        
        total = 1 + journals.count()
        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Total: {total} review form template(s) created/updated")
        )
