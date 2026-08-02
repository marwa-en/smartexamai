import json
import os
from typing import Dict, List
from dataclasses import dataclass, field

@dataclass
class QuestionResult:
    """Résultat de correction pour une question unique."""
    question_num: int
    detected_answers: List[str]
    correct_answers: List[str]
    status: str
    points: float

@dataclass
class ExamReport:
    """Rapport global de l'examen corrigé."""
    total_questions: int
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    raw_score: float
    max_possible_score: float
    scoring_system: str
    results: List[QuestionResult] = field(default_factory=list)

def load_json(file_path: str) -> Dict:
    """Charge un fichier JSON depuis le disque."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_structure(data: Dict, file_label: str) -> None:
    """Valide la structure du JSON (clés numériques, valeurs A/B/C/D)."""
    if not isinstance(data, dict):
        raise ValueError(f"[{file_label}] La racine du JSON doit être un objet/dictionnaire.")

    valid_choices = {'A', 'B', 'C', 'D'}

    for key, value in data.items():
        if not isinstance(key, str) or not key.isdigit():
            raise ValueError(f"[{file_label}] Clé invalide : '{key}'. Doit être numérique.")
        if not isinstance(value, list):
            raise ValueError(f"[{file_label}] Question '{key}' : doit contenir une liste.")
        for answer in value:
            if answer not in valid_choices:
                raise ValueError(f"[{file_label}] Réponse invalide '{answer}' à la question '{key}'.")

def compare_answers(detected: List[str], correct: List[str]) -> str:
    """Compare les réponses détectées au corrigé."""
    if len(detected) == 0:
        return "unanswered"
    if set(detected) == set(correct):
        return "correct"
    return "incorrect"

def correct_exam(detected_file: str, correction_file: str, scoring_system: str = "normal") -> ExamReport:
    """Corrige l'examen et calcule le score selon le système choisi."""
    detected_data = load_json(detected_file)
    correction_data = load_json(correction_file)

    validate_structure(detected_data, "réponses détectées")
    validate_structure(correction_data, "corrigé")

    detected_keys = set(detected_data.keys())
    correction_keys = set(correction_data.keys())

    if detected_keys != correction_keys:
        raise ValueError("Incohérence : les deux fichiers ne contiennent pas les mêmes numéros de questions.")

    if scoring_system == "canadian":
        pts_correct, pts_incorrect, pts_unanswered = 1.0, -1.0, 0.0
    else:
        pts_correct, pts_incorrect, pts_unanswered = 1.0, 0.0, 0.0

    results: List[QuestionResult] = []
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    sorted_keys = sorted(detected_data.keys(), key=lambda k: int(k))

    for q_key in sorted_keys:
        question_num = int(q_key)
        detected = detected_data[q_key]
        correct = correction_data[q_key]

        status = compare_answers(detected, correct)

        if status == "correct":
            points = pts_correct
            correct_count += 1
        elif status == "incorrect":
            points = pts_incorrect
            incorrect_count += 1
        else:
            points = pts_unanswered
            unanswered_count += 1

        results.append(QuestionResult(
            question_num=question_num,
            detected_answers=detected,
            correct_answers=correct,
            status=status,
            points=points
        ))

    total_questions = len(results)
    raw_score = sum(r.points for r in results)
    max_possible_score = total_questions * pts_correct

    return ExamReport(
        total_questions=total_questions,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered_count=unanswered_count,
        raw_score=raw_score,
        max_possible_score=max_possible_score,
        scoring_system=scoring_system,
        results=results
    )

def save_report_to_json(report: ExamReport, output_path: str) -> None:
    """Sauvegarde le rapport de correction dans un fichier JSON."""
    report_dict = {
        "scoring_system": report.scoring_system,
        "total_questions": report.total_questions,
        "correct_count": report.correct_count,
        "incorrect_count": report.incorrect_count,
        "unanswered_count": report.unanswered_count,
        "raw_score": report.raw_score,
        "max_possible_score": report.max_possible_score,
        "results": [
            {
                "question_num": r.question_num,
                "detected_answers": r.detected_answers,
                "correct_answers": r.correct_answers,
                "status": r.status,
                "points": r.points
            } for r in report.results
        ]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=4)

def main() -> None:
    """
    Fonction principale.
    - Demande au professeur les chemins des fichiers (corrigé + réponses étudiant).
    - Demande le système de notation (Normal ou Canadien).
    - Crée automatiquement le fichier JSON de résultat dans le dossier courant.
    """
    # 1. Récupération des chemins via input
    correction_file = input("Entrez le chemin du fichier corrigé (ex: corr.json) : ").strip()
    student_file = input("Entrez le chemin du fichier de réponses de l'étudiant (ex: qcm.json) : ").strip()

    # 2. Choix du système de notation
    system_input = input("Choisissez le système de notation (1: Normal, 2: Canadien) : ").strip()
    scoring_system = "canadian" if system_input == '2' else "normal"

    # 3. Exécution de la correction
    report = correct_exam(student_file, correction_file, scoring_system)

    # 4. Génération automatique du nom du fichier de sortie dans le dossier courant
    # On utilise le nom du fichier étudiant pour nommer le résultat
    student_basename = os.path.splitext(os.path.basename(student_file))[0]
    output_filename = f"resultat_{student_basename}.json"
    output_path = os.path.join(os.getcwd(), output_filename)

    # 5. Sauvegarde du résultat
    save_report_to_json(report, output_path)

if __name__ == "__main__":
    main()