import unittest
from ml.job_matcher import (
    calculate_text_similarity,
    calculate_skill_overlap,
    match_resume_to_job,
    match_and_rank_jobs,
    analyze_skill_gaps
)
from ml.skills_dictionary import extract_skills_from_text

class TestJobMatcher(unittest.TestCase):

    def setUp(self):
        self.candidate_skills_rich = ["Python", "Flask", "SQL", "Git", "Docker", "REST API", "PostgreSQL"]
        self.candidate_skills_few = ["Python"]
        self.rich_resume_text = (
            "Senior Python Developer with extensive experience in Flask web framework, "
            "PostgreSQL database optimization, REST API design, Git, and Docker containerization."
        )
        self.brief_resume_text = "Junior candidate with basic Python syntax knowledge."

    def test_skills_extraction_rich_vs_few(self):
        skills_rich = extract_skills_from_text(self.rich_resume_text)
        self.assertIn("Python", skills_rich)
        self.assertIn("Flask", skills_rich)
        self.assertIn("PostgreSQL", skills_rich)
        self.assertIn("Docker", skills_rich)
        self.assertGreaterEqual(len(skills_rich), 5)

        skills_few = extract_skills_from_text(self.brief_resume_text)
        self.assertIn("Python", skills_few)
        self.assertEqual(len(skills_few), 1)

    def test_strong_vs_weak_job_match(self):
        strong_job = {
            "title": "Python Flask Engineer",
            "description": "We need a Python developer experienced in Flask, REST API, SQL, Docker, and Git.",
            "skills": ["Python", "Flask", "REST API", "SQL", "Docker", "Git"]
        }

        weak_job = {
            "title": "Senior iOS Mobile Developer",
            "description": "Looking for Swift and Objective-C developer for Apple iOS applications. Requires Xcode and CocoaPods.",
            "skills": ["Swift", "Objective-C", "Xcode", "iOS"]
        }

        strong_result = match_resume_to_job(self.rich_resume_text, self.candidate_skills_rich, strong_job)
        weak_result = match_resume_to_job(self.rich_resume_text, self.candidate_skills_rich, weak_job)

        self.assertGreater(strong_result["match_score"], weak_result["match_score"])
        self.assertGreater(strong_result["match_score"], 50.0)
        self.assertLess(weak_result["match_score"], 35.0)

    def test_job_without_description_handling(self):
        empty_desc_job = {
            "title": "Generic Associate",
            "description": "",
            "skills": []
        }
        res = match_resume_to_job(self.rich_resume_text, self.candidate_skills_rich, empty_desc_job)
        self.assertEqual(res["match_score"], 0.0)
        self.assertIn("Insufficient information", res["score_note"])

    def test_skill_overlap_math(self):
        cand = ["Python", "SQL", "Git", "HTML"]
        job_skills = ["Python", "SQL", "Flask", "Git", "Docker"]
        
        eval_res = calculate_skill_overlap(cand, job_skills)
        # Matched: Python, SQL, Git (3)
        # Missing: Flask, Docker (2)
        # Ratio: 3 / 5 = 0.60
        self.assertEqual(eval_res["matched_count"], 3)
        self.assertEqual(eval_res["required_count"], 5)
        self.assertAlmostEqual(eval_res["skill_match_ratio"], 0.60, places=2)
        self.assertIn("Docker", eval_res["missing_skills"])
        self.assertIn("Flask", eval_res["missing_skills"])
        self.assertIn("Python", eval_res["matched_skills"])

    def test_mathematical_scoring_formula(self):
        # Verify (text_similarity * 0.60) + (skill_match * 0.40)
        job = {
            "title": "Software Developer",
            "description": "Python, SQL, and Git development.",
            "skills": ["Python", "SQL", "Git"]
        }
        cand = ["Python", "SQL", "Git"]
        res = match_resume_to_job("Python, SQL, and Git development.", cand, job)
        
        expected_score = round(((res["text_similarity_pct"] * 0.60) + (res["skill_match_pct"] * 0.40)), 1)
        self.assertEqual(res["match_score"], expected_score)

    def test_skill_gap_analysis(self):
        ranked = [
            {"title": "Job 1", "matched_skills": ["Python"], "missing_skills": ["Docker", "AWS"]},
            {"title": "Job 2", "matched_skills": ["Python"], "missing_skills": ["Docker", "Kubernetes"]},
            {"title": "Job 3", "matched_skills": ["Python"], "missing_skills": ["Docker", "AWS"]}
        ]
        gaps = analyze_skill_gaps(["Python"], ranked)
        gap_dict = {g["skill"]: g["count"] for g in gaps["gaps"]}
        
        self.assertEqual(gap_dict.get("Docker"), 3)
        self.assertEqual(gap_dict.get("AWS"), 2)
        self.assertEqual(gap_dict.get("Kubernetes"), 1)

if __name__ == "__main__":
    unittest.main()
