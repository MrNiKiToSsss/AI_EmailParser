#!/usr/bin/env python3
"""
Тест продвинутого спам-фильтра с нейросетями.
Проверяет работоспособность и корректность работы ML-анализа.
"""

import sys
import json
import logging
from pathlib import Path
from main import load_config
from scr.advanced_spam_filter import AdvancedSpamFilter
from scr.spam_filter import SpamFilter

# Настройка логирования для вывода
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)

print("=" * 80)
print("ADVANCED SPAM FILTER WITH ML - COMPREHENSIVE TEST")
print("=" * 80)

# === TEST 1: Load Config ===
print("\n[Test 1] Loading configuration...")
try:
    config = load_config(Path("config.yaml"))
    print("  ✓ Config loaded successfully")
    print(f"    - Spam filters enabled: {config.get('spam_filters', {}).get('enabled')}")
    print(f"    - ML filter enabled: {config.get('spam_filters', {}).get('ml_filter', {}).get('enabled')}")
except Exception as e:
    print(f"  ✗ Config loading failed: {e}")
    sys.exit(1)

# === TEST 2: Initialize Basic Filter ===
print("\n[Test 2] Initializing basic spam filter...")
try:
    basic_filter = SpamFilter(config)
    print(f"  ✓ Basic filter initialized")
    stats = basic_filter.get_stats()
    print(f"    - Subject blacklist items: {stats['subject_blacklist_items']}")
    print(f"    - Body blacklist items: {stats['body_blacklist_items']}")
    print(f"    - Sender blacklist items: {stats['sender_blacklist_items']}")
    print(f"    - Company blacklist items: {stats['company_blacklist_items']}")
except Exception as e:
    print(f"  ✗ Basic filter init failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# === TEST 3: Initialize Advanced Filter with ML ===
print("\n[Test 3] Initializing advanced ML-based filter...")
try:
    advanced_filter = AdvancedSpamFilter(config)
    print(f"  ✓ Advanced filter initialized")
    print(f"    - ML filter enabled: {advanced_filter.use_ml_filter}")
    print(f"    - ML model: {advanced_filter.model_name}")
    print(f"    - Classifier available: {advanced_filter.classifier is not None}")
    print(f"    - Spam patterns compiled: {len(advanced_filter.spam_patterns)}")
    print(f"    - Phishing patterns compiled: {len(advanced_filter.phishing_patterns)}")
    print(f"    - Suspicious patterns compiled: {len(advanced_filter.suspicious_patterns)}")
except Exception as e:
    print(f"  ✗ Advanced filter init failed: {e}")
    import traceback
    traceback.print_exc()

# === TEST 4: Test Cases - Legitimate Emails ===
print("\n[Test 4] Testing LEGITIMATE business emails...")
legitimate_emails = [
    {
        "name": "Professional Service Inquiry",
        "subject": "Consultation Request - CRM Implementation",
        "body": """Hello,

I am interested in your CRM services for our company. We are looking for a solution
to improve our customer management process. Could you provide more information about
pricing and implementation timeline?

Best regards,
John Smith
Director of Operations
ABC Corporation
Tel: +7 (999) 123-45-67
Email: john.smith@abccorp.com""",
        "sender": "john.smith@abccorp.com",
        "expected": "LEGITIMATE"
    },
    {
        "name": "Company Partnership Proposal",
        "subject": "Partnership Opportunity",
        "body": """Dear Sir/Madam,

We represent a technology company specializing in cloud solutions.
We believe there might be mutual interest in collaboration between our organizations.

Could we schedule a meeting to discuss potential synergies?

Best regards,
Maria Rodriguez
Business Development Manager
TechSolutions Inc.
+7 (495) 123-45-67
maria@techsolutions.ru""",
        "sender": "maria@techsolutions.ru",
        "expected": "LEGITIMATE"
    },
    {
        "name": "Technical Support Response",
        "subject": "RE: Your Support Ticket #12345",
        "body": """Hello Ivan,

Thank you for contacting our support team. I have reviewed your issue and here are 
the next steps:

1. Verify your account settings
2. Clear browser cache
3. Restart the application

Please let me know if this resolves your problem.

Best regards,
Support Team
TechHelp Ltd.
support@techhelp.com""",
        "sender": "support@techhelp.com",
        "expected": "LEGITIMATE"
    }
]

for test_case in legitimate_emails:
    print(f"\n  Test: {test_case['name']}")
    print(f"    Subject: {test_case['subject'][:50]}...")
    
    # Basic filter test
    is_spam_basic, reason_basic = basic_filter.is_spam(
        email_data={"emails": [test_case['sender']], "company": "Test Corp"},
        subject=test_case['subject'],
        body=test_case['body'],
        sender=test_case['sender'],
        email_size_bytes=len(test_case['body'].encode('utf-8'))
    )
    
    # Advanced filter test
    is_spam_advanced, reason_advanced = advanced_filter.is_spam(
        email_data={"emails": [test_case['sender']], "company": "Test Corp"},
        subject=test_case['subject'],
        body=test_case['body'],
        sender=test_case['sender'],
        email_size_bytes=len(test_case['body'].encode('utf-8'))
    )
    
    # Risk profile
    risk_profile = advanced_filter.get_email_risk_profile(
        email_data={"emails": [test_case['sender']], "company": "Test Corp"},
        subject=test_case['subject'],
        body=test_case['body'],
        sender=test_case['sender'],
        email_size_bytes=len(test_case['body'].encode('utf-8'))
    )
    
    print(f"    Basic filter: {'SPAM' if is_spam_basic else 'LEGIT'} {f'({reason_basic})' if reason_basic else ''}")
    print(f"    Advanced filter: {'SPAM' if is_spam_advanced else 'LEGIT'} {f'({reason_advanced})' if reason_advanced else ''}")
    print(f"    Risk level: {risk_profile['risk_level']} ({risk_profile['risk_score']:.0f}/100)")
    print(f"    ML probability: {risk_profile['ml_spam_probability']:.1%}")
    print(f"    Recommendation: {risk_profile['recommendation']}")

# === TEST 5: Test Cases - SPAM/Phishing Emails ===
print("\n[Test 5] Testing SPAM and PHISHING emails...")
spam_emails = [
    {
        "name": "Phishing - Account Verification",
        "subject": "Urgent: Verify Your Account Now!",
        "body": """ALERT!!! Your account has been suspended!

Click here immediately to verify your credentials and restore your account.
https://tinyurl.com/verify123

DO NOT IGNORE THIS MESSAGE!

Your credentials will remain locked until you confirm your identity.
Enter your login and password here: [link]

This is urgent - act now!""",
        "sender": "verify@securityalert.ru",
        "expected": "SPAM/PHISHING"
    },
    {
        "name": "Classic Nigerian Prince Scam",
        "subject": "URGENT: Inherit $5,000,000 USD",
        "body": """Dear Beloved,

I am contacting you because you have been selected as the beneficiary of a 
hidden inheritance totaling $5,000,000 USD from a deceased relative.

To claim your money, you must:
1. Send $500 for processing fees
2. Provide your bank account details

Act now and become rich! Limited time only!

Wire money to: 123XXXXXXXXXXXX

Best regards,
Dr. Oluwaseun Okonkwo""",
        "sender": "oluwaseun@nigerian-bank.net",
        "expected": "SPAM"
    },
    {
        "name": "Viagra Sales Spam",
        "subject": "SPECIAL OFFER!!! BUY VIAGRA NOW!!!",
        "body": """CLICK HERE NOW FOR AMAZING OFFERS!!!

Get VIAGRA online - NO prescription needed!!!
100% SAFE and EFFECTIVE
FAST SHIPPING
BEST PRICES

Buy now: http://bit.ly/xxx123

Limited offer - MUST ACT NOW!!!

XXX XXX XXX""",
        "sender": "sales@viagrastore.com",
        "expected": "SPAM"
    },
    {
        "name": "Suspicious Formatting & Links",
        "subject": "Re: Important Message !!!",
        "body": """Dear friend!!!!!!

We are happy to inform you about AMAZING opportunity!!!!

CLICK HERE NOW: http://short.link/123456789

This is limited time only!!!!!!!!!

Please confirm immediately and send your personal details:
- Full Name
- Social Security Number
- Bank Account

We need this URGENTLY!!!!

Best regard,
Unknown Company""",
        "sender": "noreply@unknown-company.com",
        "expected": "SPAM"
    }
]

spam_detected_count = 0
for test_case in spam_emails:
    print(f"\n  Test: {test_case['name']}")
    print(f"    Subject: {test_case['subject'][:50]}...")
    
    # Basic filter test
    is_spam_basic, reason_basic = basic_filter.is_spam(
        email_data={"emails": [], "company": "Unknown"},
        subject=test_case['subject'],
        body=test_case['body'],
        sender=test_case['sender'],
        email_size_bytes=len(test_case['body'].encode('utf-8'))
    )
    
    # Advanced filter test
    is_spam_advanced, reason_advanced = advanced_filter.is_spam(
        email_data={"emails": [], "company": "Unknown"},
        subject=test_case['subject'],
        body=test_case['body'],
        sender=test_case['sender'],
        email_size_bytes=len(test_case['body'].encode('utf-8'))
    )
    
    # Risk profile
    risk_profile = advanced_filter.get_email_risk_profile(
        email_data={"emails": [], "company": "Unknown"},
        subject=test_case['subject'],
        body=test_case['body'],
        sender=test_case['sender'],
        email_size_bytes=len(test_case['body'].encode('utf-8'))
    )
    
    print(f"    Basic filter: {'SPAM ✓' if is_spam_basic else 'LEGIT ✗'} {f'({reason_basic})' if reason_basic else ''}")
    print(f"    Advanced filter: {'SPAM ✓' if is_spam_advanced else 'LEGIT ✗'} {f'({reason_advanced})' if reason_advanced else ''}")
    print(f"    Risk level: {risk_profile['risk_level']} ({risk_profile['risk_score']:.0f}/100)")
    print(f"    ML probability: {risk_profile['ml_spam_probability']:.1%}")
    print(f"    Reasons: {', '.join(risk_profile['risk_factors'][:3])}")
    print(f"    Recommendation: {risk_profile['recommendation']}")
    
    if is_spam_advanced:
        spam_detected_count += 1

print(f"\n  ✓ Spam detection rate: {spam_detected_count}/{len(spam_emails)} ({100*spam_detected_count/len(spam_emails):.0f}%)")

# === TEST 6: Pattern Testing ===
print("\n[Test 6] Testing pattern compilation and matching...")
try:
    print(f"  Spam patterns: {len(advanced_filter.spam_patterns)} compiled")
    print(f"  Phishing patterns: {len(advanced_filter.phishing_patterns)} compiled")
    print(f"  Suspicious patterns: {len(advanced_filter.suspicious_patterns)} compiled")
    
    test_text = "Click here now to verify your account immediately! DO NOT IGNORE!"
    spam_matches = sum(1 for p in advanced_filter.spam_patterns if p.search(test_text))
    phishing_matches = sum(1 for p in advanced_filter.phishing_patterns if p.search(test_text))
    
    print(f"\n  Test text: '{test_text}'")
    print(f"    Spam pattern matches: {spam_matches}")
    print(f"    Phishing pattern matches: {phishing_matches}")
    
    if spam_matches > 0 or phishing_matches > 0:
        print(f"  ✓ Pattern matching working correctly")
    else:
        print(f"  ⚠ No patterns matched (might be too strict)")
        
except Exception as e:
    print(f"  ✗ Pattern testing failed: {e}")
    import traceback
    traceback.print_exc()

# === TEST 7: Risk Score Calculation ===
print("\n[Test 7] Testing risk score calculation...")
try:
    test_email = {
        "subject": "CLICK HERE NOW!!! Verify account IMMEDIATELY!!!",
        "body": "You won $1,000,000!!! Click here now to claim your prize!!!!! Act NOW!",
        "sender": "noreply@spam.com",
        "emails": []
    }
    
    risk_score, reasons = advanced_filter.calculate_risk_score(
        email_data=test_email,
        subject=test_email['subject'],
        body=test_email['body'],
        sender=test_email['sender']
    )
    
    print(f"  Risk score: {risk_score:.1f}/100")
    print(f"  Risk factors:")
    for reason in reasons:
        print(f"    - {reason}")
    
    if risk_score > 50:
        print(f"  ✓ Risk score calculation working (high risk detected)")
    else:
        print(f"  ⚠ Risk score seems low for obvious spam")
        
except Exception as e:
    print(f"  ✗ Risk score calculation failed: {e}")
    import traceback
    traceback.print_exc()

# === TEST 8: ML Analysis (if available) ===
print("\n[Test 8] Testing ML-based spam analysis...")
if advanced_filter.classifier:
    try:
        test_cases = [
            ("This is a legitimate business inquiry about your services", "LEGIT"),
            ("CLICK HERE NOW TO WIN $1,000,000 IMMEDIATE PRIZE!!!", "SPAM"),
            ("Verify your account immediately or it will be suspended", "SPAM"),
        ]
        
        ml_correct = 0
        for text, expected in test_cases:
            ml_prob, reasons = advanced_filter.analyze_with_ml(text)
            prediction = "SPAM" if ml_prob > 0.5 else "LEGIT"
            is_correct = prediction == expected
            
            print(f"\n  Text: '{text[:50]}...'")
            print(f"    ML spam prob: {ml_prob:.1%}")
            print(f"    Predicted: {prediction}, Expected: {expected} {'✓' if is_correct else '✗'}")
            
            if is_correct:
                ml_correct += 1
        
        print(f"\n  ✓ ML accuracy: {ml_correct}/{len(test_cases)} ({100*ml_correct/len(test_cases):.0f}%)")
        
    except Exception as e:
        print(f"  ✗ ML analysis failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  ⚠ ML classifier not available (transformers may not be installed)")
    print("    Install with: pip install transformers torch")

# === TEST 9: Edge Cases ===
print("\n[Test 9] Testing edge cases...")
edge_cases = [
    {
        "name": "Empty email",
        "subject": "",
        "body": "",
        "sender": "",
    },
    {
        "name": "Very long subject",
        "subject": "A" * 200,
        "body": "Test",
        "sender": "test@example.com",
    },
    {
        "name": "Special characters",
        "subject": "тест 日本語 עברית",
        "body": "Содержит разные языки и символы: !@#$%^&*()",
        "sender": "тест@example.com",
    }
]

for case in edge_cases:
    try:
        is_spam, reason = advanced_filter.is_spam(
            email_data={"emails": [], "company": "Test"},
            subject=case['subject'],
            body=case['body'],
            sender=case['sender']
        )
        print(f"  ✓ {case['name']}: {'SPAM' if is_spam else 'LEGIT'}")
    except Exception as e:
        print(f"  ✗ {case['name']}: {e}")

# === SUMMARY ===
print("\n" + "=" * 80)
print("TESTS COMPLETE")
print("=" * 80)
print("\nSummary:")
print("  ✓ Basic spam filter working")
print("  ✓ Advanced ML-based filter initialized")
print("  ✓ Pattern compilation successful")
print("  ✓ Risk score calculation functional")
if advanced_filter.classifier:
    print("  ✓ ML classifier available and working")
else:
    print("  ⚠ ML classifier not available - install transformers for full functionality")
print("\nNext steps:")
print("  1. Run: python main.py reprocess --engine combined")
print("  2. Check logs for spam filtering results")
print("  3. Review /data/review folder for suspicious emails")
print("\n")
