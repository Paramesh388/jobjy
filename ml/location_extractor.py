import re

# Canonical city aliases mapping to standardized name
CANONICAL_CITY_MAP = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "new delhi": "Delhi",
    "delhi": "Delhi",
    "delhi ncr": "Delhi",
    "noida": "Noida",
    "greater noida": "Noida",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "navi mumbai": "Mumbai",
    "thane": "Mumbai",
    "hyderabad": "Hyderabad",
    "secunderabad": "Hyderabad",
    "chennai": "Chennai",
    "madras": "Chennai",
    "pune": "Pune",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "kochi": "Kochi",
    "cochin": "Kochi",
    "trivandrum": "Thiruvananthapuram",
    "thiruvananthapuram": "Thiruvananthapuram",
    "chandigarh": "Chandigarh",
    "indore": "Indore",
    "mysuru": "Mysuru",
    "mysore": "Mysuru",
    "coimbatore": "Coimbatore"
}

# Major Indian states for parsing multi-part locations
INDIAN_STATES = [
    "Karnataka", "Maharashtra", "Telangana", "Tamil Nadu", "Delhi",
    "Uttar Pradesh", "Haryana", "West Bengal", "Gujarat", "Rajasthan",
    "Kerala", "Punjab", "Madhya Pradesh", "Andhra Pradesh", "Goa"
]

# Labels that introduce candidate location in resumes
EXPLICIT_LOCATION_PREFIXES = [
    r"(?i)(?:current\s+location|current\s+city|present\s+address|residence|based\s+in|residing\s+(?:in|at)):?\s*",
    r"(?i)(?:preferred\s+location):?\s*",
    r"(?i)(?:location|city|address):?\s*"
]

# Keywords identifying remote or work-from-home jobs
REMOTE_KEYWORDS = [
    "remote", "fully remote", "work from anywhere", "wfa", "wfh",
    "work from home", "remote - india", "india remote", "100% remote",
    "remote worldwide", "anywhere", "worldwide"
]

def normalize_city_name(city_str: str) -> str:
    """Returns canonical city name if recognized, else returns title-cased string."""
    if not city_str:
        return ""
    clean = city_str.strip().lower()
    return CANONICAL_CITY_MAP.get(clean, city_str.strip().title())

def normalize_location(raw_location: str) -> str:
    """
    Normalizes location strings:
    - 'Bangalore' -> 'Bengaluru'
    - 'Bangalore, Karnataka' -> 'Bengaluru, Karnataka'
    - 'Bangalore, Karnataka, India' -> 'Bengaluru, Karnataka, India'
    - 'New Delhi' -> 'Delhi'
    - 'Gurgaon' -> 'Gurugram'
    """
    if not raw_location:
        return ""
        
    parts = [p.strip() for p in raw_location.split(",") if p.strip()]
    if not parts:
        return raw_location.strip()
        
    city_part = parts[0]
    normalized_city = normalize_city_name(city_part)
    
    if len(parts) == 1:
        return normalized_city
        
    normalized_parts = [normalized_city]
    for part in parts[1:]:
        clean_part = part.strip().title()
        # Ensure India remains 'India' and states retain title case
        if clean_part.lower() == "india":
            normalized_parts.append("India")
        else:
            # Check state canonical
            state_match = next((s for s in INDIAN_STATES if s.lower() == clean_part.lower()), clean_part)
            normalized_parts.append(state_match)
            
    return ", ".join(normalized_parts)

def extract_candidate_location(raw_text: str) -> dict:
    """
    Extracts candidate location from resume text.
    Prioritizes:
    1. Explicit 'Current Location:' / 'Based in:' labels
    2. Header contact lines (top 10 lines of resume)
    3. Explicit 'Preferred Location:' labels
    4. General location mentions, excluding past college/past company lines
    
    Returns dict:
    {
        "candidate_location": "Bengaluru, Karnataka, India", # raw
        "normalized_location": "Bengaluru, Karnataka, India", # normalized
        "primary_city": "Bengaluru"                           # canonical city
    }
    or None if no valid location detected.
    """
    if not raw_text:
        return None
        
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    header_text = "\n".join(lines[:12])
    
    # 1. Check explicit "Current Location:" / "Based in:" labels in full text
    current_loc_patterns = [
        r"(?i)(?:current\s+location|current\s+city|present\s+address|residence|based\s+in|residing\s+(?:in|at)):?\s*([^\n\r]+)",
    ]
    for pattern in current_loc_patterns:
        match = re.search(pattern, raw_text)
        if match:
            raw_match = match.group(1).strip()
            # Clean off any trailing separator or secondary label
            raw_match = re.split(r"[|•·\t]", raw_match)[0].strip()
            city = find_canonical_city(raw_match)
            if city:
                norm = normalize_location(raw_match)
                return {
                    "candidate_location": raw_match,
                    "normalized_location": norm,
                    "primary_city": city
                }
                
    # 2. Check top 12 lines (header block: name, address, contact)
    for line in lines[:12]:
        # Ignore lines that are clearly education degrees or job titles
        if re.search(r"(?i)(?:b\.?\s?tech|b\.?\s?e\.?|engineer|developer|analyst|summary|experience)", line):
            # Check if there is a pipe or bullet separated location in the same line e.g. "Bengaluru, Karnataka | email | phone"
            segments = [seg.strip() for seg in re.split(r"[|•·\t]", line)]
            for seg in segments:
                city = find_canonical_city(seg)
                if city and not re.search(r"(?i)(?:b\.?\s?tech|university|college|company|tech)", seg):
                    norm = normalize_location(seg)
                    return {
                        "candidate_location": seg,
                        "normalized_location": norm,
                        "primary_city": city
                    }
        else:
            city = find_canonical_city(line)
            if city:
                # Extract clean segment around the city
                segments = [seg.strip() for seg in re.split(r"[|•·\t]", line)]
                for seg in segments:
                    if find_canonical_city(seg) == city:
                        norm = normalize_location(seg)
                        return {
                            "candidate_location": seg,
                            "normalized_location": norm,
                            "primary_city": city
                        }

    # 3. Check "Preferred Location:"
    pref_match = re.search(r"(?i)(?:preferred\s+location):?\s*([^\n\r]+)", raw_text)
    if pref_match:
        raw_match = pref_match.group(1).strip()
        raw_match = re.split(r"[|•·\t]", raw_match)[0].strip()
        city = find_canonical_city(raw_match)
        if city:
            norm = normalize_location(raw_match)
            return {
                "candidate_location": raw_match,
                "normalized_location": norm,
                "primary_city": city
            }

    # 4. Check general "Location:" or "City:" labels
    gen_match = re.search(r"(?i)(?:location|city|address):?\s*([^\n\r]+)", raw_text)
    if gen_match:
        raw_match = gen_match.group(1).strip()
        raw_match = re.split(r"[|•·\t]", raw_match)[0].strip()
        city = find_canonical_city(raw_match)
        if city:
            norm = normalize_location(raw_match)
            return {
                "candidate_location": raw_match,
                "normalized_location": norm,
                "primary_city": city
            }

    # No reliable candidate location found (do NOT guess)
    return None

def find_canonical_city(text: str) -> str:
    """Finds first canonical city name mentioned in a string using boundary regex."""
    if not text:
        return ""
        
    for alias, canonical in CANONICAL_CITY_MAP.items():
        pattern = rf"(?i)\b{re.escape(alias)}\b"
        if re.search(pattern, text):
            return canonical
            
    return ""

def classify_workplace_type(location_str: str, description: str = "", employment_type: str = "") -> str:
    """
    Classifies a job as 'Remote', 'Hybrid', or 'On-site'.
    Missing location is NOT treated as remote.
    """
    loc_lower = (location_str or "").lower()
    desc_lower = (description or "").lower()
    type_lower = (employment_type or "").lower()
    
    # 1. Explicit Remote check
    for kw in REMOTE_KEYWORDS:
        if kw in loc_lower or kw in type_lower:
            return "Remote"
            
    # Explicit description remote indicators
    if re.search(r"(?i)\b(100%\s+remote|fully\s+remote|work\s+from\s+anywhere|remote\s+worldwide)\b", desc_lower):
        return "Remote"
        
    # 2. Hybrid check
    if "hybrid" in loc_lower or "hybrid" in type_lower or re.search(r"(?i)\bhybrid\s+(?:work|model|role|opportunity)\b", desc_lower):
        return "Hybrid"
        
    # 3. Default: On-site
    return "On-site"

def location_matches(search_location: str, job_location: str, description: str = "", employment_type: str = "") -> bool:
    """
    Evaluates whether a job posting matches the candidate's target search location.
    
    Rules:
    - Remote jobs match ANY search location.
    - Hybrid jobs MUST match the search location city.
    - On-site jobs MUST match the search location city.
    - If search_location is 'Remote', only Remote jobs match.
    - If search_location is 'All' or empty, all jobs match.
    """
    s_loc = (search_location or "").strip().lower()
    j_loc = (job_location or "").strip()
    
    # Empty or "All" allows everything
    if not s_loc or s_loc in ("all", "any", "all locations"):
        return True
        
    workplace = classify_workplace_type(j_loc, description, employment_type)
    
    # If candidate specifically searched for 'Remote'
    if s_loc == "remote":
        return workplace == "Remote"
        
    # If the job is fully Remote, it matches any city search!
    if workplace == "Remote":
        return True
        
    # For On-site or Hybrid jobs: determine the job's canonical city
    target_city = find_canonical_city(search_location)
    job_city = find_canonical_city(j_loc)
    
    if not target_city:
        # Fallback to normalized substring comparison
        s_norm = normalize_city_name(search_location).lower()
        j_norm = normalize_city_name(j_loc).lower()
        return s_norm in j_norm or j_norm in s_norm
        
    if not job_city:
        # Check if target city is explicitly mentioned in job location string
        target_alias_regex = rf"(?i)\b{re.escape(target_city)}\b"
        return bool(re.search(target_alias_regex, j_loc))
        
    return target_city.lower() == job_city.lower()
