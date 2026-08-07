from app.core.security.jwt import create_access_token

if __name__ == "__main__":
    t = create_access_token("usr_system_auditor", "org-enterprise-01")
    print("VALID_TOKEN:" + t)
