import unittest
from unittest.mock import patch
from services.job_api import search_jobs, load_demo_jobs, strip_html_tags
from ml.job_matcher import match_and_rank_jobs

class TestJobAPI(unittest.TestCase):

    def test_strip_html_tags(self):
        raw_html = "<p>Looking for a <strong>Python</strong> developer &amp; engineer.</p>"
        clean = strip_html_tags(raw_html)
        self.assertEqual(clean, "Looking for a Python developer engineer.")

    def test_demo_jobs_schema_compliance(self):
        jobs = load_demo_jobs(limit=10)
        self.assertGreater(len(jobs), 0)
        
        required_keys = ["id", "title", "company", "location", "description", "skills", "employment_type", "posted_date", "url", "source_url", "source_name", "source", "is_demo"]
        for j in jobs:
            for k in required_keys:
                self.assertIn(k, j, f"Key '{k}' is missing from normalized job schema.")
            self.assertIsNone(j["source_url"], "Demo jobs must have null source_url to prevent placeholder links.")
            self.assertTrue(j["is_demo"], "Demo job must have is_demo set to True.")

    def test_deduplication_of_jobs(self):
        dup_jobs = [
            {"id": "1", "title": "Python Dev", "company": "Acme", "description": "Python dev", "skills": ["Python"]},
            {"id": "2", "title": "Python Dev", "company": "Acme", "description": "Python dev", "skills": ["Python"]},
            {"id": "3", "title": "Data Analyst", "company": "Acme", "description": "SQL dev", "skills": ["SQL"]}
        ]
        ranked = match_and_rank_jobs("Python and SQL", ["Python", "SQL"], dup_jobs)
        self.assertEqual(len(ranked), 2)

    @patch("services.job_api.fetch_from_himalayas")
    @patch("services.job_api.fetch_from_remoteok")
    @patch("services.job_api.fetch_from_arbeitnow")
    @patch("services.job_api.fetch_from_remotive")
    @patch("services.job_api.fetch_from_jobicy")
    def test_offline_fallback_to_demo_data(self, mock_jobicy, mock_remotive, mock_arbeitnow, mock_remoteok, mock_himalayas):
        # Simulate network failure across all public APIs
        mock_arbeitnow.side_effect = Exception("Connection timed out")
        mock_remotive.side_effect = Exception("DNS lookup failed")
        mock_jobicy.side_effect = Exception("API offline")
        mock_remoteok.side_effect = Exception("API offline")
        mock_himalayas.side_effect = Exception("API offline")

        jobs, source_name, is_demo = search_jobs(role_query="Python", location="Bengaluru", limit=10)

        self.assertTrue(is_demo)
        self.assertIn("DEMO DATA", source_name)
        self.assertGreater(len(jobs), 0)

if __name__ == "__main__":
    unittest.main()
