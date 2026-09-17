import unittest
import os
import tempfile
from utils.resume_parser import parse_resume, ResumeParsingError
from utils.text_cleaner import clean_resume_text, normalize_whitespace

class TestResumeParser(unittest.TestCase):

    def test_valid_pdf_parsing(self):
        pdf_path = os.path.join("sample_resumes", "sample_python_developer.pdf")
        if os.path.exists(pdf_path):
            text = parse_resume(pdf_path)
            self.assertIsInstance(text, str)
            self.assertGreater(len(text), 100)
            self.assertIn("Python", text)
            self.assertIn("ROHAN SHARMA", text)

    def test_valid_docx_parsing(self):
        docx_path = os.path.join("sample_resumes", "sample_data_analyst.docx")
        if os.path.exists(docx_path):
            text = parse_resume(docx_path)
            self.assertIsInstance(text, str)
            self.assertGreater(len(text), 30)
            self.assertIn("Python", text)

    def test_valid_txt_parsing(self):
        txt_path = os.path.join("sample_resumes", "sample_frontend_dev.txt")
        if os.path.exists(txt_path):
            text = parse_resume(txt_path)
            self.assertIsInstance(text, str)
            self.assertIn("React", text)
            self.assertIn("PRIYA NAIR", text)

    def test_invalid_file_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"binary executable content")
            temp_path = f.name

        try:
            with self.assertRaises(ResumeParsingError) as context:
                parse_resume(temp_path)
            self.assertIn("Unsupported file format", str(context.exception))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_empty_resume_handling(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
            f.write("   \n\n  ")
            temp_path = f.name

        try:
            with self.assertRaises(ResumeParsingError) as context:
                parse_resume(temp_path)
            self.assertIn("Unable to extract readable text", str(context.exception))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_text_cleaner_normalizes_whitespace(self):
        messy_text = "Python   \t\tDeveloper \r\n\r\n\r\nwith   SQL   • Docker"
        cleaned = clean_resume_text(messy_text)
        self.assertNotIn("\t", cleaned)
        self.assertIn("Python Developer", cleaned)
        self.assertIn("- Docker", cleaned)

if __name__ == "__main__":
    unittest.main()
