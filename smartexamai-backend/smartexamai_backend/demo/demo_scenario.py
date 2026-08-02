"""
SmartExamAI — Scénario de démonstration bout-en-bout.

Ce script illustre l'usage du backend indépendamment de toute interface :
création des entités par l'admin, définition des ressources par le
professeur, dépôt d'une copie, puis tentative de lancement de la
correction automatique (appel réel à ai_pipeline.orchestrator).

Remarque : l'appel final au pipeline échouera dans cet environnement de
démonstration si les sous-modules réels du pipeline (segmentation.py,
preprocess.py, etc.) ne sont pas présents sous `pipeline_project_root`
— ce qui est normal, puisque ces modules ne font pas partie de ce
livrable et sont fournis séparément. Le script démontre que l'erreur
est alors proprement capturée et journalisée (CorrectionPipelineError),
sans jamais faire planter le backend.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from db.init_db import init_db
from db.session import session_scope
from core.exceptions import CorrectionPipelineError, ExamResourcesIncompleteError
from modelss.enums import RoleUtilisateur

from service.admin.user_management_service import UserManagementService
from service.admin.classe_service import ClasseService
from service.admin.matiere_service import MatiereService
from service.admin.examen_service import ExamenService
from service.admin.copie_service import CopieService
from service.admin.correction_service import CorrectionService
from service.professeur.professeur_service import ProfesseurService
from service.etudiant.etudiant_service import EtudiantService


def _make_dummy_files(tmp_dir: Path) -> dict[str, Path]:
    """Crée de faux fichiers pédagogiques et une fausse image scannée,
    uniquement pour illustrer le flux (contenu non représentatif)."""
    consignes = tmp_dir / "consignes.txt"
    consignes.write_text("Répondez à toutes les questions.", encoding="utf-8")

    corrige = tmp_dir / "corrige.txt"
    corrige.write_text("Corrigé de référence.", encoding="utf-8")

    unit_tests = tmp_dir / "tests.json"
    unit_tests.write_text('[{"input": "2 3", "expected": "5"}]', encoding="utf-8")

    code_consignes = tmp_dir / "consignes_code.txt"
    code_consignes.write_text("Écrire une fonction addition(a, b).", encoding="utf-8")

    image = tmp_dir / "page_01.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")  # en-tête PNG minimal, contenu factice

    return {
        "consignes": consignes,
        "corrige": corrige,
        "unit_tests": unit_tests,
        "code_consignes": code_consignes,
        "image": image,
    }


def main() -> None:
    print("=" * 70)
    print("SmartExamAI — Démonstration du backend")
    print("=" * 70)

    init_db()

    with session_scope() as db:
        # ---------------- ADMIN : création des comptes ----------------
        users = UserManagementService(db)
        admin = users.create_user(
            username="admin_demo", email="admin_demo@smartexamai.local",
            password="Admin1234!", role=RoleUtilisateur.ADMIN,
            nom="Alaoui", prenom="Sara",
        )
        professeur = users.create_user(
            username="prof_demo", email="prof_demo@smartexamai.local",
            password="Prof1234!", role=RoleUtilisateur.PROFESSEUR,
            nom="Benali", prenom="Karim",
        )

        # ---------------- ADMIN : classe et matière ----------------
        classes = ClasseService(db)
        classe = classes.create_classe(nom="L3-INFO-A", niveau="Licence 3", annee_scolaire="2025-2026")

        matieres = MatiereService(db)
        matiere = MatiereService(db).create_matiere(nom="Algorithmique", code="ALG301")

        etudiant = users.create_user(
            username="etu_demo", email="etu_demo@smartexamai.local",
            password="Etu1234!", role=RoleUtilisateur.ETUDIANT,
            nom="Idrissi", prenom="Yasmine", cne="R123456789", classe_id=classe.id,
        )

        # ---------------- ADMIN : création de l'examen ----------------
        examens = ExamenService(db)
        examen = examens.create_examen(
            titre="Examen final Algorithmique",
            matiere_id=matiere.id,
            classe_id=classe.id,
            professeur_id=professeur.id,
            created_by_admin_id=admin.id,
        )
        print(f"✅ Examen créé : {examen.titre} (id={examen.id})")

        # ---------------- PROFESSEUR : définition des ressources ----------------
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fichiers = _make_dummy_files(tmp_path)

            profs = ProfesseurService(db)
            ressources = profs.definir_ressources(
                examen_id=examen.id,
                professeur_id=professeur.id,
                consignes_file=fichiers["consignes"],
                corrige_file=fichiers["corrige"],
                unit_tests_file=fichiers["unit_tests"],
                code_consignes_file=fichiers["code_consignes"],
                sections=["redaction", "code"],
                scoring_system="normal",
                code_language="python",
            )
            print(f"✅ Ressources définies (complètes : {ressources.is_complete()})")

            # ---------------- ADMIN : dépôt de la copie scannée ----------------
            copies = CopieService(db)
            copie = copies.deposer_copie(
                examen_id=examen.id,
                image_paths=[fichiers["image"]],
                etudiant_id=etudiant.id,
                deposee_par_admin_id=admin.id,
            )
            print(f"✅ Copie déposée (id={copie.id}, statut={copie.statut})")

            # ---------------- ADMIN : lancement de la correction ----------------
            correction = CorrectionService(db)
            try:
                resultat = correction.lancer_correction(copie.id)
                print(f"✅ Correction terminée — statut : {resultat.statut}")
                print(f"   Note totale : {resultat.total_score}/{resultat.max_score}")
            except (CorrectionPipelineError, ExamResourcesIncompleteError) as exc:
                print(f"⚠️  Correction interrompue (attendu dans cet environnement de démo) : {exc}")

        # ---------------- PROFESSEUR : consultation des statistiques ----------------
        stats = ProfesseurService(db).statistiques_examen(examen.id, professeur.id)
        print(f"📊 Statistiques examen : {stats}")

        # ---------------- ÉTUDIANT : consultation des notes + relevé ----------------
        notes = EtudiantService(db).consulter_notes(etudiant.id)
        print(f"📄 Notes de l'étudiant : {notes}")

        releve_path = EtudiantService(db).telecharger_releve(etudiant.id)
        print(f"📄 Relevé de notes généré : {releve_path}")

    print("=" * 70)
    print("Démonstration terminée.")


if __name__ == "__main__":
    main()
