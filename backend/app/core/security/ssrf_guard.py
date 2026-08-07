import socket
import ipaddress
from urllib.parse import urlparse
from typing import List, Tuple
import httpx
from app.core.security.context import SecurityException

# Reserved / Private IPv4 and IPv6 CIDR Subnets
RESTRICTED_SUBNETS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source address)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-Use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local & Cloud Metadata (AWS, GCP, Azure, etc.)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-Use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1 (RFC 5737)
    ipaddress.ip_network("192.88.99.0/24"),     # IPv6 to IPv4 relay (RFC 3068)
    ipaddress.ip_network("192.168.0.0/16"),     # Private-Use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking (RFC 2544)
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2 (RFC 5737)
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3 (RFC 5737)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast (RFC 5771)
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for Future Use (RFC 1112)
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6 Subnets
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("64:ff9b::/96"),       # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),           # Discard prefix
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Address
]

def is_ip_restricted(ip_str: str) -> bool:
    """
    Check whether an IP address belongs to loopback, private, link-local, or cloud metadata ranges.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        # Handle IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
            
        return any(ip in net for net in RESTRICTED_SUBNETS)
    except ValueError:
        return True # Fail-closed if invalid IP format

def validate_url_security(url: str) -> Tuple[str, List[str]]:
    """
    Parses scheme, resolves hostname to ALL IPs, and verifies no resolved IP is private/restricted.
    Returns parsed hostname and resolved IP list.
    """
    parsed = urlparse(url)
    
    # 1. Scheme Check: Only allow http and https
    if parsed.scheme.lower() not in ("http", "https"):
        raise SecurityException(f"SSRF Protection: Unsupported scheme '{parsed.scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityException("SSRF Protection: Invalid URL, missing hostname.")

    # 2. Prevent direct localhost / metadata hostname tricks
    lowered_host = hostname.lower()
    if lowered_host in ("localhost", "127.0.0.1", "::1", "169.254.169.254", "metadata.google.internal"):
        raise SecurityException(f"SSRF Protection: Target host '{hostname}' is a restricted domain/IP.")

    # 3. DNS Resolution: Resolve ALL target IPs for the hostname
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        resolved_ips = list(set([item[4][0] for item in addr_info]))
    except socket.gaierror as e:
        raise SecurityException(f"SSRF Protection: Hostname resolution failed for '{hostname}': {str(e)}")

    if not resolved_ips:
        raise SecurityException(f"SSRF Protection: Hostname '{hostname}' resolved to no IP addresses.")

    # 4. Inspect EVERY resolved IP against restricted subnets
    for ip in resolved_ips:
        if is_ip_restricted(ip):
            raise SecurityException(
                f"SSRF Protection: Hostname '{hostname}' resolved to restricted private/internal IP '{ip}'. Request blocked."
            )

    return hostname, resolved_ips


class SSRFSafeTransport(httpx.AsyncBaseTransport):
    """
    Custom Async Transport for httpx that validates every resolved IP dynamically
    and intercepts HTTP Redirects to re-verify the redirect target IP against SSRF policy.
    """
    def __init__(self, inner_transport: httpx.AsyncHTTPTransport = None):
        self.inner_transport = inner_transport or httpx.AsyncHTTPTransport(verify=True)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        validate_url_security(url_str)
        
        response = await self.inner_transport.handle_async_request(request)
        
        # Intercept HTTP Redirects (301, 302, 303, 307, 308) to prevent SSRF via redirect chaining
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_target = response.headers.get("Location")
            if redirect_target:
                # Resolve relative redirects
                from urllib.parse import urljoin
                resolved_redirect_url = urljoin(url_str, redirect_target)
                validate_url_security(resolved_redirect_url)

        return response
