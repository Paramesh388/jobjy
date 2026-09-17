import unittest
from utils.url_validator import is_valid_job_url
from services.job_api import (
    load_demo_jobs,
    fetch_from_arbeitnow,
    fetch_from_remotive,
    fetch_from_jobicy,
    search_jobs
)

class TestURLValidation(unittest.TestCase):

    def test_1_valid_http_and_https_urls_accepted(self):
        """Test 1: Valid HTTP and HTTPS URLs are accepted."""
        valid_urls = [
            "https://www.arbeitnow.com/jobs/companies/acme/python-dev-12345",
            "https://remotive.com/remote-jobs/software-dev/python-engineer-9876",
            "https://jobicy.com/jobs/153489-software-engineer",
            "https://jobs.github.com/positions/12345",
            "http://careers.enterprise.org/listing/456",
            "https://tech.company.de/job/lead-architect"
        ]
        for url in valid_urls:
            self.assertTrue(is_valid_job_url(url), f"Expected URL to be valid: {url}")

    def test_2_example_com_and_subdomains_rejected(self):
        """Test 2: URLs with 'example.com' and other placeholders are rejected."""
        invalid_urls = [
            "https://example.com",
            "https://example.com/jobs/123",
            "http://example.com/careers",
            "https://jobs.example.com/posting/456",
            "https://sub.example.com/test",
            "https://example.org/job",
            "https://example.net/listing",
            "https://test.com/job",
            "https://fake.com/job",
            "https://placeholder.com/job",
            "https://sample.com/job"
        ]
        for url in invalid_urls:
            self.assertFalse(is_valid_job_url(url), f"Expected URL to be rejected: {url}")

    def test_3_empty_none_and_non_string_inputs_rejected(self):
        """Test 3: Empty string, None, and non-string inputs are rejected."""
        bad_inputs = ["", "   ", None, 123, [], {}, True, False]
        for inp in bad_inputs:
            self.assertFalse(is_valid_job_url(inp), f"Expected input to be rejected: {inp}")

    def test_4_localhost_and_ip_addresses_rejected(self):
        """Test 4: Localhost and IP address URLs are rejected."""
        local_urls = [
            "http://localhost:5000/job/1",
            "http://localhost/job",
            "http://127.0.0.1:8000/api/job",
            "http://127.0.0.1/careers",
            "https://0.0.0.0:3000/jobs"
        ]
        for url in local_urls:
            self.assertFalse(is_valid_job_url(url), f"Expected localhost/IP to be rejected: {url}")

    def test_5_invalid_schemes_rejected(self):
        """Test 5: URLs without valid schemes (e.g. ftp://, javascript:, file://) are rejected."""
        non_http_urls = [
            "ftp://files.company.com/job.pdf",
            "javascript:void(0)",
            "file:///C:/Users/job.html",
            "mailto:jobs@company.com",
            "tel:+1234567890",
            "data:text/html,<h1>Job</h1>",
            "//careers.company.com/job"
        ]
        for url in non_http_urls:
            self.assertFalse(is_valid_job_url(url), f"Expected invalid scheme to be rejected: {url}")

    def test_6_invalid_domain_or_tld_rejected(self):
        """Test 6: URLs without valid domain/TLD are rejected."""
        malformed_urls = [
            "https://nodotdomain/jobs",
            "http://justwords/123",
            "https://.com/job",
            "https://abc.c/job",
            "https:///",
            "http://",
            "not a url at all"
        ]
        for url in malformed_urls:
            self.assertFalse(is_valid_job_url(url), f"Expected malformed domain to be rejected: {url}")

    def test_7_source_api_domain_matching(self):
        """Test 7: Source API domain matching works correctly when expected_domain is provided."""
        # Arbeitnow matching
        self.assertTrue(is_valid_job_url("https://www.arbeitnow.com/jobs/123", expected_domain="arbeitnow.com"))
        self.assertTrue(is_valid_job_url("https://arbeitnow.com/jobs/123", expected_domain="arbeitnow.com"))
        self.assertFalse(is_valid_job_url("https://remotive.com/jobs/123", expected_domain="arbeitnow.com"))

        # Remotive matching
        self.assertTrue(is_valid_job_url("https://remotive.com/remote-jobs/123", expected_domain="remotive.com"))
        self.assertFalse(is_valid_job_url("https://jobicy.com/jobs/123", expected_domain="remotive.com"))

        # Jobicy matching
        self.assertTrue(is_valid_job_url("https://jobicy.com/jobs/123", expected_domain="jobicy.com"))
        self.assertFalse(is_valid_job_url("https://arbeitnow.com/jobs/123", expected_domain="jobicy.com"))

    def test_8_live_job_fetching_produces_valid_urls(self):
        """Test 8: Live job fetching produces jobs with valid URLs (never example.com)."""
        # Test Arbeitnow
        arbeitnow_jobs = fetch_from_arbeitnow(limit=5)
        if arbeitnow_jobs:
            for j in arbeitnow_jobs:
                self.assertIsNotNone(j.get("source_url"))
                self.assertTrue(is_valid_job_url(j.get("source_url")))
                self.assertNotIn("example.com", j.get("source_url"))
                self.assertEqual(j.get("source_name"), "Arbeitnow")
                self.assertFalse(j.get("is_demo"))

        # Test Remotive
        remotive_jobs = fetch_from_remotive(limit=5)
        if remotive_jobs:
            for j in remotive_jobs:
                self.assertIsNotNone(j.get("source_url"))
                self.assertTrue(is_valid_job_url(j.get("source_url")))
                self.assertNotIn("example.com", j.get("source_url"))
                self.assertEqual(j.get("source_name"), "Remotive")
                self.assertFalse(j.get("is_demo"))

        # Test Jobicy
        jobicy_jobs = fetch_from_jobicy(limit=5)
        if jobicy_jobs:
            for j in jobicy_jobs:
                self.assertIsNotNone(j.get("source_url"))
                self.assertTrue(is_valid_job_url(j.get("source_url")))
                self.assertNotIn("example.com", j.get("source_url"))
                self.assertEqual(j.get("source_name"), "Jobicy")
                self.assertFalse(j.get("is_demo"))

    def test_9_demo_jobs_have_null_urls_and_demo_flag(self):
        """Test 9: Demo jobs have null/disabled URLs with proper explanation."""
        demo_jobs = load_demo_jobs(limit=20)
        self.assertGreater(len(demo_jobs), 0)
        for j in demo_jobs:
            self.assertIsNone(j.get("source_url"), f"Demo job {j.get('id')} has non-null source_url: {j.get('source_url')}")
            self.assertIsNone(j.get("url"), f"Demo job {j.get('id')} has non-null url: {j.get('url')}")
            self.assertTrue(j.get("is_demo"), f"Demo job {j.get('id')} must have is_demo=True")
            self.assertEqual(j.get("source_name"), "Demo Data")
            self.assertIn("DEMO", j.get("source").upper())

if __name__ == "__main__":
    unittest.main()
