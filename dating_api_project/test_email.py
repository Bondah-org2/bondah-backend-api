#!/usr/bin/env python
"""
Test script to verify email configuration for Bondah Dating
Run this after setting up your custom domain email
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_email_configuration():
    """Test the email configuration"""
    
    # Get email settings from environment
    email_host = os.getenv('EMAIL_HOST', 'mail.bondah.org')
    email_port = int(os.getenv('EMAIL_PORT', '587'))
    email_use_tls = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    email_use_ssl = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
    email_user = os.getenv('EMAIL_HOST_USER', 'noreply@bondah.org')
    email_password = os.getenv('EMAIL_HOST_PASSWORD', '')
    from_email = os.getenv('DEFAULT_FROM_EMAIL', email_user)
    
    print("🔧 Testing Email Configuration for Bondah Dating")
    print("=" * 50)
    print(f"SMTP Host: {email_host}")
    print(f"SMTP Port: {email_port}")
    print(f"Use TLS: {email_use_tls}")
    print(f"Use SSL: {email_use_ssl}")
    print(f"Email User: {email_user}")
    print(f"From Email: {from_email}")
    print("=" * 50)
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email_user  # Send to yourself for testing
        msg['Subject'] = "🧪 Bondah Dating - Email Configuration Test"
        
        body = """
        Hello from Bondah Dating!
        
        This is a test email to verify that your email configuration is working correctly.
        
        If you received this email, your SMTP settings are properly configured.
        
        Best regards,
        Bondah Dating Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        print("📡 Connecting to SMTP server...")
        if email_use_ssl:
            server = smtplib.SMTP_SSL(email_host, email_port)
            print("🔒 Using SSL connection...")
        else:
            server = smtplib.SMTP(email_host, email_port)
            if email_use_tls:
                print("🔒 Starting TLS encryption...")
                server.starttls()
        
        # Login
        print("🔑 Logging in...")
        server.login(email_user, email_password)
        
        # Send email
        print("📤 Sending test email...")
        text = msg.as_string()
        server.sendmail(from_email, email_user, text)
        
        # Close connection
        server.quit()
        
        print("✅ Email configuration test successful!")
        print("📧 Check your inbox for the test email")
        
    except Exception as e:
        print(f"❌ Email configuration test failed: {str(e)}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your SMTP host and port")
        print("2. Verify your email credentials")
        print("3. Ensure TLS is enabled if required")
        print("4. Check if your provider allows SMTP access")

if __name__ == "__main__":
    test_email_configuration()
