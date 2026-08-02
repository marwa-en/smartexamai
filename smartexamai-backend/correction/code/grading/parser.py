"""Parser for SmartExamAI Grading Module."""
from models.grading_result import GradingResult

def parse_grading_response(response: dict) -> GradingResult:
    try:
        result = GradingResult(**response)
        if result.score > result.max_score:
            raise ValueError(f"Le score ({result.score}) ne peut pas dépasser le score max ({result.max_score}).")
        return result
    except Exception as e:
        raise ValueError(f"Erreur de validation de la réponse de notation: {e}")