import pytest
from app.core.settings import Settings, JWTSettings, DatabaseSettings, TemporalSettings

def test_d2_complete_production_config_contract():
    print("==========================================================================")
    print("  PHASE D.2 VERIFICATION: COMPLETE PRODUCTION CONFIGURATION CONTRACT   ")
    print("==========================================================================")

    # 1. Test Development Configuration (Must Pass Cleanly)
    dev_settings = Settings(env="development")
    dev_settings.validate_production_configuration()
    print("  [PASS] Development Environment Configuration Validation: PASS")

    # 2. Negative Test 1: Insecure CORS in Production
    try:
        s_cors = Settings.model_construct(
            env="production",
            cors_origins=["http://localhost:5173"],
            jwt=JWTSettings.model_construct(secret="production_ultra_secure_secret_key_987654321"),
            db=DatabaseSettings.model_construct(mongo_uri="mongodb+srv://prod-cluster.mongodb.net", database_name="fluxa_prod"),
            temporal=TemporalSettings.model_construct(host="temporal.prod.internal:7233")
        )
        s_cors.validate_production_configuration()
        assert False, "FAIL-CLOSED VIOLATION! Unsafe CORS allowed in ENV=production!"
    except RuntimeError as e:
        print(f"  [PASS] Negative Test 1 — Insecure CORS Blocked: {str(e)}")

    # 3. Negative Test 2: Insecure Placeholder JWT Secret in Production
    try:
        s_jwt_placeholder = Settings.model_construct(
            env="production",
            cors_origins=["https://app.fluxa.ai"],
            jwt=JWTSettings.model_construct(secret="super_secret_key_change_me"),
            db=DatabaseSettings.model_construct(mongo_uri="mongodb+srv://prod-cluster.mongodb.net", database_name="fluxa_prod"),
            temporal=TemporalSettings.model_construct(host="temporal.prod.internal:7233")
        )
        s_jwt_placeholder.validate_production_configuration()
        assert False, "FAIL-CLOSED VIOLATION! Placeholder JWT_SECRET allowed in ENV=production!"
    except RuntimeError as e:
        print(f"  [PASS] Negative Test 2 — Placeholder JWT Secret Blocked: {str(e)}")

    # 4. Negative Test 3: Weak Short JWT Secret (< 16 chars) in Production
    try:
        s_jwt_weak = Settings.model_construct(
            env="production",
            cors_origins=["https://app.fluxa.ai"],
            jwt=JWTSettings.model_construct(secret="short_key_123"),
            db=DatabaseSettings.model_construct(mongo_uri="mongodb+srv://prod-cluster.mongodb.net", database_name="fluxa_prod"),
            temporal=TemporalSettings.model_construct(host="temporal.prod.internal:7233")
        )
        s_jwt_weak.validate_production_configuration()
        assert False, "FAIL-CLOSED VIOLATION! Weak JWT_SECRET allowed in ENV=production!"
    except RuntimeError as e:
        print(f"  [PASS] Negative Test 3 — Weak Short JWT Secret Blocked: {str(e)}")

    # 5. Negative Test 4: Localhost MONGO_URI in Production
    try:
        s_db = Settings.model_construct(
            env="production",
            cors_origins=["https://app.fluxa.ai"],
            jwt=JWTSettings.model_construct(secret="production_ultra_secure_secret_key_987654321"),
            db=DatabaseSettings.model_construct(mongo_uri="mongodb://localhost:27017", database_name="fluxa_prod"),
            temporal=TemporalSettings.model_construct(host="temporal.prod.internal:7233")
        )
        s_db.validate_production_configuration()
        assert False, "FAIL-CLOSED VIOLATION! Localhost MONGO_URI allowed in ENV=production!"
    except RuntimeError as e:
        print(f"  [PASS] Negative Test 4 — Localhost MONGO_URI Blocked: {str(e)}")

    # 6. Negative Test 5: Localhost TEMPORAL_HOST in Production
    try:
        s_temp = Settings.model_construct(
            env="production",
            cors_origins=["https://app.fluxa.ai"],
            jwt=JWTSettings.model_construct(secret="production_ultra_secure_secret_key_987654321"),
            db=DatabaseSettings.model_construct(mongo_uri="mongodb+srv://prod-cluster.mongodb.net", database_name="fluxa_prod"),
            temporal=TemporalSettings.model_construct(host="localhost:7233")
        )
        s_temp.validate_production_configuration()
        assert False, "FAIL-CLOSED VIOLATION! Localhost TEMPORAL_HOST allowed in ENV=production!"
    except RuntimeError as e:
        print(f"  [PASS] Negative Test 5 — Localhost TEMPORAL_HOST Blocked: {str(e)}")

    # 7. Positive Test: Complete Valid Production Configuration Contract (Must Pass Cleanly)
    s_valid = Settings.model_construct(
        env="production",
        cors_origins=["https://app.fluxa.ai", "https://admin.fluxa.ai"],
        jwt=JWTSettings.model_construct(secret="production_ultra_secure_secret_key_987654321"),
        db=DatabaseSettings.model_construct(mongo_uri="mongodb+srv://prod-cluster.mongodb.net", database_name="fluxa_prod"),
        temporal=TemporalSettings.model_construct(host="temporal.prod.internal:7233")
    )
    s_valid.validate_production_configuration()
    print("  [PASS] Complete Valid Production Configuration Contract: PASS")

    print("\n==========================================================================")
    print("  ALL PHASE D.2 COMPLETE PRODUCTION CONFIGURATION INVARIANTS PASSED ")
    print("==========================================================================")

if __name__ == "__main__":
    test_d2_complete_production_config_contract()
