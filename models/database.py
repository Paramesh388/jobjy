import sqlite3
import json
import os
from datetime import datetime
from config import Config

def get_db_connection():
    os.makedirs(Config.INSTANCE_DIR, exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table 1: Resume Analysis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resume_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            extracted_text TEXT,
            skills_json TEXT,
            education TEXT,
            experience TEXT,
            certifications TEXT,
            suggested_roles_json TEXT,
            candidate_location TEXT,
            normalized_location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Safe migration for existing database instances
    try:
        cursor.execute("ALTER TABLE resume_analysis ADD COLUMN candidate_location TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE resume_analysis ADD COLUMN normalized_location TEXT")
    except Exception:
        pass
    
    # Table 2: Saved Jobs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            match_score REAL,
            matched_skills_json TEXT,
            missing_skills_json TEXT,
            employment_type TEXT,
            posted_date TEXT,
            url TEXT,
            source_url TEXT,
            source_name TEXT,
            source TEXT,
            is_demo INTEGER DEFAULT 0,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, job_id)
        )
    ''')
    
    # Safe migrations for saved_jobs
    try:
        cursor.execute("ALTER TABLE saved_jobs ADD COLUMN source_url TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE saved_jobs ADD COLUMN source_name TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE saved_jobs ADD COLUMN is_demo INTEGER DEFAULT 0")
    except Exception:
        pass
    
    # Table 3: Search History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            query_role TEXT,
            location TEXT,
            total_found INTEGER,
            source_used TEXT,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table 4: Skill Catalog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Table 5: System Application Event Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            status TEXT DEFAULT 'INFO',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_resume_analysis(session_id, filename, text, skills, education, experience, certifications=None, suggested_roles=None, candidate_location=None, normalized_location=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resume_analysis (session_id, filename, extracted_text, skills_json, education, experience, certifications, suggested_roles_json, candidate_location, normalized_location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_id,
        filename,
        text,
        json.dumps(skills or []),
        education or "Not specified",
        experience or "Not specified",
        json.dumps(certifications or []) if isinstance(certifications, list) else (certifications or "None detected"),
        json.dumps(suggested_roles or []),
        candidate_location,
        normalized_location
    ))
    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return analysis_id

def get_latest_resume_analysis(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM resume_analysis
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    ''', (session_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    
    data = dict(row)
    data["skills"] = json.loads(data["skills_json"]) if data.get("skills_json") else []
    try:
        data["certifications"] = json.loads(data["certifications"]) if data.get("certifications") and data["certifications"].startswith("[") else [data["certifications"]]
    except Exception:
        data["certifications"] = [data.get("certifications")] if data.get("certifications") else []
    data["suggested_roles"] = json.loads(data["suggested_roles_json"]) if data.get("suggested_roles_json") else []
    
    # Resolve primary city
    cand_loc = data.get("candidate_location")
    from ml.location_extractor import find_canonical_city
    data["primary_city"] = find_canonical_city(cand_loc) if cand_loc else None
    
    return data

def update_resume_skills(session_id, skills_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Update the latest resume record for this session
    cursor.execute('''
        UPDATE resume_analysis
        SET skills_json = ?
        WHERE id = (
            SELECT id FROM resume_analysis
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        )
    ''', (json.dumps(skills_list), session_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def save_job(session_id, job_dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        source_url = job_dict.get("source_url") or job_dict.get("url")
        source_name = job_dict.get("source_name") or job_dict.get("source", "Standard")
        is_demo = 1 if job_dict.get("is_demo") else 0
        cursor.execute('''
            INSERT OR REPLACE INTO saved_jobs 
            (session_id, job_id, title, company, location, match_score, matched_skills_json, missing_skills_json, employment_type, posted_date, url, source_url, source_name, source, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            str(job_dict.get("id")),
            job_dict.get("title", "Untitled Job"),
            job_dict.get("company", "Company"),
            job_dict.get("location", "Location"),
            float(job_dict.get("match_score", 0.0)),
            json.dumps(job_dict.get("matched_skills", [])),
            json.dumps(job_dict.get("missing_skills", [])),
            job_dict.get("employment_type", "Full-time"),
            job_dict.get("posted_date", "Recent"),
            job_dict.get("url", "#"),
            source_url,
            source_name,
            job_dict.get("source", "Standard"),
            is_demo
        ))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error saving job: {e}")
        success = False
    finally:
        conn.close()
    return success

def unsave_job(session_id, job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM saved_jobs WHERE session_id = ? AND job_id = ?
    ''', (session_id, str(job_id)))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_saved_jobs(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM saved_jobs WHERE session_id = ? ORDER BY saved_at DESC
    ''', (session_id,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        item = dict(r)
        item["matched_skills"] = json.loads(item["matched_skills_json"]) if item.get("matched_skills_json") else []
        item["missing_skills"] = json.loads(item["missing_skills_json"]) if item.get("missing_skills_json") else []
        item["source_url"] = item.get("source_url") or item.get("url")
        item["source_name"] = item.get("source_name") or item.get("source", "JobMatch AI")
        item["is_demo"] = bool(item.get("is_demo", 0))
        results.append(item)
    return results

def get_saved_job_ids(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT job_id FROM saved_jobs WHERE session_id = ?', (session_id,))
    ids = {row["job_id"] for row in cursor.fetchall()}
    conn.close()
    return ids

def log_job_search(session_id, query_role, location, total_found, source_used):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO job_search_history (session_id, query_role, location, total_found, source_used)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, query_role, location, total_found, source_used))
    conn.commit()
    conn.close()

def get_search_history(limit=30):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM job_search_history ORDER BY searched_at DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard_stats(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total saved jobs for user
    cursor.execute('SELECT COUNT(*) as count FROM saved_jobs WHERE session_id = ?', (session_id,))
    saved_count = cursor.fetchone()["count"]
    
    # Total searches across system
    cursor.execute('SELECT COUNT(*) as count FROM job_search_history')
    total_searches = cursor.fetchone()["count"]
    
    # User's searches
    cursor.execute('SELECT COUNT(*) as count FROM job_search_history WHERE session_id = ?', (session_id,))
    user_searches = cursor.fetchone()["count"]
    
    conn.close()
    return {
        "saved_jobs_count": saved_count,
        "total_searches": total_searches,
        "user_searches": user_searches
    }

def seed_skills_catalog_if_empty(skills_dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM skill_catalog')
    count = cursor.fetchone()["count"]
    if count == 0:
        for category, skills in skills_dict.items():
            for skill in skills:
                cursor.execute('''
                    INSERT OR IGNORE INTO skill_catalog (name, category)
                    VALUES (?, ?)
                ''', (skill, category))
        conn.commit()
    conn.close()

def get_all_catalog_skills():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT name, category FROM skill_catalog WHERE is_active = 1 ORDER BY category, name')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_system_event(session_id, event_type, details, status="INFO"):
    """Records real application and system lifecycle events in SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_logs (session_id, event_type, details, status)
            VALUES (?, ?, ?, ?)
        ''', (session_id or "system", event_type, details, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging system event: {e}")

def get_system_logs(limit=50):
    """Retrieves chronological system audit event logs."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM system_logs ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching system logs: {e}")
        return []
