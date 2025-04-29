# processing.py
# Using Pillow (PIL) instead of OpenCV
from PIL import Image, ImageOps # Import Pillow
import pytesseract
from typing import List, Optional, Dict, Any
import io # To handle bytes as file-like object for Pillow
import re
import traceback

# Import models for type hinting
from models import LabTest

# --- Optional: Configure Tesseract Path ---
# If Tesseract is not in your PATH, uncomment and set the correct path
# Example for Windows:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Example for Linux (if installed in a non-standard location):
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

# --- Step 2 (Revised): Image Preprocessing using Pillow ---
def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Loads image from bytes using Pillow, converts to grayscale.
    Potentially add more preprocessing steps here later.
    Returns a Pillow Image object.
    """
    try:
        # Open image bytes with Pillow
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to grayscale ('L' mode in Pillow)
        gray_img = img.convert('L')

        # --- Potential Future Enhancements (using Pillow) ---
        # Auto Contrast (often helpful)
        # contrasted_img = ImageOps.autocontrast(gray_img)
        # return contrasted_img

        # Simple Thresholding (Example)
        # threshold = 128 # Adjust threshold value as needed
        # thresh_img = gray_img.point(lambda p: p > threshold and 255)
        # return thresh_img
        # --- End Enhancements ---

        print("Image preprocessing (Pillow): Converted to grayscale.")
        return gray_img # Return grayscale Pillow image object

    except Exception as e:
        print(f"Error during image preprocessing (Pillow): {e}")
        # Re-raise the exception to be caught by the main API handler
        raise ValueError(f"Preprocessing failed (Pillow): {e}") from e


# --- Step 3 (Revised): OCR Implementation ---
def perform_ocr(pil_image: Image.Image) -> str:
    """
    Performs OCR on the preprocessed Pillow image using pytesseract.
    """
    try:
        # Configure Tesseract options
        # --psm 6: Assume a single uniform block of text (good for tables)
        # Other options: 3 (default), 4 (single column), 11 (sparse text)
        custom_config = r'--oem 3 --psm 6 -l eng' # OEM 3 is default, PSM 6 for tables, lang eng

        print(f"Performing OCR with config: {custom_config}")
        # pytesseract works directly with Pillow images
        text = pytesseract.image_to_string(pil_image, config=custom_config)

        if not text or text.isspace():
             print("Warning: OCR returned empty or whitespace string.")
        else:
            print(f"OCR successful, extracted {len(text)} characters.")
            # print("---- OCR Output Start ----")
            # print(text[:500] + "...") # Print start of OCR text for debugging
            # print("---- OCR Output End ----")

        return text

    except pytesseract.TesseractNotFoundError:
        print("ERROR: Tesseract executable not found. Ensure Tesseract is installed and in PATH or configure pytesseract.pytesseract.tesseract_cmd")
        raise RuntimeError("Tesseract OCR engine not found.")
    except Exception as e:
        print(f"Error during OCR: {e}")
        raise RuntimeError(f"OCR failed: {e}") from e


# --- Step 4: Core Parsing Logic ---
# Define Regex Patterns (Compile for efficiency)
VALUE_RE = re.compile(r'(\b\d+\.\d+\b|\b\d+\b|\b[Pp]ositive\b|\b[Nn]egative\b|\b[Dd]etected\b|\b[Nn]on [Rr]eactive\b|\b[Rr]eactive\b|\b[Nn]ormal\b|\b[Aa]bnornmal\b)', re.IGNORECASE)
UNIT_RE = re.compile(r'\b(%|g/dL|gm/dL|mg/dL|Seconds|U/L|IU/L|fl|fL|cu\.?mm|cells/µL|cells/ul|million/cu\.?mm|mEq/Litre|mmol/L|pg/mL|ng/mL|H\.P\.F\.|/HPF)\b', re.IGNORECASE)
RANGE_RE = re.compile(r'(\b\d+\.?\d*\s*-\s*\d+\.?\d*\b|<\s*\d+\.?\d*|>\s*\d+\.?\d*|\b\d+-\d+\b|[Uu]p [Tt]o \d+\.?\d*|\b[Nn]egative\b|\b[Nn]ormal\b)', re.IGNORECASE)
IGNORE_KEYWORDS = ["test", "investigation", "result", "unit", "range", "reference", "interval", "method", "specimen", "serum", "plasma", "blood", "urine", "report", "page", "date", "patient", "doctor", "hospital", "pathology", "signature", "-------", "======", "*******", "end of report", "authorized", "technologist"]

def is_likely_header_or_footer(line: str) -> bool:
    """Checks if a line is likely ignorable header/footer content."""
    line_lower = line.strip().lower()
    if not line_lower: # Skip empty lines
        return True
    if any(keyword in line_lower for keyword in IGNORE_KEYWORDS) and len(line_lower.split()) < 5 :
         if re.fullmatch(r'test(\s+name)?\s+result\s+unit\s+(bio\.\s+)?ref.*range.*', line_lower):
             return True
         if re.fullmatch(r'investigation\s+result\s+unit\s+range.*', line_lower):
             return True
         if all(c in '- =_*' for c in line_lower):
            return True
    return False

def parse_text_data(text: str) -> List[Dict[str, Any]]:
    """
    Parses raw OCR text to extract structured lab test data using regex and heuristics.
    Focuses on lines that appear to contain test results in a semi-tabular format.
    """
    print("Starting OCR text parsing...")
    results = []
    lines = text.splitlines()
    potential_test_name = None

    for i, line in enumerate(lines):
        line = line.strip()

        if is_likely_header_or_footer(line):
            potential_test_name = None
            continue

        value_match = VALUE_RE.search(line)
        unit_match = UNIT_RE.search(line)
        range_match = RANGE_RE.search(line)

        if value_match:
            value_str = value_match.group(1).strip()
            value_start_index = value_match.start()
            current_test_name = "Unknown"
            unit_str = None
            range_str = None

            if unit_match:
                unit_str = unit_match.group(1).strip()

            if range_match:
                 if range_match.start() > value_start_index:
                     range_str = range_match.group(1).strip()

            possible_name_part = line[:value_start_index].strip()
            cleaned_name = re.sub(r'[^\w\s\(\)-]+$', '', possible_name_part).strip()

            if cleaned_name and len(cleaned_name) > 2:
                 if not cleaned_name and i > 0 and not is_likely_header_or_footer(lines[i-1]) and not VALUE_RE.search(lines[i-1]):
                     potential_previous_name = lines[i-1].strip()
                     if re.match(r'^[A-Za-z\s\(\)\-]+', potential_previous_name):
                           current_test_name = potential_previous_name
                     else:
                           current_test_name = "Unknown - Check Previous"
                 else:
                     current_test_name = cleaned_name
                     potential_test_name = None

                 if not re.search(r'[a-zA-Z]{3,}', current_test_name):
                     continue

            elif potential_test_name:
                 current_test_name = potential_test_name
                 potential_test_name = None
            else:
                 continue

            extracted = {
                "test_name": current_test_name,
                "test_value": value_str,
                "test_unit": unit_str,
                "bio_reference_range": range_str
            }
            results.append(extracted)

        else:
             line_trimmed = line.strip()
             if len(line_trimmed) > 3 and re.match(r'^[A-Za-z\s\(\)\-\#]+', line_trimmed) and not range_match and not unit_match:
                  potential_test_name = line_trimmed
             else:
                  potential_test_name = None

    print(f"Parsing finished. Found {len(results)} potential test entries.")
    return results


# --- Step 5: Range Calculation Logic ---
def calculate_out_of_range(value_str: Optional[str], range_str: Optional[str]) -> Optional[bool]:
    """
    Compares a test value string to a reference range string.
    Returns True (out of range), False (in range), None (cannot compare).
    """
    if value_str is None or range_str is None:
        return None

    value_str_lower = value_str.strip().lower()
    range_str_lower = range_str.strip().lower()

    if value_str_lower in ["positive", "detected", "reactive"]:
        return True if range_str_lower == "negative" else None
    if value_str_lower == "negative":
        return False if range_str_lower == "negative" else None
    if range_str_lower in ["negative", "normal"] and not value_str_lower in ["negative", "normal"]:
         return None

    try:
        cleaned_value_str = re.sub(r'[<>]', '', value_str.strip())
        value_num = float(cleaned_value_str)
    except ValueError:
        return None

    try:
        match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', range_str)
        if match:
            lower, upper = float(match.group(1)), float(match.group(2))
            return not (lower <= value_num <= upper)

        match = re.search(r'<\s*(\d+\.?\d*)', range_str)
        if match:
            upper = float(match.group(1))
            return value_num >= upper

        match = re.search(r'>\s*(\d+\.?\d*)', range_str)
        if match:
            lower = float(match.group(1))
            return value_num <= lower

        match = re.search(r'[Uu]p [Tt]o (\d+\.?\d*)', range_str, re.IGNORECASE)
        if match:
            upper = float(match.group(1))
            return value_num > upper

    except ValueError:
        return None
    except Exception as e:
        print(f"Unexpected error in calculate_out_of_range for value='{value_str}', range='{range_str}': {e}")
        return None

    return None


# --- Main Orchestrator Function --- (No changes needed here conceptually)
def process_lab_report(image_bytes: bytes) -> List[LabTest]:
    """
    Main orchestrator function for processing the lab report image using Pillow.
    """
    print("Starting lab report processing (Pillow)...")
    final_results = []
    try:
        # Uses Pillow-based preprocessing now
        preprocessed_img : Image.Image = preprocess_image(image_bytes)
        # Passes Pillow image to OCR
        ocr_text = perform_ocr(preprocessed_img)
        parsed_items = parse_text_data(ocr_text)

        for item in parsed_items:
            value_str = item.get("test_value")
            range_str = item.get("bio_reference_range")
            out_of_range = calculate_out_of_range(value_str, range_str)

            lab_test = LabTest(
                test_name=item.get("test_name", "Unknown"),
                test_value=value_str,
                bio_reference_range=range_str,
                test_unit=item.get("test_unit"),
                lab_test_out_of_range=out_of_range
            )
            final_results.append(lab_test)

        print(f"Processing complete (Pillow). Generated {len(final_results)} LabTest objects.")
        return final_results

    except Exception as e:
        print(f"Error in process_lab_report pipeline (Pillow): {e}")
        print(traceback.format_exc())
        return [] # Return empty list on failure