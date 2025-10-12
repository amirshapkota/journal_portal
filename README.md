# Journal Portal

A modern, secure, auditable Journal Publication Portal that integrates with OJS and scholarly services (ORCID, ROR, OpenAlex, iThenticate), provides an in-browser editor, automated pre-checks (formatting, plagiarism), reviewer recommendation, anomaly detection and role-based dashboards.

## Project Structure

```
journal_portal/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment configuration template
├── logs/                    # Application logs
├── journal_portal/          # Main project configuration
│   ├── __init__.py
│   ├── settings.py          # Django settings
│   ├── urls.py             # Main URL configuration
│   ├── wsgi.py             # WSGI configuration
│   └── celery.py           # Celery configuration
└── apps/                   # All Django applications
    ├── __init__.py
    ├── users/              # Authentication & user profiles
    ├── journals/           # Journal models & settings
    ├── submissions/        # Submissions, documents, versions
    ├── reviews/           # Review management & assignments
    ├── precheck/          # Plagiarism & formatting checks
    ├── integrations/      # ORCID/OJS connectors
    ├── ml/               # ML integration points
    ├── analytics/        # Metrics & reports
    └── common/           # Shared utilities
```

## Apps Overview

### 1. Users App (`apps/users/`)
- **Purpose**: Authentication & Identity Service, User Profile & Verification Service
- **Features**: ORCID authentication, session management, JWT tokens, user profiles, email verification

### 2. Journals App (`apps/journals/`)
- **Purpose**: Journal management and configuration
- **Features**: Journal models, settings, staff management, publication workflows

### 3. Submissions App (`apps/submissions/`)
- **Purpose**: Manuscript Service
- **Features**: Document management, version control, metadata editing, submission workflow

### 4. Reviews App (`apps/reviews/`)
- **Purpose**: Review Management Service
- **Features**: Review assignments, reviewer recommendations, review tracking, decisions

### 5. Precheck App (`apps/precheck/`)
- **Purpose**: Submission Pre-Check Service
- **Features**: Plagiarism detection, formatting validation, required document checks

### 6. Integrations App (`apps/integrations/`)
- **Purpose**: External service integrations
- **Features**: ORCID sync, OJS integration (OAI-PMH + REST), ROR, OpenAlex, iThenticate

### 7. ML App (`apps/ml/`)
- **Purpose**: ML/Embedding Service
- **Features**: Reviewer recommendations, anomaly detection, text analysis, similarity checks

### 8. Analytics App (`apps/analytics/`)
- **Purpose**: Reporting & Analytics Service
- **Features**: Metrics collection, dashboard data, performance reports, export functionality

### 9. Common App (`apps/common/`)
- **Purpose**: Shared utilities and components
- **Features**: Common permissions, utilities, email services, audit logging

## Technology Stack

- **Backend**: Django 5.2+ with Django REST Framework
- **Database**: PostgreSQL (configurable)
- **Cache/Queue**: Redis + Celery
- **Authentication**: Django Auth + JWT + ORCID
- **API**: RESTful API with DRF

## Setup Instructions

1. **Clone and navigate to project**:
   ```bash
   cd journal_portal
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**:
   ```bash
   copy .env.example .env
   # Edit .env with your actual configuration values
   ```

5. **Database setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run development server**:
   ```bash
   python manage.py runserver
   ```

7. **Run Celery worker** (separate terminal):
   ```bash
   celery -A journal_portal worker --loglevel=info
   ```

## API Endpoints

The API is structured with versioning and logical grouping:

- `api/v1/auth/` - Authentication and user management
- `api/v1/journals/` - Journal operations
- `api/v1/submissions/` - Submission management
- `api/v1/reviews/` - Review process
- `api/v1/precheck/` - Pre-submission checks
- `api/v1/integrations/` - External service integrations
- `api/v1/ml/` - ML services
- `api/v1/analytics/` - Analytics and reporting

## Development Notes

- The project is structured as a backend API service
- Each app has its own URLs, models, views, and serializers (to be implemented)
- Common utilities are centralized in the `common` app
- Environment-based configuration using python-decouple
- Comprehensive logging and audit trail support
- Celery integration for background tasks
- Redis for caching and message brokering

## Next Steps

This is the initial project structure. Each app will be developed incrementally with:
- Models definition
- Serializers and ViewSets
- Business logic and services
- API documentation
- Tests
- Integration with external services

## Configuration

Key configuration areas in `settings.py`:
- Database configuration (PostgreSQL recommended for production)
- Redis configuration for cache and Celery
- Email settings for notifications
- External service API keys (ORCID, OJS, iThenticate)
- File upload settings and validation
- Security settings and permissions