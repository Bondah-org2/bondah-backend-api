#!/usr/bin/env python
"""
Test different SMTP hosts for Roundcube webmail
"""

import smtplib
import socket

def test_smtp_host(host, port=587):
    """Test if an SMTP host is reachable"""
    try:
        print(f"🔍 Testing {host}:{port}...")
        
        # Test connection
        server = smtplib.SMTP(host, port, timeout=10)
        server.quit()
        
        print(f"✅ {host}:{port} is reachable!")
        return True
        
    except socket.timeout:
        print(f"⏰ {host}:{port} - Connection timeout")
        return False
    except socket.gaierror:
        print(f"❌ {host}:{port} - Host not found")
        return False
    except Exception as e:
        print(f"❌ {host}:{port} - Error: {str(e)}")
        return False

def main():
    """Test common SMTP hosts"""
    print("🔧 Testing Common SMTP Hosts for Roundcube")
    print("=" * 50)
    
    # Common SMTP hosts to test
    hosts_to_test = [
        ("mail.bondah.org", 587),
        ("smtp.bondah.org", 587),
        ("mail.bondah.org", 465),
        ("smtp.bondah.org", 465),
        ("bondah.org", 587),
        ("smtpout.secureserver.net", 587),  # GoDaddy
        ("mail.yourdomain.org", 587),  # Generic
    ]
    
    working_hosts = []
    
    for host, port in hosts_to_test:
        if test_smtp_host(host, port):
            working_hosts.append((host, port))
    
    print("\n" + "=" * 50)
    print("📋 Results Summary:")
    
    if working_hosts:
        print("✅ Working SMTP hosts:")
        for host, port in working_hosts:
            print(f"   - {host}:{port}")
        
        print("\n🎯 Recommended configuration:")
        best_host, best_port = working_hosts[0]
        print(f"EMAIL_HOST={best_host}")
        print(f"EMAIL_PORT={best_port}")
        print(f"EMAIL_USE_TLS=True")
        
    else:
        print("❌ No working SMTP hosts found")
        print("💡 Contact your hosting provider for SMTP settings")

if __name__ == "__main__":
    main()
