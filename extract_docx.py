import sys
import os
from docx import Document

def extract_text_from_docx(file_path):
    """
    Extract text from a .docx file.
    
    Args:
        file_path (str): Path to the .docx file
        
    Returns:
        str: Extracted text from the document
    """
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"Error extracting text from {file_path}: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_docx.py <path_to_docx_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    text = extract_text_from_docx(file_path)
    # Handle Unicode characters that can't be displayed in console
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: replace or ignore problematic characters
        print(text.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))