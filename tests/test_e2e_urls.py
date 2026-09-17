import unittest
import requests
import re
from utils.url_validator import is_valid_job_url

class TestE2EURLFlow(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:5000"

    def setUp(self):
        self.session = requests.Session()
        # Upload resume to initialize session
        with open("sample_resumes/sample_python_developer.txt", "rb") as f:
            res = self.session.post(f"{self.BASE_URL}/upload", files={"resume": f})
        self.assertEqual(res.status_code, 200)

    def test_bengaluru_demo_fallback_has_no_fake_links(self):
        """Verify Bengaluru search does NOT contain example.com and handles live/demo states properly."""
        res = self.session.get(f"{self.BASE_URL}/jobs?role=Python&location=Bengaluru")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("example.com", res.text)
        if "DEMO DATA" in res.text:
            self.assertIn("Demo Job — Application link unavailable", res.text)
            self.assertIn("disabled", res.text)
        else:
            self.assertIn("View & Apply on ", res.text)
            self.assertIn('target="_blank"', res.text)

    def test_remote_jobs_have_valid_live_urls(self):
        """Verify remote live search provides valid, real external links in new tabs."""
        res = self.session.get(f"{self.BASE_URL}/jobs?role=Developer&location=Remote")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("example.com", res.text)
        
        # Check target="_blank" and rel="noopener noreferrer"
        if "View & Apply on " in res.text:
            self.assertIn('target="_blank"', res.text)
            self.assertIn('rel="noopener noreferrer"', res.text)
            # Find URLs in href
            urls = re.findall(r'href="(https://[^"]+)"', res.text)
            self.assertGreater(len(urls), 0)
            for u in urls:
                if "cdn" not in u and "google" not in u: # ignore CDN stylesheets/fonts
                    self.assertTrue(is_valid_job_url(u), f"URL is invalid: {u}")
                    self.assertNotIn("example.com", u)

    def test_job_details_page_url_handling(self):
        """Verify job details page correctly handles live URLs and demo fallback."""
        res_demo = self.session.get(f"{self.BASE_URL}/job/demo-py-01")
        self.assertEqual(res_demo.status_code, 200)
        self.assertNotIn("example.com", res_demo.text)
        self.assertIn("Demo Job — Application link unavailable", res_demo.text)

    def test_saved_jobs_page_url_handling(self):
        """Verify saved jobs page renders without example.com."""
        res_saved = self.session.get(f"{self.BASE_URL}/saved-jobs")
        self.assertEqual(res_saved.status_code, 200)
        self.assertNotIn("example.com", res_saved.text)

if __name__ == "__main__":
    unittest.main()
