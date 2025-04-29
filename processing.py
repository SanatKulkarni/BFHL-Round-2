# processing.py
import cv2
import numpy as np
import pytesseract
from typing import List, Optional, Dict, Any
import io
import re # Import regular expression module
import traceback

# Import models for type hinting
from models import LabTest

# --- Optional: Configure Tesseract Path ---
# ... (keep the Tesseract path configuration as before if needed) ...

# --- preprocess_image function ---
# ... (keep the preprocess_image function as defined before) ...

# --- perform_ocr function ---
# ... (keep the perform_ocr function as defined before) ...


# --- Step 4: Core Parsing Logic ---

# Define Regex Patterns (Compile for efficiency)
# Value: Catches numbers (int/float) and common qualitative results. Added case-insensitivity for text.
VALUE_RE = re.compile(r'(\b\d+\.\d+\b|\b\d+\b|\b[Pp]ositive\b|\b[Nn]egative\b|\b[Dd]etected\b|\b[Nn]on [Rr]eactive\b|\b[Rr]eactive\b|\b[Nn]ormal\b|\b[Aa]bnornmal\b)', re.IGNORECASE)

# Unit: Common lab units. Added word boundaries (\b) to avoid partial matches. Case-insensitive.
# Expanded list slightly based on sample images. Needs refinement.
UNIT_RE = re.compile(r'\b(%|g/dL|gm/dL|mg/dL|Seconds|U/L|IU/L|fl|fL|cu\.?mm|cells/µL|cells/ul|million/cu\.?mm|mEq/Litre|mmol/L|pg/mL|ng/mL|H\.P\.F\.|/HPF)\b', re.IGNORECASE)

# Range: Handles 'X - Y', '< X', '> Y', 'X-Y', 'Up to Y', 'Negative'. Added case-insensitivity.
RANGE_RE = re.compile(r'(\b\d+\.?\d*\s*-\s*\d+\.?\d*\b|<\s*\d+\.?\d*|>\s*\d+\.?\d*|\b\d+-\d+\b|[Uu]p [Tt]o \d+\.?\d*|\b[Nn]egative\b|\b[Nn]ormal\b)', re.IGNORECASE)

# Possible Header/Footer Keywords to Ignore (simple list, can be expanded)
IGNORE_KEYWORDS = ["test", "investigation", "result", "unit", "range", "reference", "interval", "method", "specimen", "serum", "plasma", "blood", "urine", "report", "page", "date", "patient", "doctor", "hospital", "pathology", "signature", "-------", "======", "*******", "end of report", "authorized", "technologist"]

def is_likely_header_or_footer(line: str) -> bool:
    """Checks if a line is likely ignorable header/footer content."""
    line_lower = line.strip().lower()
    if not line_lower: # Skip empty lines
        return True
    # Check if line predominantly contains ignore keywords or looks like a separator
    if any(keyword in line_lower for keyword in IGNORE_KEYWORDS) and len(line_lower.split()) < 5 :
         # Basic check: if it contains a keyword and is short, likely header
         # More sophisticated checks possible (e.g., if ONLY keywords are present)
         # Or check if it matches common headers like "Test Name Result Unit Range" exactly
         if re.fullmatch(r'test(\s+name)?\s+result\s+unit\s+(bio\.\s+)?ref.*range.*', line_lower):
             return True
         if re.fullmatch(r'investigation\s+result\s+unit\s+range.*', line_lower):
             return True
         # Simple check for separators
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
    potential_test_name = None # Keep track of test names that might span lines

    for i, line in enumerate(lines):
        line = line.strip()
        # print(f"Processing line {i}: '{line}'") # Debugging line

        if is_likely_header_or_footer(line):
            # print(f"  Skipping line (header/footer/empty): '{line}'")
            potential_test_name = None # Reset multi-line name potential
            continue

        # --- Attempt to find Value, Unit, and Range on the current line ---
        value_match = VALUE_RE.search(line)
        unit_match = UNIT_RE.search(line)
        range_match = RANGE_RE.search(line)

        # --- Heuristic: A line is likely a result row if it contains a value ---
        if value_match:
            value_str = value_match.group(1).strip()
            value_start_index = value_match.start()

            # Initialize components for this potential result
            current_test_name = "Unknown"
            unit_str = None
            range_str = None

            # Try to find Unit
            if unit_match:
                unit_str = unit_match.group(1).strip()
                # Simple check: unit often appears relatively close *after* the value in tables
                # This is a weak heuristic, layout analysis would be better.
                # if unit_match.start() < value_start_index + 20: # Arbitrary proximity check
                #    pass # Keep the unit
                # else:
                #    unit_str = None # Discard if too far? Risky.

            # Try to find Range
            if range_match:
                 # Simple check: range often appears towards the end, *after* the value/unit
                 if range_match.start() > value_start_index:
                     range_str = range_match.group(1).strip()


            # --- Try to identify Test Name ---
            # Assumption 1: Name is the text before the value
            possible_name_part = line[:value_start_index].strip()

            # Clean up potential name part (remove trailing non-alphanumeric except brackets/hyphens)
            cleaned_name = re.sub(r'[^\w\s\(\)-]+$', '', possible_name_part).strip()

            if cleaned_name and len(cleaned_name) > 2: # Avoid very short/garbage names
                 # Check if the *previous* line might have been the name (if this line starts numeric/symbolic)
                 if not cleaned_name and i > 0 and not is_likely_header_or_footer(lines[i-1]) and not VALUE_RE.search(lines[i-1]):
                     potential_previous_name = lines[i-1].strip()
                     # Check if previous line looks like a plausible name (e.g., mostly text)
                     if re.match(r'^[A-Za-z\s\(\)\-]+', potential_previous_name):
                           current_test_name = potential_previous_name
                     else:
                           current_test_name = "Unknown - Check Previous" # Flag for review
                 else:
                     current_test_name = cleaned_name
                     potential_test_name = None # Reset potential multi-line name

                 # Basic check to filter out lines that might just be numeric data without a clear name
                 if not re.search(r'[a-zA-Z]{3,}', current_test_name): # Needs at least 3 letters
                     # print(f"  Discarding row - Name part '{current_test_name}' seems invalid.")
                     continue # Skip this row

            elif potential_test_name:
                 # Use the name identified from the previous line if current line lacks a name part
                 current_test_name = potential_test_name
                 potential_test_name = None # Reset
            else:
                 # If no name found on this line or previous, skip (likely noise)
                 # print(f"  Discarding row - Could not identify a plausible Test Name for value '{value_str}'")
                 continue


            # --- Store the extracted data ---
            extracted = {
                "test_name": current_test_name,
                "test_value": value_str,
                "test_unit": unit_str,
                "bio_reference_range": range_str
            }
            results.append(extracted)
            # print(f"  Found potential result: {extracted}") # Debugging

        else:
            # If no value found, this line *might* be a test name that continues on the next line
            # Heuristic: Check if it looks like text and doesn't contain clear numeric results/ranges itself
             line_trimmed = line.strip()
             if len(line_trimmed) > 3 and re.match(r'^[A-Za-z\s\(\)\-\#]+', line_trimmed) and not range_match and not unit_match:
                  potential_test_name = line_trimmed
                  # print(f"  Potential multi-line test name found: '{potential_test_name}'")
             else:
                  potential_test_name = None # Reset if it doesn't look like a name

    print(f"Parsing finished. Found {len(results)} potential test entries.")
    return results


# --- Step 5: Range Calculation Logic --- (Keep placeholder for now, update later)
def calculate_out_of_range(value_str: Optional[str], range_str: Optional[str]) -> Optional[bool]:
    """
    Compares a test value string to a reference range string.
    Returns True (out of range), False (in range), None (cannot compare).
    """
    if value_str is None or range_str is None:
        # print(f"Cannot calculate range: Value='{value_str}', Range='{range_str}' (Missing)")
        return None

    # --- 1. Handle Textual Values/Ranges First ---
    value_str_lower = value_str.strip().lower()
    range_str_lower = range_str.strip().lower()

    if value_str_lower in ["positive", "detected", "reactive"]:
        if range_str_lower == "negative":
            return True # Positive value vs Negative range is out of range
        else:
            return None # Cannot easily compare Positive to numeric ranges or other text

    if value_str_lower == "negative":
        if range_str_lower == "negative":
            return False # Negative value vs Negative range is within range
        else:
            return None # Cannot compare Negative to numeric ranges easily

    # If range is textual but value isn't, comparison is unclear
    if range_str_lower in ["negative", "normal"] and not value_str_lower in ["negative", "normal"]:
         return None # Numeric value vs text range - needs specific rules

    # --- 2. Try Numeric Comparison ---
    try:
        # Clean value string (remove common symbols like '<', '>') before converting
        cleaned_value_str = re.sub(r'[<>]', '', value_str.strip())
        value_num = float(cleaned_value_str)
    except ValueError:
        # print(f"Cannot calculate range: Value '{value_str}' is not numeric after cleaning.")
        return None # Value is not purely numeric (and not handled above)

    try:
        # Case 1: Range like "X - Y" or "X-Y"
        match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', range_str)
        if match:
            lower = float(match.group(1))
            upper = float(match.group(2))
            result = not (lower <= value_num <= upper)
            # print(f"  Range Compare ({lower}-{upper}): {value_num} -> OutOfRange={result}")
            return result

        # Case 2: Range like "< X" or "Less than X"
        match = re.search(r'<\s*(\d+\.?\d*)', range_str)
        if match:
            upper = float(match.group(1))
            result = value_num >= upper # Out of range if >= upper bound
            # print(f"  Range Compare (<{upper}): {value_num} -> OutOfRange={result}")
            return result

        # Case 3: Range like "> X" or "Greater than X"
        match = re.search(r'>\s*(\d+\.?\d*)', range_str)
        if match:
            lower = float(match.group(1))
            result = value_num <= lower # Out of range if <= lower bound
            # print(f"  Range Compare (>{lower}): {value_num} -> OutOfRange={result}")
            return result

        # Case 4: Range like "Up to X"
        match = re.search(r'[Uu]p [Tt]o (\d+\.?\d*)', range_str, re.IGNORECASE)
        if match:
            upper = float(match.group(1))
            result = value_num > upper # Out of range if > upper bound
            # print(f"  Range Compare (UpTo {upper}): {value_num} -> OutOfRange={result}")
            return result

        # Case 5: Maybe a single number range (e.g., if normal is just '100') - Less common
        # match = re.fullmatch(r'(\d+\.?\d*)', range_str.strip())
        # if match:
        #    # How to interpret? Assume it's an upper limit? Needs clarification.
        #    # upper = float(match.group(1))
        #    # return value_num > upper
        #    pass # Skip for now

    except ValueError:
        # print(f"Cannot calculate range: Error converting range '{range_str}' parts to float.")
        return None # Error during range number conversion
    except Exception as e:
        print(f"Unexpected error in calculate_out_of_range for value='{value_str}', range='{range_str}': {e}")
        return None


    # print(f"Cannot calculate range: Range format '{range_str}' not recognized for value '{value_str}'.")
    return None # Range format not recognized


# --- Main Orchestrator Function --- (Now uses the real parsing and calculation)
def process_lab_report(image_bytes: bytes) -> List[LabTest]:
    """
    Main orchestrator function for processing the lab report image.
    """
    print("Starting lab report processing...")
    final_results = []
    try:
        preprocessed_img = preprocess_image(image_bytes)
        ocr_text = perform_ocr(preprocessed_img)
        parsed_items = parse_text_data(ocr_text)

        for item in parsed_items:
            # Ensure all keys exist, defaulting to None if missing from parsing
            value_str = item.get("test_value")
            range_str = item.get("bio_reference_range")

            out_of_range = calculate_out_of_range(value_str, range_str)

            lab_test = LabTest(
                test_name=item.get("test_name", "Unknown"), # Default if missing
                test_value=value_str,
                bio_reference_range=range_str,
                test_unit=item.get("test_unit"),
                lab_test_out_of_range=out_of_range
            )
            final_results.append(lab_test)

        print(f"Processing complete. Generated {len(final_results)} LabTest objects.")
        return final_results

    except Exception as e:
        print(f"Error in process_lab_report pipeline: {e}")
        print(traceback.format_exc())
        # Return empty list on failure to maintain API contract
        return []