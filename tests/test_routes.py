import unittest
import os
import io
import json
from app import create_app
from config import Config

class TestFlaskRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"JobMatch", response.data)
        self.assertIn(b"Upload Resume", response.data)

    def test_upload_page_loads(self):
        response = self.client.get("/upload")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Upload Your Resume", response.data)

    def test_resume_upload_and_analysis_flow(self):
        sample_txt = b"ROHAN SHARMA\nBengaluru, India\nB.Tech in Computer Science\nSkills: Python, Flask, SQL, Git, Docker, REST API\nExperience: 2 Years as Software Developer at Tech Corp."
        
        data = {
            "resume": (io.BytesIO(sample_txt), "test_resume.txt")
        }
        
        # Post resume
        response = self.client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Resume Analysis", response.data)
        self.assertIn(b"Python", response.data)

    def test_update_skills_api(self):
        with self.client.session_transaction() as sess:
            sess["session_id"] = "test-session-123"

        # Update skills
        payload = {"skills": ["Python", "Flask", "Docker", "AWS"]}
        response = self.client.post(
            "/api/update-skills",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        res_json = response.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["count"], 4)

    def test_save_and_unsave_job_api(self):
        with self.client.session_transaction() as sess:
            sess["session_id"] = "test-session-save-job"

        job_data = {
            "id": "demo-test-01",
            "title": "Python Developer",
            "company": "Apex Corp",
            "location": "Bengaluru",
            "match_score": 85.5,
            "employment_type": "Full-time",
            "posted_date": "Today",
            "url": "https://remotive.com/remote-jobs/software-dev-1",
            "source_url": "https://remotive.com/remote-jobs/software-dev-1",
            "source_name": "Remotive",
            "source": "Live API (Remotive)"
        }

        # 1. Save job
        res_save = self.client.post(
            "/api/save-job",
            data=json.dumps(job_data),
            content_type="application/json"
        )
        self.assertEqual(res_save.status_code, 200)
        self.assertTrue(res_save.get_json()["success"])

        # 2. Verify in saved-jobs page
        res_view = self.client.get("/saved-jobs")
        self.assertEqual(res_view.status_code, 200)
        self.assertIn(b"Apex Corp", res_view.data)

        # 3. Unsave job
        res_unsave = self.client.post(
            "/api/unsave-job",
            data=json.dumps({"id": "demo-test-01"}),
            content_type="application/json"
        )
        self.assertEqual(res_unsave.status_code, 200)
        self.assertTrue(res_unsave.get_json()["success"])

    def test_dashboard_and_admin_pages(self):
        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"Dashboard", res_dash.data)

        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"System Audit", res_admin.data)

if __name__ == "__main__":
    unittest.main()
