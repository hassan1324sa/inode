import PyPDF2
import sys

def extract_text(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            print(text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_text(sys.argv[1])
