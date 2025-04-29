
# Bajaj Finserv Health - Lab Report OCR API (Pillow Version)

## Overview

This project implements a FastAPI service designed to process lab report images and extract structured information, specifically targeting lab test names, their measured values, units, and biological reference ranges.

The core objective is to achieve this using Optical Character Recognition (OCR) and rule-based parsing **without relying on any Large Language Models (LLMs)** like GPT, Gemini, Claude, etc., as per the specific constraints of the Bajaj Finserv Health Data Science Q2 problem statement.

**Note:** This version uses the Pillow (PIL) library for image processing instead of OpenCV.

## Problem Statement (Brief)

Develop a scalable and accurate solution (deployed as a FastAPI service) to process lab report images, extracting all lab test names, their corresponding values, and reference ranges. Calculate whether the test value falls outside the reference range.

## Features

*   Accepts lab report images (PNG, JPG, JPEG) via a POST request.
*   Performs basic image preprocessing using **Pillow (PIL)** (Grayscale).
*   Utilizes the Tesseract OCR engine (via `pytesseract`) to extract text from the image.
*   Applies regular expressions and line-based heuristics to parse the OCR text and identify potential test entries.
*   Attempts to extract:
    *   `test_name`
    *   `test_value` (as string)
    *   `test_unit` (as string)
    *   `bio_reference_range` (as string)
*   Calculates `lab_test_out_of_range` (boolean) by comparing the extracted value and range strings numerically or textually where possible.
*   Returns the extracted data in a structured JSON format.

## Technology Stack

*   **Python 3.x**
*   **FastAPI:** Web framework for building the API.
*   **Uvicorn:** ASGI server to run the FastAPI application.
*   **Pillow (PIL):** For image loading and preprocessing.
*   **Pytesseract:** Python wrapper for the Tesseract OCR engine.
*   **Tesseract OCR Engine:** (System Dependency) The core OCR engine.

## Prerequisites

**CRITICAL:** You **must** have the Tesseract OCR engine installed on your system and accessible in your PATH. `pytesseract` is only a Python wrapper.

*   **Ubuntu/Debian:**
    ```bash
    sudo apt update
    sudo apt install -y tesseract-ocr libtesseract-dev
    ```
*   **macOS (using Homebrew):**
    ```bash
    brew update
    brew install tesseract
    ```
*   **Windows:** Download the installer from the [Tesseract UB-Mannheim repository](https://github.com/UB-Mannheim/tesseract/wiki). **Ensure you check the option to add Tesseract to your system PATH during installation.**

Verify installation by opening a *new* terminal and running `tesseract --version`.

## Setup

1.  **Clone or Download:** Get the project code onto your local machine.
2.  **Navigate to Project Directory:**
    ```bash
    cd path/to/bajaj_lab_report_ocr
    ```
3.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows (cmd):
    # venv\Scripts\activate.bat
    # On Windows (PowerShell):
    # venv\Scripts\Activate.ps1
    ```
4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure `requirements.txt` includes `Pillow` and not `opencv-python-headless`. If not finalized, run `pip install fastapi uvicorn[standard] python-multipart Pillow pytesseract`)*

## Running the Application

1.  Make sure your virtual environment is activated.
2.  Run the Uvicorn server from the project's root directory:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    *   `--reload`: Enables auto-reloading when code changes (useful for development).
    *   `--host 0.0.0.0`: Makes the server accessible from other devices on your network (use `127.0.0.1` for local access only).
    *   `--port 8000`: Specifies the port to run on.

3.  Access the API documentation (Swagger UI) in your browser at: `http://localhost:8000/docs`

## API Usage

### Endpoint

*   **URL:** `/get-lab-tests`
*   **Method:** `POST`
*   **Description:** Upload a lab report image to extract test data.

### Request

*   **Body:** `multipart/form-data`
*   **Field:** `file`: The image file (must be PNG, JPG, or JPEG format).

### Success Response (`200 OK`)

The API returns a JSON object with the following structure:

```json
{
  "is_success": true,
  "data": [
    {
      "test_name": "HEMOGLOBIN",
      "test_value": "14.5",
      "bio_reference_range": "13.5-17.5",
      "test_unit": "g/dL",
      "lab_test_out_of_range": false
    },
    {
      "test_name": "PLATELET COUNT",
      "test_value": "150",
      "bio_reference_range": "150-450",
      "test_unit": "thousand/cu.mm",
      "lab_test_out_of_range": false
    },
    {
       "test_name": "C-REACTIVE PROTEIN, CRP",
       "test_value": "16.17",
       "bio_reference_range": "<0.5",
       "test_unit": "mg/dl",
       "lab_test_out_of_range": true
    }
    
  ]
}
```

Error Response

If an internal error occurs during processing, or the file type is invalid, the API aims to return:

{
  "is_success": false,
  "data": []
}
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Json
IGNORE_WHEN_COPYING_END

(Note: Invalid file type currently raises a 400 HTTPException, which might have a different default FastAPI error format unless customized further.)

Output Format Details

Each object within the data list represents one extracted lab test and contains:

test_name (str | null): The identified name of the lab test.

test_value (str | null): The measured value, kept as a string.

bio_reference_range (str | null): The reference range, kept as a string.

test_unit (str | null): The unit associated with the value.

lab_test_out_of_range (bool | null): true if the value falls outside the range, false if within, null if comparison couldn't be performed.

Core Logic Overview

The extraction process follows these main steps:

Image Input: Receives image bytes via the API.

Preprocessing (Pillow): Loads the image using Pillow and converts it to grayscale ('L' mode) to aid OCR.

OCR (Tesseract): Uses pytesseract to extract raw text from the preprocessed Pillow image, configured to assume blocks of text (suitable for some tables).

Parsing (Regex & Heuristics): Iterates through the OCR text lines, applying regular expressions to identify potential values, units, and ranges. It uses heuristics (like relative positions on a line) to associate these with a potential test name found on the same or previous line. It filters out lines presumed to be headers/footers. No LLMs are used.

Range Calculation: Compares the extracted test_value string and bio_reference_range string. It handles common numeric formats (X-Y, <X, >X) and basic textual comparisons ("Positive" vs "Negative").

JSON Output: Structures the extracted and calculated data into the specified JSON format using Pydantic models.

Known Limitations

Layout Sensitivity: The parsing logic heavily relies on text appearing in roughly expected columnar formats (Name, Value, Unit, Range on the same line). It struggles significantly with non-tabular layouts, merged cells, or complex formatting.

OCR Accuracy: The quality of the extraction is highly dependent on the input image quality and the accuracy of Tesseract OCR. Poor scans, noise, unusual fonts, or skew can lead to incorrect text and failed parsing.

Handwritten Text: Cannot process handwritten notes or values.

Heuristic Parsing: The rules for associating names, values, units, and ranges are based on assumptions and may fail or misinterpret data in many real-world reports.

Range Format Support: Only supports a limited set of common numeric and basic textual range formats. More complex descriptions or units within ranges may not be parsed correctly.

Multi-Page Reports: Designed to process a single image at a time. Does not handle context across multiple pages.

How to Test

Use the Swagger UI (http://localhost:8000/docs) or tools like curl or Postman to send POST requests with image files to the /get-lab-tests endpoint. Analyze the returned JSON and compare it against the original report image. Check terminal logs for debugging information.
