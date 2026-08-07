from app.core.security.jwt import create_access_token
from datetime import timedelta

if __name__ == "__main__":
    t = create_access_token("usr_system_auditor", "org-enterprise-01", expires_delta=timedelta(days=3650))
    print("LONG_DEV_TOKEN:" + t)
