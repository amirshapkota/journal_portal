"""
Common permissions for the Journal Portal.
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to the owner
        return obj.owner == request.user


class IsAuthorOrReviewer(permissions.BasePermission):
    """
    Permission for submission access - author or assigned reviewer.
    """

    def has_object_permission(self, request, view, obj):
        # Check if user is the author
        if hasattr(obj, 'author') and obj.author == request.user:
            return True
        
        # Check if user is an assigned reviewer
        if hasattr(obj, 'reviewers') and request.user in obj.reviewers.all():
            return True
        
        return False


class IsJournalStaff(permissions.BasePermission):
    """
    Permission for journal staff members.
    """

    def has_object_permission(self, request, view, obj):
        # Check if user is journal staff
        if hasattr(obj, 'journal'):
            return obj.journal.staff.filter(user=request.user).exists()
        return False


class IsEditorOrReviewer(permissions.BasePermission):
    """
    Permission for editors and reviewers.
    """

    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=['Editor', 'Reviewer']).exists()