# Frontend Specification - Journal Portal (Subject to changee)

---

**Phase 1:** Authentication & User Management (100% Complete)
- User registration, login, logout, JWT tokens
- Profile management, roles, password reset
- **Pages:** Login, Register, Profile, Email Verification, Password Reset

**Phase 2:** Journal & Submission Management (100% Complete)
- Journal CRUD, staff management
- Submission workflow (draft → published)
- Document upload, versioning, file management
- **Pages:** Journal Browse, Submission Creation, Submission Details, File Management

**Phase 3:** ORCID & Verification (100% Complete)
- ORCID OAuth integration
- Identity verification workflow
- Email notification system (14 templates)
- **Pages:** ORCID Connection, Verification Request, Email Preferences, Email Logs

**Phase 4:** Review System (100% Complete)
- Review assignment, submission, recommendations
- Editorial decisions, revision rounds
- Review forms, decision letters
- **Pages:** Reviewer Dashboard, Review Submission, Editor Decision Making, Revision Management

###  **NOT YET IMPLEMENTED IN BACKEND**

**Phase 5:** Advanced Features (Not Built)
- ML reviewer recommendations (placeholder only)
- Plagiarism detection (iThenticate integration)
- Live document editing (OnlyOffice/Collabora)
- ROR/OpenAlex integrations

**Phase 6:** Analytics & Reporting (Not Built)
- Advanced analytics dashboard
- Performance metrics
- Custom reports
- Audit logs

**Phase 7:** Production Features (Not Built)
- System monitoring
- Performance optimization
- Advanced security features

---


###  Ready to Build (Backend Complete)
1. [Public Pages](#public-pages)
2. [Authentication Pages](#authentication-pages)
3. [User Dashboard & Profile](#user-dashboard--profile)
4. [Author Pages](#author-pages)
5. [Reviewer Pages](#reviewer-pages)
6. [Editor Pages](#editor-pages)
7. [Admin Pages](#admin-pages)

###  Plan for Later (Backend Not Built)
8. [Future Features](#future-features-phases-5-7)

###  Reference
9. [Common Components](#common-components)
10. [API Integration Notes](#api-integration-notes)


#  PAGES WITH COMPLETE BACKEND (BUILD THESE NOW)

---

##  PUBLIC PAGES

### 1. Landing Page `/`
**Purpose:** Public homepage showcasing the platform
**Backend Status:** Journal & submission APIs complete

**Components:**
- Hero section with CTA buttons
- Featured journals list
- Statistics dashboard (total journals, submissions, published articles)
- How it works section (3-step process)
- Recent publications feed
- Footer with links

**API Calls:**
- `GET /api/v1/journals/` - List active journals
- `GET /api/v1/submissions/?status=PUBLISHED` - Recent publications

---

### 2. Browse Journals Page `/journals`  
**Purpose:** Explore available journals
**Backend Status:** Complete with search, filters, pagination

**Components:**
- Search bar with filters (subject, ISSN, publisher)
- Journal cards grid with:
  - Journal title and short name
  - ISSN numbers
  - Description preview
  - Submission status badge
  - View details button
- Pagination component
- Sort dropdown (A-Z, newest, most submissions)

**API Calls:**
- `GET /api/v1/journals/?search=&ordering=`

---

### 3. Journal Details Page `/journals/:id`  
**Purpose:** View journal information and submission guidelines
**Backend Status:** All journal endpoints operational

**Components:**
- Journal header (title, ISSN, publisher)
- About section (description, scope)
- Editorial team list
- Submission guidelines accordion
- Journal settings display
- "Submit to This Journal" CTA button
- Journal statistics (total submissions, acceptance rate)

**API Calls:**
- `GET /api/v1/journals/:id/`
- `GET /api/v1/journals/:id/staff/`
- `GET /api/v1/journals/:id/statistics/`
- `GET /api/v1/journals/:id/get_settings/`

---

##  AUTHENTICATION PAGES

### 4. Register Page `/register`  **Phase 1 - Ready**
**Purpose:** New user account creation
**Backend Status:** JWT authentication fully implemented

**Components:**
- Registration form:
  - Email field (with validation)
  - Password field (with strength indicator)
  - Confirm password field
  - First name, Last name
  - Institution (optional)
  - Country dropdown
- Terms & conditions checkbox
- "Already have account?" link
- ORCID connect option
- Email verification notice

**API Calls:**
- `POST /api/v1/auth/register/`

**Form Fields:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "institution": "University Name",
  "country": "USA"
}
```

---

### 5. Login Page `/login`  **Phase 1 - Ready**
**Purpose:** User authentication
**Backend Status:** JWT tokens, refresh, blacklisting all working

**Components:**
- Login form (email, password)
- "Remember me" checkbox
- "Forgot password?" link
- Social login buttons (ORCID)
- "Don't have account?" link
- Error message display

**API Calls:**
- `POST /api/v1/auth/login/` - Returns JWT tokens

**Success Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

---

### 6. Email Verification Page `/verify-email/:token`  **Phase 1 - Ready**
**Purpose:** Confirm email address
**Backend Status:** Email verification system complete

**Components:**
- Verification status message
- Success/error icon
- Redirect countdown timer
- "Go to Login" button

**API Calls:**
- `POST /api/v1/auth/verify-email/` with token

---

### 7. Password Reset Pages  **Phase 1 - Ready**
**Backend Status:** Password reset flow fully functional

**7a. Request Reset `/forgot-password`**
**Components:**
- Email input field
- Submit button
- Back to login link
- Success message display

**API Calls:**
- `POST /api/v1/auth/password/reset/`

**7b. Reset Confirm `/reset-password/:token`**
**Components:**
- New password field
- Confirm password field
- Password strength indicator
- Submit button
- Success/error message

**API Calls:**
- `POST /api/v1/auth/password/reset/confirm/`

---

##  USER DASHBOARD & PROFILE

### 8. User Dashboard `/dashboard`  **Phase 1-4 - Ready**
**Purpose:** Main user hub with role-based content
**Backend Status:** All user, submission, review APIs complete

**Components:**
- Welcome header with user name
- Quick stats cards:
  - My Submissions (count)
  - Pending Reviews (count)
  - Verification Status
  - ORCID Status
- Recent activity timeline
- Quick action buttons (New Submission, View Reviews)
- Notifications panel
- Role-based navigation tabs

**API Calls:**
- `GET /api/v1/auth/me/` - Current user info
- `GET /api/v1/submissions/?corresponding_author=me`
- `GET /api/v1/reviews/assignments/?reviewer=me`
- `GET /api/v1/notifications/email-logs/user_stats/`

---

### 9. User Profile Page `/profile`  **Phase 1 & 3 - Ready**
**Purpose:** View and edit user information
**Backend Status:** Profile CRUD + ORCID integration complete

**Components:**
- Profile header with avatar
- Editable fields:
  - Personal info (name, email, institution, country)
  - Bio textarea
  - Expertise areas (multi-select tags)
  - Website URL
  - Profile picture upload
- ORCID connection section:
  - Connect button (if not connected)
  - ORCID ID display (if connected)
  - Disconnect option
- Verification status badge
- Save/Cancel buttons

**API Calls:**
- `GET /api/v1/profiles/:id/`
- `PATCH /api/v1/profiles/:id/` - Update profile
- `GET /api/v1/integrations/orcid/status/`
- `GET /api/v1/integrations/orcid/connect/` - Initiate OAuth
- `POST /api/v1/integrations/orcid/disconnect/`

---

### 10. Verification Request Page `/verification/request`  **Phase 3 - Ready**
**Purpose:** Request Author/Reviewer role verification
**Backend Status:** Complete verification system with auto-scoring

**Components:**
- Request form:
  - Role selection (Author, Reviewer, Both)
  - Institutional email input
  - Institutional affiliation input
  - ORCID ID (auto-filled if connected)
  - Google Scholar URL
  - ResearchGate URL
  - Resume upload (PDF)
  - Cover letter textarea
  - Supporting documents upload (multiple files)
- Auto-score display (calculated in real-time)
- Score breakdown tooltip
- Submit button
- Current status display (if already submitted)

**API Calls:**
- `POST /api/v1/users/verification-requests/` - Submit request
- `GET /api/v1/users/verification/status/` - Check current status

**Auto-Score Calculation Display:**
- ORCID Connected: +30 points ✓
- Institutional Email: +20 points
- Google Scholar: +15 points
- ResearchGate: +15 points
- Resume: +10 points
- Cover Letter: +10 points
- **Total: 0-100 points**

---

### 11. Verification Status Page `/verification/status`  **Phase 3 - Ready**
**Purpose:** Track verification request progress
**Backend Status:** Full workflow with admin approval/rejection

**Components:**
- Status badge (Pending, Approved, Rejected, Info Requested)
- Request details summary
- Auto-score display
- Timeline/stepper showing progress
- Admin feedback section (if rejected or info requested)
- Response form (if info requested):
  - Response textarea
  - Additional documents upload
  - Submit response button
- Withdraw request button (if pending)

**API Calls:**
- `GET /api/v1/users/verification-requests/my_requests/`
- `POST /api/v1/users/verification-requests/:id/respond/` - Respond to admin
- `POST /api/v1/users/verification-requests/:id/withdraw/` - Cancel request

---

### 12. Email Preferences Page `/settings/email`  **Phase 3 - Ready**
**Purpose:** Manage email notification preferences
**Backend Status:** 14 email types with full preference management

**Components:**
- Master toggle (Enable/Disable all notifications)
- Preference categories with individual toggles:
  - **Account Activity:**
    - Login notifications
    - Profile updates
    - Password changes
  - **Verification:**
    - Verification submitted confirmation
    - Verification approved
    - Verification rejected
    - Info requested from admin
  - **ORCID:**
    - ORCID connected
    - ORCID disconnected
  - **Submissions:**
    - Submission status changes
  - **Reviews:**
    - Review invitations
    - Review reminders
    - Review submissions
  - **Editorial:**
    - Editorial decisions
- Save button
- "Toggle All" button

**API Calls:**
- `GET /api/v1/notifications/email-preferences/`
- `PATCH /api/v1/notifications/email-preferences/:id/`
- `POST /api/v1/notifications/email-preferences/:id/toggle_all/`

---

### 13. Email Log Page `/settings/email-log`  **Phase 3 - Ready**
**Purpose:** View sent email history
**Backend Status:** Complete email logging with statistics

**Components:**
- Email list table:
  - Date/time
  - Email type badge
  - Subject
  - Status badge (Sent, Pending, Failed, Delivered, Opened)
  - View details button
- Filter dropdowns:
  - Status filter
  - Template type filter
- Search bar (by subject)
- Pagination
- Email statistics summary card
- View email modal (shows full email content)

**API Calls:**
- `GET /api/v1/notifications/email-logs/` - List emails
- `GET /api/v1/notifications/email-logs/:id/` - Email details
- `GET /api/v1/notifications/email-logs/user_stats/` - Statistics

---

##  AUTHOR PAGES

### 14. Author Dashboard `/author/dashboard`  
**Purpose:** Author-specific overview
**Backend Status:** Complete submission management system

**Components:**
- Submissions overview cards:
  - Draft submissions (count)
  - Under review (count)
  - Revision required (count)
  - Accepted (count)
- Submissions table with columns:
  - Title
  - Journal
  - Status badge
  - Submission date
  - Last updated
  - Actions dropdown
- "New Submission" button
- Quick filters (by status, journal)
- Search bar

**API Calls:**
- `GET /api/v1/submissions/?corresponding_author=me`

---

### 15. New Submission Page `/author/submit`  
**Purpose:** Create new manuscript submission
**Backend Status:** Full submission workflow + file management

**Components:**
- Multi-step wizard:
  
  **Step 1: Journal Selection**
  - Journal dropdown (searchable)
  - Selected journal info display
  - Submission guidelines preview
  
  **Step 2: Manuscript Information**
  - Title input (500 chars)
  - Abstract textarea
  - Keywords input (multi-tag)
  - Review type selection (Single Blind, Double Blind, Open)
  - Subject area selection
  - Funding information textarea
  - Ethics declarations checkboxes
  
  **Step 3: Authors**
  - Corresponding author info (auto-filled)
  - Add co-authors section:
    - Search existing users
    - Manual entry (name, email, institution, ORCID)
    - Contribution role dropdown
  - Author order management (drag-and-drop)
  - Author list preview
  
  **Step 4: Document Upload**
  - Manuscript file upload (PDF, DOCX)
  - Supplementary files upload (multiple)
  - Cover letter upload
  - File type badges
  - Upload progress bars
  - File validation messages
  
  **Step 5: Review & Submit**
  - All information preview
  - Edit buttons for each section
  - Terms acceptance checkbox
  - "Save as Draft" button
  - "Submit for Review" button

**API Calls:**
- `GET /api/v1/journals/` - List journals
- `POST /api/v1/submissions/` - Create draft
- `PATCH /api/v1/submissions/:id/` - Update draft
- `POST /api/v1/submissions/:id/add_author/` - Add co-author
- `DELETE /api/v1/submissions/:id/authors/:profile_id/` - Remove co-author
- `POST /api/v1/files/upload/:document_id/` - Upload files
- `POST /api/v1/submissions/:id/submit/` - Final submission

---

### 16. Submission Details Page `/author/submissions/:id`  **Phase 2 & 4 - Ready**
**Purpose:** View submission details and status
**Backend Status:** Submission + review + decision APIs complete

**Components:**
- Submission header:
  - Title
  - Submission number
  - Status badge
  - Journal name
  - Submission date
- Status timeline/tracker
- Manuscript information section
- Authors list
- Uploaded documents section:
  - Document cards with:
    - File name
    - File type badge
    - Upload date
    - Version number
    - Download button
    - Preview button (for PDFs)
- Reviews section (if available):
  - Review status badges
  - Reviewer comments (anonymized)
  - Scores display
- Editorial decision section (if available):
  - Decision badge
  - Decision letter
  - Revision requirements (if applicable)
- Action buttons (context-dependent):
  - Edit (if draft)
  - Withdraw submission
  - Upload revision (if revision required)
- Activity log accordion

**API Calls:**
- `GET /api/v1/submissions/:id/`
- `GET /api/v1/submissions/:id/authors/`
- `GET /api/v1/files/download/:version_id/` - Download file
- `GET /api/v1/files/preview/:version_id/` - Preview file
- `GET /api/v1/reviews/?submission=:id` - View reviews (if permitted)
- `GET /api/v1/reviews/decisions/?submission=:id` - Editorial decision
- `POST /api/v1/submissions/:id/withdraw/` - Withdraw

---

### 17. Revision Submission Page `/author/revisions/:round_id`  **Phase 4 - Ready**
**Purpose:** Submit revised manuscript
**Backend Status:** Complete revision round system with deadlines

**Components:**
- Revision requirements display:
  - Editorial decision letter
  - Reviewer comments
  - Required changes checklist
  - Deadline countdown
- Response form:
  - Response to reviewers textarea
  - Point-by-point response section
- Updated manuscript upload
- Track changes document upload
- Supplementary files upload
- Revision notes textarea
- Submit revision button

**API Calls:**
- `GET /api/v1/reviews/revision-rounds/:id/`
- `POST /api/v1/reviews/revision-rounds/:id/submit/` - Submit revision

---

##  REVIEWER PAGES

### 18. Reviewer Dashboard `/reviewer/dashboard`  **Phase 4 - Ready**
**Purpose:** Reviewer's review management hub
**Backend Status:** Complete review assignment system

**Components:**
- Review invitations cards:
  - Pending invitations (count)
  - Accepted reviews (count)
  - Completed reviews (count)
  - Overdue reviews (count + warning)
- Review assignments table:
  - Submission title (anonymized if double-blind)
  - Journal name
  - Status badge
  - Due date (with countdown)
  - Accept/Decline buttons (if pending)
  - Review button (if accepted)
  - Days remaining indicator
- Quick filters (by status, journal)
- Availability toggle (open to new reviews)

**API Calls:**
- `GET /api/v1/reviews/assignments/?reviewer=me`

---

### 19. Review Invitation Page `/reviewer/invitations/:id`  **Phase 4 - Ready**
**Purpose:** Review assignment details and accept/decline
**Backend Status:** Accept/decline workflow fully functional

**Components:**
- Invitation details:
  - Submission title (based on review type)
  - Abstract (if single-blind or open)
  - Journal name
  - Editor's invitation message
  - Due date
  - Review round number
- Submission metadata display
- Conflict of interest declaration
- Accept/Decline buttons
- Decline reason textarea (if declining)

**API Calls:**
- `GET /api/v1/reviews/assignments/:id/`
- `POST /api/v1/reviews/assignments/:id/accept/` - Accept invitation
- `POST /api/v1/reviews/assignments/:id/decline/` - Decline with reason

---

### 20. Review Submission Page `/reviewer/review/:assignment_id`  **Phase 4 - Ready**
**Purpose:** Submit peer review
**Backend Status:** Review forms, scores, recommendations all working

**Components:**
- Submission information section:
  - Title (anonymized if needed)
  - Abstract
  - Manuscript download button
  - Supplementary files list
- Review form (dynamic based on journal template):
  - Recommendation dropdown:
    - Accept
    - Minor Revision
    - Major Revision
    - Reject
  - Confidence level (Low, Medium, High)
  - Structured scores (sliders 1-10):
    - Originality
    - Methodology
    - Results & Discussion
    - Clarity & Organization
    - Significance
  - Review text textarea (for authors)
  - Confidential comments textarea (for editors only)
  - Strengths section
  - Weaknesses section
  - Specific comments section
- Review attachments upload
- Save draft button
- Submit review button

**API Calls:**
- `GET /api/v1/reviews/assignments/:id/`
- `GET /api/v1/files/download/:version_id/` - Download manuscript
- `POST /api/v1/reviews/` - Submit review
- `PATCH /api/v1/reviews/:id/` - Update draft review

**Review Submission Payload:**
```json
{
  "assignment": "uuid",
  "recommendation": "MINOR_REVISION",
  "confidence_level": "HIGH",
  "scores": {
    "originality": 8,
    "methodology": 7,
    "results": 8,
    "clarity": 7,
    "significance": 9
  },
  "review_text": "Detailed feedback...",
  "confidential_comments": "For editor only..."
}
```

---

### 21. Completed Reviews Page `/reviewer/completed`  **Phase 4 - Ready**
**Purpose:** View past reviews
**Backend Status:** Review history and statistics available

**Components:**
- Completed reviews list:
  - Submission title
  - Journal
  - Review date
  - Recommendation badge
  - View review button
- Filter options (by journal, date range)
- Review statistics:
  - Total reviews completed
  - Average review time
  - Reviews by recommendation type (pie chart)

**API Calls:**
- `GET /api/v1/reviews/?reviewer=me&status=COMPLETED`

---

##  EDITOR PAGES

### 22. Editor Dashboard `/editor/dashboard`  **Phase 2 & 4 - Ready**
**Purpose:** Editorial management hub
**Backend Status:** Journal + submission + review management complete

**Components:**
- Journal selector dropdown (if managing multiple)
- Quick stats cards:
  - New submissions (count)
  - Under review (count)
  - Awaiting decision (count)
  - Pending revisions (count)
- Submissions requiring attention list
- Recent activity feed
- Performance metrics charts:
  - Submission volume (line chart)
  - Average review time
  - Decision distribution (pie chart)

**API Calls:**
- `GET /api/v1/journals/?editor=me` - Managed journals
- `GET /api/v1/submissions/?journal=:id` - Journal submissions
- `GET /api/v1/journals/:id/statistics/`

---

### 23. Submissions Management Page `/editor/submissions`  
**Purpose:** Manage all submissions for journal
**Backend Status:** Advanced filtering and search operational

**Components:**
- Submissions table:
  - Submission number
  - Title
  - Author name
  - Status badge
  - Submission date
  - Days in current status
  - Assigned reviewers count
  - Actions dropdown
- Advanced filters:
  - Status filter (multi-select)
  - Date range picker
  - Reviewer assignment status
  - Sort options
- Search bar (title, author, submission number)
- Bulk actions dropdown
- Export to CSV button
- Column visibility settings

**API Calls:**
- `GET /api/v1/submissions/?journal=:id&status=&search=`

---

### 24. Submission Editorial View `/editor/submissions/:id`  **Phase 4 - Ready**
**Purpose:** Comprehensive submission management
**Backend Status:** Full editorial workflow implemented

**Components:**
- Submission header with status
- Tabbed interface:
  
  **Tab 1: Manuscript**
  - Full submission details
  - Authors list
  - Documents with preview
  - Metadata display
  
  **Tab 2: Reviewers**
  - Assigned reviewers list:
    - Reviewer name
    - Status badge
    - Due date
    - Reminder button
    - Remove reviewer button
  - Add reviewers section:
    - Reviewer search/recommendation
    - Invitation message textarea
    - Due date picker
    - Assign button
  - Reviewer recommendations (if applicable)
  
  **Tab 3: Reviews**
  - Submitted reviews display:
    - Reviewer ID (anonymized if needed)
    - Recommendation badge
    - Scores display (radar chart)
    - Review text
    - Confidential comments
    - Review date
  - Reviews summary dashboard
  
  **Tab 4: Decision**
  - Decision form:
    - Decision type dropdown:
      - Accept
      - Reject
      - Minor Revision
      - Major Revision
    - Decision letter editor (rich text)
    - Revision deadline picker (if revision)
    - Additional comments
    - Send decision button
  - Previous decisions history (if revision round)
  
  **Tab 5: History**
  - Complete activity timeline
  - Status changes log
  - Email communications log

**API Calls:**
- `GET /api/v1/submissions/:id/`
- `GET /api/v1/reviews/assignments/?submission=:id` - List reviewers
- `POST /api/v1/reviews/assignments/` - Assign reviewer
- `POST /api/v1/reviews/assignments/:id/send_reminder/` - Reminder
- `GET /api/v1/reviews/reviewer-recommendations/?submission=:id` - Get recommendations
- `GET /api/v1/reviews/?submission=:id` - View reviews
- `POST /api/v1/reviews/decisions/` - Make decision
- `POST /api/v1/reviews/decisions/:id/send_letter/` - Send decision letter

---

### 25. Reviewer Search Page `/editor/reviewers/search`  **Phase 4 - Ready**
**Purpose:** Find suitable reviewers
**Backend Status:** Reviewer search with expertise matching (basic ML placeholder ready for Phase 5 enhancement)

**Components:**
- Search interface:
  - Keyword search (expertise areas)
  - Subject filter
  - Availability filter
  - Workload filter (reviews currently assigned)
  - Institution filter
- Reviewer cards:
  - Name and institution
  - Expertise areas (tags)
  - ORCID badge (if connected)
  - Current workload (X active reviews)
  - Average review time
  - Reviews completed (count)
  - Recommendation score (if ML enabled)
  - Invite button
- Saved reviewers list
- Recently used reviewers

**API Calls:**
- `GET /api/v1/reviews/reviewer-search/?expertise=&availability=`
- `GET /api/v1/reviews/reviewer-recommendations/?submission=:id`

---

### 26. Review Invitations Management `/editor/invitations`  **Phase 4 - Ready**
**Purpose:** Track all review invitations
**Backend Status:** Complete invitation tracking with reminders

**Components:**
- Invitations table:
  - Reviewer name
  - Submission title
  - Invitation date
  - Status badge (Pending, Accepted, Declined)
  - Due date
  - Actions (Remind, Cancel)
- Status filter tabs
- Reminder automation settings
- Bulk reminder button

**API Calls:**
- `GET /api/v1/reviews/assignments/?journal=:id`
- `POST /api/v1/reviews/assignments/:id/send_reminder/`

---

### 27. Editorial Decisions Page `/editor/decisions`  **Phase 4 - Ready**
**Purpose:** View and manage all editorial decisions
**Backend Status:** Decision making system fully operational

**Components:**
- Decisions table:
  - Submission title
  - Decision type badge
  - Decision date
  - Decided by (editor name)
  - Current status
  - View decision button
- Filter by decision type
- Date range filter
- Decision analytics dashboard:
  - Acceptance rate
  - Average time to decision
  - Decisions by type (pie chart)

**API Calls:**
- `GET /api/v1/reviews/decisions/?journal=:id`
- `GET /api/v1/reviews/decisions/:id/` - View decision details

---

### 28. Revision Rounds Management `/editor/revisions`  **Phase 4 - Ready**
**Purpose:** Track revision submissions
**Backend Status:** Revision workflow with approve/reject complete

**Components:**
- Revision rounds table:
  - Submission title
  - Round number
  - Status badge (Pending, Submitted, Approved, Rejected)
  - Deadline
  - Days remaining
  - View/Review button
- Overdue revisions section (highlighted)
- Revision details modal:
  - Original decision and requirements
  - Author's response
  - Updated manuscript
  - Track changes document
  - Approve/Reject buttons

**API Calls:**
- `GET /api/v1/reviews/revision-rounds/?journal=:id`
- `GET /api/v1/reviews/revision-rounds/:id/`
- `POST /api/v1/reviews/revision-rounds/:id/approve/`
- `POST /api/v1/reviews/revision-rounds/:id/reject/`

---

### 29. Journal Settings Page `/editor/journal/:id/settings`  
**Purpose:** Configure journal settings
**Backend Status:** Journal settings CRUD complete

**Components:**
- Settings sections:
  
  **General Settings**
  - Review deadline (days)
  - Reminder schedule
  - Auto-assignment rules
  
  **Review Configuration**
  - Default review type
  - Review form template selector
  - Reviewer anonymity settings
  
  **Submission Guidelines**
  - Rich text editor for guidelines
  - File requirements
  - Formatting requirements
  
  **Email Templates**
  - Invitation template editor
  - Decision letter templates
  - Reminder template
  
  **Workflow Rules**
  - Minimum reviewers required
  - Decision criteria
  - Revision policies

**API Calls:**
- `GET /api/v1/journals/:id/get_settings/`
- `PUT /api/v1/journals/:id/update_settings/`

---

### 30. Staff Management Page `/editor/journal/:id/staff`  
**Purpose:** Manage editorial team
**Backend Status:** Staff assignment system operational

**Components:**
- Staff list table:
  - Name
  - Email
  - Role badge (Editor-in-Chief, Associate Editor, Managing Editor)
  - Assigned since
  - Active status toggle
  - Permissions
  - Edit/Remove buttons
- Add staff member form:
  - User search/select
  - Role dropdown
  - Permissions checkboxes
  - Add button
- Staff roles legend
- Pending invitations section

**API Calls:**
- `GET /api/v1/journals/:id/staff/`
- `POST /api/v1/journals/:id/add_staff/`
- `PATCH /api/v1/journals/:id/staff/:profile_id/update/`
- `DELETE /api/v1/journals/:id/staff/:profile_id/`

---

##  ADMIN PAGES

### 31. Admin Dashboard `/admin/dashboard`  **Phase 1-4 - Ready**
**Purpose:** System-wide administration overview
**Backend Status:** All admin APIs operational

**Components:**
- Global statistics cards:
  - Total users
  - Total journals
  - Total submissions
  - Active reviews
- System health indicators
- Recent activity feed
- User growth chart
- Submission trends chart
- Quick links to admin sections

**API Calls:**
- Various GET endpoints for statistics

---

### 32. User Management Page `/admin/users`  **Phase 1 - Ready**
**Purpose:** Manage all platform users
**Backend Status:** User CRUD with role management complete

**Components:**
- Users table:
  - Name
  - Email
  - Roles badges
  - Verification status
  - Account status (Active/Inactive)
  - Registration date
  - Last login
  - Actions dropdown
- Search and filters:
  - Search by name/email
  - Filter by role
  - Filter by verification status
  - Filter by active status
- User details modal:
  - Full profile info
  - Activity summary
  - Verification details
  - Edit user button
  - Deactivate/Activate button
- Bulk actions (export, email)

**API Calls:**
- `GET /api/v1/users/` - List all users (admin)
- `GET /api/v1/users/:id/` - User details
- `PATCH /api/v1/users/:id/` - Update user
- `DELETE /api/v1/users/:id/` - Deactivate user

---

### 33. Verification Requests Page `/admin/verifications`  **Phase 3 - Ready**
**Purpose:** Review and approve verification requests
**Backend Status:** Complete verification admin workflow

**Components:**
- Verification queue tabs:
  - Pending Review (default)
  - High Score (>70 auto-score)
  - Approved
  - Rejected
  - Info Requested
- Request cards/table:
  - User name and email
  - Requested role badge
  - Auto-score (with color coding)
  - Submission date
  - Review button
- Request details modal:
  - User information
  - ORCID status badge
  - Institutional details
  - Academic profiles (Google Scholar, ResearchGate)
  - Resume download button
  - Cover letter display
  - Supporting documents list
  - Auto-score breakdown
  - Admin notes textarea
  - Action buttons:
    - Approve
    - Reject (with reason)
    - Request Info (with question)
- Bulk approve for high scores

**API Calls:**
- `GET /api/v1/users/admin/verifications/pending_review/`
- `GET /api/v1/users/admin/verifications/high_score/`
- `GET /api/v1/users/admin/verifications/:id/`
- `POST /api/v1/users/admin/verifications/:id/approve/`
- `POST /api/v1/users/admin/verifications/:id/reject/`
- `POST /api/v1/users/admin/verifications/:id/request_info/`

---

### 34. Journal Management Page `/admin/journals`  
**Purpose:** Manage all journals in system
**Backend Status:** Journal admin CRUD operational

**Components:**
- Journals list:
  - Title and short name
  - ISSN numbers
  - Publisher
  - Active status toggle
  - Accepting submissions toggle
  - Editor-in-Chief name
  - Submission count
  - Actions (Edit, View, Delete)
- Create journal button
- Journal form modal:
  - Title
  - Short name
  - Publisher
  - ISSN (print and online)
  - Description
  - Website URL
  - Contact email
  - Active status
  - Accepting submissions
- Search and filter options

**API Calls:**
- `GET /api/v1/journals/` (admin sees all)
- `POST /api/v1/journals/` - Create journal
- `PATCH /api/v1/journals/:id/` - Update journal
- `DELETE /api/v1/journals/:id/` - Delete journal

---

### 35. Email Templates Management `/admin/email-templates`  **Phase 3 - Ready**
**Purpose:** Manage system email templates
**Backend Status:** Template management system complete

**Components:**
- Templates list:
  - Template name
  - Template type
  - Last updated
  - Active status toggle
  - Edit button
- Template editor modal:
  - Template name
  - Template type (readonly)
  - Subject line (with variables)
  - HTML body editor (rich text)
  - Text body (auto-generated)
  - Available variables reference
  - Preview button
  - Test email button
  - Save button

**API Calls:**
- `GET /api/v1/notifications/email-templates/`
- `PATCH /api/v1/notifications/email-templates/:id/`

---

### 36. Email Logs (Admin) `/admin/email-logs`  **Phase 3 - Ready**
**Purpose:** Monitor all system emails
**Backend Status:** Email logging with statistics operational

**Components:**
- Email logs table:
  - Recipient
  - User name (if linked)
  - Template type
  - Status badge
  - Sent date
  - Delivered date
  - Error message (if failed)
  - View button
- Global email statistics:
  - Total sent
  - Success rate
  - Failed emails count
  - By template type breakdown
- Filters:
  - Date range
  - Status
  - Template type
  - Recipient search
- Email detail modal:
  - Full email content preview
  - Delivery timeline
  - Error details (if failed)
  - Resend button (if failed)

**API Calls:**
- `GET /api/v1/notifications/email-logs/` (admin access)
- `GET /api/v1/notifications/email-logs/stats/`
- `GET /api/v1/notifications/email-logs/:id/`

---

---

#  FUTURE PAGES (DO NOT BUILD YET - Backend Not Ready)

These pages are planned for Phases 5-7 but the backend APIs are NOT implemented yet. Document them for future reference but DO NOT start development.

---

## Other Pages (Backend not built till now)

### 37. System Analytics Page `/admin/analytics`
**Purpose:** Comprehensive platform analytics and reporting
**Backend Status:**  NOT IMPLEMENTED - Planned for Phase 6

**Components:**

**Header Section:**
- Page title: "Analytics Dashboard"
- Date range selector dropdown:
  - Presets: Last 7 days, Last 30 days, Last 90 days, Last year, Custom
  - Custom date picker (from/to dates)
  - Apply button
- Export dropdown:
  - Export as PDF
  - Export as Excel
  - Export as CSV
- Real-time update toggle

**Key Metrics Cards (Grid Layout):**
- Total Users card:
  - Current count
  - Growth percentage vs previous period
  - Mini sparkline chart
  - Breakdown: Authors, Reviewers, Editors
- Total Submissions card:
  - Current count
  - Growth percentage
  - Status breakdown (Draft, Under Review, Accepted, etc.)
- Active Reviews card:
  - Current count
  - Completion rate
  - Average time to complete
- Publication Rate card:
  - Accepted vs Total submissions
  - Acceptance rate percentage
  - Trend indicator

**User Analytics Section:**
- User registration trend (line chart):
  - X-axis: Time periods
  - Y-axis: Number of registrations
  - Filters: By role
  - Hover tooltip with exact numbers
- User activity heatmap:
  - Days of week vs hours
  - Color intensity for activity level
- User geographic distribution (map or chart):
  - By country
  - Top 10 countries list

**Submission Analytics Section:**
- Submissions over time (multi-line chart):
  - Lines for different statuses
  - Trend lines
  - Toggle visibility per status
- Submission by journal (bar chart):
  - Horizontal bars
  - Sorted by volume
  - Click to drill down
- Time in each status (funnel chart):
  - Draft → Submitted → Under Review → Decision
  - Average days in each stage
  - Drop-off rates

**Review Analytics Section:**
- Review completion rate (gauge/donut chart):
  - Percentage completed on time
  - Overdue count
  - Pending count
- Average review time (metric + chart):
  - Overall average
  - By journal comparison
  - Trend over time
- Reviewer performance table:
  - Top 10 reviewers
  - Reviews completed
  - Average time
  - Quality score (if available)

**Editorial Decision Analytics:**
- Decision distribution (pie chart):
  - Accept
  - Minor Revision
  - Major Revision
  - Reject
  - Percentages and counts
- Time to decision (box plot or histogram):
  - Distribution of days
  - Median, average, min, max
- Decision trends by journal (stacked area chart):
  - Compare journals
  - Acceptance rates over time

**Journal Performance Section:**
- Journal comparison table:
  - Journal name
  - Total submissions
  - Acceptance rate
  - Average review time
  - Active reviewers
  - Publications
  - Sort by any column
- Journal health indicators:
  - Green: healthy metrics
  - Yellow: needs attention
  - Red: action required

**System Health Metrics:**
- API response times (line chart)
- Error rates (line chart)
- Email delivery rates (gauge)
- Storage usage (progress bar)

**Export & Scheduling:**
- Schedule recurring reports:
  - Frequency dropdown (daily, weekly, monthly)
  - Recipients email list
  - Report type selection
  - Save schedule button
- Custom report builder:
  - Select metrics
  - Choose visualization
  - Generate button

**API Calls (Planned for Phase 6):**
```javascript
// These endpoints will be available
GET /api/v1/analytics/overview/?start_date=&end_date=
GET /api/v1/analytics/users/registrations/
GET /api/v1/analytics/users/activity/
GET /api/v1/analytics/submissions/trends/
GET /api/v1/analytics/submissions/by-journal/
GET /api/v1/analytics/submissions/status-duration/
GET /api/v1/analytics/reviews/completion-rate/
GET /api/v1/analytics/reviews/average-time/
GET /api/v1/analytics/decisions/distribution/
GET /api/v1/analytics/decisions/time-to-decision/
GET /api/v1/analytics/journals/performance/
GET /api/v1/analytics/export/?format=pdf&start_date=&end_date=
POST /api/v1/analytics/schedules/ - Schedule recurring reports
```

**Filters Available:**
- Date range (all charts respect this)
- Journal filter (multi-select)
- Status filter
- Role filter (for user analytics)
- Export format

---

### 38. Audit Log Page `/admin/audit-log` 
**Purpose:** Comprehensive system activity tracking and compliance logging
**Backend Status:**  NOT IMPLEMENTED till now

**Components:**

**Header Section:**
- Page title: "System Audit Log"
- Date range selector (last 24 hours, 7 days, 30 days, custom)
- Search bar: "Search by user, resource ID, IP address..."
- Export button (CSV, JSON)
- Real-time mode toggle (auto-refresh)

**Filter Panel (Collapsible Sidebar):**
- **Actor Filters:**
  - User search/select (autocomplete)
  - Actor type dropdown: User, System, API, Scheduled Task
  - Role filter (Admin, Editor, Reviewer, Author)
  
- **Action Filters:**
  - Action type multi-select: CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, APPROVE, REJECT, ASSIGN, SUBMIT
  - Severity level: INFO, WARNING, ERROR, CRITICAL
  
- **Resource Filters:**
  - Resource type: User, Profile, Submission, Review, Journal, Document, Email, Settings
  - Resource ID input
  
- **Network Filters:**
  - IP address input
  - Country filter

**Main Activity Log Table:**
- **Timestamp** (sortable) - Date/time, relative time, timezone
- **Actor** (clickable) - Avatar, name, email, actor type badge
- **Action** (with icon) - Action type badge, description, severity
- **Resource** (clickable) - Type icon, name/title, ID, link to resource
- **IP Address** - IP, country flag, location (hover)
- **Status** - Success/Failed/Partial badge
- **Details** - Expandable view button
- **Actions** - View full, copy, export

**Expandable Row Details:**
- Before/After comparison (diff view)
- Request details (method, path, headers, body)
- Response details (status, time, errors)
- Context (session ID, user agent, geo-location)
- Related events timeline

**Quick Stats Summary:**
- Total events today
- Failed actions count
- Unique users active
- Most active user
- Most modified resource type

**Alert Rules Section:**
- Create alert rules (condition builder)
- Alert actions (email, dashboard, webhook)
- Active alerts list
- Acknowledge button

**API Calls (Planned for Phase 6):**
```javascript
GET /api/v1/audit-logs/?page=&filters=
GET /api/v1/audit-logs/:id/ - Full details
GET /api/v1/audit-logs/stats/
GET /api/v1/audit-logs/export/?format=csv
GET /api/v1/audit-logs/anomalies/
POST /api/v1/audit-logs/alert-rules/
GET /api/v1/audit-logs/alerts/
```

---

### 39. ML Reviewer Recommendations Page 
**Purpose:** AI-powered intelligent reviewer matching and suggestions
**Backend Status:** Basic search exists (Phase 4), ML enhancement planned for Phase 5

**Components:**

**Header Section:**
- Page title: "AI Reviewer Recommendations"
- Submission selector dropdown (current submission)
- Confidence threshold slider (show matches above X%)
- Refresh recommendations button

**Submission Context Panel:**
- **Manuscript Information:**
  - Title display
  - Abstract (truncated, expandable)
  - Keywords/tags
  - Subject areas
  - Research field
  
- **Required Expertise:**
  - Auto-extracted keywords from abstract
  - Topic modeling results
  - Research methodology tags
  - Domain-specific terminology

**ML Recommendation Algorithm Info:**
- Algorithm explanation tooltip
- Factors considered:
  - Expertise area matching (semantic similarity)
  - Publication history in similar topics
  - Previous review quality scores
  - Current workload
  - Review completion rate
  - Response time history
  - Geographic diversity
  - Institution conflicts

**Recommended Reviewers List:**

**Each Reviewer Card Contains:**
- **Match Score (Prominent):**
  - Percentage (e.g., 92% match)
  - Color-coded bar (green = excellent, yellow = good, gray = moderate)
  - Score breakdown button
  
- **Reviewer Profile:**
  - Avatar/photo
  - Name
  - Institution
  - Country flag
  - ORCID badge (if connected)
  - Profile completeness indicator
  
- **Expertise Matching:**
  - Matching keywords (highlighted)
  - Expertise areas (tags)
  - Semantic similarity score
  - Shared research topics
  
- **Performance Metrics:**
  - Reviews completed: X
  - Average review time: X days
  - Completion rate: X%
  - Quality score: X/10 (if available)
  - Last review date
  
- **Current Status:**
  - Current workload badge (e.g., "2 active reviews")
  - Availability indicator (Available/Busy/Unknown)
  - Recent activity indicator
  
- **Conflict of Interest Check:**
  - Institution match warning
  - Co-authorship check
  - Previous conflicts indicator
  
- **Similar Past Reviews:**
  - "Reviewed 3 similar submissions"
  - Links to past review summaries
  - Average recommendation type
  
- **Actions:**
  - "Invite as Reviewer" button (primary)
  - "View Full Profile" link
  - "Save to Favorites" star icon
  - "Not Suitable" dismiss button

**Score Breakdown Modal:**
When clicking score breakdown:
- **Expertise Match:** 40% weight
  - Keyword overlap: 8/10
  - Semantic similarity: 0.89
  - Topic modeling match: High
  
- **Performance History:** 30% weight
  - Review completion rate: 95%
  - Average review time: 18 days
  - Quality score: 8.5/10
  
- **Availability:** 20% weight
  - Current workload: Light (2 reviews)
  - Response rate: 85%
  - Accepts invitations: Often
  
- **Diversity Factors:** 10% weight
  - Geographic diversity
  - Institution variety
  - Career stage balance

**Filter & Sort Panel:**
- **Filters:**
  - Minimum match score slider
  - Maximum current workload
  - Institution filter (exclude specific)
  - Country filter
  - ORCID required checkbox
  - Availability only checkbox
  
- **Sort Options:**
  - Best match (default)
  - Fastest average review time
  - Most reviews completed
  - Highest quality score
  - Most available
  - Recent activity

**Bulk Actions:**
- Select multiple reviewers (checkboxes)
- "Invite Selected" button
- "Add All to Shortlist" button
- Export recommendations list

**Alternative Suggestions Section:**
- "Similar reviewers you might consider"
- Lower confidence matches (60-70%)
- Reviewers with partial expertise match

**Shortlist Panel (Sidebar):**
- Saved reviewer candidates
- Drag to reorder priority
- Remove from shortlist
- Send invitations to all

**Invitation Preview:**
- Before inviting, preview:
  - Reviewer name
  - Estimated match quality
  - Suggested due date
  - Custom invitation message (editable)
  - Send button

**Feedback & Learning:**
- "Was this recommendation helpful?" thumbs up/down
- "Report incorrect match" button
- System learns from:
  - Accepted/declined invitations
  - Completed review quality
  - Editor override decisions

**Explanation Panel (Collapsible):**
- "How AI Matching Works"
- Methodology explanation
- Data sources used
- Privacy information
- Accuracy metrics

**API Calls (Planned for Phase 5):**
```javascript
// These ML endpoints will be available in Phase 5
POST /api/v1/ml/reviewer-recommendations/ - Get AI recommendations
Body: {
  "submission_id": "uuid",
  "min_confidence": 0.7,
  "max_results": 20,
  "exclude_reviewers": ["uuid1", "uuid2"]
}

Response: {
  "recommendations": [
    {
      "reviewer_id": "uuid",
      "reviewer_name": "Dr. Jane Smith",
      "match_score": 0.92,
      "score_breakdown": {
        "expertise_match": 0.89,
        "performance_score": 0.95,
        "availability_score": 0.88
      },
      "matching_keywords": ["machine learning", "NLP"],
      "current_workload": 2,
      "average_review_time_days": 18,
      "completion_rate": 0.95,
      "conflicts": []
    }
  ],
  "algorithm_version": "1.2.3",
  "generated_at": "timestamp"
}

GET /api/v1/ml/reviewer-recommendations/:id/explain/ - Explain score
GET /api/v1/ml/reviewer-profile-similarity/?reviewer1=&reviewer2=
POST /api/v1/ml/reviewer-recommendations/feedback/ - Submit feedback
GET /api/v1/ml/models/reviewer-matching/metrics/ - Model performance
```

**Comparison View:**
- Select 2-3 reviewers to compare side-by-side
- Table comparing all metrics
- Highlighting differences
- "Choose Best" button

---

### 40. Plagiarism Check Interface **Phase 5 - Not Built**
**Purpose:** iThenticate/Turnitin plagiarism detection integration
**Backend Status:** NOT IMPLEMENTED till now

**Components:**

**Submission Plagiarism Check Page:**

**Header Section:**
- Page title: "Plagiarism Check"
- Submission info (title, ID, author)
- Check status badge
- Last checked date/time

**Check Initiation Panel:**
- **For New Checks:**
  - "Run Plagiarism Check" button (primary)
  - Estimated time display (e.g., "~5-10 minutes")
  - Credit cost display (if applicable)
  - Include/exclude bibliography checkbox
  - Include/exclude quotes checkbox
  - Repository selection (if multiple available)
  
- **For Existing Checks:**
  - "View Report" button
  - "Re-check" button
  - Previous check results summary

**Check Progress:**
- Progress bar with stages:
  - Uploading document ✓
  - Processing text ⏳
  - Comparing against databases...
  - Generating report...
- Cancel check button
- Status messages

**Similarity Report Dashboard:**

**Overall Similarity Score (Prominent):**
- Large percentage display (e.g., "23%")
- Color-coded severity:
  - Green: 0-10% (Acceptable)
  - Yellow: 11-25% (Review Needed)
  - Orange: 26-50% (Concerning)
  - Red: 50%+ (High Risk)
- Similarity index explanation tooltip
- Pass/Fail indicator (based on journal threshold)

**Similarity Breakdown:**
- **Matched Sources:**
  - Internet sources: X%
  - Publications: X%
  - Student papers: X%
  - Institutional repository: X%
  - Previous submissions: X%
  
- **Excluded Content:**
  - Bibliography: X%
  - Quotes: X%
  - Small matches (<8 words): X%

**Top Matching Sources List:**
- **Each Source Card:**
  - Source rank (#1, #2, etc.)
  - Match percentage (e.g., "8%")
  - Source type badge (Internet/Journal/Book)
  - Source title/URL
  - Author (if available)
  - Publication date
  - Match word count
  - "View Matches" button
  - "Exclude Source" option

**Document Viewer with Highlights:**
- **Split View:**
  - Left: Your document
  - Right: Matched source document
  
- **Text Highlighting:**
  - Color-coded by source (different color per source)
  - Hover to see source info tooltip
  - Click to view source details
  
- **Highlight Legend:**
  - Source color mapping
  - Toggle visibility per source
  - "Show only high matches" filter
  
- **Navigation:**
  - Jump to next/previous match
  - Go to specific page
  - Search within document
  - Zoom in/out controls

**Match Details Panel:**
When clicking a highlighted section:
- Matched text display
- Source information
- Match type (exact, paraphrase, translated)
- Context from source
- "This is acceptable" checkbox (with reason)
- Add to ignore list

**Acceptable Matches Section:**
- Mark sections as acceptable:
  - Common phrases
  - Standard methodology
  - Widely used definitions
  - Author's own previous work
  - Properly cited content
- Add notes for editor/reviewer

**Actions & Export:**
- **Export Options:**
  - Download PDF report
  - Download detailed report (with sources)
  - Export summary (Excel/CSV)
  - Share report link (time-limited)
  
- **Actions:**
  - "Flag for Editor Review" button
  - "Request Author Revision" button
  - "Accept Report" button
  - "Dispute Match" button

**Comparison History:**
- Previous check results
- Similarity score trend chart
- Compare before/after revisions
- View changes between versions

**Settings:**
- Similarity threshold settings
- Auto-check on submission toggle
- Notification preferences
- Exclude sources list

**Editor Review Panel:**
- **For Editors:**
  - Overall assessment textarea
  - Recommendation dropdown:
    - Accept (low similarity)
    - Request minor clarification
    - Request revision
    - Reject (plagiarism confirmed)
  - Share report with author checkbox
  - Share report with reviewers checkbox
  - Internal notes (not visible to author)
  - Submit decision button

**Author View (Limited):**
- If shared by editor:
  - Overall similarity score
  - Matched sources (sanitized)
  - Highlighted document
  - Cannot see other submissions
  - Cannot export detailed report
  - Response submission form

**Batch Checking (Admin):**
- Select multiple submissions
- Run checks in queue
- Results table with similarity scores
- Priority queue management
- Bulk actions

**API Calls (Planned for Phase 5):**
```javascript
// These endpoints will be available in Phase 5
POST /api/v1/plagiarism/check/ - Initiate check
Body: {
  "submission_id": "uuid",
  "include_bibliography": false,
  "include_quotes": false,
  "repositories": ["internet", "publications"]
}

GET /api/v1/plagiarism/check/:id/status/ - Check progress
Response: {
  "status": "processing|completed|failed",
  "progress": 75,
  "stage": "comparing_databases",
  "estimated_time_remaining": 120
}

GET /api/v1/plagiarism/report/:id/ - Get full report
Response: {
  "overall_similarity": 23,
  "matched_sources": [
    {
      "source_id": "uuid",
      "similarity_percentage": 8,
      "source_type": "internet",
      "title": "...",
      "url": "...",
      "matches": [
        {
          "your_text": "...",
          "matched_text": "...",
          "word_count": 45,
          "page_number": 3,
          "match_type": "exact"
        }
      ]
    }
  ]
}

GET /api/v1/plagiarism/report/:id/document/?format=pdf - Export report
POST /api/v1/plagiarism/report/:id/exclude-source/ - Exclude source
POST /api/v1/plagiarism/report/:id/mark-acceptable/ - Mark section OK
GET /api/v1/plagiarism/submissions/:id/history/ - Check history
POST /api/v1/plagiarism/report/:id/share/ - Share with author/reviewers
```

**Integration Notes:**
- iThenticate API key required
- Turnitin alternative supported
- Credits/quota management
- Auto-check workflow integration
- Email notifications on completion

---

### 41. Live Document Editor **Not implemented**
**Purpose:** Collaborative real-time document editing 
**Backend Status:** NOT IMPLEMENTED - Planned for Phase 5

**Components:**

**Document Editor Page:**

**Header Section:**
- Document title (editable)
- Save status indicator (Saved/Saving/Draft)
- Version number
- Last edited by (user + timestamp)
- Share/Collaborate button
- Close editor button

**Toolbar**
- **Standard Editing Tools:**
  - Font selection
  - Font size
  - Bold, Italic, Underline
  - Text color, highlight color
  - Alignment options
  - Bullet lists, numbered lists
  - Indentation
  - Styles dropdown (Heading 1-6, Normal, etc.)
  
- **Document Tools:**
  - Insert table
  - Insert image
  - Insert chart
  - Insert equation (LaTeX support)
  - Insert citation
  - Insert cross-reference
  - Insert footnote/endnote
  
- **Review Tools:**
  - Track changes toggle
  - Accept/Reject changes
  - Add comment
  - Show/hide markup
  - Compare documents
  - Protect document
  
- **Collaboration Tools:**
  - Share document
  - See active collaborators
  - Chat panel toggle
  - Version history
  - Permissions

**Main Editor Canvas:**
- **Embedded Editor (OnlyOffice/Collabora iframe):**
  - Full WYSIWYG editing
  - Real-time rendering
  - Page view/layout
  - Ruler and margins
  - Zoom controls (50%-200%)
  
- **Format Support:**
  - DOCX (primary)
  - PDF export
  - TXT

**Collaboration Features:**

**Active Users Panel (Sidebar):**
- **User Indicators:**
  - Avatar/profile picture
  - Name
  - Online status (green dot)
  - Current cursor position (color-coded)
  - Current selection highlight
  - "Viewing" or "Editing" badge
  
- **User Actions:**
  - Follow user's cursor
  - Jump to user's position
  - Send direct message
  - Remove user (if owner)

**Real-time Cursors:**
- Color-coded cursor for each user
- Username label on cursor
- Selection highlighting per user
- Cursor movement animation

**Live Chat Panel (Collapsible):**
- Message thread
- Send message input
- @ mentions
- Emoji support
- File sharing in chat
- Chat history
- Notification badges

**Track Changes Mode:**
- **Change Tracking:**
  - Insertions (green highlight)
  - Deletions (red strikethrough)
  - Formatting changes
  - Author attribution
  - Timestamp on each change
  
- **Review Panel:**
  - List of all changes
  - Filter by author
  - Filter by change type
  - Accept/reject individual changes
  - Accept/reject all changes
  - Navigate to next/previous change
  
- **Change Details:**
  - Change author
  - Change timestamp
  - Change type
  - Original text
  - New text
  - Accept/reject buttons

**Comments System:**
- **Add Comment:**
  - Select text
  - Click "Add Comment" or Ctrl+Alt+M
  - Comment textarea
  - Mention users with @
  - Attach files
  - Post button
  
- **Comment Threads:**
  - Comment bubble in margin
  - Thread conversation
  - Reply to comments
  - Resolve/reopen comments
  - Edit own comments
  - Delete own comments
  - Highlight linked text
  
- **Comments Panel (Sidebar):**
  - All comments list
  - Filter: All/My comments/Mentions/Resolved
  - Sort: Newest/Oldest/Position
  - Search comments
  - Comment count badge
  - Navigate to comment in document

**Version History:**
- **Versions List:**
  - Version number/name
  - Saved date/time
  - Author
  - File size
  - Change description
  - "View" button
  - "Restore" button
  - "Compare" button
  
- **Version Comparison:**
  - Side-by-side view
  - Inline changes view
  - Diff highlighting
  - Navigate changes
  - Restore previous version option

**Sharing & Permissions:**
- **Share Dialog:**
  - Add collaborators (user search)
  - Role assignment:
    - Viewer (read-only)
    - Commenter (can comment)
    - Editor (full edit)
    - Owner (all permissions)
  - Link sharing toggle
  - Link permissions (anyone/team only)
  - Expiration date setting
  - Password protection
  - Download permission toggle
  - Print permission toggle
  
- **Current Collaborators:**
  - User list with roles
  - Change role dropdown
  - Remove user button
  - Resend invitation

**Auto-save & Sync:**
- Auto-save indicator (every 30 seconds)
- Manual save button
- Sync status badge
- Conflict resolution dialog
- Offline mode support (save locally)

**Document Actions Menu:**
- Download as DOCX
- Download as PDF
- Export to LaTeX
- Export to HTML
- Print document
- Email document
- Duplicate document
- Move to folder
- Delete document
- Document properties

**Citations & References:**
- **Citation Manager:**
  - Insert citation button
  - Citation style selector (APA, MLA, Chicago, etc.)
  - Reference library
  - Search references
  - Add manual reference
  - Import from DOI/PubMed
  - Generate bibliography
  
- **Bibliography:**
  - Auto-generated reference list
  - Update bibliography button
  - Format references
  - Sort references

**Templates:**
- Document templates library
- Journal-specific templates
- Apply template to document
- Save as template
- Template preview

**Keyboard Shortcuts Panel:**
- Ctrl+S: Save
- Ctrl+B: Bold
- Ctrl+I: Italic
- Ctrl+U: Underline
- Ctrl+Z: Undo
- Ctrl+Y: Redo
- Ctrl+F: Find
- Ctrl+H: Find & replace
- Ctrl+Alt+M: Add comment
- Show all shortcuts

**Notification Center:**
- New comments badge
- Mentions notification
- Changes requiring review
- Version saved notification
- Collaboration invites
- Permission changes

**API Calls (Planned for Phase 5):**
```javascript
// These endpoints will be available in Phase 5
POST /api/v1/documents/editor/open/ - Open document in editor
Body: {
  "document_id": "uuid",
  "mode": "edit|view"
}
Response: {
  "editor_url": "https://...",
  "token": "...",
  "permissions": ["read", "write", "comment"]
}

GET /api/v1/documents/:id/collaborators/ - Get collaborators
POST /api/v1/documents/:id/share/ - Share with user
PATCH /api/v1/documents/:id/collaborator/:user_id/ - Update permissions
DELETE /api/v1/documents/:id/collaborator/:user_id/ - Remove collaborator

GET /api/v1/documents/:id/versions/ - Version history
GET /api/v1/documents/:id/versions/:version_id/ - Get specific version
POST /api/v1/documents/:id/versions/:version_id/restore/ - Restore version

GET /api/v1/documents/:id/comments/ - Get all comments
POST /api/v1/documents/:id/comments/ - Add comment
PATCH /api/v1/documents/:id/comments/:comment_id/ - Edit comment
DELETE /api/v1/documents/:id/comments/:comment_id/ - Delete comment
POST /api/v1/documents/:id/comments/:comment_id/resolve/ - Resolve comment

GET /api/v1/documents/:id/changes/ - Get tracked changes
POST /api/v1/documents/:id/changes/:change_id/accept/ - Accept change
POST /api/v1/documents/:id/changes/:change_id/reject/ - Reject change

POST /api/v1/documents/:id/export/ - Export document
Body: { "format": "pdf|docx|latex|html" }

WebSocket: ws://localhost:8000/ws/document/:id/
// Real-time collaboration events:
// - user_joined
// - user_left
// - cursor_moved
// - text_changed
// - comment_added
// - chat_message
```

**Integration Requirements:**
- OnlyOffice Document Server or Collabora Online
- WebSocket server for real-time sync
- Storage for document versions
- Redis for session management

---

### 42. ROR/OpenAlex Integration Pages  **Phase 5 - Not Built**
**Purpose:** Research Organization Registry (ROR) & OpenAlex integration for data enrichment
**Backend Status:**  NOT IMPLEMENTED - Planned for Phase 5

**Components:**

**Institution Validator (During Registration/Profile Edit):**

**Institution Search Component:**
- **Search Input:**
  - "Search for your institution..." placeholder
  - Autocomplete dropdown
  - Search as you type (debounced)
  - Minimum 3 characters
  
- **Suggestions Dropdown:**
  - **Each Institution Item:**
    - Institution name (bold)
    - Country flag + country name
    - City
    - ROR ID badge
    - Type badge (University/Research Institute/Hospital/etc.)
    - Website link
    - Select button
  
- **No Results:**
  - "Institution not found"
  - "Enter manually" button
  - "Suggest new institution" link

**Selected Institution Display:**
- **Institution Card:**
  - Official name
  - Logo (from ROR)
  - Address
  - Country
  - Website (clickable)
  - ROR ID (with copy button)
  - Verified badge ✓
  - Change institution button
  
- **Validation Benefits:**
  - Auto-fill institution details
  - Verified affiliation badge
  - Institutional statistics
  - Conflict of interest detection

**Manual Entry Fallback:**
- Institution name input
- Country dropdown
- City input
- Website URL
- "Unverified" badge
- "Search again" button

---

**Author Profile Enrichment Page:**

**Profile Enrichment Dashboard:**

**Header:**
- Page title: "Enrich Your Profile"
- Sync status indicator
- Last synced timestamp
- Manual refresh button

**Data Source Connections:**
- **ORCID** (Phase 3 - Already Implemented ✓)
- **OpenAlex** (Phase 5 - New)
- **Google Scholar** (Phase 3 - Link only, Phase 5 - Full import)
- **ResearchGate** (Phase 3 - Link only, Phase 5 - Full import)
- **Scopus** (Phase 5 - New)
- **Web of Science** (Phase 5 - New)

**OpenAlex Profile Sync:**

**Search Author in OpenAlex:**
- **Search Form:**
  - Name input (pre-filled from profile)
  - Institution filter (from ROR)
  - ORCID filter (if connected)
  - Search button
  
- **Results List:**
  - **Each Author Result:**
    - Name
    - Institution(s)
    - ORCID (if available)
    - Publications count
    - Citations count
    - H-index
    - Match confidence score
    - "This is me" button
    - "Not me" button

**Confirm Author Match:**
- Selected author details
- Publication sample (5 most cited)
- Co-authors list
- Research topics
- "Confirm and Import" button
- "This isn't me" button

**Import Options:**
- **Select What to Import:**
  - Publications list
  - Citation metrics
  - Co-author network
  - Research topics
  - Institutional affiliations
  - Biography (if available)
  
- Import frequency:
  - One-time import
  - Auto-sync monthly
  - Auto-sync on profile view

**Imported Data Display:**

**Publications Section:**
- **Publication List Table:**
  - Title
  - Authors
  - Journal/Conference
  - Year
  - Citations count
  - DOI link
  - Open access badge
  - Edit button
  - Delete button (from profile, not from OpenAlex)
  
- **Filters:**
  - Year range slider
  - Publication type (Article, Conference, Book, etc.)
  - Journal filter
  - Sort: Citations/Year/Title
  
- **Actions:**
  - Add missing publication manually
  - Hide publication (not relevant)
  - Feature publication (show on profile)
  - Export publications list (BibTeX, RIS, CSV)

**Citation Metrics Dashboard:**
- **Metrics Cards:**
  - Total publications
  - Total citations
  - H-index
  - i10-index
  - Average citations per paper
  - Most cited paper
  
- **Citation Trend Chart:**
  - Line chart: Citations over time
  - Bar chart: Publications per year
  
- **Top Cited Papers:**
  - Top 10 list with citation counts
  - Link to full paper

**Co-Author Network:**
- **Network Visualization:**
  - Interactive graph/network diagram
  - Node size = publication count
  - Edge thickness = collaboration strength
  - Color = institution
  - Zoom/pan controls
  
- **Co-Authors List:**
  - Name
  - Institution
  - Joint publications count
  - ORCID link
  - "Suggest as reviewer" button (for their submissions)

**Research Topics:**
- **Topic Cloud:**
  - Word cloud or tag cloud
  - Size based on relevance
  - Click to filter publications
  
- **Topic List:**
  - Topic name
  - Publication count
  - Citation count
  - Edit/remove topic
  - Add custom topic

**Institutional History:**
- **Affiliations Timeline:**
  - Institution name (from ROR)
  - Start date
  - End date (if left)
  - Position/role
  - Current institution badge
  - Edit/add affiliation

---

**Institution Statistics Page (For Admin/Editors):**

**Institution Dashboard:**
- **Institution Search:** (ROR-powered)
- **Selected Institution Info:**
  - Name and logo
  - Location and website
  - ROR ID
  - Type and established year
  
- **Statistics Cards:**
  - Authors from this institution:
  - Submissions from this institution:
  - Reviewers from this institution:
  - Publications from this institution:
  - Average acceptance rate:
  
- **Research Output:**
  - Publications trend chart
  - Top research areas
  - Most active authors
  - Collaboration network

---

**Conflict of Interest Detection:**

**CoI Check Component:**
- **Automatic Detection:**
  - Same institution (ROR match)
  - Recent co-authorship (OpenAlex)
  - Shared publications in last 3 years
  - Common research grants (if available)
  - Advisor-advisee relationships
  
- **CoI Alert:**
  - Warning badge on reviewer assignment
  - Conflict details display
  - Override option (with justification)
  - Block assignment button

**CoI Review Page:**
- **For Submission:**
  - List potential reviewers
  - Show CoI indicators
  - Filter: Hide conflicted reviewers
  - "Why is this a conflict?" tooltip

---

**Institution Verification Admin:**

**For Admin Only:**
- **Unverified Institutions List:**
  - User-entered institution name
  - User who entered
  - Count of users with this institution
  - Search ROR button
  - Approve button
  - Merge with existing button

**ROR Integration Settings:**
- API key configuration
- Sync frequency
- Auto-validation toggle
- Data retention settings

**API Calls (Planned for Phase 5):**
```javascript
// ROR Institution Search
GET /api/v1/integrations/ror/search/?query=Stanford&country=US
Response: {
  "results": [
    {
      "id": "https://ror.org/00f54p054",
      "name": "Stanford University",
      "country": "United States",
      "city": "Stanford",
      "type": "Education",
      "website": "https://www.stanford.edu",
      "established": 1885,
      "logo": "url"
    }
  ]
}

GET /api/v1/integrations/ror/institution/:ror_id/ - Get full details

// OpenAlex Author Search
GET /api/v1/integrations/openalex/author/search/?name=&institution=&orcid=
Response: {
  "results": [
    {
      "id": "A1234567890",
      "display_name": "Jane Smith",
      "orcid": "0000-0002-1234-5678",
      "works_count": 145,
      "cited_by_count": 3420,
      "h_index": 28,
      "institutions": ["Stanford University"],
      "topics": ["Machine Learning", "NLP"]
    }
  ]
}

GET /api/v1/integrations/openalex/author/:id/ - Get author details
GET /api/v1/integrations/openalex/author/:id/works/ - Get publications
POST /api/v1/integrations/openalex/sync/ - Sync author data
Body: {
  "profile_id": "uuid",
  "openalex_id": "A1234567890",
  "import_options": ["publications", "metrics", "coauthors", "topics"]
}

GET /api/v1/integrations/openalex/institution/:id/stats/ - Institution stats

// Conflict of Interest
GET /api/v1/integrations/coi/check/ - Check potential conflicts
Body: {
  "author_id": "uuid",
  "reviewer_id": "uuid"
}
Response: {
  "has_conflict": true,
  "conflicts": [
    {
      "type": "same_institution",
      "details": "Both at Stanford University"
    },
    {
      "type": "coauthor",
      "details": "2 joint publications in last 3 years"
    }
  ]
}
```

**Benefits of Integration:**
- Verified institutional affiliations
- Automatic profile enrichment
- Publication tracking
- Citation metrics
- Conflict of interest detection
- Collaboration network visualization
- Research topic identification
- Institutional statistics

---

##  COMMON COMPONENTS

### Reusable UI Components

#### 1. **Status Badge**
**Props:** `status, type`  
**Variants:**
- Submission: DRAFT, SUBMITTED, UNDER_REVIEW, REVISION_REQUIRED, REVISED, ACCEPTED, REJECTED, WITHDRAWN, PUBLISHED
- Review: PENDING, ACCEPTED, DECLINED, COMPLETED, OVERDUE, CANCELLED
- Verification: UNVERIFIED, PENDING, GENUINE, SUSPICIOUS, FAKE
- Email: PENDING, SENT, FAILED, BOUNCED, DELIVERED, OPENED
- Decision: ACCEPT, REJECT, MINOR_REVISION, MAJOR_REVISION
**Color Coding:** Green (success), Yellow (warning), Red (error), Blue (info), Gray (neutral)

---

#### 2. **File Upload Component**
**Features:**
- Drag & drop area
- File type validation
- Size validation
- Upload progress bar
- Multiple file support
- Preview thumbnails
- Remove file button
**Props:** `accept, maxSize, multiple, onUpload`

---

#### 3. **Data Table Component**
**Features:**
- Sortable columns
- Pagination
- Row selection (checkboxes)
- Search/filter
- Column visibility toggle
- Export options
- Responsive design
**Props:** `columns, data, actions, filters, pagination`

---

#### 4. **Modal/Dialog Component**
**Variants:**
- Confirmation modal
- Form modal
- Detail view modal
- Full-screen modal
**Props:** `title, content, actions, size, closable`

---

#### 5. **Form Input Components**
- Text input
- Textarea
- Select/Dropdown (single & multi)
- Date picker
- File upload
- Rich text editor
- Tag input (multi-select)
- Checkbox/Radio
- Password input (with visibility toggle)
**All include:** Label, validation, error messages, help text

---

#### 6. **Toast/Notification Component**
**Types:** Success, Error, Warning, Info  
**Features:** Auto-dismiss, manual close, action buttons  
**Position:** Top-right, top-center, bottom-right

---

#### 7. **Loading Spinner**
**Variants:**
- Full page overlay
- Section loader
- Button spinner
- Inline loader
**Props:** `size, color, overlay`

---

#### 8. **Empty State Component**
**Use Cases:**
- No data found
- Search returned no results
- No permissions
- Feature coming soon
**Props:** `icon, title, description, action`

---

#### 9. **Pagination Component**
**Features:**
- Page numbers
- Previous/Next buttons
- Items per page selector
- Total count display
- Jump to page
**Props:** `currentPage, totalPages, itemsPerPage, onPageChange`

---

#### 10. **Timeline Component**
**Use Cases:**
- Submission workflow progress
- Activity history
- Status changes
**Props:** `items, orientation (vertical/horizontal), active`

---

#### 11. **Card Component**
**Variants:**
- Info card
- Stat card
- Action card
- List card
**Props:** `header, content, footer, actions, clickable`

---

#### 12. **Breadcrumb Component**
**Features:**
- Auto-generated from route
- Manual items
- Clickable navigation
**Props:** `items, separator`

---

#### 13. **Tabs Component**
**Features:**
- Horizontal/vertical layout
- URL sync
- Badge on tabs
- Disabled tabs
**Props:** `tabs, activeTab, onChange, orientation`

---

#### 14. **Search Bar Component**
**Features:**
- Debounced input
- Clear button
- Search icon
- Loading state
- Suggestions dropdown (autocomplete)
**Props:** `placeholder, onSearch, debounce, suggestions`

---

#### 15. **Filter Panel Component**
**Features:**
- Multiple filter types
- Clear all button
- Applied filters display
- Collapsible sections
**Props:** `filters, values, onChange, onReset`

---

#### 16. **Avatar Component**
**Features:**
- Image avatar
- Initials fallback
- Status indicator (online/offline)
- Size variants (xs, sm, md, lg, xl)
- Shape (circle/square)
**Props:** `src, name, size, status, shape`

---

#### 17. **Progress Bar/Stepper**
**Use Cases:**
- Multi-step forms
- Process progress
- File upload progress
**Props:** `steps, currentStep, orientation`

---

#### 18. **Dropdown Menu**
**Features:**
- Actions dropdown
- User menu
- Context menu
- Nested menus
**Props:** `items, trigger, position`

---

#### 19. **Alert/Banner Component**
**Types:** Info, Success, Warning, Error  
**Features:** Dismissible, with icon, action buttons  
**Props:** `type, message, closable, actions`

---

#### 20. **Tooltip Component**
**Props:** `content, position (top/bottom/left/right), trigger (hover/click)`

---

#### 21. **Accordion Component**
**Features:**
- Single/multiple open
- Animated expand/collapse
**Props:** `items, allowMultiple, defaultOpen`

---

#### 22. **Score Display Component**
**Use Cases:**
- Review scores
- Auto-scores
- Ratings
**Variants:**
- Slider/progress bar
- Numeric badge
- Star rating
- Radar chart
**Props:** `score, maxScore, label, variant`

---

#### 23. **Rich Text Editor**
**Features:**
- Basic formatting (bold, italic, underline)
- Lists (bullet, numbered)
- Links
- Headings
- Text alignment
- Code blocks
- Preview mode
**Props:** `value, onChange, toolbar, height`

---

#### 24. **Date Range Picker**
**Features:**
- Single date
- Date range
- Presets (Today, Last 7 days, Last 30 days, etc.)
- Min/max date
**Props:** `value, onChange, presets, minDate, maxDate`

---

#### 25. **Confirm Dialog**
**Use Cases:**
- Delete confirmation
- Action confirmation
- Warning dialogs
**Props:** `title, message, confirmText, cancelText, onConfirm, onCancel, variant (danger/warning/info)`

---

## 🔌 API INTEGRATION NOTES

### Base Configuration

```javascript
// API Base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Authentication Header
const getAuthHeader = () => ({
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`
});
```

---

### Authentication Flow

```javascript
// 1. Login
POST /api/v1/auth/login/
Body: { email, password }
Response: { access, refresh, user }
Action: Store tokens in localStorage

// 2. Token Refresh
POST /api/v1/auth/refresh/
Body: { refresh: localStorage.getItem('refresh_token') }
Response: { access }
Action: Update access_token in localStorage

// 3. Auto-refresh on 401
Interceptor: If response.status === 401, try refresh, retry request

// 4. Logout
POST /api/v1/auth/logout/
Action: Clear localStorage, redirect to /login
```

---

### Error Handling

```javascript
// Standard Error Response Format
{
  "detail": "Error message",
  "errors": {
    "field_name": ["Error 1", "Error 2"]
  }
}

// HTTP Status Codes
200 - Success (GET, PATCH, PUT)
201 - Created (POST)
204 - No Content (DELETE)
400 - Bad Request (validation errors)
401 - Unauthorized (token invalid/expired)
403 - Forbidden (no permission)
404 - Not Found
500 - Server Error
```

---

### Pagination

```javascript
// Request
GET /api/v1/submissions/?page=2&page_size=20

// Response
{
  "count": 156,
  "next": "http://...?page=3",
  "previous": "http://...?page=1",
  "results": [...]
}
```

---

### File Upload

```javascript
// Content-Type: multipart/form-data
const formData = new FormData();
formData.append('file', fileObject);
formData.append('document_type', 'MANUSCRIPT');

POST /api/v1/files/upload/:document_id/
Headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'multipart/form-data'
}
Body: formData
```

---

### File Download

```javascript
// Get download URL
GET /api/v1/files/download/:version_id/
Response: { url: 'signed_download_url' }

// Or direct download
window.location.href = `${API_BASE_URL}/files/download/${versionId}/`;
// With auth header in fetch:
fetch(url, { headers: getAuthHeader() })
  .then(res => res.blob())
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  });
```

---

### Search & Filtering

```javascript
// Multiple filters
GET /api/v1/submissions/?status=UNDER_REVIEW&journal=:journal_id&search=machine+learning&ordering=-created_at

// Available ordering fields (prefix with - for descending)
ordering: created_at, updated_at, title, status, submitted_at

// Search fields (depends on endpoint)
search: Searches across title, abstract, etc.
```

---

### WebSocket/Real-time (Future - Phase 5+)

```javascript
// Notifications WebSocket
ws://localhost:8000/ws/notifications/

// Message format
{
  "type": "notification",
  "data": {
    "id": "uuid",
    "title": "New Review Assignment",
    "message": "You have been assigned to review...",
    "action_url": "/reviewer/invitations/:id"
  }
}
```

---

##  RESPONSIVE DESIGN NOTES

### Breakpoints
- **Mobile:** < 640px (sm)
- **Tablet:** 640px - 1024px (md, lg)
- **Desktop:** > 1024px (xl, 2xl)

### Mobile-Specific Components
1. **Bottom Navigation** (replaces sidebar on mobile)
2. **Hamburger Menu** for secondary navigation
3. **Collapsible sections** for long forms
4. **Swipeable cards** for lists
5. **Pull-to-refresh** on data lists
6. **Floating Action Button** for primary actions

### Tablet Optimizations
- **Split view** for list/detail pages
- **Sidebar** toggleable/collapsible
- **Optimized table** with horizontal scroll

---

## SECURITY CONSIDERATIONS

1. **Token Storage:** Use httpOnly cookies or secure localStorage
2. **CSRF Protection:** Include CSRF token in state-changing requests
3. **Input Sanitization:** Sanitize all user inputs before rendering
4. **File Upload:** Validate file types client-side (server validates too)
5. **Sensitive Data:** Never log tokens, passwords, or personal data
6. **HTTPS Only:** Enforce HTTPS in production
7. **Rate Limiting:** Implement client-side request throttling
8. **Session Timeout:** Auto-logout after inactivity

---

## PERFORMANCE OPTIMIZATION

1. **Lazy Loading:** Code-split routes and heavy components
2. **Caching:** Cache API responses with React Query/SWR
3. **Pagination:** Always paginate large lists
4. **Image Optimization:** Compress and lazy-load images
5. **Debouncing:** Debounce search inputs (300-500ms)
6. **Memoization:** Use React.memo for expensive components
7. **Virtual Scrolling:** For very long lists (react-window)
8. **Progressive Enhancement:** Core functionality without JS

---

## TESTING REQUIREMENTS

### Unit Tests
- All components with >20 lines logic
- All utility functions
- Form validations

### Integration Tests
- API calls
- Authentication flow
- Form submissions
- File uploads

### E2E Tests (Critical Paths)
1. User registration → verification → login
2. Create submission → upload files → submit
3. Accept review → submit review
4. Make editorial decision → send letter
5. Admin approve verification

---

## RECOMMENDED TECH STACK

### Core
- **Framework:** React 18+ or Next.js 14+
- **State Management:** React Query + Zustand/Context
- **Routing:** React Router v6 or Next.js App Router
- **Styling:** Tailwind CSS + Headless UI

### UI Libraries
- **Component Library:** Radix UI or Shadcn/ui
- **Forms:** React Hook Form + Zod validation
- **Tables:** TanStack Table
- **Charts:** Recharts or Chart.js
- **Rich Text:** Tiptap or Quill
- **Date Picker:** React DatePicker

### Utilities
- **HTTP Client:** Axios or Fetch with interceptors
- **File Upload:** react-dropzone
- **Notifications:** react-hot-toast
- **Icons:** Heroicons or Lucide React
- **PDF Viewer:** react-pdf

---

### Build Optimization
- Enable production mode
- Minify JS/CSS
- Optimize images
- Generate source maps (separate file)
- Enable gzip/brotli compression


## SUMMARY: What to Build Now vs Later

###  BUILD NOW (Phases 1-4 Complete - 36 Pages)

**Authentication & Users (7 pages):**
- Login, Register, Profile, Email Verification, Password Reset, Verification Request, Verification Status

**Dashboards (4 pages):**
- User Dashboard, Author Dashboard, Reviewer Dashboard, Editor Dashboard

**Author Workflows (3 pages):**
- Browse Journals, New Submission, Submission Details, Revision Submission

**Reviewer Workflows (3 pages):**
- Review Invitations, Review Submission, Completed Reviews

**Editor Workflows (7 pages):**
- Submissions Management, Editorial View, Reviewer Search, Invitations, Decisions, Revisions, Journal Settings, Staff Management

**Admin (6 pages):**
- Admin Dashboard, User Management, Verification Requests, Journal Management, Email Templates, Email Logs

**Settings (2 pages):**
- Email Preferences, Email Log

**Total: 36 fully functional pages with complete backend support**

---

###  BUILD LATER (Phases 5-7 - 6 Pages Fully Specified)

**Backend NOT ready - Do not start development yet**

**All 6 future pages have COMPLETE specifications above with:**
-  Full component lists and UI/UX details
-  User flows and interactions
-  Planned API endpoint documentation
-  Data structures and response formats
-  Integration requirements

**Phase 5 - Advanced Features (4 Pages):**
1. **ML Reviewer Recommendations Page** (#39)
   - AI-powered matching, confidence scores, expertise visualization, performance metrics
   
2. **Plagiarism Check Interface** (#40)
   - iThenticate/Turnitin integration, similarity reports, source matching, document viewer
   
3. **Live Document Editor** (#41)
   - OnlyOffice/Collabora with real-time collaboration, track changes, comments, version control
   
4. **ROR/OpenAlex Integration Pages** (#42)
   - Institution validation, author profile enrichment, publication import, CoI detection

**Phase 6 - Analytics (2 Pages):**
5. **System Analytics Dashboard** (#37)
   - Comprehensive metrics, charts, trends, journal performance, user analytics
   
6. **Audit Log Page** (#38)
   - Activity tracking, compliance logging, alert rules, anomaly detection

**Phase 7 - Production:**
- System monitoring (integrated into existing admin pages)
- Error tracking (integrated features)
- Advanced security (integrated features)

**Total: 6 complete page specifications (~40 API endpoints planned)**

---

##  API ENDPOINT SUMMARY

###  Available Now: 100+ Endpoints (Phases 1-4)
###  Coming Later: 40+ Endpoints (Phases 5-7)

### Total Planned: 140+ Endpoints

###  Fully Operational Endpoints (Build with these):

**Authentication (8) - Phase 1:**
- register, login, logout, refresh, verify-email, password-change, password-reset, me

**Users (8) - Phase 1:**
- list, get, update, delete, profiles, roles, verification-requests, verification-status

**Journals (12) - Phase 2:**
- CRUD, settings, staff management, statistics

**Submissions (15) - Phase 2:**
- CRUD, submit, withdraw, authors, documents, search, filter

**Files (7) - Phase 2:**
- upload, download, preview, info, delete, versions, compare

**Reviews (35) - Phase 4:**
- assignments, accept, decline, submit review, reviewer search, recommendations, forms, decisions, revision rounds

**Notifications (11) - Phase 3:**
- email preferences, email logs, statistics, templates

**Integrations (4) - Phase 3:**
- ORCID connect, callback, status, disconnect

**Admin (12) - Phase 1-3:**
- users, journals, verifications, email templates (analytics & audit logs NOT ready)

**Total Ready: ~100 endpoints** 

---

###  Coming in Future Phases:

**Phase 5 (Not Built):**
- ML reviewer recommendations API
- iThenticate plagiarism API
- Document editor API (OnlyOffice/Collabora)
- ROR integration API
- OpenAlex integration API

**Phase 6 (Not Built):**
- Analytics & reporting API (~15 endpoints)
- Audit log API (~5 endpoints)
- Custom reports API

**Phase 7 (Not Built):**
- System monitoring API
- Performance metrics API

**Total Future: ~40 endpoints** 

---

##  PRIORITY IMPLEMENTATION ORDER

### Phase 1: Core Authentication & Profile
1. Login/Register pages
2. Profile page
3. Email verification
4. Password reset
5. Dashboard layout

### Phase 2: Submission System
6. Author dashboard
7. New submission wizard
8. Submission details page
9. File upload components

### Phase 3: Review System
10. Reviewer dashboard
11. Review invitation page
12. Review submission form
13. Editor submission view

### Phase 4: Editorial & Admin
14. Editor dashboard
15. Reviewer search
16. Editorial decision page
17. Admin verification page
18. Journal settings

### Phase 5: Polish & Optimization
19. Email preferences
20. Analytics views
21. Mobile optimization
22. Testing & bug fixes

---

---

## COMPLETE PAGE REFERENCE TABLE

| # | Page Name | Route | Phase | Backend | Components | Priority |
|---|-----------|-------|-------|---------|------------|----------|
| 1 | Landing Page | `/` | 2 |  Ready | Hero, Stats, Journal List | High |
| 2 | Browse Journals | `/journals` | 2 |  Ready | Search, Cards, Pagination | High |
| 3 | Journal Details | `/journals/:id` | 2 |  Ready | Header, Staff, Guidelines | High |
| 4 | Register | `/register` | 1 |  Ready | Form, Validation | Critical |
| 5 | Login | `/login` | 1 |  Ready | Form, OAuth Links | Critical |
| 6 | Email Verification | `/verify-email/:token` | 1 |  Ready | Status Message | Critical |
| 7 | Forgot Password | `/forgot-password` | 1 |  Ready | Email Form | Medium |
| 8 | Reset Password | `/reset-password/:token` | 1 |  Ready | Password Form | Medium |
| 9 | User Dashboard | `/dashboard` | 1-4 |  Ready | Stats, Activity, Tabs | Critical |
| 10 | User Profile | `/profile` | 1,3 |  Ready | Form, ORCID, Avatar | High |
| 11 | Verification Request | `/verification/request` | 3 |  Ready | Multi-form, Score | High |
| 12 | Verification Status | `/verification/status` | 3 |  Ready | Timeline, Response | High |
| 13 | Email Preferences | `/settings/email` | 3 |  Ready | Toggles, Categories | Medium |
| 14 | Email Log | `/settings/email-log` | 3 |  Ready | Table, Filters | Low |
| 15 | Author Dashboard | `/author/dashboard` | 2 |  Ready | Submissions Table | High |
| 16 | New Submission | `/author/submit` | 2 |  Ready | Wizard, Upload | Critical |
| 17 | Submission Details | `/author/submissions/:id` | 2,4 |  Ready | Tabs, Files, Reviews | High |
| 18 | Revision Submission | `/author/revisions/:id` | 4 |  Ready | Form, Upload | High |
| 19 | Reviewer Dashboard | `/reviewer/dashboard` | 4 |  Ready | Assignments Table | High |
| 20 | Review Invitation | `/reviewer/invitations/:id` | 4 |  Ready | Details, Accept/Decline | High |
| 21 | Review Submission | `/reviewer/review/:id` | 4 |  Ready | Form, Scores, Comments | Critical |
| 22 | Completed Reviews | `/reviewer/completed` | 4 |  Ready | List, Stats | Low |
| 23 | Editor Dashboard | `/editor/dashboard` | 2,4 |  Ready | Stats, Activity | High |
| 24 | Submissions Management | `/editor/submissions` | 2 |  Ready | Table, Filters | High |
| 25 | Editorial View | `/editor/submissions/:id` | 4 |  Ready | Tabs, Reviews, Decision | Critical |
| 26 | Reviewer Search | `/editor/reviewers/search` | 4 |  Ready | Search, Cards | High |
| 27 | Invitations Management | `/editor/invitations` | 4 |  Ready | Table, Reminders | Medium |
| 28 | Editorial Decisions | `/editor/decisions` | 4 |  Ready | Table, Analytics | Medium |
| 29 | Revision Management | `/editor/revisions` | 4 |  Ready | Table, Approve/Reject | Medium |
| 30 | Journal Settings | `/editor/journal/:id/settings` | 2 |  Ready | Forms, Sections | Medium |
| 31 | Staff Management | `/editor/journal/:id/staff` | 2 |  Ready | Table, Add/Remove | Medium |
| 32 | Admin Dashboard | `/admin/dashboard` | 1-4 |  Ready | Stats, Health | Medium |
| 33 | User Management | `/admin/users` | 1 |  Ready | Table, Search | Medium |
| 34 | Verification Requests | `/admin/verifications` | 3 |  Ready | Queue, Approve | High |
| 35 | Journal Management | `/admin/journals` | 2 |  Ready | Table, CRUD | Medium |
| 36 | Email Templates | `/admin/email-templates` | 3 |  Ready | List, Editor | Low |
| **37** | **System Analytics** | `/admin/analytics` | **6** | **Wait** | Charts, Metrics | Future |
| **38** | **Audit Log** | `/admin/audit-log` | **6** | **Wait** | Table, Filters | Future |
| **39** | **ML Recommendations** | `/editor/ml-reviewers` | **5** | **Wait** | AI Cards, Scores | Future |
| **40** | **Plagiarism Check** | `/editor/plagiarism/:id` | **5** | **Wait** | Viewer, Report | Future |
| **41** | **Document Editor** | `/editor/docs/:id` | **5** | **Wait** | Embedded Editor | Future |
| **42** | **ROR/OpenAlex** | `/profile/enrich` | **5** | **Wait** | Search, Import | Future |

**Legend:**
-  Ready = Backend complete
-  Wait = Backend not ready, specification complete for planning

**Total:** 42 pages (36 ready to build + 6 future pages fully specified)

---

**END OF SPECIFICATION**

*This document covers all 42 pages for the Journal Portal (Phases 1-7). Phases 1-4 are complete and ready for frontend development. Phases 5-7 are fully specified but awaiting backend implementation.*

---

**Questions or Clarifications?**
- Backend API Documentation: `/api/redoc/`
- Phase Summaries: See `PHASE1_SUMMARY.md`, `PHASE2_SUMMARY.md`, `PHASE3_SUMMARY.md`, `PHASE4_SUMMARY.md`
- Database Schema: See individual phase documentation
- Live API Testing: Use Swagger UI at `/api/docs/` with JWT token
