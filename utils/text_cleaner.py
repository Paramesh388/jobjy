import re
import unicodedata

def normalize_whitespace(text: str) -> str:
    """Replaces multiple consecutive spaces, tabs, and linebreaks with a single space."""
    if not text:
        return ""
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    # Replace non-breaking spaces and tabs
    text = text.replace("\xa0", " ").replace("\t", " ")
    # Replace carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse more than two consecutive newlines into two
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()

def clean_resume_text(text: str) -> str:
    """
    Cleans raw resume text by removing binary garbage, control characters,
    normalizing whitespace, and standardizing bullet points.
    """
    if not text:
        return ""
        
    # Remove null bytes and non-printable characters
    text = "".join(ch for ch in text if ch.isprintable() or ch in ("\n", "\t"))
    
    # Replace various bullet characters with standard dash
    text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u25AA\u25CF\u2013\u2014]", "-", text)
    
    # Normalize whitespace
    text = normalize_whitespace(text)
    
    return text

def clean_for_nlp(text: str) -> str:
    """
    Prepares text for TF-IDF vectorization:
    - Lowercases text
    - Preserves meaningful characters (letters, numbers, +, # for C++, C#)
    - Removes punctuation and emails
    """
    if not text:
        return ""
        
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    
    # Remove email addresses
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", " ", text)
    
    # Remove phone numbers
    text = re.sub(r"\+?\d[\d -]{8,}\d", " ", text)
    
    # Replace punctuation characters except '+' and '#' which matter for tech skills like C++, C#
    text = re.sub(r"[^\w\s+#]", " ", text)
    
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()
