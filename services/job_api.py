import os
import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config
from ml.skills_dictionary import extract_skills_from_text
from ml.location_extractor import classify_workplace_type, location_matches, find_canonical_city
from utils.url_validator import is_valid_job_url

# Strip HTML tags from description texts
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

def strip_html_tags(text: str) -> str:
    """Removes HTML markup from raw job API descriptions."""
    if not text:
        return ""
    clean = HTML_TAG_PATTERN.sub(" ", text)
    clean = re.sub(r"&nbsp;|&amp;|&lt;|&gt;|&quot;|&#39;", " ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()

def is_relevant_role(title: str, desc: str, role_query: str) -> bool:
    """Checks if a job title or description is meaningfully relevant to the role query."""
    if not role_query:
        return True
    rq = role_query.lower().strip()
    words = [w for w in re.split(r"[\s,\-/]+", rq) if len(w) > 2]
    if not words:
        return True
    
    t_lower = (title or "").lower()
    d_lower = (desc or "").lower()
    
    # 1. Full phrase in title or desc
    if rq in t_lower or rq in d_lower:
        return True
        
    # 2. Key specialized keywords
    specialized_roles = {
        "frontend": ["frontend", "front-end", "front end", "react", "angular", "vue", "ui/ux", "web developer", "javascript"],
        "backend": ["backend", "back-end", "back end", "node", "django", "flask", "spring", "java", "golang", "ruby"],
        "python": ["python", "django", "flask", "fastapi"],
        "java": ["java", "spring", "springboot", "hibernate"],
        "data": ["data", "analyst", "analytics", "sql", "bi", "tableau", "power bi", "etl"],
        "machine learning": ["machine learning", "ml", "ai", "deep learning", "nlp", "computer vision", "tensorflow", "pytorch"],
        "ai": ["ai", "artificial intelligence", "machine learning", "deep learning", "nlp"],
        "devops": ["devops", "cloud", "aws", "azure", "docker", "kubernetes", "ci/cd", "terraform", "sre"],
        "full stack": ["full stack", "fullstack", "full-stack", "mern", "mean"],
        "mobile": ["mobile", "android", "ios", "flutter", "react native"],
        "qa": ["qa", "quality assurance", "test", "testing", "automation"]
    }
    
    # Identify if query matches any specialized domain
    active_domains = []
    for domain, kws in specialized_roles.items():
        if any(w in words or domain in rq for w in kws):
            active_domains.append(kws)
            
    if active_domains:
        for domain_kws in active_domains:
            if any(k in t_lower for k in domain_kws) or any(k in d_lower for k in domain_kws):
                return True
        return False
        
    # General fallback: check if any significant word appears in title or description
    return any(w in t_lower for w in words) or any(w in d_lower for w in words)

def load_demo_jobs(role_filter=None, location_filter=None, limit=20):
    """Loads curated demo jobs from local JSON data file with strict location filtering."""
    data_path = os.path.join(Config.BASE_DIR, "data", "demo_jobs.json")
    if not os.path.exists(data_path):
        return []
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
            
        filtered = []
        role_q = (role_filter or "").lower().strip()
        loc_q = (location_filter or "").strip()
        
        for job in jobs:
            # Ensure demo jobs explicitly have no external apply links
            job["url"] = None
            job["source_url"] = None
            job["source_name"] = "Demo Data"
            job["is_demo"] = True

            # Classify workplace type
            w_type = classify_workplace_type(
                job.get("location", ""),
                job.get("description", ""),
                job.get("employment_type", "")
            )
            job["workplace_type"] = w_type

            # Strict location matching: reject unrelated cities unless remote
            if loc_q and not location_matches(loc_q, job.get("location", ""), job.get("description", ""), job.get("employment_type", "")):
                continue

            # Role matching (if provided)
            if role_q:
                if not is_relevant_role(job.get("title", ""), job.get("description", ""), role_q):
                    continue

            filtered.append(job)
            
        return filtered[:limit]
    except Exception as e:
        print(f"Error loading demo jobs: {e}")
        return []

def fetch_from_arbeitnow(role_query: str = "", limit: int = 30) -> list:
    """
    Fetches real live tech jobs from Arbeitnow public job API.
    Returns normalized job objects with validated source URLs.
    """
    url = "https://www.arbeitnow.com/api/job-board-api"
    headers = {"User-Agent": "JobMatchAI/1.0 (College-Project-Demo)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code != 200:
            return []
            
        data = response.json()
        raw_jobs = data.get("data", [])
        
        normalized = []
        for item in raw_jobs:
            raw_url = item.get("url") or item.get("apply_url") or item.get("link")
            if not is_valid_job_url(raw_url, expected_domain="arbeitnow.com"):
                continue

            title = item.get("title", "Software Engineer")
            company = item.get("company_name", "Tech Enterprise")
            raw_desc = item.get("description", "")
            clean_desc = strip_html_tags(raw_desc)
            
            # Check relevance to requested role
            if role_query and not is_relevant_role(title, clean_desc, role_query):
                continue
                    
            location = item.get("location", "Remote")
            if item.get("remote", False):
                location = f"{location} (Remote)" if location else "Remote"
                
            skills = item.get("tags") or []
            if not skills:
                skills = extract_skills_from_text(f"{title} {clean_desc}")
                
            job_obj = {
                "id": f"arbeitnow-{item.get('slug', abs(hash(title)))}",
                "title": title,
                "company": company,
                "location": location,
                "description": clean_desc,
                "skills": skills[:8],
                "employment_type": "Remote" if item.get("remote") else "Full-time",
                "workplace_type": classify_workplace_type(location, clean_desc, "Remote" if item.get("remote") else "Full-time"),
                "posted_date": "Recently",
                "url": raw_url,
                "source_url": raw_url,
                "source_name": "Arbeitnow",
                "source": "Live API (Arbeitnow)",
                "is_demo": False
            }
            normalized.append(job_obj)
            if len(normalized) >= limit:
                break
                
        return normalized
    except Exception as e:
        print(f"Arbeitnow API fetch failed: {e}")
        return []

def fetch_from_remotive(role_query: str = "", limit: int = 25) -> list:
    """
    Fetches real live remote jobs from Remotive public API.
    Returns normalized job objects with validated source URLs.
    """
    url = "https://remotive.com/api/remote-jobs"
    params = {}
    if role_query:
        params["search"] = role_query
        
    headers = {"User-Agent": "JobMatchAI/1.0 (College-Project-Demo)"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=6)
        if response.status_code != 200:
            return []
            
        data = response.json()
        raw_jobs = data.get("jobs", [])
        
        normalized = []
        for item in raw_jobs:
            raw_url = item.get("url")
            if not is_valid_job_url(raw_url, expected_domain="remotive.com"):
                continue

            title = item.get("title", "Remote Developer")
            company = item.get("company_name", "Global Tech")
            raw_desc = item.get("description", "")
            clean_desc = strip_html_tags(raw_desc)
            
            # Check relevance to requested role
            if role_query and not is_relevant_role(title, clean_desc, role_query):
                continue

            tags = item.get("tags") or []
            skills = extract_skills_from_text(f"{title} {' '.join(tags)} {clean_desc}")
            raw_geo = item.get("candidate_required_location") or "Worldwide"
            loc_str = f"Remote ({raw_geo})" if "remote" not in raw_geo.lower() else raw_geo
            emp_type = item.get("job_type", "Full-time")
            
            job_obj = {
                "id": f"remotive-{item.get('id', abs(hash(title)))}",
                "title": title,
                "company": company,
                "location": loc_str,
                "description": clean_desc,
                "skills": skills[:8],
                "employment_type": emp_type,
                "workplace_type": "Remote",
                "posted_date": item.get("publication_date", "Recently")[:10] if item.get("publication_date") else "Recently",
                "url": raw_url,
                "source_url": raw_url,
                "source_name": "Remotive",
                "source": "Live API (Remotive)",
                "is_demo": False
            }
            normalized.append(job_obj)
            if len(normalized) >= limit:
                break
            
        return normalized
    except Exception as e:
        print(f"Remotive API fetch failed: {e}")
        return []

def fetch_from_jobicy(role_query: str = "", limit: int = 25) -> list:
    """
    Fetches real live remote jobs from Jobicy public API.
    Returns normalized job objects with validated source URLs.
    """
    url = "https://jobicy.com/api/v2/remote-jobs"
    params = {"count": 50}
    if role_query:
        # Check if first word is a clean tag keyword
        first_word = role_query.split()[0].lower()
        if first_word in ("python", "frontend", "backend", "javascript", "react", "java", "devops", "data"):
            params["tag"] = first_word

    headers = {"User-Agent": "JobMatchAI/1.0 (College-Project-Demo)"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=6)
        if response.status_code != 200:
            return []
            
        data = response.json()
        raw_jobs = data.get("jobs", [])
        
        normalized = []
        for item in raw_jobs:
            raw_url = item.get("url")
            if not is_valid_job_url(raw_url, expected_domain="jobicy.com"):
                continue

            title = item.get("jobTitle", "Remote Developer")
            company = item.get("companyName", "Tech Enterprise")
            raw_desc = item.get("jobDescription") or item.get("jobExcerpt", "")
            clean_desc = strip_html_tags(raw_desc)
            
            # Check relevance to requested role
            if role_query and not is_relevant_role(title, clean_desc, role_query):
                continue

            geo_raw = item.get("jobGeo") or "Anywhere"
            loc_str = f"Remote ({geo_raw})" if "remote" not in geo_raw.lower() else geo_raw
            emp_type_raw = item.get("jobType", "Full-time")
            emp_type = ", ".join(emp_type_raw) if isinstance(emp_type_raw, list) else str(emp_type_raw)
            
            skills = extract_skills_from_text(f"{title} {item.get('jobIndustry', '')} {clean_desc}")
            
            job_obj = {
                "id": f"jobicy-{item.get('id', abs(hash(title)))}",
                "title": title,
                "company": company,
                "location": loc_str,
                "description": clean_desc,
                "skills": skills[:8],
                "employment_type": emp_type,
                "workplace_type": "Remote",
                "posted_date": item.get("pubDate", "Recently")[:10] if item.get("pubDate") else "Recently",
                "url": raw_url,
                "source_url": raw_url,
                "source_name": "Jobicy",
                "source": "Live API (Jobicy)",
                "is_demo": False
            }
            normalized.append(job_obj)
            if len(normalized) >= limit:
                break
                
        return normalized
    except Exception as e:
        print(f"Jobicy API fetch failed: {e}")
        return []

def fetch_from_remoteok(role_query: str = "", limit: int = 30) -> list:
    """
    Fetches real live tech jobs from RemoteOK public API.
    Returns normalized job objects with validated source URLs.
    """
    url = "https://remoteok.com/api"
    params = {}
    if role_query:
        first_word = role_query.split()[0].lower()
        if first_word in ("python", "frontend", "backend", "javascript", "react", "java", "devops", "data", "ai", "ml", "golang", "ruby", "rust"):
            params["tag"] = first_word

    headers = {"User-Agent": "JobMatchAI/1.0 (Mozilla/5.0)"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=6)
        if response.status_code != 200:
            return []
        data = response.json()
        if not isinstance(data, list):
            return []
            
        raw_jobs = [j for j in data if isinstance(j, dict) and "position" in j]
        normalized = []
        for item in raw_jobs:
            raw_url = item.get("apply_url") or item.get("url")
            if not is_valid_job_url(raw_url, expected_domain="remoteok.com"):
                continue

            title = item.get("position", "Software Engineer")
            company = item.get("company", "Tech Company")
            raw_desc = item.get("description", "")
            clean_desc = strip_html_tags(raw_desc)

            if role_query and not is_relevant_role(title, clean_desc, role_query):
                continue

            tags = item.get("tags") or []
            skills = extract_skills_from_text(f"{title} {' '.join(tags)} {clean_desc}")
            raw_geo = item.get("location") or "Worldwide"
            loc_str = f"Remote ({raw_geo})" if "remote" not in raw_geo.lower() else raw_geo

            date_val = item.get("date") or item.get("epoch")
            if isinstance(date_val, (int, float)):
                import datetime
                posted_str = datetime.datetime.fromtimestamp(date_val).strftime("%Y-%m-%d")
            elif date_val:
                posted_str = str(date_val)[:10]
            else:
                posted_str = "Recently"

            job_obj = {
                "id": f"remoteok-{item.get('id', abs(hash(title)))}",
                "title": title,
                "company": company,
                "location": loc_str,
                "description": clean_desc,
                "skills": skills[:8],
                "employment_type": "Full-time",
                "workplace_type": "Remote",
                "posted_date": posted_str,
                "url": raw_url,
                "source_url": raw_url,
                "source_name": "RemoteOK",
                "source": "Live API (RemoteOK)",
                "is_demo": False
            }
            normalized.append(job_obj)
            if len(normalized) >= limit:
                break
        return normalized
    except Exception as e:
        print(f"RemoteOK API fetch failed: {e}")
        return []

def fetch_from_himalayas(role_query: str = "", limit: int = 30) -> list:
    """
    Fetches real live remote jobs from Himalayas public API.
    Returns normalized job objects with validated source URLs.
    """
    url = "https://himalayas.app/jobs/api"
    params = {"limit": max(limit * 2, 40)}
    if role_query:
        params["q"] = role_query

    headers = {"User-Agent": "JobMatchAI/1.0 (Mozilla/5.0)"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=6)
        if response.status_code != 200:
            return []
        data = response.json()
        raw_jobs = data.get("jobs", [])

        normalized = []
        for item in raw_jobs:
            raw_url = item.get("applicationLink") or item.get("guid")
            if not is_valid_job_url(raw_url, expected_domain="himalayas.app"):
                continue

            title = item.get("title", "Software Engineer")
            company = item.get("companyName", "Tech Company")
            raw_desc = item.get("description", "") or item.get("excerpt", "")
            clean_desc = strip_html_tags(raw_desc)

            if role_query and not is_relevant_role(title, clean_desc, role_query):
                continue

            loc_restr = item.get("locationRestrictions") or []
            loc_geo = ", ".join(loc_restr) if loc_restr else "Worldwide"
            loc_str = f"Remote ({loc_geo})"

            categories = item.get("categories") or []
            skills = extract_skills_from_text(f"{title} {' '.join(categories)} {clean_desc}")

            pub_val = item.get("pubDate")
            if isinstance(pub_val, (int, float)):
                import datetime
                pub_str = datetime.datetime.fromtimestamp(pub_val).strftime("%Y-%m-%d")
            elif pub_val:
                pub_str = str(pub_val)[:10]
            else:
                pub_str = "Recently"

            job_obj = {
                "id": f"himalayas-{item.get('companySlug', 'job')}-{abs(hash(title)) % 100000}",
                "title": title,
                "company": company,
                "location": loc_str,
                "description": clean_desc,
                "skills": skills[:8],
                "employment_type": item.get("employmentType", "Full-time") or "Full-time",
                "workplace_type": "Remote",
                "posted_date": pub_str,
                "url": raw_url,
                "source_url": raw_url,
                "source_name": "Himalayas",
                "source": "Live API (Himalayas)",
                "is_demo": False
            }
            normalized.append(job_obj)
            if len(normalized) >= limit:
                break
        return normalized
    except Exception as e:
        print(f"Himalayas API fetch failed: {e}")
        return []

def fetch_from_adzuna(role_query: str = "", location: str = "Bengaluru", limit: int = 20) -> list:
    """
    Fetches from Adzuna API if ADZUNA_APP_ID and ADZUNA_APP_KEY are provided.
    Supports location-based search across India.
    """
    app_id = Config.ADZUNA_APP_ID
    app_key = Config.ADZUNA_APP_KEY
    if not app_id or not app_key:
        return []
        
    url = f"https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": limit,
        "what": role_query or "Software Engineer",
        "where": location or "Bengaluru",
        "content-type": "application/json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=6)
        if response.status_code != 200:
            return []
            
        data = response.json()
        results = data.get("results", [])
        
        normalized = []
        for item in results:
            raw_url = item.get("redirect_url")
            if not is_valid_job_url(raw_url):
                continue

            title = item.get("title", "")
            title = strip_html_tags(title)
            company = item.get("company", {}).get("display_name", "Enterprise")
            desc = strip_html_tags(item.get("description", ""))
            skills = extract_skills_from_text(f"{title} {desc}")
            loc_str = item.get("location", {}).get("display_name", location)
            emp_type = item.get("contract_time", "Full-time")
            
            job_obj = {
                "id": f"adzuna-{item.get('id', abs(hash(title)))}",
                "title": title,
                "company": company,
                "location": loc_str,
                "description": desc,
                "skills": skills[:8],
                "employment_type": emp_type,
                "workplace_type": classify_workplace_type(loc_str, desc, emp_type),
                "posted_date": item.get("created", "Recently")[:10],
                "url": raw_url,
                "source_url": raw_url,
                "source_name": "Adzuna",
                "source": "Live API (Adzuna)",
                "is_demo": False
            }
            normalized.append(job_obj)
            
        return normalized
    except Exception as e:
        print(f"Adzuna API fetch failed: {e}")
        return []

def search_jobs(role_query: str = "", location: str = "", limit: int = 20) -> tuple:
    """
    Main job retrieval service method.
    Tries live job providers first:
    1. Adzuna (if configured)
    2. Live Public APIs concurrently (Jobicy, RemoteOK, Himalayas, Arbeitnow, Remotive)
    3. Transparent fallback to DEMO DATA ONLY if live APIs fail or return 0 usable jobs.
    
    Returns (jobs_list, source_name, is_demo_mode)
    """
    if Config.FORCE_DEMO_DATA:
        demo_jobs = load_demo_jobs(role_query, location, limit)
        return demo_jobs, "DEMO DATA — NOT LIVE JOB OPENINGS", True
        
    jobs = []
    total_fetched_count = 0
    valid_url_count = 0
    rejected_url_count = 0
    sample_url = None
    
    fetchers = [
        lambda: fetch_from_jobicy(role_query, limit=limit),
        lambda: fetch_from_remoteok(role_query, limit=limit),
        lambda: fetch_from_himalayas(role_query, limit=limit),
        lambda: fetch_from_arbeitnow(role_query, limit=limit),
        lambda: fetch_from_remotive(role_query, limit=limit)
    ]
    if Config.ADZUNA_APP_ID and Config.ADZUNA_APP_KEY:
        fetchers.append(lambda: fetch_from_adzuna(role_query, location, limit=limit))

    # Execute all public web job API queries in parallel
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = [executor.submit(f) for f in fetchers]
        for fut in as_completed(futures):
            try:
                res = fut.result()
                if res:
                    jobs.extend(res)
            except Exception as e:
                print(f"API fetcher worker error: {e}")

    # Audit & telemetry on retrieved live jobs' URLs
    total_fetched_count = len(jobs)
    valid_jobs = []
    for j in jobs:
        url_to_test = j.get("source_url") or j.get("url")
        if is_valid_job_url(url_to_test):
            valid_url_count += 1
            valid_jobs.append(j)
            if not sample_url:
                sample_url = url_to_test
        else:
            rejected_url_count += 1
            print(f"[URL Validation Warning] Rejected live job {j.get('id')} with invalid URL: {url_to_test}")

    jobs = valid_jobs

    print("=" * 60)
    print(f"[URL Validation] Total jobs fetched from APIs: {total_fetched_count}")
    print(f"[URL Validation] Jobs with valid URLs: {valid_url_count}")
    print(f"[URL Validation] Jobs rejected due to invalid URLs: {rejected_url_count}")
    print(f"[URL Validation] Sample valid URL: {sample_url or 'None'}")
    print("=" * 60)
            
    # Strict location filtering across all retrieved live jobs
    if location and location.lower() not in ("all", "any", "all locations", "") and jobs:
        jobs = [
            j for j in jobs 
            if location_matches(location, j.get("location", ""), j.get("description", ""), j.get("employment_type", ""))
        ]
            
    # If live jobs successfully passed location filter, return them!
    if jobs:
        seen = set()
        deduped = []
        for j in jobs:
            key = f"{j['title'].strip().lower()}|{j['company'].strip().lower()}"
            if key not in seen:
                seen.add(key)
                deduped.append(j)
                
        return deduped[:limit], "Live Public Job APIs (Jobicy, RemoteOK, Himalayas, Arbeitnow, Remotive)", False
        
    # Fallback to Demo Data mode ONLY when live providers return no usable jobs
    demo_jobs = load_demo_jobs(role_query, location, limit)
    if demo_jobs:
        return demo_jobs, "DEMO DATA — NOT LIVE JOB OPENINGS (API Offline Fallback)", True
        
    return [], "No Openings Found", False
