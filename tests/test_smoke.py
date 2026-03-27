import requests
import os
import sys

def test_api_health():
    """Smoke test: Verify API responds"""
    api_url = os.environ.get('API_URL', 'https://nqo9rfa75i.execute-api.us-east-1.amazonaws.com/prod/tasks')
    
    print(f"Testing API: {api_url}")
    
    # Test OPTIONS (CORS)
    response = requests.options(api_url, timeout=10)
    assert response.status_code in [200, 403], f"OPTIONS failed: {response.status_code}"
    print("✅ CORS preflight works")
    
    # Test GET without auth (should return 401)
    response = requests.get(api_url, timeout=10)
    assert response.status_code == 401, f"Expected 401 (unauthorized), got {response.status_code}"
    print("✅ Auth required (as expected)")
    
    print("\n✅ All smoke tests passed! API is healthy.")

if __name__ == '__main__':
    test_api_health()
