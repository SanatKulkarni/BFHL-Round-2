# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List
import os
import traceback # For detailed error logging

# Import Pydantic models and processing functions
from models import ApiResponse, LabTest
from processing import process_lab_report # Import the main processing function

app = FastAPI(title="Bajaj Lab Report OCR API (Pillow)")

@app.post("/get-lab-tests",
          response_model=ApiResponse,
          summary="Extract Lab Tests from Image",
          description="Upload a lab report image (PNG, JPG, JPEG) to extract test names, values, units, and reference ranges.")
async def get_lab_tests_endpoint(file: UploadFile = File(..., description="Lab report image file.")):
    """
    Endpoint to process a lab report image and extract structured data.
    """
    if not file.content_type in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload PNG, JPG, or JPEG images.")

    try:
        # Read image bytes directly into memory
        image_bytes = await file.read()

        # ---- Call the core processing logic ----
        print(f"Processing file: {file.filename} ({file.content_type})")
        extracted_data: List[LabTest] = process_lab_report(image_bytes)
        print(f"Extracted {len(extracted_data)} potential tests.")
        # ---- End processing logic call ----

        return ApiResponse(is_success=True, data=extracted_data)

    except Exception as e:
        # Log the detailed error for debugging
        print(f"Error processing file: {file.filename}")
        print(traceback.format_exc()) # Print full traceback

        # Return a structured failure response
        return ApiResponse(is_success=False, data=[])

    finally:
        # Ensure the uploaded file stream is closed
        await file.close()
        print(f"Finished processing request for: {file.filename}")


@app.get("/", summary="API Root", description="Basic check to see if the API is running.")
def read_root():
    """
    Root endpoint providing a simple status message.
    """
    return {"message": "Bajaj Lab Report OCR API is running. Use the /docs endpoint for API documentation."}

# Command to run (from the bajaj_lab_report_ocr directory):
# uvicorn main:app --reload --host localhost --port 8000