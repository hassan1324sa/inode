import os
import sys
import uuid
import json
import base64
import time
import urllib.request
import urllib.error

BASE_URL = os.environ.get("API_BASE_URL")
if not BASE_URL:
    print("API_BASE_URL environment variable is required")
    sys.exit(1)

def print_section(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def decode_jwt_without_verify(token):
    try:
        header, payload, signature = token.split('.')
        # add padding
        header_pad = header + '=' * (-len(header) % 4)
        payload_pad = payload + '=' * (-len(payload) % 4)
        
        decoded_header = base64.urlsafe_b64decode(header_pad).decode('utf-8')
        decoded_payload = base64.urlsafe_b64decode(payload_pad).decode('utf-8')
        return json.loads(decoded_header), json.loads(decoded_payload)
    except Exception as e:
        print(f"Failed to decode token: {e}")
        return None, None

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    if data:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except urllib.error.URLError as e:
        return 0, str(e)

def main():
    email = os.environ.get("DEBUG_EMAIL")
    password = os.environ.get("DEBUG_PASSWORD")
    if not email or not password:
        print("DEBUG_EMAIL and DEBUG_PASSWORD environment variables are required")
        sys.exit(1)
    
    print_section("1. Registering User")
    status, body = make_request(f"{BASE_URL}/auth/register", method="POST", data={
        "email": email,
        "password": password,
        "name": "Test User"
    })
    print(f"Status: {status}")
    print(f"Body: {body}")
    
    print_section("2. Logging In")
    status, body = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": email,
        "password": password
    })
    print(f"Status: {status}")
    
    try:
        log_data = json.loads(body)
        print(f"Response Keys: {list(log_data.keys())}")
    except Exception:
        print("Failed to parse login response as JSON")
        return
    
    token = log_data.get("access_token")
    if not token:
        print("No access token returned!")
        return
        
    print_section("3. Decoding JWT")
    header, payload = decode_jwt_without_verify(token)
    print(f"Header: {json.dumps(header, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    exp = payload.get('exp')
    current_time = time.time()
    print(f"Exp: {exp}")
    print(f"Current UTC Timestamp (Unix): {current_time}")
    
    if exp:
        if exp < current_time:
            print("TOKEN IS EXPIRED!")
        else:
            print(f"Token is valid for {exp - current_time} more seconds.")
    else:
        print("NO EXPIRATION SET")
        
    print_section("4. Testing Authenticated Request")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    status, body = make_request(f"{BASE_URL}/workflows/", headers=headers)
    print(f"Status: {status}")
    print(f"Body: {body}")

if __name__ == "__main__":
    main()
