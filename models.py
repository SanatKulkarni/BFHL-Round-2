from pydantic import BaseModel, Field
from typing import List, Optional

class LabTest(BaseModel):
    test_name: Optional[str] = None 
    test_value: Optional[str] = None
    bio_reference_range: Optional[str] = None
    test_unit: Optional[str] = None
    lab_test_out_of_range: Optional[bool] = None

class ApiResponse(BaseModel):
    is_success: bool
    data: List[LabTest] = Field(default_factory=list) # Default to empty list