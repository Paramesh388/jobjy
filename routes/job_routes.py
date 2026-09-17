import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from services.job_api import search_jobs, load_demo_jobs
from ml.job_matcher import match_and_rank_jobs, analyze_skill_gaps, match_resume_to_job
from models.database import (
    get_latest_resume_analysis,
    log_job_search,
    save_job,
    unsave_job,
    get_saved_jobs,
    get_saved_job_ids,
    log_system_event
)

from ml.location_extractor import location_matches, classify_workplace_type, normalize_city_name

job_bp = Blueprint("jobs", __name__)

def ensure_session_id():
    import uuid
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

# Cache current search results in memory keyed by session to support comparison & detail routes
SEARCH_CACHE = {}

@job_bp.route("/jobs", methods=["GET", "POST"])
def list_jobs():
    session_id = ensure_session_id()
    analysis = get_latest_resume_analysis(session_id)
    
    if not analysis:
        flash("Please upload your resume before searching for matching jobs.", "info")
        return redirect(url_for("resume.upload"))
        
    candidate_skills = analysis.get("skills", [])
    resume_text = analysis.get("extracted_text", "")
    suggested_roles = analysis.get("suggested_roles", [])
    candidate_location = analysis.get("candidate_location")
    normalized_location = analysis.get("normalized_location")
    primary_city = analysis.get("primary_city")
    
    # Determine default location from resume if available
    default_location = primary_city or (candidate_location.split(",")[0].strip() if candidate_location else "") or "Bengaluru"
    
    # Query parameters
    if request.method == "POST":
        role_query = request.form.get("role", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "All").strip()
        min_score = float(request.form.get("min_score", 0))
        sort_by = request.form.get("sort_by", "score").strip()
        limit = int(request.form.get("limit", 20))
    else:
        # Defaults
        default_role = suggested_roles[0] if suggested_roles else "Software Engineer"
        role_query = request.args.get("role", default_role).strip()
        location = request.args.get("location", default_location).strip()
        job_type = request.args.get("job_type", "All").strip()
        min_score = float(request.args.get("min_score", 0))
        sort_by = request.args.get("sort_by", "score").strip()
        limit = int(request.args.get("limit", 20))
        
    # Check if user has manually changed / overridden the location
    is_user_override = False
    if candidate_location:
        cand_canonical = primary_city or normalize_city_name(candidate_location)
        sel_canonical = normalize_city_name(location)
        if sel_canonical and cand_canonical and sel_canonical.lower() != cand_canonical.lower():
            is_user_override = True
            
    # Step 1: Retrieve raw job openings from API / source
    raw_jobs, source_name, is_demo_mode = search_jobs(
        role_query=role_query,
        location=location,
        limit=max(limit * 2, 40)
    )
    
    # Step 2: MANDATORY HARD LOCATION FILTER before scoring
    valid_location_jobs = []
    remote_jobs_count = 0
    rejected_count = 0
    
    for j in raw_jobs:
        j_loc = j.get("location", "")
        j_desc = j.get("description", "")
        j_emp = j.get("employment_type", "")
        
        # Ensure workplace_type is classified
        if "workplace_type" not in j or not j["workplace_type"]:
            j["workplace_type"] = classify_workplace_type(j_loc, j_desc, j_emp)
            
        if location_matches(location, j_loc, j_desc, j_emp):
            valid_location_jobs.append(j)
            if j.get("workplace_type") == "Remote":
                remote_jobs_count += 1
        else:
            rejected_count += 1
            
    # Debug logging as required by spec #17
    print("=" * 60)
    print(f"Detected resume location: {candidate_location or 'None'}")
    print(f"Normalized resume location: {normalized_location or 'None'}")
    print(f"Selected job search location: {location}")
    print(f"Jobs before location filtering: {len(raw_jobs)}")
    print(f"Jobs after location filtering: {len(valid_location_jobs)}")
    print(f"Remote jobs included: {remote_jobs_count}")
    print(f"Rejected due to location mismatch: {rejected_count}")
    print("=" * 60)
    
    # Real-time system event logging
    log_system_event(session_id, "Live Job API Requested", f"Queried for Role: '{role_query}', Location: '{location}'", status="INFO")
    log_system_event(session_id, "Jobs Filtered", f"{len(valid_location_jobs)} passed location filter ({remote_jobs_count} remote, {rejected_count} rejected)", status="INFO")

    # Step 3: AIML Matching & Ranking ONLY for valid location jobs!
    scored_jobs = match_and_rank_jobs(resume_text, candidate_skills, valid_location_jobs)
    if scored_jobs:
        log_system_event(session_id, "Jobs Matched", f"Ranked {len(scored_jobs)} jobs using TF-IDF & Skill Overlap (Top match: {scored_jobs[0].get('match_score', 0)}%)", status="SUCCESS")
    
    # Cache for detail/compare lookups
    SEARCH_CACHE[session_id] = {j["id"]: j for j in scored_jobs}
    
    # Apply job-type and min-score filters
    filtered_jobs = scored_jobs
    
    # Job type filter
    if job_type and job_type != "All":
        jt = job_type.lower()
        if jt == "remote":
            filtered_jobs = [j for j in filtered_jobs if j.get("workplace_type") == "Remote" or "remote" in j.get("employment_type", "").lower()]
        elif jt == "full-time":
            filtered_jobs = [j for j in filtered_jobs if ("full-time" in j.get("employment_type", "").lower() or "full time" in j.get("employment_type", "").lower()) and "intern" not in j.get("employment_type", "").lower()]
        elif jt == "internship":
            filtered_jobs = [j for j in filtered_jobs if "intern" in j.get("employment_type", "").lower()]
        elif jt == "part-time":
            filtered_jobs = [j for j in filtered_jobs if "part-time" in j.get("employment_type", "").lower() or "part time" in j.get("employment_type", "").lower()]
        elif jt == "contract":
            filtered_jobs = [j for j in filtered_jobs if "contract" in j.get("employment_type", "").lower() or "freelance" in j.get("employment_type", "").lower()]
        else:
            filtered_jobs = [j for j in filtered_jobs if jt in j.get("employment_type", "").lower()]
        
    # Minimum match score filter
    if min_score > 0:
        filtered_jobs = [j for j in filtered_jobs if j.get("match_score", 0) >= min_score]
        
    # Complete Sorting Options
    if sort_by == "recent":
        filtered_jobs.sort(key=lambda x: str(x.get("posted_date", "")), reverse=True)
    elif sort_by == "oldest":
        filtered_jobs.sort(key=lambda x: str(x.get("posted_date", "")), reverse=False)
    elif sort_by == "score_asc":
        filtered_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=False)
    elif sort_by == "title":
        filtered_jobs.sort(key=lambda x: x.get("title", "").lower())
    elif sort_by == "company":
        filtered_jobs.sort(key=lambda x: x.get("company", "").lower())
    else: # default: "score" (High to Low)
        filtered_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
    # Log search audit in SQLite
    log_job_search(
        session_id=session_id,
        query_role=role_query or "All",
        location=location or "All",
        total_found=len(filtered_jobs),
        source_used=source_name
    )
    
    # Skill-gap analysis on the recommendations
    skill_gaps = analyze_skill_gaps(candidate_skills, scored_jobs)
    
    # Saved job IDs for quick save/unsave toggle state
    saved_ids = get_saved_job_ids(session_id)
    
    return render_template(
        "jobs.html",
        jobs=filtered_jobs[:limit],
        total_found=len(valid_location_jobs),
        displayed_count=len(filtered_jobs[:limit]),
        role_query=role_query,
        location=location,
        job_type=job_type,
        min_score=min_score,
        sort_by=sort_by,
        limit=limit,
        source_name=source_name,
        is_demo_mode=is_demo_mode,
        analysis=analysis,
        skill_gaps=skill_gaps,
        saved_ids=saved_ids,
        candidate_location=candidate_location,
        primary_city=primary_city,
        is_user_override=is_user_override
    )

@job_bp.route("/job/<job_id>", methods=["GET"])
def job_details(job_id):
    session_id = ensure_session_id()
    analysis = get_latest_resume_analysis(session_id)
    
    # Look up in cache or demo
    cached = SEARCH_CACHE.get(session_id, {})
    job = cached.get(job_id)
    
    if not job:
        # Fallback: search demo jobs
        all_demos = load_demo_jobs(limit=50)
        found = next((j for j in all_demos if j["id"] == job_id), None)
        if found and analysis:
            job = match_resume_to_job(analysis.get("extracted_text", ""), analysis.get("skills", []), found)
        else:
            job = found
            
    if not job:
        flash("Job details could not be found or the search session expired.", "error")
        return redirect(url_for("jobs.list_jobs"))
        
    saved_ids = get_saved_job_ids(session_id)
    is_saved = job_id in saved_ids
    
    return render_template("job_details.html", job=job, is_saved=is_saved, analysis=analysis)

@job_bp.route("/apply/<job_id>", methods=["GET"])
def apply_redirect(job_id):
    """Logs candidate application click and redirects straight to the official external job posting."""
    session_id = ensure_session_id()
    cached = SEARCH_CACHE.get(session_id, {})
    job = cached.get(job_id)
    if not job:
        all_demos = load_demo_jobs(limit=50)
        job = next((j for j in all_demos if j["id"] == job_id), None)
        
    if job and job.get("source_url"):
        log_system_event(
            session_id, 
            "Candidate Applied to Job", 
            f"Redirecting to official job: {job.get('title')} at {job.get('company')} ({job.get('source_url')})", 
            status="SUCCESS"
        )
        return redirect(job["source_url"])
        
    flash("The official application link for this job is currently unavailable.", "warning")
    return redirect(url_for("jobs.list_jobs"))

@job_bp.route("/compare", methods=["GET", "POST"])
def compare_jobs():
    session_id = ensure_session_id()
    analysis = get_latest_resume_analysis(session_id)
    
    if not analysis:
        flash("Please upload your resume first to compare jobs.", "info")
        return redirect(url_for("resume.upload"))
        
    cached = SEARCH_CACHE.get(session_id, {})
    job_ids = request.args.get("ids", "").split(",")
    job_ids = [jid.strip() for jid in job_ids if jid.strip()]
    
    selected_jobs = []
    for jid in job_ids:
        if jid in cached:
            selected_jobs.append(cached[jid])
            
    # If no jobs found from parameters, select top 2-3 from cache or demo
    if not selected_jobs:
        if cached:
            selected_jobs = list(cached.values())[:3]
        else:
            demos = load_demo_jobs(limit=3)
            for d in demos:
                selected_jobs.append(match_resume_to_job(analysis.get("extracted_text", ""), analysis.get("skills", []), d))
                
    # Build comparison union of skills across selected jobs and candidate
    all_job_skills = set()
    for j in selected_jobs:
        for s in j.get("skills", []):
            all_job_skills.add(s)
            
    candidate_skills = set(analysis.get("skills", []))
    all_skills_list = sorted(list(all_job_skills.union(candidate_skills)))
    
    return render_template(
        "comparison.html",
        jobs=selected_jobs,
        all_skills=all_skills_list,
        candidate_skills=candidate_skills,
        analysis=analysis
    )

@job_bp.route("/api/save-job", methods=["POST"])
def api_save_job():
    session_id = ensure_session_id()
    data = request.get_json() or {}
    job_id = data.get("id")
    
    if not job_id:
        return jsonify({"success": False, "error": "Job ID is required"}), 400
        
    cached = SEARCH_CACHE.get(session_id, {})
    job = cached.get(job_id) or data
    
    success = save_job(session_id, job)
    if success:
        log_system_event(session_id, "Job Saved", f"Saved job '{job.get('title', 'Position')}' at {job.get('company', 'Company')} ({job_id})", status="SUCCESS")
    return jsonify({
        "success": success,
        "job_id": job_id,
        "message": "Job saved to your profile." if success else "Failed to save job."
    })

@job_bp.route("/api/unsave-job", methods=["POST"])
def api_unsave_job():
    session_id = ensure_session_id()
    data = request.get_json() or {}
    job_id = data.get("id") or data.get("job_id")
    
    if not job_id:
        return jsonify({"success": False, "error": "Job ID is required"}), 400
        
    deleted = unsave_job(session_id, job_id)
    if deleted:
        log_system_event(session_id, "Job Unsaved", f"Removed job ID: {job_id} from saved bookmarks", status="INFO")
    return jsonify({
        "success": deleted,
        "job_id": job_id,
        "message": "Job removed from saved jobs." if deleted else "Job was not found in saved list."
    })
