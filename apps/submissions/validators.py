"""
Validators for manuscript submissions against section settings.
"""
import re
from django.core.exceptions import ValidationError


class SubmissionSectionValidator:
    """
    Validates submission content against section-specific limits and requirements.
    """
    
    @staticmethod
    def count_words(text):
        """
        Count words in text, stripping HTML tags if present.
        
        Args:
            text (str): Text to count words in
            
        Returns:
            int: Number of words
        """
        if not text:
            return 0
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace and count words
        words = text.strip().split()
        return len(words)
    
    @staticmethod
    def validate_abstract_word_limit(abstract, section):
        """
        Validate abstract word count against section limit.
        
        Args:
            abstract (str): Abstract text
            section (Section): Section instance
            
        Raises:
            ValidationError: If abstract exceeds word limit
        """
        if not section or section.abstract_word_limit == 0:
            return  # No limit or no section
        
        word_count = SubmissionSectionValidator.count_words(abstract)
        
        if word_count > section.abstract_word_limit:
            raise ValidationError(
                f"Abstract exceeds the maximum word limit of {section.abstract_word_limit} words. "
                f"Current count: {word_count} words."
            )
    
    @staticmethod
    def validate_author_count(author_count, section):
        """
        Validate author count against section limits.
        
        Args:
            author_count (int): Number of authors
            section (Section): Section instance
            
        Raises:
            ValidationError: If author count violates limits
        """
        if not section:
            return
        
        # Check minimum authors
        if author_count < section.min_authors:
            raise ValidationError(
                f"This section requires at least {section.min_authors} author(s). "
                f"Current count: {author_count}."
            )
        
        # Check maximum authors (if set)
        if section.max_authors > 0 and author_count > section.max_authors:
            raise ValidationError(
                f"This section allows a maximum of {section.max_authors} author(s). "
                f"Current count: {author_count}."
            )
    
    @staticmethod
    def validate_figure_count(figure_count, section):
        """
        Validate figure count against section limit.
        
        Args:
            figure_count (int): Number of figures
            section (Section): Section instance
            
        Raises:
            ValidationError: If figure count exceeds limit
        """
        if not section or section.max_figures == 0:
            return  # No limit
        
        if figure_count > section.max_figures:
            raise ValidationError(
                f"This section allows a maximum of {section.max_figures} figure(s). "
                f"Current count: {figure_count}."
            )
    
    @staticmethod
    def validate_table_count(table_count, section):
        """
        Validate table count against section limit.
        
        Args:
            table_count (int): Number of tables
            section (Section): Section instance
            
        Raises:
            ValidationError: If table count exceeds limit
        """
        if not section or section.max_tables == 0:
            return  # No limit
        
        if table_count > section.max_tables:
            raise ValidationError(
                f"This section allows a maximum of {section.max_tables} table(s). "
                f"Current count: {table_count}."
            )
    
    @staticmethod
    def validate_total_word_count(submission_data, section):
        """
        Validate total word count of submission against section limit.
        
        Calculates total from abstract, author details, acknowledgements, references, etc.
        
        Args:
            submission_data (dict): Submission data containing various text fields
            section (Section): Section instance
            
        Raises:
            ValidationError: If total word count exceeds limit
        """
        if not section or section.total_word_limit == 0:
            return  # No limit
        
        total_words = 0
        
        # Count words from various fields
        fields_to_count = [
            'abstract',
            'acknowledgements',
            'funding_statement',
            'conflict_of_interest_statement',
        ]
        
        for field in fields_to_count:
            if field in submission_data and submission_data[field]:
                total_words += SubmissionSectionValidator.count_words(submission_data[field])
        
        if total_words > section.total_word_limit:
            raise ValidationError(
                f"Submission exceeds the maximum total word limit of {section.total_word_limit} words. "
                f"Current total: {total_words} words. "
                f"This includes abstract, acknowledgements, funding statement, and conflict of interest statement."
            )
    
    @staticmethod
    def validate_submission_against_section(submission, section):
        """
        Validate a complete submission against all section requirements.
        
        Args:
            submission (Submission): Submission instance or dict with submission data
            section (Section): Section instance
            
        Raises:
            ValidationError: If any validation fails
        """
        errors = {}
        
        # Validate abstract word limit
        try:
            abstract = submission.abstract if hasattr(submission, 'abstract') else submission.get('abstract', '')
            SubmissionSectionValidator.validate_abstract_word_limit(abstract, section)
        except ValidationError as e:
            errors['abstract'] = str(e)
        
        # Validate author count
        try:
            if hasattr(submission, 'author_contributions'):
                # For submission instances
                author_count = submission.author_contributions.count() + 1  # +1 for corresponding author
            else:
                # For submission data dict
                author_count = len(submission.get('coauthors', [])) + 1  # +1 for corresponding author
            
            SubmissionSectionValidator.validate_author_count(author_count, section)
        except ValidationError as e:
            errors['authors'] = str(e)
        
        # Validate figure count (if metadata available)
        try:
            figure_count = submission.get('figure_count', 0) if isinstance(submission, dict) else getattr(submission, 'figure_count', 0)
            SubmissionSectionValidator.validate_figure_count(figure_count, section)
        except ValidationError as e:
            errors['figures'] = str(e)
        
        # Validate table count (if metadata available)
        try:
            table_count = submission.get('table_count', 0) if isinstance(submission, dict) else getattr(submission, 'table_count', 0)
            SubmissionSectionValidator.validate_table_count(table_count, section)
        except ValidationError as e:
            errors['tables'] = str(e)
        
        # Validate total word count
        try:
            if isinstance(submission, dict):
                SubmissionSectionValidator.validate_total_word_count(submission, section)
            else:
                # For model instances, build dict from model fields
                submission_data = {
                    'abstract': submission.abstract,
                    'acknowledgements': getattr(submission, 'acknowledgements', ''),
                    'funding_statement': getattr(submission, 'funding_statement', ''),
                    'conflict_of_interest_statement': getattr(submission, 'conflict_of_interest_statement', ''),
                }
                SubmissionSectionValidator.validate_total_word_count(submission_data, section)
        except ValidationError as e:
            errors['total_words'] = str(e)
        
        if errors:
            raise ValidationError(errors)
        
        return True


def validate_submission_section_limits(submission, section):
    """
    Convenience function to validate a submission against section limits.
    
    Args:
        submission: Submission instance or dict
        section: Section instance
        
    Raises:
        ValidationError: If validation fails
    """
    return SubmissionSectionValidator.validate_submission_against_section(submission, section)
