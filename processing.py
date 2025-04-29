# processing.py
import cv2
import numpy as np
import pytesseract
from typing import List
import io # To handle bytes as file-like object for OpenCV

# Import models for type hinting
from models import LabTest

# --- Optional: Configure Tesseract Path ---
# If Tesseract is not in your PATH, uncomment and set the correct path
# Example for Windows:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Example for Linux (if installed in a non-standard location):
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Loads image from bytes, converts to grayscale using OpenCV.
    Potentially add more preprocessing steps here later.
    """
    try:
        # Decode image bytes into an OpenCV image object
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode image bytes. Check file format/integrity.")

        # Convert to grayscale
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # --- Potential Future Enhancements (Keep it simple for now) ---
        # Thresholding (Example: Otsu's thresholding)
        # _, thresh_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # return thresh_img # Return thresholded if uncommented

        # Denoising (Example: Median Blur)
        # denoised_img = cv2.medianBlur(gray_img, 3)
        # return denoised_img # Return denoised if uncommented
        # --- End Enhancements ---

        print("Image preprocessing: Converted to grayscale.")
        return gray_img # Return grayscale for now

    except Exception as e:
        print(f"Error during image preprocessing: {e}")
        # Re-raise the exception to be caught by the main API handler
        raise ValueError(f"Preprocessing failed: {e}") from e

# processing.py (continued)

def perform_ocr(cv_image: np.ndarray) -> str:
    """
    Performs OCR on the preprocessed OpenCV image using pytesseract.
    """
    try:
        # Configure Tesseract options
        # --psm 6: Assume a single uniform block of text (good for tables)
        # Other options: 3 (default), 4 (single column), 11 (sparse text)
        custom_config = r'--oem 3 --psm 6 -l eng' # OEM 3 is default, PSM 6 for tables, lang eng

        print(f"Performing OCR with config: {custom_config}")
        text = pytesseract.image_to_string(cv_image, config=custom_config)

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

# --- Placeholder for the rest of the processing ---
# We still need parse_text_data, calculate_out_of_range, and process_lab_report

def parse_text_data(text: str) -> List[dict]:
    """Placeholder for text parsing logic."""
    print("Parsing OCR text (placeholder)...")
    # TODO: Implement actual parsing logic here (Step 4)
    return [] # Return empty list for now

def calculate_out_of_range(value_str: Optional[str], range_str: Optional[str]) -> Optional[bool]:
    """Placeholder for range calculation logic."""
    # TODO: Implement range comparison logic here (Step 5)
    return None # Return None for now

def process_lab_report(image_bytes: bytes) -> List[LabTest]:
    """
    Main orchestrator function for processing the lab report image.
    """
    print("Starting lab report processing...")
    preprocessed_img = preprocess_image(image_bytes)
    ocr_text = perform_ocr(preprocessed_img)

    # --- Currently uses placeholder functions ---
    parsed_items = parse_text_data(ocr_text) # Will be empty for now
    final_results = []
    for item in parsed_items: # Loop will not run initially
        out_of_range = calculate_out_of_range(item.get("test_value"), item.get("bio_reference_range"))
        lab_test = LabTest(
            test_name=item.get("test_name"),
            test_value=item.get("test_value"),
            bio_reference_range=item.get("bio_reference_range"),
            test_unit=item.get("test_unit"),
            lab_test_out_of_range=out_of_range
        )
        final_results.append(lab_test)
    # --- End placeholder section ---

    # For now, just return an empty list until parsing is implemented
    print("Processing complete (parsing logic pending).")
    return final_results # Return empty list until Step 4 is done