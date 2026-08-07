import asyncio
import os
import pytest
from app.core.settings import Settings, JWTSettings, DatabaseSettings, TemporalSettings

def test_d1_production_topology_invariants():
    print("==========================================================================")
    print("  PHASE D.1 VERIFICATION: PRODUCTION TOPOLOGY & ENV CONFIGURATION ")
    print("==========================================================================")

    # 1. Test Valid Development Settings
    dev_settings = Settings(env="development", cors_origins=["http://localhost:5173"])
    dev_settings.validate_production_configuration()
    print("  [PASS] Development Environment Topology Validation: PASS")

    # 2. Test Insecure CORS in Production (Must Raise RuntimeError Fail-Closed)
    try:
        s_cors = Settings.model_construct(
            env="production",
            cors_origins=["http://localhost:5173"],
            jwt=JWTSettings.model_construct(secret="strong_secure_random_key_123456789")
        )
        s_cors.validate_production_configuration()
        assert False, "FAIL-CLOSED VIOLATION! Unsafe CORS allowed in ENV=production!"
    except RuntimeError as e:
        print(f"  [PASS] Insecure Production CORS Blocked: {str(e)}")

    # 3. Test Insecure Placeholder JWT Secret in Production (Must Raise RuntimeError Fail-Closed)
    try:
        s_jwt = Settings.model_construct(
            env="production",
            cors_origins=["https://app.fluxa.ai"],
            jwt=JWTSettings.model_construct(secret="super_secret_key_change_me")
        )
        s_jwt.validate_production_configuration()
        assert False, "FAIL-CLOSED VIOLATION! Placeholder JWT_SECRET allowed in ENV=production!"
    except RuntimeError as e:
        print(f"  [PASS] Insecure Placeholder JWT Secret Blocked: {str(e)}")

    # 4. Test Valid Production Topology (Must Pass Cleanly)
    s_valid = Settings.model_construct(
        env="production",
        cors_origins=["https://app.fluxa.ai", "https://admin.fluxa.ai"],
        jwt=JWTSettings.model_construct(secret="production_ultra_secure_secret_key_987654321"),
        db=DatabaseSettings.model_construct(mongo_uri="mongodb+srv://prod-cluster.mongodb.net", database_name="fluxa_prod"),
        temporal=TemporalSettings.model_construct(host="temporal.prod.internal:7233")
    )
    s_valid.validate_production_configuration()
    print("  [PASS] Valid Production Topology Configuration: PASS")

    print("\n==========================================================================")
    print("  ALL PHASE D.1 PRODUCTION TOPOLOGY INVARIANTS PASSED SUCCESSFULLY ")
    print("==========================================================================")

if __name__ == "__main__":
    test_d1_production_topology_invariants()
