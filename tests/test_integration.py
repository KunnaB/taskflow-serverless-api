import requests
import os

def test_api_responds():
    """Test that API Gateway is reachable"""
    api_url = os.environ.get('API_URL', 'https://nqo9rfa75i.execute-api.us-east-1.amazonaws.com/prod/tasks')
    
    try:
        # OPTIONS request should work without auth (CORS preflight)
        response = requests.options(api_url, timeout=5)
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"
        print("✅ Integration test passed: API is reachable")
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise

if __name__ == '__main__':
    test_api_responds()
    print("\n✅ Integration test passed!")
