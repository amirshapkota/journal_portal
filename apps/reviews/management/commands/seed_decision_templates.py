"""
Management command to seed decision letter templates.
Creates default templates for Accept, Reject, Minor Revision, and Major Revision decisions.
"""
from django.core.management.base import BaseCommand
from apps.reviews.models import DecisionLetterTemplate
from apps.journals.models import Journal


class Command(BaseCommand):
    help = 'Seed decision letter templates for all decision types'

    def handle(self, *args, **options):
        self.stdout.write('Seeding decision letter templates...\n')
        
        # Get all journals
        journals = list(Journal.objects.all())
        
        # Define templates for each decision type
        templates = {
            'ACCEPT': {
                'name': 'Standard Acceptance Letter',
                'subject': 'Manuscript Accepted - {{ submission.title }}',
                'body': '''Dear {{ author_name }},

We are pleased to inform you that your manuscript titled "{{ submission.title }}" (Submission ID: {{ submission.submission_number }}) has been ACCEPTED for publication in {{ journal_name }}.

REVIEW SUMMARY:
{{ reviews_summary }}

Your manuscript was reviewed by {{ num_reviewers }} expert reviewer(s), and based on their recommendations and our editorial assessment, we have decided to accept your work for publication.

NEXT STEPS:
1. You will receive further instructions regarding the production process
2. Please prepare your manuscript according to our publication guidelines
3. Copyright and licensing agreements will be sent to you shortly
4. Expected publication timeline: {{ expected_timeline }}

Congratulations on this achievement! We look forward to publishing your work.

Best regards,
{{ editor_name }}
{{ editor_title }}
{{ journal_name }}''',
                'description': 'Standard template for manuscript acceptance',
                'variables_info': {
                    'author_name': 'Corresponding author name',
                    'submission.title': 'Manuscript title',
                    'submission.submission_number': 'Submission identifier',
                    'journal_name': 'Journal name',
                    'reviews_summary': 'Summary of reviewer recommendations',
                    'num_reviewers': 'Number of reviewers',
                    'expected_timeline': 'Expected publication timeline',
                    'editor_name': 'Editor name',
                    'editor_title': 'Editor title',
                }
            },
            'REJECT': {
                'name': 'Standard Rejection Letter',
                'subject': 'Manuscript Decision - {{ submission.title }}',
                'body': '''Dear {{ author_name }},

Thank you for submitting your manuscript titled "{{ submission.title }}" (Submission ID: {{ submission.submission_number }}) to {{ journal_name }}.

After careful consideration and review by our editorial team and expert reviewers, we regret to inform you that we are unable to accept your manuscript for publication at this time.

REVIEW SUMMARY:
{{ reviews_summary }}

This decision is based on:
- Reviewer recommendations and assessments
- Alignment with journal scope and standards
- Current publication priorities

We understand that receiving a rejection can be disappointing. Please note that this decision reflects the competitive nature of our journal and does not diminish the value of your research.

We encourage you to consider submitting your work to other journals that may be a better fit for your research. We appreciate your interest in {{ journal_name }} and wish you success with your future submissions.

Best regards,
{{ editor_name }}
{{ editor_title }}
{{ journal_name }}''',
                'description': 'Standard template for manuscript rejection',
                'variables_info': {
                    'author_name': 'Corresponding author name',
                    'submission.title': 'Manuscript title',
                    'submission.submission_number': 'Submission identifier',
                    'journal_name': 'Journal name',
                    'reviews_summary': 'Summary of reviewer recommendations',
                    'editor_name': 'Editor name',
                    'editor_title': 'Editor title',
                }
            },
            'MINOR_REVISION': {
                'name': 'Minor Revision Request',
                'subject': 'Revision Required - {{ submission.title }}',
                'body': '''Dear {{ author_name }},

Thank you for submitting your manuscript titled "{{ submission.title }}" (Submission ID: {{ submission.submission_number }}) to {{ journal_name }}.

Your manuscript has been reviewed by {{ num_reviewers }} expert reviewer(s). While the reviewers and editors found merit in your work, MINOR REVISIONS are required before a final decision can be made.

REVIEW SUMMARY:
{{ reviews_summary }}

REQUIRED REVISIONS:
{{ revision_requirements }}

SUBMISSION GUIDELINES:
1. Please address all reviewer comments in your revised manuscript
2. Provide a detailed point-by-point response to each reviewer comment
3. Highlight all changes made in the revised manuscript
4. Submit your revision by: {{ revision_deadline }}

REQUIRED DOCUMENTS:
- Revised manuscript with changes highlighted
- Point-by-point response letter to reviewers
- Cover letter summarizing major changes (optional but recommended)

Please submit your revised manuscript through our submission system. We look forward to receiving your revised submission.

Best regards,
{{ editor_name }}
{{ editor_title }}
{{ journal_name }}''',
                'description': 'Template for requesting minor revisions',
                'variables_info': {
                    'author_name': 'Corresponding author name',
                    'submission.title': 'Manuscript title',
                    'submission.submission_number': 'Submission identifier',
                    'journal_name': 'Journal name',
                    'num_reviewers': 'Number of reviewers',
                    'reviews_summary': 'Summary of reviewer recommendations',
                    'revision_requirements': 'Specific revision requirements',
                    'revision_deadline': 'Deadline for revised submission',
                    'editor_name': 'Editor name',
                    'editor_title': 'Editor title',
                }
            },
            'MAJOR_REVISION': {
                'name': 'Major Revision Request',
                'subject': 'Major Revision Required - {{ submission.title }}',
                'body': '''Dear {{ author_name }},

Thank you for submitting your manuscript titled "{{ submission.title }}" (Submission ID: {{ submission.submission_number }}) to {{ journal_name }}.

Your manuscript has been reviewed by {{ num_reviewers }} expert reviewer(s). While the reviewers and editors found potential in your work, MAJOR REVISIONS are required before a final decision can be made.

REVIEW SUMMARY:
{{ reviews_summary }}

REQUIRED MAJOR REVISIONS:
{{ revision_requirements }}

IMPORTANT NOTES:
- The requested revisions are substantial and may require significant additional work
- Your revised manuscript will undergo another round of peer review
- Please carefully address all reviewer concerns
- Additional experiments or analyses may be required

SUBMISSION GUIDELINES:
1. Thoroughly address ALL reviewer comments and concerns
2. Provide a comprehensive point-by-point response to each reviewer
3. Clearly highlight all changes and additions in the revised manuscript
4. Submit your revision by: {{ revision_deadline }}

REQUIRED DOCUMENTS:
- Revised manuscript with all changes clearly marked
- Detailed point-by-point response letter addressing each reviewer comment
- Cover letter explaining major changes and improvements
- Any additional supplementary materials requested by reviewers

Please note that submission of a revised manuscript does not guarantee acceptance. The revised manuscript will be re-evaluated, and reviewers may be consulted again.

If you have questions about the revisions or need clarification, please contact us before submitting your revision.

Best regards,
{{ editor_name }}
{{ editor_title }}
{{ journal_name }}''',
                'description': 'Template for requesting major revisions',
                'variables_info': {
                    'author_name': 'Corresponding author name',
                    'submission.title': 'Manuscript title',
                    'submission.submission_number': 'Submission identifier',
                    'journal_name': 'Journal name',
                    'num_reviewers': 'Number of reviewers',
                    'reviews_summary': 'Summary of reviewer recommendations',
                    'revision_requirements': 'Specific revision requirements',
                    'revision_deadline': 'Deadline for revised submission',
                    'editor_name': 'Editor name',
                    'editor_title': 'Editor title',
                }
            }
        }
        
        created_count = 0
        
        # Create system-wide default templates
        self.stdout.write('Creating system-wide default templates...')
        for decision_type, template_data in templates.items():
            template, created = DecisionLetterTemplate.objects.get_or_create(
                decision_type=decision_type,
                journal__isnull=True,
                is_default=True,
                defaults={
                    'name': template_data['name'],
                    'subject': template_data['subject'],
                    'body': template_data['body'],
                    'description': template_data['description'],
                    'variables_info': template_data['variables_info'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {template.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  - Already exists: {template.name}'))
        
        # Create journal-specific templates (optional)
        if journals:
            self.stdout.write(f'\nCreating journal-specific templates for {len(journals)} journal(s)...')
            for journal in journals:
                for decision_type, template_data in templates.items():
                    template, created = DecisionLetterTemplate.objects.get_or_create(
                        decision_type=decision_type,
                        journal=journal,
                        defaults={
                            'name': f'{template_data["name"]} - {journal.title}',
                            'subject': template_data['subject'],
                            'body': template_data['body'],
                            'description': f'{template_data["description"]} for {journal.title}',
                            'variables_info': template_data['variables_info'],
                            'is_active': True,
                            'is_default': False,
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {template.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n Successfully created {created_count} decision letter template(s)'))
        total_templates = DecisionLetterTemplate.objects.count()
        self.stdout.write(self.style.SUCCESS(f' Total templates in database: {total_templates}'))
