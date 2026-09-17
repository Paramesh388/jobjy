import re
from urllib.parse import urlparse

# Prohibited placeholder domains and prefixes
INVALID_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "sample.com",
    "test.com",
    "fake.com",
    "placeholder.com",
    "foo.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0"
}

def is_valid_job_url(url: str, expected_domain: str = None) -> bool:
    """
    Validates whether a job posting URL is a legitimate, reachable HTTP/HTTPS URL.
    Rejects:
    - None, empty strings, whitespace
    - example.com, example.org, example.net and subdomains
    - Localhost or loopback IPs
    - Obvious mock or placeholder domains
    - Non-HTTP/HTTPS protocols
    - URLs without a valid hostname
    - URLs that don't match the expected domain (if specified)
    """
    if not url or not isinstance(url, str):
        return False
        
    clean_url = url.strip()
    if len(clean_url) < 10:
        return False
        
    try:
        parsed = urlparse(clean_url)
    except Exception:
        return False
        
    # Must use http or https
    if parsed.scheme.lower() not in ("http", "https"):
        return False
        
    netloc = parsed.netloc.lower()
    if not netloc:
        return False
        
    # Strip port if present (e.g. localhost:5000)
    domain = netloc.split(":")[0]
    
    # Check exact domain or subdomains (e.g. www.example.com, jobs.example.com)
    for bad_domain in INVALID_DOMAINS:
        if domain == bad_domain or domain.endswith("." + bad_domain):
            return False
            
    # Hostname must contain at least one dot (unless local which is rejected)
    if "." not in domain:
        return False
        
    parts = domain.split(".")
    # Any empty part (e.g. .com, test..com, test.) is invalid
    if any(len(p) == 0 for p in parts):
        return False

    # Domain suffix must have at least 2 characters (e.g. .com, .org, .de, .io)
    if len(parts[-1]) < 2:
        return False
        
    # If expected_domain is provided, ensure domain matches or is a subdomain
    if expected_domain:
        exp = expected_domain.lower().strip()
        if domain != exp and not domain.endswith("." + exp) and exp not in domain:
            return False
            
    return True
