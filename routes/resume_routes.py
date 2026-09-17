import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from config import Config
from utils.resume_parser import parse_resume, ResumeParsingError
from ml.resume_analyzer import analyze_resume
from models.database import (
    save_resume_analysis,
    get_latest_resume_analysis,
    update_resume_skills,
    log_system_event
)

resume_bp = Blueprint("resume", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def ensure_session():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

@resume_bp.route("/upload", methods=["GET", "POST"])
def upload():
    ensure_session()
    
    if request.method == "POST":
        # Check if file part is present
        if "resume" not in request.files:
            flash("No file part selected. Please select a resume file to upload.", "error")
            return redirect(request.url)
            
        file = request.files["resume"]
        if not file or file.filename.strip() == "":
            flash("Please choose a resume file before uploading.", "error")
            return redirect(request.url)
            
        if not allowed_file(file.filename):
            flash("Invalid file format. Please upload a PDF, DOCX, or TXT resume.", "error")
            return redirect(request.url)
            
        try:
            # Secure filename generation using UUID to prevent overwrite / execution
            original_name = secure_filename(file.filename)
            ext = original_name.rsplit(".", 1)[1].lower()
            safe_filename = f"{uuid.uuid4().hex}_{original_name}"
            
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            save_path = os.path.join(Config.UPLOAD_FOLDER, safe_filename)
            file.save(save_path)
            
            # File size check
            file_size_bytes = os.path.getsize(save_path)
            if file_size_bytes > Config.MAX_CONTENT_LENGTH:
                os.remove(save_path)
                flash("File exceeds maximum allowed size of 5 MB. Please upload a smaller file.", "error")
                return redirect(request.url)
                
            # Parse text from resume
            extracted_text = parse_resume(save_path)
            
            # Run NLP entity and skill analysis
            analysis = analyze_resume(extracted_text)
            
            # Save to SQLite
            session_id = session["session_id"]
            save_resume_analysis(
                session_id=session_id,
                filename=original_name,
                text=extracted_text,
                skills=analysis["skills"],
                education=analysis["education"],
                experience=analysis["experience"],
                certifications=analysis["certifications"],
                suggested_roles=analysis["suggested_roles"],
                candidate_location=analysis.get("candidate_location"),
                normalized_location=analysis.get("normalized_location")
            )
            
            # Update session context
            session["resume_uploaded"] = True
            session["resume_filename"] = original_name
            session["skills"] = analysis["skills"]
            session["candidate_location"] = analysis.get("candidate_location")
            session["normalized_location"] = analysis.get("normalized_location")
            session["primary_city"] = analysis.get("primary_city")
            
            # Log real system events
            log_system_event(session_id, "Resume Uploaded", f"Uploaded resume: {original_name} ({round(file_size_bytes/1024, 1)} KB)", status="SUCCESS")
            log_system_event(session_id, "Resume Analyzed", f"Detected {len(analysis['skills'])} skills, Education: {analysis['education']}", status="SUCCESS")
            cand_loc = analysis.get("candidate_location")
            primary_c = analysis.get("primary_city")
            if cand_loc:
                log_system_event(session_id, "Location Detected", f"Detected: '{cand_loc}', Primary Search City: '{primary_c}'", status="SUCCESS")
            else:
                log_system_event(session_id, "Location Detected", "No explicit city in resume; default set to Bengaluru", status="INFO")
            
            flash("Resume uploaded and analyzed successfully!", "success")
            return redirect(url_for("resume.analysis"))
            
        except ResumeParsingError as rpe:
            log_system_event(session.get("session_id"), "Upload Error", str(rpe), status="ERROR")
            flash(str(rpe), "error")
            return redirect(request.url)
        except Exception as e:
            log_system_event(session.get("session_id"), "Upload Error", f"Unexpected error: {str(e)}", status="ERROR")
            flash(f"An unexpected error occurred during processing: {str(e)}", "error")
            return redirect(request.url)
            
    return render_template("upload.html")

@resume_bp.route("/analysis", methods=["GET"])
def analysis():
    session_id = ensure_session()
    data = get_latest_resume_analysis(session_id)
    
    if not data:
        flash("No resume found. Please upload your resume first to view analysis.", "info")
        return redirect(url_for("resume.upload"))
        
    return render_template("analysis.html", analysis=data)

@resume_bp.route("/api/update-skills", methods=["POST"])
def update_skills():
    session_id = ensure_session()
    payload = request.get_json() or {}
    skills = payload.get("skills", [])
    
    if not isinstance(skills, list):
        return jsonify({"success": False, "error": "Invalid skills format"}), 400
        
    # Clean and deduplicate skills
    cleaned_skills = sorted(list(set(s.strip() for s in skills if s.strip())))
    
    # Update SQLite database and session
    updated = update_resume_skills(session_id, cleaned_skills)
    session["skills"] = cleaned_skills
    log_system_event(session_id, "Skills Updated", f"User modified skills catalog ({len(cleaned_skills)} skills active)", status="INFO")
    
    return jsonify({
        "success": True,
        "skills": cleaned_skills,
        "count": len(cleaned_skills),
        "message": "Skills updated successfully."
    })
