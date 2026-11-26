"""
Data models for incoming student submissions.
"""
from pydantic import BaseModel, Field
from typing import Optional


class StudentSubmission(BaseModel):
    """
    Represents the raw extracted student code received from the frontend/system.
    Strictly matches the expected JSON structure.
    
    Attributes:
        code: The raw source code extracted from the student's submission.
        language: The detected or provided programming language (e.g., 'php', 'python').
        file_path: The original file path or name, if available.
    """
    code: str = Field(..., description="The raw source code extracted from the student's submission.")
    language: Optional[str] = Field(None, description="The detected or provided programming language.")
    file_path: Optional[str] = Field(None, description="The original file path or name, if available.")

    class Config:
        # Allow population by field name or alias if needed in the future
        populate_by_name = True 