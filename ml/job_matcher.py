from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.text_cleaner import clean_for_nlp
from ml.skills_dictionary import extract_skills_from_text
from config import Config

def calculate_text_similarity(resume_text: str, job_description: str) -> float:
    """
    Computes TF-IDF vector representations and calculates Cosine Similarity.
    Returns a float between 0.0 and 1.0.
    """
    cleaned_resume = clean_for_nlp(resume_text)
    cleaned_job = clean_for_nlp(job_description)
    
    # If either text is empty or too brief
    if not cleaned_resume or not cleaned_job or len(cleaned_job.split()) < 5:
        return 0.0
        
    try:
        # Use English stop words and unigrams + bigrams for phrase matching
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        tfidf_matrix = vectorizer.fit_transform([cleaned_resume, cleaned_job])
        similarity_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        sim_score = float(similarity_matrix[0][0])
        return max(0.0, min(1.0, sim_score))
    except Exception as e:
        print(f"Error in TF-IDF cosine similarity: {e}")
        return 0.0

def calculate_skill_overlap(candidate_skills: list, job_skills: list) -> dict:
    """
    Calculates exact skill overlap between candidate's skills and job's required skills.
    Returns matched skills, missing skills, and skill match ratio.
    """
    cand_set = {s.strip().lower(): s for s in candidate_skills if s.strip()}
    job_set = {s.strip().lower(): s for s in job_skills if s.strip()}
    
    matched_canonical = []
    missing_canonical = []
    
    for lower_skill, original_name in job_set.items():
        if lower_skill in cand_set:
            matched_canonical.append(original_name)
        else:
            missing_canonical.append(original_name)
            
    total_required = len(job_set)
    if total_required == 0:
        # If no explicit skills were listed in the job, neutral fallback
        ratio = 0.5
    else:
        ratio = len(matched_canonical) / total_required
        
    return {
        "matched_skills": sorted(matched_canonical),
        "missing_skills": sorted(missing_canonical),
        "skill_match_ratio": round(ratio, 4),
        "matched_count": len(matched_canonical),
        "required_count": total_required
    }

def match_resume_to_job(resume_text: str, candidate_skills: list, job: dict) -> dict:
    """
    Computes transparent combined match score for a single job opening.
    Weights: 60% TF-IDF text similarity, 40% exact skill overlap.
    """
    job_desc = job.get("description", "")
    
    # 1. Job skills: if not pre-populated, extract them from job description & title
    job_skills = job.get("skills") or []
    if not job_skills:
        extracted = extract_skills_from_text(f"{job.get('title', '')} {job_desc}")
        job_skills = extracted
        
    # 2. Text Similarity (TF-IDF + Cosine Similarity)
    text_sim = calculate_text_similarity(resume_text, job_desc)
    
    # 3. Skill Overlap
    skill_eval = calculate_skill_overlap(candidate_skills, job_skills)
    skill_ratio = skill_eval["skill_match_ratio"]
    
    # 4. Final Combined Score (0 - 100%)
    w_text = Config.WEIGHT_TEXT_SIMILARITY
    w_skill = Config.WEIGHT_SKILL_MATCH
    
    # Check if job description was virtually empty
    if len(job_desc.strip()) < 30 and skill_eval["required_count"] == 0:
        match_score = 0.0
        score_note = "Insufficient information to calculate a reliable match."
    else:
        raw_combined = (text_sim * w_text) + (skill_ratio * w_skill)
        match_score = round(raw_combined * 100, 1)
        score_note = "Valid AIML match calculated."
        
    return {
        **job,
        "match_score": match_score,
        "text_similarity_pct": round(text_sim * 100, 1),
        "skill_match_pct": round(skill_ratio * 100, 1),
        "matched_skills": skill_eval["matched_skills"],
        "missing_skills": skill_eval["missing_skills"],
        "score_note": score_note
    }

def match_and_rank_jobs(resume_text: str, candidate_skills: list, jobs_list: list) -> list:
    """
    Evaluates and ranks all retrieved jobs for the candidate.
    Deduplicates jobs by title and company before ranking.
    """
    scored_jobs = []
    seen_keys = set()
    
    for job in jobs_list:
        # Deduplication key based on normalized title and company
        dedup_key = f"{job.get('title', '').strip().lower()}|{job.get('company', '').strip().lower()}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        
        scored = match_resume_to_job(resume_text, candidate_skills, job)
        scored_jobs.append(scored)
        
    # Sort descending by match score
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_jobs

def analyze_skill_gaps(candidate_skills: list, ranked_jobs: list, top_n: int = 15) -> dict:
    """
    Performs skill-gap analysis by aggregating missing skills across top-matched job openings.
    Identifies skills frequently required by employers that the candidate lacks.
    """
    if not ranked_jobs:
        return {"gaps": [], "top_skills_matched": []}
        
    # Inspect top jobs (e.g. top 15)
    sample_pool = ranked_jobs[:top_n]
    pool_size = len(sample_pool)
    
    missing_counter = Counter()
    matched_counter = Counter()
    
    for j in sample_pool:
        for sk in j.get("missing_skills", []):
            missing_counter[sk] += 1
        for sk in j.get("matched_skills", []):
            matched_counter[sk] += 1
            
    gaps = []
    for skill, count in missing_counter.most_common(10):
        demand_pct = round((count / pool_size) * 100, 1)
        gaps.append({
            "skill": skill,
            "count": count,
            "demand_percentage": demand_pct,
            "relevance_advice": f"Appears in {count} of top {pool_size} recommended jobs ({demand_pct}%)."
        })
        
    matched_summary = []
    for skill, count in matched_counter.most_common(8):
        matched_summary.append({
            "skill": skill,
            "count": count
        })
        
    return {
        "gaps": gaps,
        "matched_summary": matched_summary,
        "analyzed_jobs_count": pool_size
    }
