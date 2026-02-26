#!/usr/bin/env python
"""
Force Railway Redeploy
"""
import os
import time

def force_redeploy():
    """Force Railway to redeploy by updating a file"""
    print("🚀 FORCING RAILWAY REDEPLOY")
    print("=" * 40)
    
    # Create a timestamp file to force redeploy
    timestamp = int(time.time())
    
    with open('DEPLOY_TIMESTAMP.txt', 'w') as f:
        f.write(f"Last deploy: {timestamp}\n")
        f.write("This file forces Railway to redeploy\n")
    
    print(f"✅ Created DEPLOY_TIMESTAMP.txt with timestamp: {timestamp}")
    print("📋 Railway will detect the change and auto-redeploy")
    print("⏳ Wait 2-3 minutes for deployment to complete")

if __name__ == "__main__":
    force_redeploy()
