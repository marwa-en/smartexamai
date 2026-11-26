"""
Validation logic for student submissions.
"""

class SubmissionValidator:
    """
    Validates the student submission before processing.
    """
    
    # Languages currently supported by the Docker sandbox runners
    SUPPORTED_LANGUAGES = {"python", "java", "c", "cpp", "php", "javascript", "typescript"}
    
    # Maximum allowed code size in characters (approx 100KB)
    MAX_CODE_LENGTH = 100_000

    def validate(self, code: str, language: str) -> tuple[bool, str]:
        """
        Validates the code and language.
        
        Args:
            code: The cleaned code.
            language: The detected/provided language.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not code or not code.strip():
            return False, "Submission is empty."
            
        if language not in self.SUPPORTED_LANGUAGES:
            return False, f"Unsupported or undetected language: '{language}'."
            
        if len(code) > self.MAX_CODE_LENGTH:
            return False, "Submission exceeds maximum allowed size."
            
        return True, ""