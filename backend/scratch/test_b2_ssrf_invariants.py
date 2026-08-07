import asyncio
import socket
from app.core.security.ssrf_guard import validate_url_security, is_ip_restricted
from app.core.security.context import SecurityException

async def test_phase_b2_ssrf_security_invariants():
    print("================================================================")
    print("  PHASE B.2 REMEDIATION VERIFICATION: P1 SSRF & DNS GUARD     ")
    print("================================================================")

    # ---------------------------------------------------------------------
    # SECURITY INVARIANT 1: Loopback & Localhost Blocking
    # ---------------------------------------------------------------------
    print("\n[TEST 1] Testing Direct Loopback & Localhost Target Blocking...")
    loopback_targets = [
        "http://127.0.0.1",
        "http://127.0.0.1:8000/api/v1/internal",
        "http://localhost",
        "http://localhost:3000",
        "http://[::1]"
    ]
    for target in loopback_targets:
        try:
            validate_url_security(target)
            assert False, f"SSRF SECURITY VIOLATION! Target '{target}' was NOT blocked!"
        except SecurityException as e:
            print(f"[PASS] Loopback Target '{target}' Blocked Successfully: {str(e)}")

    # ---------------------------------------------------------------------
    # SECURITY INVARIANT 2: Cloud Metadata API Blocking (AWS, GCP, Azure, etc.)
    # ---------------------------------------------------------------------
    print("\n[TEST 2] Testing Cloud Metadata IP & Domain Target Blocking...")
    metadata_targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/user-data",
        "http://metadata.google.internal/computeMetadata/v1/"
    ]
    for target in metadata_targets:
        try:
            validate_url_security(target)
            assert False, f"SSRF SECURITY VIOLATION! Cloud Metadata target '{target}' was NOT blocked!"
        except SecurityException as e:
            print(f"[PASS] Cloud Metadata Target '{target}' Blocked Successfully: {str(e)}")

    # ---------------------------------------------------------------------
    # SECURITY INVARIANT 3: Private Subnet (RFC 1918 / IPv6 ULA / Link-Local) Blocking
    # ---------------------------------------------------------------------
    print("\n[TEST 3] Testing Private CIDR Subnet Target Blocking...")
    private_subnet_ips = [
        "http://10.0.0.1",
        "http://10.255.255.254",
        "http://172.16.0.1",
        "http://172.31.255.255",
        "http://192.168.1.1",
        "http://192.168.100.50"
    ]
    for target in private_subnet_ips:
        try:
            validate_url_security(target)
            assert False, f"SSRF SECURITY VIOLATION! Private IP target '{target}' was NOT blocked!"
        except SecurityException as e:
            print(f"[PASS] Private Subnet Target '{target}' Blocked Successfully: {str(e)}")

    # ---------------------------------------------------------------------
    # SECURITY INVARIANT 4: Scheme Injection & Protocol Smuggling Prevention
    # ---------------------------------------------------------------------
    print("\n[TEST 4] Testing Scheme Protocol Smuggling Blocking...")
    invalid_schemes = [
        "file:///etc/passwd",
        "ftp://internal-server.com",
        "gopher://127.0.0.1:70",
        "dict://127.0.0.1:11211"
    ]
    for target in invalid_schemes:
        try:
            validate_url_security(target)
            assert False, f"SSRF SECURITY VIOLATION! Invalid Scheme target '{target}' was NOT blocked!"
        except SecurityException as e:
            print(f"[PASS] Non-HTTP Scheme Target '{target}' Blocked Successfully: {str(e)}")

    # ---------------------------------------------------------------------
    # SECURITY INVARIANT 5: Legitimate Public HTTP Target Authorization
    # ---------------------------------------------------------------------
    print("\n[TEST 5] Verifying Legitimate Public HTTP Target Access...")
    public_targets = [
        "https://api.github.com",
        "https://httpbin.org/get",
        "https://openrouter.ai/api/v1/models"
    ]
    for target in public_targets:
        try:
            hostname, ips = validate_url_security(target)
            print(f"[PASS] Public Target '{target}' Authorized (Host: {hostname}, Resolved IPs: {ips})")
        except SecurityException as e:
            assert False, f"False Positive! Legitimate public URL '{target}' was incorrectly blocked: {str(e)}"

    print("\n================================================================")
    print("  ALL PHASE B.2 SECURITY INVARIANTS (P1) PASSED SUCCESSFULLY!  ")
    print("================================================================")

if __name__ == "__main__":
    asyncio.run(test_phase_b2_ssrf_security_invariants())
