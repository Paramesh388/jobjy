import re
from ml.skills_dictionary import extract_skills_from_text
from ml.location_extractor import extract_candidate_location

# Common education degree patterns
EDUCATION_PATTERNS = [
    (r"(?i)\b(B\.?\s?Tech|Bachelor\s+of\s+Technology)\b.*?(?:in\s+([A-Za-z\s]+))?", "B.Tech"),
    (r"(?i)\b(B\.?\s?E\.?|Bachelor\s+of\s+Engineering)\b.*?(?:in\s+([A-Za-z\s]+))?", "B.E."),
    (r"(?i)\b(M\.?\s?Tech|Master\s+of\s+Technology)\b.*?(?:in\s+([A-Za-z\s]+))?", "M.Tech"),
    (r"(?i)\b(B\.?\s?C\.?\s?A\.?|Bachelor\s+of\s+Computer\s+Applications)\b", "BCA"),
    (r"(?i)\b(M\.?\s?C\.?\s?A\.?|Master\s+of\s+Computer\s+Applications)\b", "MCA"),
    (r"(?i)\b(B\.?\s?Sc|Bachelor\s+of\s+Science)\b.*?(?:in\s+([A-Za-z\s]+))?", "B.Sc"),
    (r"(?i)\b(M\.?\s?Sc|Master\s+of\s+Science)\b.*?(?:in\s+([A-Za-z\s]+))?", "M.Sc"),
    (r"(?i)\b(M\.?\s?B\.?\s?A\.?|Master\s+of\s+Business\s+Administration)\b", "MBA"),
    (r"(?i)\b(Diploma\s+in\s+[A-Za-z\s]+)\b", "Diploma")
]

# Common certification patterns
CERTIFICATION_KEYWORDS = [
    "AWS Certified", "Azure Certified", "Google Cloud Certified", "GCP Certified",
    "Certified Kubernetes", "CKA", "CKAD", "CCNA", "PMP", "Scrum Master", "PSM",
    "Oracle Certified", "TensorFlow Developer", "DataCamp", "Coursera", "Udemy",
    "IBM Certified", "HackerRank", "LeetCode"
]

def extract_education(text: str) -> str:
    """Detects highest or primary educational qualification from resume text."""
    if not text:
        return "Not specified"
        
    detected_degrees = []
    for pattern, degree_label in EDUCATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            # Capture branch/specialization if present
            matched_text = match.group(0).strip()
            # Truncate clean string
            clean_degree = re.sub(r"\s+", " ", matched_text)[:50]
            detected_degrees.append(clean_degree)
            
    if detected_degrees:
        # Return the most prominent or first degree detected
        return detected_degrees[0]
        
    # Check general keywords
    if re.search(r"(?i)\b(bachelor|undergraduate|degree)\b", text):
        return "Bachelor's Degree (Field not specified)"
    if re.search(r"(?i)\b(master|postgraduate)\b", text):
        return "Master's Degree (Field not specified)"
        
    return "Not specified"

def extract_experience(text: str) -> str:
    """Estimates years of experience or fresher status from resume text."""
    if not text:
        return "Not specified"
        
    # Check explicit fresher mentions
    if re.search(r"(?i)\b(fresher|entry[\s-]level|recent\s+graduate|college\s+student)\b", text):
        return "Fresher (0 years)"
        
    # Search for explicit 'X years of experience'
    exp_matches = re.findall(r"(?i)(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp|work)", text)
    if exp_matches:
        try:
            years = [float(y) for y in exp_matches if float(y) < 40]
            if years:
                max_year = max(years)
                if max_year == 0:
                    return "Fresher (0 years)"
                elif max_year == 1:
                    return "1 Year"
                else:
                    return f"{int(max_year) if max_year.is_integer() else max_year} Years"
        except Exception:
            pass
            
    # Check for date ranges in experience section (e.g. 2021 - 2024, 2022 to Present)
    date_ranges = re.findall(r"\b(201\d|202\d)\s*(?:-|–|to)\s*(201\d|202\d|Present|current)\b", text, re.IGNORECASE)
    if date_ranges:
        total_years = 0
        current_year = 2026
        for start_year, end_str in date_ranges:
            try:
                start = int(start_year)
                end = current_year if end_str.lower() in ("present", "current") else int(end_str)
                if 0 <= (end - start) <= 15:
                    total_years += (end - start)
            except Exception:
                continue
                
        if total_years > 0:
            return f"Approx. {min(total_years, 15)} Years"
            
    return "Fresher / Entry-level (Estimated)"

def extract_certifications(text: str) -> list:
    """Identifies certifications mentioned in text."""
    if not text:
        return []
        
    detected_certs = []
    # Check keyword mentions
    for cert in CERTIFICATION_KEYWORDS:
        if re.search(rf"(?i)\b{re.escape(cert)}\b", text):
            detected_certs.append(cert)
            
    # Also look for explicit section "Certifications" and extract lines
    cert_section = re.search(r"(?i)(?:certifications?|licenses?|credentials?):?\s*\n(.*?)(?=\n\s*(?:projects?|education|experience|skills|interests|$))", text, re.DOTALL)
    if cert_section:
        section_text = cert_section.group(1)
        lines = [line.strip().lstrip("-•* ") for line in section_text.split("\n") if line.strip()]
        for line in lines[:5]:
            if len(line) > 5 and len(line) < 80 and line not in detected_certs:
                detected_certs.append(line)
                
    return detected_certs[:5]

def suggest_job_roles(skills: list) -> list:
    """
    Intelligently suggests relevant job titles based on the candidate's detected skills.
    """
    skills_lower = {s.lower() for s in skills}
    suggestions = []
    
    # AI / ML
    if any(s in skills_lower for s in ["machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "computer vision"]):
        suggestions.append("Machine Learning Engineer")
        suggestions.append("AI Engineer")
        
    # Data Science / Analytics
    if any(s in skills_lower for s in ["pandas", "numpy", "power bi", "tableau", "data analysis", "excel"]):
        suggestions.append("Data Analyst")
        suggestions.append("Data Scientist")
        
    # Python
    if "python" in skills_lower:
        suggestions.append("Python Developer")
        if any(s in skills_lower for s in ["django", "flask", "fastapi"]):
            suggestions.append("Backend Developer (Python)")
            
    # Frontend / Web
    if any(s in skills_lower for s in ["react", "angular", "vue", "javascript", "typescript", "html", "css"]):
        suggestions.append("Frontend Developer")
        suggestions.append("Web Developer")
        
    # Java
    if "java" in skills_lower or "spring boot" in skills_lower:
        suggestions.append("Java Developer")
        suggestions.append("Backend Developer")
        
    # Cloud / DevOps
    if any(s in skills_lower for s in ["aws", "azure", "docker", "kubernetes", "devops", "ci/cd", "linux"]):
        suggestions.append("DevOps Engineer")
        suggestions.append("Cloud Engineer")
        
    # Generic / Software Engineering
    if not suggestions or "sql" in skills_lower or "git" in skills_lower:
        suggestions.append("Junior Software Engineer")
        suggestions.append("Software Developer")
        
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for role in suggestions:
        if role not in seen:
            seen.add(role)
            deduped.append(role)
            
    return deduped[:4]

def analyze_resume(raw_text: str) -> dict:
    """
    Comprehensive resume NLP analyzer.
    Extracts skills, education, experience, certifications, location, and suggests matching roles.
    """
    skills = extract_skills_from_text(raw_text)
    education = extract_education(raw_text)
    experience = extract_experience(raw_text)
    certifications = extract_certifications(raw_text)
    suggested_roles = suggest_job_roles(skills)
    loc_data = extract_candidate_location(raw_text)
    
    candidate_location = loc_data["candidate_location"] if loc_data else None
    normalized_location = loc_data["normalized_location"] if loc_data else None
    primary_city = loc_data["primary_city"] if loc_data else None
    
    return {
        "skills": skills,
        "education": education,
        "experience": experience,
        "certifications": certifications,
        "suggested_roles": suggested_roles,
        "candidate_location": candidate_location,
        "normalized_location": normalized_location,
        "primary_city": primary_city,
        "text_preview": raw_text[:400] + ("..." if len(raw_text) > 400 else "")
    }
