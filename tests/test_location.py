import unittest
from ml.location_extractor import (
    extract_candidate_location,
    normalize_location,
    location_matches,
    classify_workplace_type
)

class TestLocationExtractionAndFiltering(unittest.TestCase):

    def test_1_extract_location_full_format(self):
        resume_text = (
            "ROHAN SHARMA\n"
            "Bengaluru, Karnataka, India | rohan.sharma@example.com | +91 9876543210\n"
            "PROFESSIONAL SUMMARY: Software Engineer with Python skills."
        )
        res = extract_candidate_location(resume_text)
        self.assertIsNotNone(res)
        self.assertEqual(res["candidate_location"], "Bengaluru, Karnataka, India")
        self.assertEqual(res["primary_city"], "Bengaluru")

    def test_2_candidate_bengaluru_job_bangalore_matches(self):
        matched = location_matches("Bengaluru", "Bangalore, Karnataka")
        self.assertTrue(matched)

    def test_3_candidate_bengaluru_job_mumbai_no_match(self):
        matched = location_matches("Bengaluru", "Mumbai, Maharashtra")
        self.assertFalse(matched)

    def test_4_candidate_bengaluru_job_hyderabad_no_match(self):
        matched = location_matches("Bengaluru", "Hyderabad, Telangana")
        self.assertFalse(matched)

    def test_5_candidate_bengaluru_job_remote_india_matches(self):
        matched = location_matches("Bengaluru", "Remote - India")
        self.assertTrue(matched)

    def test_6_candidate_bengaluru_job_hybrid_bengaluru_matches(self):
        matched = location_matches("Bengaluru", "Hybrid - Bengaluru")
        self.assertTrue(matched)

    def test_7_candidate_bengaluru_job_hybrid_mumbai_no_match(self):
        matched = location_matches("Bengaluru", "Hybrid - Mumbai")
        self.assertFalse(matched)

    def test_8_prioritize_current_location_over_previous(self):
        resume_text = (
            "Name: Jane Doe\n"
            "Current Location: Bengaluru, Karnataka\n"
            "Previous Location: Hyderabad, Telangana\n"
            "Education: Visvesvaraya Technological University, Belagavi\n"
            "Experience: 3 years"
        )
        res = extract_candidate_location(resume_text)
        self.assertIsNotNone(res)
        self.assertEqual(res["primary_city"], "Bengaluru")

    def test_9_no_location_not_guessed(self):
        resume_text = (
            "ALEX SMITH\n"
            "alex.smith@example.com | +1 555-1234\n"
            "Skills: Python, Machine Learning, SQL\n"
            "Experience: Built recommendation models"
        )
        res = extract_candidate_location(resume_text)
        self.assertIsNone(res, "Location should not be guessed when missing from resume.")

    def test_workplace_type_classification(self):
        self.assertEqual(classify_workplace_type("Remote - India"), "Remote")
        self.assertEqual(classify_workplace_type("Hybrid - Bengaluru"), "Hybrid")
        self.assertEqual(classify_workplace_type("Bengaluru, India"), "On-site")
        # Missing location is NOT automatically remote
        self.assertNotEqual(classify_workplace_type(""), "Remote")

    def test_normalization_mappings(self):
        self.assertEqual(normalize_location("Bangalore"), "Bengaluru")
        self.assertEqual(normalize_location("Bangalore, Karnataka"), "Bengaluru, Karnataka")
        self.assertEqual(normalize_location("Gurgaon, Haryana"), "Gurugram, Haryana")
        self.assertEqual(normalize_location("New Delhi"), "Delhi")

if __name__ == "__main__":
    unittest.main()
