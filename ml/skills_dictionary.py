import re

# Comprehensive skills taxonomy categorized by tech domain
TECH_SKILLS_TAXONOMY = {
    "Programming Languages": [
        "Python", "Java", "C++", "C#", "C", "JavaScript", "TypeScript",
        "PHP", "Ruby", "Go", "Rust", "Kotlin", "Swift", "R", "Scala", "Dart"
    ],
    "Web Technologies": [
        "HTML", "CSS", "React", "Angular", "Vue.js", "Vue", "Node.js", "Express.js",
        "Flask", "Django", "FastAPI", "Spring Boot", "Bootstrap", "Tailwind CSS",
        "Next.js", "jQuery", "REST API", "GraphQL", "ASP.NET", "WebSockets"
    ],
    "Databases": [
        "SQL", "MySQL", "PostgreSQL", "MongoDB", "Oracle", "SQLite",
        "Redis", "Cassandra", "DynamoDB", "MariaDB", "Elasticsearch", "Firebase"
    ],
    "Data Science & Analytics": [
        "Pandas", "NumPy", "Matplotlib", "Seaborn", "Power BI", "Tableau",
        "Excel", "Apache Spark", "Hadoop", "SciPy", "Statistics", "Data Analysis",
        "Big Data", "Data Visualization", "ETL"
    ],
    "AI & Machine Learning": [
        "Machine Learning", "Deep Learning", "NLP", "Natural Language Processing",
        "Computer Vision", "TensorFlow", "PyTorch", "Scikit-learn", "Keras",
        "OpenCV", "BERT", "LLM", "Generative AI", "Neural Networks", "Reinforcement Learning"
    ],
    "Cloud & DevOps": [
        "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes",
        "Git", "GitHub", "GitLab", "CI/CD", "Linux", "Terraform", "Jenkins",
        "Ansible", "Nginx", "DevOps"
    ],
    "Core Software Concepts": [
        "Data Structures", "Algorithms", "Object-Oriented Programming", "OOP",
        "Microservices", "System Design", "Agile", "Scrum", "Unit Testing", "Debugging"
    ]
}

# Inverted mapping: skill name (lowercase) -> canonical skill name
CANONICAL_SKILLS = {}
for category, skills in TECH_SKILLS_TAXONOMY.items():
    for s in skills:
        CANONICAL_SKILLS[s.lower()] = s

# Special skill alias / normalized mapping
SKILL_ALIASES = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "postgres": "PostgreSQL",
    "k8s": "Kubernetes",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "sklearn": "Scikit-learn",
    "tf": "TensorFlow",
    "cv": "Computer Vision",
    "restful api": "REST API",
    "restful apis": "REST API",
    "rest apis": "REST API",
    "oops": "Object-Oriented Programming",
    "amazon web services": "AWS",
    "google cloud platform": "GCP",
    "microsoft azure": "Azure"
}

def get_skill_extraction_patterns():
    """
    Build compiled regular expressions for precise skill extraction,
    taking special care of punctuation symbols like C++, C#, .NET.
    """
    patterns = []
    
    # Process all canonical skills + aliases
    all_terms = list(CANONICAL_SKILLS.keys()) + list(SKILL_ALIASES.keys())
    
    # Sort terms by length descending to match multi-word phrases first (e.g. 'Machine Learning' before 'Learning')
    all_terms = sorted(all_terms, key=len, reverse=True)
    
    for term in all_terms:
        # Determine canonical name
        canonical = CANONICAL_SKILLS.get(term) or SKILL_ALIASES.get(term)
        
        # Build boundary regex:
        # Punctuation skills like C++ or C# require special regex boundaries
        if term == "c++":
            pattern = re.compile(r'(?i)(?<![a-zA-Z0-9])c\+\+(?![a-zA-Z0-9])')
        elif term == "c#":
            pattern = re.compile(r'(?i)(?<![a-zA-Z0-9])c#(?![a-zA-Z0-9])')
        elif term == "c":
            pattern = re.compile(r'(?i)\bC\b')
        elif term == "r":
            pattern = re.compile(r'(?i)\bR\b')
        elif term == "go":
            pattern = re.compile(r'(?i)\b(golang|go)\b')
        else:
            escaped = re.escape(term)
            pattern = re.compile(rf'(?i)\b{escaped}\b')
            
        patterns.append((pattern, canonical))
        
    return patterns

COMPILED_PATTERNS = get_skill_extraction_patterns()

def extract_skills_from_text(text):
    """
    Extracts canonical skill names from given raw or cleaned text.
    Returns a sorted list of unique recognized skills.
    """
    if not text:
        return []
        
    detected = set()
    for pattern, canonical in COMPILED_PATTERNS:
        if pattern.search(text):
            detected.add(canonical)
            
    return sorted(list(detected))
