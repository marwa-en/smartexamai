"""
Code cleaning and normalization utilities.
"""
import re


class CodeCleaner:
    """
    Cleans and normalizes raw student code to ensure consistent execution.
    Removes markdown formatting, normalizes line endings, and trims whitespace.
    """
    
    # Regex to match markdown code blocks like ```python ... ```
    # Uses DOTALL to match across multiple lines.
    MARKDOWN_BLOCK_PATTERN = re.compile(r"```[a-zA-Z0-9]*\n(.*?)\n```", re.DOTALL)
    
    def clean(self, code: str) -> str:
        """
        Cleans the raw code string.
        
        Args:
            code: The raw code string.
            
        Returns:
            The cleaned and normalized code string.
        """
        if not code:
            return ""
            
        # 1. Remove markdown code block wrappers if present (common when copying from LLMs/Docs)
        match = self.MARKDOWN_BLOCK_PATTERN.search(code)
        if match:
            code = match.group(1)
            
        # 2. Normalize line endings to LF (\n) for consistent cross-platform execution
        code = code.replace('\r\n', '\n').replace('\r', '\n')
        
        # 3. Remove trailing whitespace on each line, but preserve leading indentation
        lines = code.split('\n')
        lines = [line.rstrip() for line in lines]
        code = '\n'.join(lines)
        
        # 4. Strip leading and trailing whitespace/newlines from the entire block
        code = code.strip()
        
        return code