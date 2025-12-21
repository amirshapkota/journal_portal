# Production Workflow Integration - Complete Guide

## Overview

The production workflow handles the final preparation and publication of manuscripts after the copyediting stage. This document outlines the complete production workflow implementation, including backend models, API endpoints, and frontend components.

## Backend Implementation

### 1. Models (`production_models.py`)

#### ProductionAssignment

- **Purpose**: Manages production assistant assignments
- **Key Fields**:
  - `production_assistant`: The assigned production assistant/layout editor
  - `assigned_by`: Editor who made the assignment
  - `status`: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
  - `participants`: ManyToMany field for additional collaborators
  - `due_date`: Deadline for production completion
  - `instructions`: Special instructions from editor
  - `completion_notes`: Notes upon completion

#### ProductionFile

- **Purpose**: Manages galley files and production-ready files
- **Key Fields**:
  - `file_type`: PRODUCTION_READY or GALLEY
  - `galley_format`: PDF, HTML, XML, EPUB, MOBI, OTHER
  - `label`: Display label (e.g., "PDF", "Full Text HTML")
  - `is_published`: Publication status
  - `is_approved`: Approval status
  - `version`: File version number

#### ProductionDiscussion

- **Purpose**: Discussion threads during production
- **Key Fields**:
  - `subject`: Discussion topic
  - `status`: OPEN or CLOSED
  - `participants`: Users involved in discussion
  - `started_by`: User who started the discussion

### 2. API Endpoints (`workflow_views.py`)

#### Production Assignment Endpoints

- **POST** `/submissions/production/assignments/` - Create assignment
- **GET** `/submissions/production/assignments/` - List assignments
- **GET** `/submissions/production/assignments/{id}/` - Get assignment details
- **PATCH** `/submissions/production/assignments/{id}/` - Update assignment
- **POST** `/submissions/production/assignments/{id}/start/` - Start production
- **POST** `/submissions/production/assignments/{id}/complete/` - Complete production
- **GET** `/submissions/production/assignments/{id}/participants/` - List participants
- **POST** `/submissions/production/assignments/{id}/add_participant/` - Add participant
- **POST** `/submissions/production/assignments/{id}/remove_participant/` - Remove participant
- **GET** `/submissions/production/assignments/{id}/files/` - Get assignment files
- **GET** `/submissions/production/assignments/{id}/discussions/` - Get assignment discussions

#### Production File (Galley) Endpoints

- **POST** `/submissions/production/files/` - Upload galley file
- **GET** `/submissions/production/files/` - List galley files
- **GET** `/submissions/production/files/{id}/` - Get file details
- **PATCH** `/submissions/production/files/{id}/` - Update file
- **POST** `/submissions/production/files/{id}/approve/` - Approve file
- **POST** `/submissions/production/files/{id}/publish/` - Publish file
- **GET** `/submissions/production/files/{id}/load/` - Load file for editing
- **POST** `/submissions/production/files/{id}/save/` - Save file (manual save)
- **GET** `/submissions/production/files/{id}/download/` - Download file
- **DELETE** `/submissions/production/files/{id}/` - Delete file

#### Production Discussion Endpoints

- **POST** `/submissions/production/discussions/` - Create discussion
- **GET** `/submissions/production/discussions/` - List discussions
- **GET** `/submissions/production/discussions/{id}/` - Get discussion with messages
- **PATCH** `/submissions/production/discussions/{id}/` - Update discussion
- **POST** `/submissions/production/discussions/{id}/add_message/` - Add message
- **POST** `/submissions/production/discussions/{id}/close/` - Close discussion
- **POST** `/submissions/production/discussions/{id}/reopen/` - Reopen discussion
- **DELETE** `/submissions/production/discussions/{id}/` - Delete discussion

#### Publication Schedule Endpoints

- **POST** `/submissions/production/schedules/` - Schedule publication
- **GET** `/submissions/production/schedules/` - List schedules
- **GET** `/submissions/production/schedules/{id}/` - Get schedule details
- **PATCH** `/submissions/production/schedules/{id}/` - Update schedule
- **POST** `/submissions/production/schedules/{id}/publish_now/` - Publish immediately
- **POST** `/submissions/production/schedules/{id}/cancel/` - Cancel publication
- **DELETE** `/submissions/production/schedules/{id}/` - Delete schedule

## Frontend Implementation

### 1. API Functions (`productionApi.js`)

All API endpoints are wrapped in JavaScript functions for easy consumption by React hooks.

### 2. React Hooks

#### Query Hooks (`hooks/query/`)

- `useProductionAssignments(params)` - Fetch assignments list
- `useProductionAssignment(assignmentId)` - Fetch single assignment
- `useProductionAssignmentFiles(assignmentId)` - Fetch assignment files
- `useProductionAssignmentDiscussions(assignmentId)` - Fetch assignment discussions
- `useProductionAssignmentParticipants(assignmentId)` - Fetch participants
- `useProductionFiles(params)` - Fetch production files list
- `useProductionFile(fileId)` - Fetch single file
- `useProductionDiscussions(params)` - Fetch discussions list
- `useProductionDiscussion(discussionId)` - Fetch single discussion
- `usePublicationSchedules(params)` - Fetch publication schedules

#### Mutation Hooks (`hooks/mutation/`)

- `useCreateProductionAssignment()` - Create assignment
- `useUpdateProductionAssignment()` - Update assignment
- `useStartProductionAssignment()` - Start production
- `useCompleteProductionAssignment()` - Complete production
- `useAddProductionParticipant()` - Add participant
- `useRemoveProductionParticipant()` - Remove participant
- `useUploadProductionFile()` - Upload galley file
- `useUpdateProductionFile()` - Update file
- `useApproveProductionFile()` - Approve file
- `usePublishGalleyFile()` - Publish file
- `useDeleteProductionFile()` - Delete file
- `useCreateProductionDiscussion()` - Create discussion
- `useUpdateProductionDiscussion()` - Update discussion
- `useAddProductionMessage()` - Add message to discussion
- `useCloseProductionDiscussion()` - Close discussion
- `useReopenProductionDiscussion()` - Reopen discussion
- `useDeleteProductionDiscussion()` - Delete discussion

### 3. Components

#### ProductionParticipants

- **Location**: `components/production/ProductionParticipants.jsx`
- **Features**:
  - Lists all participants (production assistant, editor, author, additional participants)
  - Add participant functionality with profile UUID input
  - Remove participant with confirmation dialog
  - Role-based badges (color-coded)
  - Only allows removal of additional participants (not core roles)

#### ProductionDiscussions

- **Location**: `components/production/ProductionDiscussions.jsx`
- **Features**:
  - Lists all discussions with search functionality
  - Create new discussion
  - View discussion details
  - Status badges (OPEN/CLOSED)
  - Message count display
  - Last reply timestamp

#### ProductionReadyFiles

- **Location**: `components/production/ProductionReadyFiles.jsx`
- **Features**:
  - Lists all production files/galleys
  - Upload new galley files (PDF, HTML, XML, EPUB, MOBI)
  - Required fields: File, Label, Galley Format
  - Optional description field
  - View and download files
  - File type badges
  - Uploader information

#### AssignProductionAssistantDialog

- **Location**: `components/production/AssignProductionAssistantDialog.jsx`
- **Features**:
  - Assign production assistant to submission
  - Role selection (Production Assistant, Layout Editor, Proofreader)
  - User search functionality
  - Due date and instructions fields

#### AddProductionDiscussionDialog

- **Location**: `components/production/AddProductionDiscussionDialog.jsx`
- **Features**:
  - Create new discussion thread
  - Add subject and initial message
  - Select participants

## Production Workflow Steps

### 1. Assignment Creation

1. Editor navigates to production tab
2. Clicks "Assign Production Assistant"
3. Selects user, role, due date, and provides instructions
4. Submission status moves to IN_PRODUCTION

### 2. Production Work

1. Production assistant starts the assignment
2. Upload galley files (PDF, HTML, XML, etc.) with labels
3. Communicate via discussions if needed
4. Add additional participants if required

### 3. Completion

1. All galley files are uploaded and approved
2. Production assistant marks assignment as complete
3. Files are ready for publication scheduling

### 4. Publication Scheduling

1. Editor schedules publication date
2. Sets volume, issue, year, DOI, and page numbers
3. Can publish immediately or schedule for future date

## Key Features

### Participant Management

- Core participants: Production Assistant, Editor (Assigned By), Author
- Additional participants can be added/removed
- Participants have access to files and discussions

### File Management

- Multiple galley formats supported
- Version tracking
- Approval workflow
- Publication status tracking
- Manual save/load for editing

### Discussion System

- Threaded discussions
- Participant management
- Open/closed status
- Message attachments support

### Permissions

- Production assistants can manage their assignments
- Editors can manage all production tasks
- Authors can view their submission's production status
- Participants have appropriate access levels

## Database Migrations

### Migration 0018: Add Participants to ProductionAssignment

- Adds `participants` ManyToManyField to ProductionAssignment model
- Allows additional collaborators beyond the assigned production assistant
- Applied successfully

## Frontend-Backend Integration

All components are fully integrated with:

- React Query for data fetching and caching
- Optimistic updates for better UX
- Error handling with toast notifications
- Loading states with skeletons
- Automatic query invalidation on mutations

## Testing Checklist

- ✅ Create production assignment
- ✅ Start production
- ✅ Add/remove participants
- ✅ Upload galley files with different formats
- ✅ Create and manage discussions
- ✅ Complete production
- ✅ Schedule publication
- ✅ Approve and publish files

## Notes

- All production components receive `submissionId` as prop (not `assignmentId`)
- Components automatically fetch the production assignment for the submission
- Graceful handling when no production assignment exists
- File uploads require assignment and submission IDs
- Label field is required for galley files
