import uuid
from flask import Blueprint, render_template, session, redirect, url_for
from models.database import (
    get_latest_resume_analysis,
    get_saved_jobs,
    get_search_history,
    get_dashboard_stats,
    get_all_catalog_skills,
    get_system_logs
)
from ml.job_matcher import analyze_skill_gaps
from services.job_api import search_jobs
from ml.job_matcher import match_and_rank_jobs

dashboard_bp = Blueprint("dashboard", __name__)

def ensure_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

@dashboard_bp.route("/")
def index():
    ensure_session_id()
    return render_template("index.html")

@dashboard_bp.route("/dashboard")
def dashboard():
    session_id = ensure_session_id()
    analysis = get_latest_resume_analysis(session_id)
    stats = get_dashboard_stats(session_id)
    saved_jobs = get_saved_jobs(session_id)
    
    # Analyze skill gaps if candidate has uploaded a resume
    skill_gaps = []
    strong_matches_count = 0
    recent_jobs = []
    
    if analysis:
        # Run a background evaluation on top jobs for this user
        candidate_skills = analysis.get("skills", [])
        suggested_roles = analysis.get("suggested_roles", ["Software Engineer"])
        role_to_check = suggested_roles[0] if suggested_roles else "Software Engineer"
        cand_location = analysis.get("primary_city") or (analysis.get("candidate_location").split(",")[0].strip() if analysis.get("candidate_location") else "") or "Bengaluru"
        
        raw_jobs, _, _ = search_jobs(role_query=role_to_check, location=cand_location, limit=15)
        scored = match_and_rank_jobs(analysis.get("extracted_text", ""), candidate_skills, raw_jobs)
        recent_jobs = scored[:5]
        strong_matches_count = len([j for j in scored if j.get("match_score", 0) >= 70])
        
        gaps_result = analyze_skill_gaps(candidate_skills, scored)
        skill_gaps = gaps_result.get("gaps", [])
        
    return render_template(
        "dashboard.html",
        analysis=analysis,
        stats=stats,
        saved_jobs=saved_jobs,
        skill_gaps=skill_gaps,
        strong_matches_count=strong_matches_count,
        recent_jobs=recent_jobs
    )

@dashboard_bp.route("/saved-jobs")
def saved_jobs_view():
    session_id = ensure_session_id()
    saved = get_saved_jobs(session_id)
    return render_template("saved_jobs.html", saved_jobs=saved)

@dashboard_bp.route("/admin")
def admin_view():
    session_id = ensure_session_id()
    search_history = get_search_history(limit=30)
    system_logs = get_system_logs(limit=50)
    stats = get_dashboard_stats(session_id)
    catalog = get_all_catalog_skills()
    
    # Group catalog skills by category
    categorized_skills = {}
    for item in catalog:
        cat = item["category"]
        if cat not in categorized_skills:
            categorized_skills[cat] = []
        categorized_skills[cat].append(item["name"])
        
    return render_template(
        "admin.html",
        search_history=search_history,
        system_logs=system_logs,
        stats=stats,
        categorized_skills=categorized_skills,
        total_catalog_skills=len(catalog)
    )
