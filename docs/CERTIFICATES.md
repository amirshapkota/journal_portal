# Certificate System Documentation

## Overview

The certificate system automatically generates verifiable certificates for awards earned through the achievements system. Certificates are created automatically when awards are generated and can be verified using unique verification codes.

## Architecture

### Backend Components

#### Certificate Model (`apps/achievements/models.py`)

```python
class Certificate(TimeStampedModel):
    """
    Model for storing achievement certificates
    """
    CERTIFICATE_TYPES = [
        ('AWARD', 'Award Certificate'),
        ('BADGE', 'Badge Certificate'),
        ('RECOGNITION', 'Recognition Certificate'),
        ('PARTICIPATION', 'Participation Certificate'),
    ]

    certificate_type = models.CharField(max_length=20, choices=CERTIFICATE_TYPES)
    certificate_number = models.CharField(max_length=50, unique=True, editable=False)
    verification_code = models.CharField(max_length=64, unique=True, editable=False)
    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    award = models.ForeignKey(Award, on_delete=models.CASCADE, null=True, blank=True)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, null=True, blank=True)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, null=True, blank=True)
    issued_date = models.DateField()
    file_url = models.URLField(max_length=500, blank=True, null=True)
    pdf_generated = models.BooleanField(default=False)
    custom_data = models.JSONField(default=dict, blank=True)
```

**Key Features:**

- **Auto-generated certificate_number**: Format `{TYPE}{YEAR}{COUNT:05d}` (e.g., AWARD202400001)
- **Auto-generated verification_code**: 20-character SHA256 hash for public verification
- **Multiple certificate types**: Award, Badge, Recognition, Participation
- **Custom data**: JSON field for additional metadata (award_type, year, citation, etc.)
- **PDF support**: file_url and pdf_generated fields for future PDF generation

#### Automatic Certificate Generation (`apps/achievements/tasks.py`)

Certificates are automatically generated when awards are created via Celery tasks:

```python
def _generate_certificate_for_award(award):
    """Helper function to generate certificate for an award"""
    certificate = Certificate.objects.create(
        recipient=award.recipient,
        certificate_type='AWARD',
        title=award.title,
        description=f'This certificate is awarded to {award.recipient.display_name} for {award.title}',
        award=award,
        journal=award.journal,
        issued_date=date.today(),
        custom_data={
            'award_type': award.award_type,
            'year': award.year,
            'citation': award.citation
        }
    )

    award.certificate_generated = True
    award.save()

    return certificate
```

**Integration Points:**

- `generate_yearly_awards()` - Creates certificates for Best Reviewer and Researcher of Year awards
- `generate_monthly_awards()` - Creates certificates for Excellence in Review awards
- All award creation tasks automatically call `_generate_certificate_for_award()`

#### Certificate API (`apps/achievements/views.py`)

**Endpoints:**

1. **List User Certificates**

   ```
   GET /api/certificates/
   ```

   Returns all certificates for the authenticated user.

2. **Get Certificate by ID**

   ```
   GET /api/certificates/{id}/
   ```

   Returns details of a specific certificate.

3. **Generate Award Certificate**

   ```
   POST /api/certificates/generate-award/{award_id}/
   ```

   Manually generates a certificate for a specific award (used if automatic generation failed).

4. **Verify Certificate**
   ```
   GET /api/certificates/verify/?code={verification_code}
   ```
   Public endpoint to verify certificate authenticity using the verification code.

### Frontend Components

#### CertificateCard Component (`frontend/features/shared/components/achievements/CertificateCard.jsx`)

**Features:**

- Displays certificate type badge (Award, Badge, Recognition, Participation)
- Shows certificate number and verification code
- Displays issued date and description
- Shows associated award/badge details
- Download PDF button (when PDF is generated)
- Generate PDF button (when PDF not yet generated)
- Copy verification link button
- Responsive grid layout for multiple certificates

**Props:**

```javascript
CertificateCard({
  certificate, // Certificate object from API
  onGenerateCertificate, // Callback function to generate PDF (optional)
});

CertificateGrid({
  certificates, // Array of certificate objects
  onGenerateCertificate, // Callback function for PDF generation (optional)
});
```

#### Certificate Hooks (`frontend/features/shared/hooks/`)

1. **useGetMyCertificates**

   ```javascript
   const { data, isPending, error } = useGetMyCertificates();
   ```

   Fetches all certificates for the current user.

2. **useGenerateAwardCertificate**

   ```javascript
   const generateCertificate = useGenerateAwardCertificate();
   generateCertificate.mutate(awardId);
   ```

   Generates a certificate for a specific award.

3. **useGetCertificateById**

   ```javascript
   const { data, isPending, error } = useGetCertificateById(certificateId);
   ```

   Fetches details of a specific certificate.

4. **useVerifyCertificate**
   ```javascript
   const { data, isPending, error } = useVerifyCertificate(verificationCode);
   ```
   Verifies a certificate using its verification code.

## Certificate Flow

### Automatic Generation Flow

```
1. Award Created (via Celery Task)
   ↓
2. _generate_certificate_for_award() called
   ↓
3. Certificate Model Auto-generates:
   - certificate_number (AWARD202400001)
   - verification_code (20-char hash)
   ↓
4. Certificate saved to database
   ↓
5. award.certificate_generated = True
   ↓
6. User can view certificate in Achievements page
```

### Certificate Verification Flow

```
1. User receives certificate with verification code
   ↓
2. Visitor enters code at /certificates/verify
   ↓
3. GET /api/certificates/verify/?code={code}
   ↓
4. System validates certificate
   ↓
5. Returns certificate details if valid
```

## Certificate Types and Generation Rules

### Award Certificates

**Auto-generated for:**

- **Best Reviewer of Year**: Top reviewer with min 5 reviews (yearly, Jan 1st)
- **Researcher of Year**: Top author with min 3 publications (yearly, Jan 1st)
- **Excellence in Review**: Top 3 reviewers with min 3 reviews (monthly, 1st of month)
- **Top Contributor**: Manual awards for exceptional contributions

**Certificate includes:**

- Award title and description
- Recipient name
- Journal name (if applicable)
- Year awarded
- Citation text
- Unique certificate number
- Verification code

### Badge Certificates (Future)

**Can be generated for:**

- Milestone badges (1st, 5th, 10th review, etc.)
- Special achievement badges
- Manually upon user request or achievement

### Recognition & Participation Certificates (Future)

**Can be issued for:**

- Conference participation
- Editorial board membership
- Peer review excellence programs
- Special recognitions

## Integration with Achievement Pages

### Author Achievements Page

Located at: `/author/achievements`

**Certificates Tab:**

- Shows all certificates earned by the author
- Displays certificates in grid layout
- Allows generation of missing PDFs
- Shows verification codes for sharing

### Reviewer Achievements Page

Located at: `/reviewer/achievements`

**Certificates Tab:**

- Shows all certificates earned by the reviewer
- Same features as author page
- Filters for reviewer-specific awards only

## Database Schema

```sql
-- Certificate Table
CREATE TABLE certificates (
    id INTEGER PRIMARY KEY,
    certificate_type VARCHAR(20),  -- AWARD, BADGE, RECOGNITION, PARTICIPATION
    certificate_number VARCHAR(50) UNIQUE,  -- Auto-generated
    verification_code VARCHAR(64) UNIQUE,   -- Auto-generated hash
    recipient_id INTEGER,  -- FK to Profile
    title VARCHAR(200),
    description TEXT,
    award_id INTEGER,      -- FK to Award (nullable)
    badge_id INTEGER,      -- FK to Badge (nullable)
    journal_id INTEGER,    -- FK to Journal (nullable)
    issued_date DATE,
    file_url VARCHAR(500), -- PDF download URL (future)
    pdf_generated BOOLEAN, -- PDF generation status
    custom_data JSONB,     -- Additional metadata
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_cert_recipient ON certificates(recipient_id);
CREATE INDEX idx_cert_award ON certificates(award_id);
CREATE INDEX idx_cert_verification ON certificates(verification_code);
CREATE INDEX idx_cert_number ON certificates(certificate_number);
```

## API Response Examples

### Certificate List Response

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "certificate_type": "AWARD",
      "certificate_number": "AWARD202400001",
      "verification_code": "a1b2c3d4e5f6g7h8i9j0",
      "recipient": {
        "id": 42,
        "display_name": "Dr. Jane Smith",
        "user": {
          "email": "jane.smith@university.edu"
        }
      },
      "title": "Best Reviewer of the Year 2024",
      "description": "This certificate is awarded to Dr. Jane Smith for Best Reviewer of the Year 2024",
      "award": {
        "id": 10,
        "award_type": "BEST_REVIEWER",
        "title": "Best Reviewer of the Year 2024",
        "year": 2024
      },
      "journal": {
        "id": 5,
        "title": "Journal of Advanced Science"
      },
      "issued_date": "2024-01-01",
      "file_url": null,
      "pdf_generated": false,
      "custom_data": {
        "award_type": "BEST_REVIEWER",
        "year": 2024,
        "citation": "For exceptional contributions to peer review excellence"
      },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Certificate Verification Response

```json
{
  "valid": true,
  "certificate": {
    "certificate_number": "AWARD202400001",
    "recipient_name": "Dr. Jane Smith",
    "title": "Best Reviewer of the Year 2024",
    "issued_date": "2024-01-01",
    "journal": "Journal of Advanced Science"
  }
}
```

## Future Enhancements

### 1. PDF Generation

- **Library**: ReportLab or WeasyPrint
- **Template**: Professional certificate design
- **Storage**: AWS S3 or local media storage
- **Features**:
  - Custom certificate templates per type
  - Journal branding/logo
  - QR code for verification
  - Digital signature

### 2. Email Notifications

- Send email when certificate is generated
- Include PDF attachment
- Verification link in email
- Congratulations message

### 3. Social Sharing

- Share certificate on social media
- Generate shareable image
- LinkedIn integration
- Twitter cards

### 4. Certificate Revocation

- Admin ability to revoke certificates
- Revocation reason tracking
- Verification shows revoked status
- Audit trail for revocations

### 5. Bulk Certificate Generation

- Admin tool to generate certificates in bulk
- Batch processing for historical awards
- Progress tracking
- Error handling and retry logic

## Testing

### Manual Testing Checklist

**Backend:**

- [ ] Certificate auto-generates when award created
- [ ] Certificate number is unique and follows format
- [ ] Verification code is unique and secure
- [ ] Award.certificate_generated flag is set
- [ ] Verification endpoint returns correct data
- [ ] Invalid verification codes return error

**Frontend:**

- [ ] Certificates tab shows in achievements page
- [ ] Certificate grid displays correctly
- [ ] Certificate details are accurate
- [ ] Verification code can be copied
- [ ] Generate certificate button works
- [ ] Loading and error states display

### Test Data Generation

To test certificates, run the Celery tasks:

```python
# In Django shell
from apps.achievements.tasks import generate_yearly_awards, generate_monthly_awards

# Generate yearly awards (creates certificates)
generate_yearly_awards()

# Generate monthly awards (creates certificates)
generate_monthly_awards()

# Check certificates created
from apps.achievements.models import Certificate
Certificate.objects.all()
```

## Security Considerations

1. **Verification Code Generation**

   - Uses SHA256 hash for security
   - 20-character random string
   - Impossible to guess or brute-force

2. **Public Verification**

   - No authentication required for verification
   - Only returns minimal public data
   - Prevents enumeration attacks

3. **PDF Security** (Future)

   - Watermarked PDFs
   - Digital signatures
   - Tamper-proof design

4. **Access Control**
   - Users can only view their own certificates
   - Admin can view all certificates
   - Public can verify using code only

## Troubleshooting

### Certificates Not Generating

**Check:**

1. Celery worker is running
2. Celery beat scheduler is active
3. Award creation task completed successfully
4. Database constraints not violated (unique certificate_number)

**Solution:**

```python
# Manually generate certificate for award
from apps.achievements.tasks import _generate_certificate_for_award
from apps.achievements.models import Award

award = Award.objects.get(id=YOUR_AWARD_ID)
certificate = _generate_certificate_for_award(award)
```

### Verification Code Not Working

**Check:**

1. Code is exactly 20 characters
2. No spaces or special characters
3. Certificate exists in database
4. Code matches database entry

**Solution:**

```python
# Check certificate by code
from apps.achievements.models import Certificate

cert = Certificate.objects.filter(verification_code='YOUR_CODE').first()
print(cert)
```

### Frontend Not Showing Certificates

**Check:**

1. API endpoint returning data
2. React Query cache not stale
3. Component exports are correct
4. Hooks imported properly

**Solution:**

- Check browser console for errors
- Verify API response in Network tab
- Clear React Query cache
- Check component import paths

## Conclusion

The certificate system provides a complete, automated solution for generating and verifying achievement certificates. It integrates seamlessly with the achievements system and provides users with official recognition of their contributions.

**Key Benefits:**

- **Automatic**: Certificates generate when awards are created
- **Verifiable**: Unique verification codes for public validation
- **Secure**: SHA256 hashing and proper access controls
- **User-Friendly**: Simple UI for viewing and sharing certificates
- **Extensible**: Easy to add new certificate types and features

For more information, see:

- [Badges and Awards Documentation](./BADGES_AND_AWARDS.md)
- [Achievement System Overview](./README.md)
