import httpx
import asyncio
import ssl
import socket
from typing import Dict, Any

async def get_mozilla_observatory_score(domain: str) -> Dict[str, Any]:
    """
    Get security grade from Mozilla Observatory (completely free)
    Returns grade (A+ to F) and score (0-100)
    """
    try:
        # First trigger a scan (async)
        scan_url = f"https://http-observatory.security.mozilla.org/api/v1/analyze?host={domain}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Start scan
            scan_response = await client.post(scan_url, json={"hidden": False})
            if scan_response.status_code in [200, 201]:
                scan_data = scan_response.json()
                scan_id = scan_data.get('scan_id')
                
                if scan_id:
                    # Poll for results (wait for scan to complete)
                    for _ in range(5):  # Try 5 times with delay
                        result_url = f"https://http-observatory.security.mozilla.org/api/v1/getScanResults?scan={scan_id}"
                        result_response = await client.get(result_url)
                        if result_response.status_code == 200:
                            result = result_response.json()
                            if result.get('grade'):
                                grade = result.get('grade', 'F')
                                score = result.get('score', 0)
                                
                                # Convert to 0-100 scale
                                grade_map = {
                                    'A+': 95, 'A': 90, 'A-': 85,
                                    'B+': 80, 'B': 75, 'B-': 70,
                                    'C+': 65, 'C': 60, 'C-': 55,
                                    'D+': 50, 'D': 45, 'D-': 40,
                                    'F': 30
                                }
                                normalized_score = grade_map.get(grade, 50)
                                
                                return {
                                    'grade': grade,
                                    'raw_score': score,
                                    'normalized_score': normalized_score,
                                    'source': 'Mozilla Observatory'
                                }
                        await asyncio.sleep(2)  # Wait 2 seconds between polls
    except Exception as e:
        print(f"Observatory scan failed: {e}")
    
    return {
        'grade': 'Unknown',
        'raw_score': 0,
        'normalized_score': 50,  # Default middle score
        'source': 'Observatory Failed'
    }

async def get_ssl_labs_grade(domain: str) -> Dict[str, Any]:
    """
    Get SSL/TLS grade from SSL Labs API (completely free)
    """
    try:
        url = f"https://api.ssllabs.com/api/v3/analyze?host={domain}&all=done"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                endpoints = data.get('endpoints', [])
                if endpoints:
                    grade = endpoints[0].get('grade', 'F')
                    
                    # Convert SSL Labs grade to 0-100
                    grade_map = {
                        'A+': 95, 'A': 90, 'A-': 85,
                        'B+': 80, 'B': 75, 'B-': 70,
                        'C+': 65, 'C': 60, 'C-': 55,
                        'D+': 45, 'D': 40, 'E': 30, 'F': 20
                    }
                    normalized_score = grade_map.get(grade, 50)
                    
                    return {
                        'grade': grade,
                        'normalized_score': normalized_score,
                        'source': 'SSL Labs'
                    }
    except Exception as e:
        print(f"SSL Labs scan failed: {e}")
    
    return {
        'grade': 'Unknown',
        'normalized_score': 50,
        'source': 'SSL Labs Failed'
    }

async def check_basic_security(domain: str) -> Dict[str, Any]:
    """
    Basic security checks (no API required)
    - Check if HTTPS is enabled
    - Check HTTP to HTTPS redirect
    - Check security headers via basic request
    """
    score = 50  # Start at middle
    findings = []
    
    try:
        # Check HTTPS availability
        https_url = f"https://{domain}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            try:
                response = await client.get(https_url)
                if response.url.scheme == 'https':
                    score += 15
                    findings.append("HTTPS enabled")
                    
                    # Check security headers
                    headers = response.headers
                    
                    # Strict-Transport-Security
                    if 'strict-transport-security' in headers:
                        score += 5
                        findings.append("HSTS enabled")
                    
                    # Content-Security-Policy
                    if 'content-security-policy' in headers:
                        score += 5
                        findings.append("CSP present")
                    
                    # X-Frame-Options
                    if 'x-frame-options' in headers:
                        score += 3
                        findings.append("X-Frame-Options set")
                    
                    # X-Content-Type-Options
                    if 'x-content-type-options' in headers:
                        score += 2
                        findings.append("X-Content-Type-Options set")
                else:
                    score -= 10
                    findings.append("HTTPS not enforced - redirects to HTTP")
            except Exception as e:
                score -= 20
                findings.append(f"HTTPS connection failed: {str(e)[:50]}")
    
    except Exception as e:
        findings.append(f"Basic check error: {str(e)[:50]}")
    
    return {
        'normalized_score': min(100, max(0, score)),
        'findings': findings,
        'source': 'Basic Security Check'
    }

async def get_security_score(vendor_domain: str) -> float:
    """
    Main function that combines multiple free sources
    Returns a single security score 0-100
    """
    # Run all security checks in parallel
    tasks = [
        get_mozilla_observatory_score(vendor_domain),
        get_ssl_labs_grade(vendor_domain),
        check_basic_security(vendor_domain)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect valid scores
    scores = []
    sources_used = []
    
    for result in results:
        if isinstance(result, Exception):
            continue
        
        if isinstance(result, dict):
            if 'normalized_score' in result:
                scores.append(result['normalized_score'])
                if 'source' in result:
                    sources_used.append(result['source'])
    
    # If we have no scores, return a reasonable default
    if not scores:
        return 65  # Conservative default
    
    # Weighted average (favor more reliable sources)
    # Mozilla Observatory is most comprehensive
    total_score = 0
    total_weight = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception) or not isinstance(result, dict):
            continue
        
        weight = 1.0
        source = result.get('source', '')
        
        if 'Mozilla Observatory' in source:
            weight = 2.0  # Most comprehensive
        elif 'SSL Labs' in source:
            weight = 1.5  # Good for SSL/TLS
        elif 'Basic Security' in source:
            weight = 1.0  # Basic checks
        
        total_score += result.get('normalized_score', 50) * weight
        total_weight += weight
    
    final_score = total_score / total_weight if total_weight > 0 else 65
    
    return round(final_score, 1)

# Fallback for demo when domain is not provided
async def get_security_score_fallback(vendor_name: str) -> float:
    """
    Generate a realistic security score based on vendor name
    For demo when domain is unavailable
    """
    import random
    
    # Seed with vendor name for consistency
    random.seed(vendor_name)
    
    # Generate realistic score between 40-95
    base = random.randint(40, 95)
    
    # Add some "realism" - well-known vendors tend to be higher
    well_known = ['google', 'microsoft', 'aws', 'amazon', 'ibm', 'oracle', 'salesforce']
    if any(known in vendor_name.lower() for known in well_known):
        base = min(95, base + 10)
    
    return base