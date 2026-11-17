from pathlib import Path
import pdfplumber
import pytesseract
from PIL import Image
import logging

logging.getLogger("pdfminer").setLevel(logging.ERROR)

# Set Tesseract executable path for Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class ReportDetector:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found at: {self.file_path}")

    def get_file_type(self) -> str:
        """
        Inspects the file extension and inner text layer 
        to return: 'digital_pdf', 'scanned_pdf', or 'image'.
        """
        suffix = self.file_path.suffix.lower()

        if suffix == ".pdf":
            has_text = False
            try:
                with pdfplumber.open(self.file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text() or ""
                        if len(text.strip()) > 50:
                            has_text = True
                            break
            except Exception as e:
                print(f"Error checking PDF text layer: {e}")

            return "digital_pdf" if has_text else "scanned_pdf"

        elif suffix in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
            return "image"

        else:
            raise ValueError(f"Unsupported file format: {suffix}")


class PDFExtractor:
    def __init__(self, file_path: str | Path):
        self.pdf_path = Path(file_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"File not found at: {file_path}")

    def extract(self) -> str:
        extracted_text = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                # layout=True preserves column spacing cleanly for the LLM
                text = page.extract_text(layout=True) or ""
                extracted_text.append(text)
        return "\n".join(extracted_text)


class OCRExtractor:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found at: {self.file_path}")

    def extract(self) -> str:
        """Extracts text from scanned PDFs (page-by-page) or image files using Tesseract OCR."""
        if self.file_path.suffix.lower() == ".pdf":
            extracted_text = []
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    # Render scanned PDF page to high-res PIL Image before OCR
                    pil_image = page.to_image(resolution=300).original
                    text = pytesseract.image_to_string(pil_image, lang="eng")
                    extracted_text.append(text)
            return "\n".join(extracted_text)
        else:
            image = Image.open(self.file_path)
            return pytesseract.image_to_string(image, lang="eng")


def extract_report_text(file_path: str | Path) -> str:
    """Unified pipeline helper to route and extract raw text."""
    detector = ReportDetector(file_path)
    file_type = detector.get_file_type()

    if file_type == "digital_pdf":
        return PDFExtractor(file_path).extract()
    else:
        return OCRExtractor(file_path).extract()
