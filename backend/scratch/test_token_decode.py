from app.core.security.jwt import decode_access_token

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3Jfc3lzdGVtX2F1ZGl0b3IiLCJvcmdfaWQiOiJvcmctZW50ZXJwcmlzZS0wMSIsIndzX2lkIjoiZGVmYXVsdC13IiwiZW52X2lkIjoiZGVmYXVsdC1lIiwicHJval9pZCI6ImRlZmF1bHQtcCIsImV4cCI6MTc4NjA0Mjk1Mn0._enBviek09UiDqmY_5VjZIkkIryJHOSg3QA6bonZf0c"
try:
    ctx = decode_access_token(token)
    print("DECODE_SUCCESS:", ctx)
except Exception as e:
    print("DECODE_FAILED:", e)
