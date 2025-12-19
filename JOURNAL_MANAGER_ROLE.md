# JOURNAL_MANAGER Role Documentation

## Overview
The `JOURNAL_MANAGER` role has been created to separate journal administrative management from editorial activities. Users with this role can manage journal settings and staff but cannot participate in the editorial process.

## What JOURNAL_MANAGER Can Do

### 1. Journal Management
- **Create journals**: Users with JOURNAL_MANAGER role can create new journals
- **View journals**: Can view all journal details and settings
- **Update journals**: Can modify journal settings, metadata, and configuration
- **Delete journals**: Can remove journals (subject to system constraints)

### 2. Staff Management
- **Add staff members**: Can add new staff members to journals with specific roles
- **Remove staff members**: Can deactivate staff members from journals
- **Update staff roles**: Can change staff member roles and permissions
- **Change Editor-in-Chief**: Can assign and change the Editor-in-Chief of journals

### 3. Journal Settings
- Can manage all journal-level configurations
- Can update journal metadata
- Can configure journal preferences

## What JOURNAL_MANAGER Cannot Do

### Editorial Activities (Explicitly Blocked)
Users with JOURNAL_MANAGER role are **explicitly prevented** from:

1. **Submission Management**
   - Cannot view submissions
   - Cannot edit submissions
   - Cannot update submission status
   - Cannot make editorial decisions

2. **Workflow Activities**
   - Cannot access copyediting workflows
   - Cannot access production workflows
   - Cannot manage publication schedules
   - Cannot participate in any editorial discussions

3. **Document Management**
   - Cannot access SuperDoc documents
   - Cannot view or edit manuscript files
   - Cannot add comments or track changes

4. **Review Process**
   - Cannot assign reviewers
   - Cannot view review assignments
   - Cannot make acceptance/rejection decisions

## Implementation Details

### Files Modified

1. **apps/users/models.py**
   - Added `('JOURNAL_MANAGER', 'Journal Manager')` to `Role.ROLE_CHOICES`
   - Migration: `0011_alter_role_name.py`

2. **apps/journals/views.py**
   - Updated `JournalPermissions` class to allow JOURNAL_MANAGER:
     - `has_permission()`: Checks for JOURNAL_MANAGER role alongside EDITOR role
     - `has_object_permission()`: Allows JOURNAL_MANAGER to modify journals
   - Updated staff management actions:
     - `add_staff()`: Allows JOURNAL_MANAGER to add staff
     - `remove_staff()`: Allows JOURNAL_MANAGER to remove staff
     - `update_staff()`: Allows JOURNAL_MANAGER to update staff (including Editor-in-Chief)

3. **apps/submissions/views.py**
   - Updated `SubmissionPermissions`:
     - Added explicit check to **deny** JOURNAL_MANAGER access to submissions
     - Returns `False` before checking other permissions

4. **apps/submissions/workflow_views.py**
   - Updated `WorkflowPermissions`:
     - Added explicit check to **deny** JOURNAL_MANAGER access to workflow
     - Logs denial for debugging

5. **apps/submissions/superdoc_views.py**
   - Updated `SuperDocPermission`:
     - Added explicit check to **deny** JOURNAL_MANAGER access to documents
   - Updated `can_access_document()` helper function:
     - Returns `(False, False)` for users with JOURNAL_MANAGER role

## Permission Check Flow

### For Journal Management
```
1. Is user superuser/staff? → GRANT
2. Is user authenticated? → Continue
3. Does user have JOURNAL_MANAGER or EDITOR role? → GRANT for journal operations
4. For specific journal objects:
   - Has JOURNAL_MANAGER role? → GRANT
   - Is journal staff (EDITOR_IN_CHIEF/MANAGING_EDITOR)? → GRANT
```

### For Editorial Activities
```
1. Is user superuser/staff? → GRANT
2. Has JOURNAL_MANAGER role? → DENY (explicit block)
3. Other checks (author, journal staff, etc.) → Continue as normal
```

## Usage Example

### Assigning JOURNAL_MANAGER Role
```python
from apps.users.models import Role, Profile

# Get the role
journal_manager_role = Role.objects.get(name='JOURNAL_MANAGER')

# Assign to a user's profile
user_profile = Profile.objects.get(user__email='manager@example.com')
user_profile.roles.add(journal_manager_role)
```

### API Access
A user with JOURNAL_MANAGER role can:
- `GET /api/v1/journals/journals/` - List all journals
- `POST /api/v1/journals/journals/` - Create a journal
- `GET /api/v1/journals/journals/{id}/` - View journal details
- `PUT/PATCH /api/v1/journals/journals/{id}/` - Update journal
- `POST /api/v1/journals/journals/{id}/add_staff/` - Add staff member
- `DELETE /api/v1/journals/journals/{id}/staff/{user_id}/` - Remove staff
- `PUT /api/v1/journals/journals/{id}/staff/{user_id}/update/` - Update staff (including Editor-in-Chief)

But **cannot** access:
- `/api/v1/submissions/submissions/*` - Any submission endpoints
- `/api/v1/submissions/copyediting/*` - Copyediting workflows
- `/api/v1/submissions/production/*` - Production workflows
- `/api/v1/submissions/publication-schedules/*` - Publication schedules
- `/api/v1/submissions/superdoc/*` - Document management

## Security Considerations

1. **Separation of Concerns**: The role ensures administrative tasks are separate from editorial decisions
2. **Explicit Denial**: JOURNAL_MANAGER is explicitly blocked from editorial activities (not just omitted from allowed roles)
3. **Early Exit**: Permission checks for JOURNAL_MANAGER return False early to prevent bypass
4. **Comprehensive Coverage**: All editorial-related permissions (submissions, workflow, documents) check and block JOURNAL_MANAGER

## Testing

To verify the implementation:

1. **Create a user with JOURNAL_MANAGER role**
2. **Test allowed operations**:
   - Create a journal
   - Add staff members
   - Change Editor-in-Chief
   - Update journal settings
3. **Test blocked operations** (should all fail):
   - Attempt to view submissions
   - Attempt to access workflow endpoints
   - Attempt to view documents

## Migration

Run the migration:
```bash
python manage.py migrate users
```

This will add the new JOURNAL_MANAGER choice to the Role model's name field.
