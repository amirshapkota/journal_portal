"""
Test script for Anomaly Detection System
"""

import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.ml.anomaly_detection import AnomalyDetectionEngine
from apps.submissions.models import Submission
from apps.users.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()

def print_separator(title=""):
    """Print a formatted separator."""
    print("\n" + "=" * 70)
    if title:
        print(title.center(70))
        print("=" * 70)


def test_anomaly_detection():
    """Test the anomaly detection system."""
    print_separator("ANOMALY DETECTION SYSTEM TEST")
    
    engine = AnomalyDetectionEngine()
    
    # Test 1: Scan a specific author
    print("\n TEST 1: Scanning Author Behavior")
    print("-" * 70)
    
    author = Profile.objects.filter(
        corresponding_submissions__isnull=False
    ).first()
    
    if author:
        print(f"\nScanning author: {author.user.email}")
        anomalies = engine.scan_author(author)
        
        if anomalies:
            print(f" Found {len(anomalies)} anomaly(ies):")
            for i, anomaly in enumerate(anomalies, 1):
                print(f"\n{i}. {anomaly['type']}")
                print(f"   Severity: {anomaly['severity']}")
                print(f"   Description: {anomaly['description']}")
                print(f"   Recommendation: {anomaly['recommendation']}")
        else:
            print(" No anomalies detected for this author")
    else:
        print("  No authors found in database")
    
    # Test 2: Scan a specific reviewer
    print("\n\n TEST 2: Scanning Reviewer Behavior")
    print("-" * 70)
    
    reviewer = Profile.objects.filter(
        roles__name='REVIEWER'
    ).first()
    
    if reviewer:
        print(f"\nScanning reviewer: {reviewer.user.email}")
        anomalies = engine.scan_reviewer(reviewer)
        
        if anomalies:
            print(f" Found {len(anomalies)} anomaly(ies):")
            for i, anomaly in enumerate(anomalies, 1):
                print(f"\n{i}. {anomaly['type']}")
                print(f"   Severity: {anomaly['severity']}")
                print(f"   Description: {anomaly['description']}")
        else:
            print(" No anomalies detected for this reviewer")
    else:
        print("  No reviewers found in database")
    
    # Test 3: Scan a specific submission
    print("\n\n TEST 3: Scanning Submission")
    print("-" * 70)
    
    submission = Submission.objects.first()
    
    if submission:
        print(f"\nScanning submission: {submission.title}")
        print(f"Author: {submission.corresponding_author.user.email}")
        
        anomalies = engine.scan_submission(submission)
        
        if anomalies:
            print(f" Found {len(anomalies)} anomaly(ies):")
            for i, anomaly in enumerate(anomalies, 1):
                print(f"\n{i}. {anomaly['type']}")
                print(f"   Severity: {anomaly['severity']}")
                print(f"   Description: {anomaly['description']}")
        else:
            print(" No anomalies detected for this submission")
    else:
        print("  No submissions found in database")
    
    # Test 4: Get user risk score
    print("\n\n TEST 4: User Risk Assessment")
    print("-" * 70)
    
    if author:
        print(f"\nCalculating risk score for: {author.user.email}")
        risk_assessment = engine.get_user_risk_score(author)
        
        print(f"\n Risk Assessment Results:")
        print(f"   User: {risk_assessment['user_email']}")
        print(f"   Risk Score: {risk_assessment['risk_score']}")
        print(f"   Risk Level: {risk_assessment['risk_level']}")
        print(f"   Anomalies Found: {risk_assessment['anomaly_count']}")
        
        if risk_assessment['anomalies']:
            print(f"\n   Detected Issues:")
            for anomaly in risk_assessment['anomalies']:
                print(f"   • [{anomaly['severity']}] {anomaly['type']}: {anomaly['description']}")
    
    # Test 5: Detect review rings
    print("\n\n TEST 5: Detecting Review Rings")
    print("-" * 70)
    
    ring_anomalies = engine.detect_review_rings()
    
    if ring_anomalies:
        print(f" Found {len(ring_anomalies)} potential review ring(s):")
        for i, anomaly in enumerate(ring_anomalies, 1):
            print(f"\n{i}. Review Ring Detected")
            print(f"   Severity: {anomaly['severity']}")
            print(f"   User 1: {anomaly['user1']}")
            print(f"   User 2: {anomaly['user2']}")
            print(f"   Reciprocal Reviews: {anomaly['reciprocal_reviews']}")
            print(f"   Description: {anomaly['description']}")
    else:
        print(" No review rings detected")
    
    # Test 6: Comprehensive system scan
    print("\n\n TEST 6: Comprehensive System Scan")
    print("-" * 70)
    
    print("\n Running comprehensive anomaly scan...")
    print("   (This may take a moment...)")
    
    results = engine.scan_all()
    
    print(f"\n Scan Complete!")
    print(f"\n Summary:")
    print(f"   Total Anomalies: {results['total_count']}")
    print(f"\n   By Severity:")
    print(f"   • HIGH:   {results['severity_counts']['HIGH']}")
    print(f"   • MEDIUM: {results['severity_counts']['MEDIUM']}")
    print(f"   • LOW:    {results['severity_counts']['LOW']}")
    
    print(f"\n   By Category:")
    print(f"   • Author Anomalies:       {len(results['author_anomalies'])}")
    print(f"   • Reviewer Anomalies:     {len(results['reviewer_anomalies'])}")
    print(f"   • Review Ring Anomalies:  {len(results['review_ring_anomalies'])}")
    
    # Show sample anomalies
    if results['author_anomalies']:
        print(f"\n    Sample Author Anomalies:")
        for anomaly in results['author_anomalies'][:3]:
            print(f"   • [{anomaly['severity']}] {anomaly['type']}: {anomaly['description']}")
    
    if results['reviewer_anomalies']:
        print(f"\n    Sample Reviewer Anomalies:")
        for anomaly in results['reviewer_anomalies'][:3]:
            print(f"   • [{anomaly['severity']}] {anomaly['type']}: {anomaly['description']}")
    
    if results['review_ring_anomalies']:
        print(f"\n    Review Ring Anomalies:")
        for anomaly in results['review_ring_anomalies']:
            print(f"   • [{anomaly['severity']}] {anomaly['user1']} ↔ {anomaly['user2']}")
    
    # Test 7: Bot detection
    print("\n\n TEST 7: Bot Account Detection")
    print("-" * 70)
    
    print("\nScanning all profiles for bot-like behavior...")
    
    bot_count = 0
    profiles = Profile.objects.all()[:10]  # Sample first 10
    
    for profile in profiles:
        anomaly = engine.detect_bot_account(profile)
        if anomaly:
            bot_count += 1
            print(f"\n  Potential bot detected:")
            print(f"   User: {anomaly['user_email']}")
            print(f"   Suspicion Score: {anomaly['suspicion_score']}")
            print(f"   Reasons: {', '.join(anomaly['reasons'])}")
    
    if bot_count == 0:
        print(" No bot accounts detected in sample")
    else:
        print(f"\n  Found {bot_count} potential bot account(s)")
    
    print_separator("TEST COMPLETE")
    print("\n Anomaly Detection System is functional!")
    print("\n Available API Endpoints:")
    print("   GET  /api/v1/ml/anomaly-detection/scan/")
    print("   GET  /api/v1/ml/anomaly-detection/user/<user_id>/")
    print("   GET  /api/v1/ml/anomaly-detection/submission/<submission_id>/")
    print("   GET  /api/v1/ml/anomaly-detection/reviewer/<reviewer_id>/")
    print()


if __name__ == '__main__':
    try:
        test_anomaly_detection()
    except Exception as e:
        print(f"\n Error during testing: {e}")
        import traceback
        traceback.print_exc()
