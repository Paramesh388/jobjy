import unittest
import io
import json
from app import create_app
from models.database import init_db, log_system_event, get_system_logs

class TestUIControlsAndFilters(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Seed candidate resume session
        sample_txt = b"RAHUL VERMA\nBengaluru, Karnataka, India\nSenior Full Stack Python & React Developer\nSkills: Python, Django, Flask, React, JavaScript, Docker, AWS, PostgreSQL, REST API\nExperience: 4 years designing distributed web systems."
        data = {"resume": (io.BytesIO(sample_txt), "sample_resume.txt")}
        self.client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)

    def test_role_search_query(self):
        """Verify searching for specific roles returns matching jobs and sets the role query."""
        res = self.client.get("/jobs?role=Python&location=Bengaluru")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Python", res.data)

        res_fe = self.client.get("/jobs?role=Frontend&location=Bengaluru")
        self.assertEqual(res_fe.status_code, 200)
        self.assertIn(b"Frontend", res_fe.data)

    def test_location_selection(self):
        """Verify location filter updates search location and applies location constraints."""
        res_blr = self.client.get("/jobs?role=Developer&location=Bengaluru")
        self.assertEqual(res_blr.status_code, 200)
        self.assertIn(b"Bengaluru", res_blr.data)

        res_hyd = self.client.get("/jobs?role=Developer&location=Hyderabad")
        self.assertEqual(res_hyd.status_code, 200)
        self.assertIn(b"Hyderabad", res_hyd.data)

    def test_all_sorting_modes(self):
        """Verify all 6 sort options execute successfully without 500 errors."""
        sort_options = ["score", "score_asc", "recent", "oldest", "title", "company"]
        for sort_by in sort_options:
            res = self.client.get(f"/jobs?role=Developer&location=Bengaluru&sort_by={sort_by}")
            self.assertEqual(res.status_code, 200, f"Failed for sort_by={sort_by}")
            self.assertIn(b"Recommended Jobs", res.data)

    def test_all_job_type_filters(self):
        """Verify all job type filters (Full-time, Part-time, Contract, Internship, Remote) execute."""
        types = ["All", "Full-time", "Part-time", "Contract", "Internship", "Remote"]
        for jt in types:
            res = self.client.get(f"/jobs?role=Developer&location=Bengaluru&job_type={jt}")
            self.assertEqual(res.status_code, 200, f"Failed for job_type={jt}")

    def test_min_score_filter(self):
        """Verify min score filtering."""
        res_high = self.client.get("/jobs?role=Developer&location=Bengaluru&min_score=95")
        self.assertEqual(res_high.status_code, 200)
        res_zero = self.client.get("/jobs?role=Developer&location=Bengaluru&min_score=0")
        self.assertEqual(res_zero.status_code, 200)

    def test_system_event_logging_audit(self):
        """Verify system logs table records real lifecycle events."""
        with self.client.session_transaction() as sess:
            sess_id = sess.get("session_id", "test-session-audit")
        
        log_system_event(sess_id, "Test Audit Event", "Testing system event persistence", status="SUCCESS")
        logs = get_system_logs(limit=20)
        self.assertTrue(any(l["event_type"] == "Test Audit Event" for l in logs))

        # Check /admin route
        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"Test Audit Event", res_admin.data)

if __name__ == "__main__":
    unittest.main()
