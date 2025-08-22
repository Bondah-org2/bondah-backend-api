#!/usr/bin/env python
"""
Test Translation Endpoints
"""

import requests
import json

def test_translation_endpoints():
    """Test all translation endpoints"""
    print("🌐 TESTING TRANSLATION ENDPOINTS")
    print("=" * 50)
    
    base_url = "https://bondah-backend-api-production.up.railway.app"
    
    # Test 1: Get supported languages
    print("\n📋 Test 1: Get Supported Languages")
    print(f"URL: {base_url}/api/translate/languages/")
    
    try:
        response = requests.get(f"{base_url}/api/translate/languages/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Total languages: {data.get('total_languages', 'N/A')}")
            print(f"Sample languages: {list(data.get('languages', {}).keys())[:5]}")
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False
    
    # Test 2: Translate text
    print("\n📋 Test 2: Translate Text")
    print(f"URL: {base_url}/api/translate/")
    
    try:
        data = {
            "text": "Hello, how are you?",
            "source_language": "auto",
            "target_language": "es"
        }
        
        response = requests.post(
            f"{base_url}/api/translate/",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"Translated: {result.get('translation', {}).get('translated_text', 'N/A')}")
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False
    
    # Test 3: Get translation history
    print("\n📋 Test 3: Get Translation History")
    print(f"URL: {base_url}/api/translate/history/")
    
    try:
        response = requests.get(f"{base_url}/api/translate/history/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Total translations: {len(data.get('translations', []))}")
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False
    
    # Test 4: Get translation stats
    print("\n📋 Test 4: Get Translation Stats")
    print(f"URL: {base_url}/api/translate/stats/")
    
    try:
        response = requests.get(f"{base_url}/api/translate/stats/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Stats: {data.get('stats', {})}")
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False
    
    print("\n🎉 ALL TRANSLATION ENDPOINTS ARE WORKING!")
    return True

if __name__ == "__main__":
    success = test_translation_endpoints()
    exit(0 if success else 1)
