"""
SmartExamAI — Interface CLI interactive.

Permet à chaque rôle (admin, professeur, étudiant) de se connecter
et d'effectuer ses actions via les services existants.
"""
from __future__ import annotations

import getpass
import os
import sys
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Optional

from sqlalchemy.exc import IntegrityError

from configss.settings import settings
from core.exceptions import (
    CorrectionPipelineError,
    DuplicateEntityError,
    ExamResourcesIncompleteError,
    PermissionDeniedError,
    SmartExamError,
    WrongPasswordError,
)
from core.security import hash_password, verify_password
from db.session import session_scope
from modelss.enums import RoleUtilisateur
from modelss.user import User
from service.admin.classe_service import ClasseService
from service.admin.copie_service import CopieService
from service.admin.correction_service import CorrectionService
from service.admin.examen_service import ExamenService
from service.admin.matiere_service import MatiereService
from service.admin.user_management_service import UserManagementService
from service.etudiant.etudiant_service import EtudiantService
from service.professeur.professeur_service import ProfesseurService


# ---------------------------------------------------------------------------
# Utilitaires d'affichage
# ---------------------------------------------------------------------------

def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str) -> None:
    width = 70
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)


def print_menu(options: Dict[str, str]) -> None:
    print()
    for key, label in options.items():
        print(f"  [{key}] {label}")
    print()


def ask(prompt: str, required: bool = True) -> str:
    while True:
        value = input(f"➡️  {prompt} : ").strip()
        if value or not required:
            return value
        print("❌ Ce champ est obligatoire.")


def ask_int(prompt: str, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    while True:
        raw = ask(prompt)
        try:
            value = int(raw)
            if min_val is not None and value < min_val:
                print(f"❌ Minimum : {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"❌ Maximum : {max_val}")
                continue
            return value
        except ValueError:
            print("❌ Veuillez entrer un nombre entier.")


def ask_float(prompt: str) -> float:
    while True:
        raw = ask(prompt)
        try:
            return float(raw)
        except ValueError:
            print("❌ Veuillez entrer un nombre.")


def ask_choice(prompt: str, choices: List[str]) -> str:
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        print(f"  {i}. {choice}")
    while True:
        raw = ask("Votre choix")
        try:
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
        except ValueError:
            pass
        print(f"❌ Choisissez entre 1 et {len(choices)}.")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "O/n" if default else "o/N"
    while True:
        raw = input(f"➡️  {prompt} ({suffix}) : ").strip().lower()
        if not raw:
            return default
        if raw in {"o", "oui", "y", "yes"}:
            return True
        if raw in {"n", "non", "no"}:
            return False
        print("❌ Répondez par o (oui) ou n (non).")


def ask_date(prompt: str) -> Optional[date]:
    raw = ask(prompt, required=False)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        print("❌ Format invalide. Utilisez YYYY-MM-DD.")
        return ask_date(prompt)


def pause() -> None:
    input("\n⏸️  Appuyez sur Entrée pour continuer...")


def ask_file(prompt: str, must_exist: bool = True) -> Optional[str]:
    """Demande un chemin de fichier. Retourne None si vide."""
    path_str = ask(prompt, required=False)
    if not path_str:
        return None
    p = Path(path_str)
    if must_exist and not p.is_file():
        print(f"❌ Fichier introuvable : {p}")
        return None
    return str(p.resolve())


def ask_dir(prompt: str, must_exist: bool = True) -> Optional[str]:
    """Demande un chemin de dossier. Retourne None si vide."""
    path_str = ask(prompt, required=False)
    if not path_str:
        return None
    p = Path(path_str)
    if must_exist and not p.is_dir():
        print(f"❌ Dossier introuvable : {p}")
        return None
    return str(p.resolve())


def list_image_files(directory: str) -> List[str]:
    """Liste tous les fichiers images (png/jpg/jpeg) d'un dossier."""
    p = Path(directory)
    extensions = {".png", ".jpg", ".jpeg"}
    return sorted(str(f) for f in p.iterdir() if f.is_file() and f.suffix.lower() in extensions)


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

def authenticate() -> Optional[User]:
    """Authentifie un utilisateur et retourne l'objet User ou None."""
    print_header("🔐 CONNEXION")
    username = ask("Nom d'utilisateur")
    password = getpass.getpass("➡️  Mot de passe : ")

    with session_scope() as db:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print("\n❌ Utilisateur inconnu.")
            return None
        if not user.is_active:
            print("\n❌ Compte désactivé.")
            return None
        if not verify_password(password, user.password_hash):
            print("\n❌ Mot de passe incorrect.")
            return None

        # Détache l'objet de la session pour pouvoir l'utiliser après fermeture du bloc
        db.expunge(user)
        return user


# ---------------------------------------------------------------------------
# Menu Administrateur
# ---------------------------------------------------------------------------

class AdminMenu:
    """Menu de l'administrateur."""

    def __init__(self, user: User):
        self.user = user

    def run(self) -> None:
        actions: Dict[str, Callable[[], None]] = {
            "1": self._create_user,
            "2": self._list_users,
            "3": self._create_classe,
            "4": self._list_classes,
            "5": self._create_matiere,
            "6": self._list_matieres,
            "7": self._create_examen,
            "8": self._list_examens,
            "9": self._deposer_copie,
            "10": self._lancer_correction,
            "11": self._changer_mdp,
            "12": self._generer_csv_etudiants,  
            "0": lambda: sys.exit(0),
        }

        while True:
            clear_screen()
            print_header(f"👤 ADMINISTRATEUR — {self.user.username}")
            print_menu({
                "1": "Créer un utilisateur (professeur ou étudiant)",
                "2": "Lister tous les utilisateurs",
                "3": "Créer une classe",
                "4": "Lister les classes",
                "5": "Créer une matière",
                "6": "Lister les matières",
                "7": "Créer un examen",
                "8": "Lister les examens",
                "9": "Déposer une copie scannée",
                "10": "Lancer la correction d'une copie",
                "11": "Changer mon mot de passe",
                "12": "Générer le CSV des étudiants pour un examen",
                "0": "Quitter",
            })
            choice = ask("Votre choix")
            action = actions.get(choice)
            if action is None:
                print("❌ Choix invalide.")
                pause()
                continue
            try:
                action()
            except SmartExamError as e:
                print(f"\n❌ Erreur métier : {e}")
                pause()
            except Exception as e:
                print(f"\n❌ Erreur inattendue : {e}")
                pause()

    # --- Utilisateurs ---
    def _create_user(self) -> None:
        print_header("➕ CRÉER UN UTILISATEUR")
        role_str = ask_choice("Rôle", ["professeur", "etudiant", "admin"])
        role_enum = RoleUtilisateur(role_str)

        username = ask("Nom d'utilisateur (login)")
        email = ask("Email")
        nom = ask("Nom")
        prenom = ask("Prénom")
        cne = ask("CNE (laisser vide si non-étudiant)", required=False) or None
        password = getpass.getpass("➡️  Mot de passe : ")
        confirm = getpass.getpass("➡️  Confirmer le mot de passe : ")
        if password != confirm:
            print("❌ Les mots de passe ne correspondent pas.")
            return

        classe_id = None
        if role_enum == RoleUtilisateur.ETUDIANT:
            with session_scope() as db:
                classe_svc = ClasseService(db)
                classes = classe_svc.list_classes()
                if classes:
                    print("\n📚 Classes disponibles :")
                    for c in classes:
                        print(f"  {c.id}. {c.nom} ({c.niveau})")
                    if ask_yes_no("Associer à une classe ?", default=True):
                        classe_id = ask_int("ID de la classe")

        with session_scope() as db:
            svc = UserManagementService(db)
            try:
                user = svc.create_user(
                    username=username, email=email, password=password,
                    role=role_enum, nom=nom, prenom=prenom,
                    cne=cne, classe_id=classe_id,
                )
                print(f"\n✅ Utilisateur créé : {user.username} (id={user.id})")
            except DuplicateEntityError as e:
                print(f"\n❌ {e}")
        pause()

    def _list_users(self) -> None:
        print_header("📋 LISTE DES UTILISATEURS")
        with session_scope() as db:
            svc = UserManagementService(db)
            users = svc.list_users()
            if not users:
                print("  (aucun utilisateur)")
            else:
                print(f"  {'ID':<4} {'Username':<15} {'Rôle':<12} {'Nom complet':<25} {'Actif'}")
                print("  " + "-" * 70)
                for u in users:
                    nom_complet = f"{u.nom or ''} {u.prenom or ''}".strip()
                    print(f"  {u.id:<4} {u.username:<15} {u.role:<12} {nom_complet:<25} {'✅' if u.is_active else '❌'}")
        pause()

    # --- Classes ---
    def _create_classe(self) -> None:
        print_header("🏫 CRÉER UNE CLASSE")
        nom = ask("Nom de la classe (ex: GI2)")
        niveau = ask("Niveau (ex: L3, M1)", required=False) or None
        annee = ask("Année scolaire (ex: 2025-2026)", required=False) or None
        with session_scope() as db:
            svc = ClasseService(db)
            try:
                classe = svc.create_classe(nom=nom, niveau=niveau, annee_scolaire=annee)
                print(f"\n✅ Classe créée : {classe.nom} (id={classe.id})")
            except DuplicateEntityError as e:
                print(f"\n❌ {e}")
        pause()

    def _list_classes(self) -> None:
        print_header("📋 LISTE DES CLASSES")
        with session_scope() as db:
            svc = ClasseService(db)
            classes = svc.list_classes()
            if not classes:
                print("  (aucune classe)")
            else:
                for c in classes:
                    print(f"  • id={c.id} — {c.nom} ({c.niveau or '—'}) — {c.annee_scolaire or '—'}")
        pause()

    # --- Matières ---
    def _create_matiere(self) -> None:
        print_header("📚 CRÉER UNE MATIÈRE")
        nom = ask("Nom de la matière")
        code = ask("Code (ex: ALGO, BDD)", required=False) or None
        with session_scope() as db:
            svc = MatiereService(db)
            try:
                matiere = svc.create_matiere(nom=nom, code=code)
                print(f"\n✅ Matière créée : {matiere.nom} (id={matiere.id})")
            except DuplicateEntityError as e:
                print(f"\n❌ {e}")
        pause()

    def _list_matieres(self) -> None:
        print_header("📋 LISTE DES MATIÈRES")
        with session_scope() as db:
            svc = MatiereService(db)
            matieres = svc.list_matieres()
            if not matieres:
                print("  (aucune matière)")
            else:
                for m in matieres:
                    print(f"  • id={m.id} — {m.code or '—'} : {m.nom}")
        pause()

    # --- Examens ---
    def _create_examen(self) -> None:
        print_header("📝 CRÉER UN EXAMEN")
        with session_scope() as db:
            classe_svc = ClasseService(db)
            classes = classe_svc.list_classes()
            if not classes:
                print("❌ Aucune classe. Créez-en une d'abord.")
                pause()
                return
            print("\n📚 Classes disponibles :")
            for c in classes:
                print(f"  {c.id}. {c.nom} ({c.niveau})")
            classe_id = ask_int("ID de la classe")

            matiere_svc = MatiereService(db)
            matieres = matiere_svc.list_matieres()
            if not matieres:
                print("❌ Aucune matière. Créez-en une d'abord.")
                pause()
                return
            print("\n📖 Matières disponibles :")
            for m in matieres:
                print(f"  {m.id}. {m.code or '—'} : {m.nom}")
            matiere_id = ask_int("ID de la matière")

            titre = ask("Titre de l'examen")
            date_examen = ask_date("Date (YYYY-MM-DD, ou Entrée pour ignorer)")

            professeurs = db.query(User).filter(User.role == RoleUtilisateur.PROFESSEUR.value).all()
            professeur_id = None
            if professeurs:
                print("\n👨‍🏫 Professeurs disponibles :")
                for p in professeurs:
                    print(f"  {p.id}. {p.username} ({p.nom} {p.prenom})")
                if ask_yes_no("Assigner un professeur ?", default=False):
                    professeur_id = ask_int("ID du professeur")

            examen_svc = ExamenService(db)
            examen = examen_svc.create_examen(
                titre=titre,
                matiere_id=matiere_id,
                classe_id=classe_id,
                professeur_id=professeur_id,
                date_examen=date_examen,
                created_by_admin_id=self.user.id,
            )
            print(f"\n✅ Examen créé : {examen.titre} (id={examen.id})")
        pause()

    def _list_examens(self) -> None:
        print_header("📋 LISTE DES EXAMENS")
        with session_scope() as db:
            examen_svc = ExamenService(db)
            examens = examen_svc.list_examens()
            if not examens:
                print("  (aucun examen)")
            else:
                for e in examens:
                    prof = e.professeur.username if e.professeur else "—"
                    date_str = e.date_examen.isoformat() if e.date_examen else "—"
                    print(f"  • id={e.id} — {e.titre} [{e.classe.nom} / {e.matiere.code}] Prof: {prof} Date: {date_str}")
        pause()

    # --- Copies ---
    def _deposer_copie(self) -> None:
        print_header("📄 DÉPOSER UNE COPIE")
        with session_scope() as db:
            examen_svc = ExamenService(db)
            examens = examen_svc.list_examens()
            if not examens:
                print("❌ Aucun examen.")
                pause()
                return
            for e in examens:
                print(f"  {e.id}. {e.titre}")
            examen_id = ask_int("ID de l'examen")

            examen = examen_svc.get_examen(examen_id)
            classe_svc = ClasseService(db)
            etudiants = classe_svc.list_etudiants(examen.classe_id)
            etudiant_id = None
            if etudiants:
                print("\n🎓 Étudiants de la classe :")
                for et in etudiants:
                    print(f"  {et.id}. {et.username} ({et.nom} {et.prenom})")
                if ask_yes_no("Identifier l'étudiant maintenant ?", default=False):
                    etudiant_id = ask_int("ID de l'étudiant")

            images_dir = ask_dir("Chemin du dossier contenant les images scannées")
            if not images_dir:
                print("❌ Dossier invalide.")
                return
            image_files = list_image_files(images_dir)
            if not image_files:
                print("❌ Aucune image (png/jpg/jpeg) trouvée dans ce dossier.")
                return
            print(f"\n📷 {len(image_files)} image(s) détectée(s) :")
            for img in image_files:
                print(f"   • {Path(img).name}")

            if not ask_yes_no("Confirmer le dépôt ?", default=True):
                return

            copie_svc = CopieService(db)
            copie = copie_svc.deposer_copie(
                examen_id=examen_id,
                image_paths=image_files,
                etudiant_id=etudiant_id,
                deposee_par_admin_id=self.user.id,
            )
            print(f"\n✅ Copie déposée : id={copie.id}, statut={copie.statut}")
        pause()

    def _lancer_correction(self) -> None:
        print_header("🤖 LANCER LA CORRECTION")
        with session_scope() as db:
            examen_svc = ExamenService(db)
            examens = examen_svc.list_examens()
            if not examens:
                print("❌ Aucun examen.")
                pause()
                return
            for e in examens:
                print(f"  {e.id}. {e.titre}")
            examen_id = ask_int("ID de l'examen")

            copie_svc = CopieService(db)
            copies = copie_svc.list_copies_by_examen(examen_id)
            copies_deposees = [c for c in copies if c.statut == "deposee"]
            if not copies_deposees:
                print("❌ Aucune copie à corriger pour cet examen.")
                pause()
                return
            for c in copies_deposees:
                etu = c.etudiant.username if c.etudiant else "inconnu"
                print(f"  {c.id}. Copie — étudiant={etu} — statut={c.statut}")
            copie_id = ask_int("ID de la copie à corriger")

            print("\n⏳ Lancement du pipeline IA...")
            try:
                correction_svc = CorrectionService(db)
                resultat = correction_svc.lancer_correction(copie_id)
                print(f"\n✅ Correction terminée !")
                print(f"   Statut      : {resultat.statut}")
                if resultat.total_score is not None:
                    print(f"   Score       : {resultat.total_score} / {resultat.max_score}")
                if resultat.percentage is not None:
                    print(f"   Pourcentage : {resultat.percentage}%")
                if resultat.note_finale is not None:
                    print(f"   Note finale : {resultat.note_finale}")
            except CorrectionPipelineError as e:
                print(f"\n❌ Échec du pipeline : {e}")
            except ExamResourcesIncompleteError as e:
                print(f"\n❌ Ressources incomplètes : {e}")
                print("   → Le professeur doit d'abord remplir les ressources de l'examen.")
        pause()

    def _changer_mdp(self) -> None:
        print_header("🔑 CHANGER MON MOT DE PASSE")
        old = getpass.getpass("➡️  Ancien mot de passe : ")
        if not verify_password(old, self.user.password_hash):
            print("\n❌ Ancien mot de passe incorrect.")
            pause()
            return
        new = getpass.getpass("➡️  Nouveau mot de passe : ")
        confirm = getpass.getpass("➡️  Confirmer : ")
        if new != confirm:
            print("❌ Les mots de passe ne correspondent pas.")
            pause()
            return
        with session_scope() as db:
            svc = UserManagementService(db)
            svc.update_user(self.user.id, password=new)
            print("\n✅ Mot de passe modifié.")
        pause()
    def _generer_csv_etudiants(self) -> None:
        print_header("📄 GÉNÉRER LE CSV DES ÉTUDIANTS")
        print("Ce fichier est nécessaire pour que le pipeline IA identifie")
        print("automatiquement l'étudiant à partir de la copie scannée.\n")
        
        with session_scope() as db:
            examen_svc = ExamenService(db)
            examens = examen_svc.list_examens()
            if not examens:
                print("❌ Aucun examen.")
                pause()
                return
            for e in examens:
                print(f"  {e.id}. {e.titre} [{e.classe.nom}]")
            examen_id = ask_int("ID de l'examen")
            
            examen = examen_svc.get_examen(examen_id)
            classe_svc = ClasseService(db)
            etudiants = classe_svc.list_etudiants(examen.classe_id)
            
            if not etudiants:
                print(f"\n❌ Aucun étudiant dans la classe '{examen.classe.nom}'.")
                print("   Créez d'abord des étudiants et associez-les à cette classe.")
                pause()
                return
            
            print(f"\n🎓 {len(etudiants)} étudiant(s) trouvé(s) dans la classe '{examen.classe.nom}' :")
            for et in etudiants:
                cne = et.cne or "⚠️  CNE MANQUANT"
                print(f"   • {et.nom} {et.prenom} — CNE: {cne}")
            
            if any(not et.cne for et in etudiants):
                print("\n⚠️  Attention : certains étudiants n'ont pas de CNE.")
                print("   Le pipeline pourrait ne pas les identifier correctement.")
                if not ask_yes_no("Continuer quand même ?", default=False):
                    return
            
            try:
                csv_path = classe_svc.generate_students_csv_for_examen(
                    classe_id=examen.classe_id,
                    examen_id=examen_id,
                )
                print(f"\n✅ CSV généré avec succès !")
                print(f"   📄 Chemin : {csv_path}")
                print(f"   📊 {len(etudiants)} étudiant(s) enregistré(s)")
                print(f"\n💡 Vous pouvez maintenant lancer la correction (option 10).")
            except Exception as e:
                print(f"\n❌ Erreur lors de la génération : {e}")
        pause()


# ---------------------------------------------------------------------------
# Menu Professeur
# ---------------------------------------------------------------------------

class ProfesseurMenu:
    """Menu du professeur."""

    def __init__(self, user: User):
        self.user = user

    def run(self) -> None:
        actions: Dict[str, Callable[[], None]] = {
            "1": self._remplir_ressources,
            "2": self._voir_ressources,
            "3": self._voir_resultats,
            "4": self._voir_statistiques,
            "5": self._ajuster_note,
            "6": self._valider_note,
            "7": self._changer_mdp,
            "0": lambda: sys.exit(0),
        }

        while True:
            clear_screen()
            print_header(f"👨‍🏫 PROFESSEUR — {self.user.username}")
            print_menu({
                "1": "Remplir les ressources d'un examen",
                "2": "Voir les ressources d'un examen",
                "3": "Voir les résultats d'un examen",
                "4": "Voir les statistiques d'un examen",
                "5": "Ajuster une note",
                "6": "Valider une note",
                "7": "Changer mon mot de passe",
                "0": "Quitter",
            })
            choice = ask("Votre choix")
            action = actions.get(choice)
            if action is None:
                print("❌ Choix invalide.")
                pause()
                continue
            try:
                action()
            except SmartExamError as e:
                print(f"\n❌ Erreur : {e}")
                pause()
            except Exception as e:
                print(f"\n❌ Erreur inattendue : {e}")
                pause()

    def _mes_examens(self, db):
        from modelss.exam import Examen
        return db.query(Examen).filter(Examen.professeur_id == self.user.id).all()

    def _choisir_examen(self, db):
        examens = self._mes_examens(db)
        if not examens:
            print("❌ Aucun examen ne vous est assigné.")
            return None
        for e in examens:
            print(f"  {e.id}. {e.titre}")
        return ask_int("ID de l'examen")

    def _remplir_ressources(self) -> None:
        print_header("📦 REMPLIR LES RESSOURCES")
        with session_scope() as db:
            examen_id = self._choisir_examen(db)
            if examen_id is None:
                pause()
                return

            print("\nIndiquez les chemins des fichiers (Entrée pour ignorer) :")
            consignes_file = ask_file("Chemin des consignes générales")
            corrige_file = ask_file("Chemin du corrigé")
            unit_tests_file = ask_file("Chemin des tests unitaires (JSON)")
            code_consignes_file = ask_file("Chemin des consignes de code")
            qcm_template_file = ask_file("Chemin du template QCM (image)")
            qcm_answer_key_file = ask_file("Chemin du corrigé QCM (JSON)")
            cours_file = ask_file("Chemin du support de cours")
            bareme_file = ask_file("Chemin du barème")

            sections = []
            if ask_yes_no("Section INFO (identification étudiant) ?", default=True):
                sections.append("info")
            if ask_yes_no("Section QCM ?", default=True):
                sections.append("qcm")
            if ask_yes_no("Section RÉDACTION ?", default=True):
                sections.append("redaction")
            if ask_yes_no("Section CODE ?", default=True):
                sections.append("code")

            scoring = ask_choice(
                "Système de notation QCM",
                ["normal", "canadian"],
            )

            # Métadonnées code
            code_language = ask_choice(
                "Langage de l'exercice code",
                ["python", "c", "java", "php"],
            )

            svc = ProfesseurService(db)
            try:
                ressources = svc.definir_ressources(
                    examen_id=examen_id,
                    professeur_id=self.user.id,
                    consignes_file=consignes_file,
                    corrige_file=corrige_file,
                    unit_tests_file=unit_tests_file,
                    code_consignes_file=code_consignes_file,
                    qcm_template_file=qcm_template_file,
                    qcm_answer_key_file=qcm_answer_key_file,
                    cours_file=cours_file,
                    bareme_file=bareme_file,
                    sections=sections,
                    scoring_system=scoring,
                    code_language=code_language,
                )
                print(f"\n✅ Ressources enregistrées (complètes : {ressources.is_complete()})")
            except PermissionDeniedError as e:
                print(f"\n❌ {e}")
        pause()

    def _voir_ressources(self) -> None:
        print_header("📦 RESSOURCES D'UN EXAMEN")
        with session_scope() as db:
            examen_id = self._choisir_examen(db)
            if examen_id is None:
                pause()
                return

            from repositories.exam_repository import ExamResourcesRepository
            repo = ExamResourcesRepository(db)
            ressources = repo.get_by_examen(examen_id)
            if ressources is None:
                print("\n❌ Aucune ressource définie.")
            else:
                print(f"\n📋 Ressources de l'examen #{examen_id} :")
                print(f"  Consignes       : {ressources.consignes_path or '—'}")
                print(f"  Corrigé         : {ressources.corrige_path or '—'}")
                print(f"  Tests unitaires : {ressources.unit_tests_path or '—'}")
                print(f"  Consignes code  : {ressources.code_consignes_path or '—'}")
                print(f"  Template QCM    : {ressources.qcm_template_path or '—'}")
                print(f"  Corrigé QCM     : {ressources.qcm_answer_key_path or '—'}")
                print(f"  Cours           : {ressources.cours_path or '—'}")
                print(f"  Barème          : {ressources.bareme_path or '—'}")
                print(f"  Sections        : {', '.join(ressources.sections) or '—'}")
                print(f"  Notation QCM    : {ressources.scoring_system or '—'}")
                print(f"  Langage code    : {ressources.code_language or '—'}")
                print(f"  Complètes ?     : {'✅' if ressources.is_complete() else '❌'}")
        pause()
    def _voir_resultats(self) -> None:
        print_header("📊 RÉSULTATS D'UN EXAMEN")
        with session_scope() as db:
            examen_id = self._choisir_examen(db)
            if examen_id is None:
                pause()
                return

            svc = ProfesseurService(db)
            try:
                resultats = svc.consulter_resultats(examen_id, self.user.id)
            except PermissionDeniedError as e:
                print(f"\n❌ {e}")
                pause()
                return

            if not resultats:
                print("\n  (aucun résultat)")
                pause()
                return

           
            etudiant_ids = {r.etudiant_id for r in resultats if r.etudiant_id}
            etudiants_map = {}
            if etudiant_ids:
                etudiants = db.query(User).filter(User.id.in_(etudiant_ids)).all()
                etudiants_map = {e.id: e for e in etudiants}

            print(f"\n  {'ID':<5} {'Copie':<7} {'Étudiant':<20} {'Note':<12} {'%':<8} {'Validée'}")
            print("  " + "-" * 65)
            for r in resultats:
                # ✅ Accès via la map au lieu de r.etudiant
                etudiant = etudiants_map.get(r.etudiant_id)
                nom_et = f"{etudiant.nom} {etudiant.prenom}" if etudiant else "—"
                note = r.note_ajustee if r.note_ajustee is not None else r.note_finale
                score = f"{note or '—'} / {r.max_score or '—'}"
                pct = f"{r.percentage}%" if r.percentage is not None else "—"
                validee = "✅" if r.valide_par_professeur else "⏳"
                print(f"  {r.id:<5} {r.copie_id:<7} {nom_et:<20} {score:<12} {pct:<8} {validee}")
        pause()

    def _voir_statistiques(self) -> None:
        print_header("📈 STATISTIQUES D'UN EXAMEN")
        with session_scope() as db:
            examen_id = self._choisir_examen(db)
            if examen_id is None:
                pause()
                return

            svc = ProfesseurService(db)
            try:
                stats = svc.statistiques_examen(examen_id, self.user.id)
            except PermissionDeniedError as e:
                print(f"\n❌ {e}")
                pause()
                return

            print(f"\n  Copies corrigées   : {stats['nombre_copies_corrigees']}")
            print(f"  Moyenne            : {stats['moyenne']}")
            print(f"  Médiane            : {stats['mediane']}")
            print(f"  Note min           : {stats['note_min']}")
            print(f"  Note max           : {stats['note_max']}")
            print(f"  Taux échec pipeline: {stats['taux_echec_pipeline']}%")
        pause()

    def _ajuster_note(self) -> None:
        print_header("✏️  AJUSTER UNE NOTE")
        with session_scope() as db:
            examen_id = self._choisir_examen(db)
            if examen_id is None:
                pause()
                return

            svc = ProfesseurService(db)
            try:
                resultats = svc.consulter_resultats(examen_id, self.user.id)
            except PermissionDeniedError as e:
                print(f"\n❌ {e}")
                pause()
                return

            if not resultats:
                print("❌ Aucun résultat pour cet examen.")
                pause()
                return

            # Charger les étudiants
          
            etudiant_ids = {r.etudiant_id for r in resultats if r.etudiant_id}
            etudiants_map = {}
            if etudiant_ids:
                etudiants = db.query(User).filter(User.id.in_(etudiant_ids)).all()
                etudiants_map = {e.id: e for e in etudiants}

            print("\n  Résultats disponibles :")
            for r in resultats:
                etudiant = etudiants_map.get(r.etudiant_id)
                etu_username = etudiant.username if etudiant else "—"
                note = r.note_ajustee if r.note_ajustee is not None else r.note_finale
                print(f"  • id={r.id} — copie={r.copie_id} — étudiant={etu_username} — note={note}")

            resultat_id = ask_int("ID du résultat à ajuster")
            nouvelle_note = ask_float("Nouvelle note")
            commentaire = ask("Commentaire (optionnel)", required=False) or None

            try:
                svc.ajuster_note(
                    resultat_id=resultat_id,
                    professeur_id=self.user.id,
                    nouvelle_note=nouvelle_note,
                    commentaire=commentaire,
                )
                print("\n✅ Note ajustée.")
            except PermissionDeniedError as e:
                print(f"\n❌ {e}")
        pause()

    def _valider_note(self) -> None:
        print_header("✅ VALIDER UNE NOTE")
        with session_scope() as db:
            examen_id = self._choisir_examen(db)
            if examen_id is None:
                pause()
                return

            svc = ProfesseurService(db)
            try:
                resultats = svc.consulter_resultats(examen_id, self.user.id)
            except PermissionDeniedError as e:
                print(f"\n❌ {e}")
                pause()
                return

            if not resultats:
                print("❌ Aucun résultat pour cet examen.")
                pause()
                return

            # Charger les étudiants
            
            etudiant_ids = {r.etudiant_id for r in resultats if r.etudiant_id}
            etudiants_map = {}
            if etudiant_ids:
                etudiants = db.query(User).filter(User.id.in_(etudiant_ids)).all()
                etudiants_map = {e.id: e for e in etudiants}

            print("\n  Résultats disponibles :")
            for r in resultats:
                etudiant = etudiants_map.get(r.etudiant_id)
                etu_username = etudiant.username if etudiant else "—"
                statut = "✅" if r.valide_par_professeur else "⏳"
                print(f"  • id={r.id} — copie={r.copie_id} — étudiant={etu_username} — {statut}")

            resultat_id = ask_int("ID du résultat à valider")
            commentaire = ask("Commentaire (optionnel)", required=False) or None

            try:
                svc.valider_note(
                    resultat_id=resultat_id,
                    professeur_id=self.user.id,
                    commentaire=commentaire,
                )
                print("\n✅ Note validée.")
            except PermissionDeniedError as e:
                print(f"\n❌ {e}")
        pause()

    def _changer_mdp(self) -> None:
        print_header("🔑 CHANGER MON MOT DE PASSE")
        old = getpass.getpass("➡️  Ancien mot de passe : ")
        if not verify_password(old, self.user.password_hash):
            print("\n❌ Ancien mot de passe incorrect.")
            pause()
            return
        new = getpass.getpass("➡️  Nouveau mot de passe : ")
        confirm = getpass.getpass("➡️  Confirmer : ")
        if new != confirm:
            print("❌ Les mots de passe ne correspondent pas.")
            pause()
            return
        with session_scope() as db:
            svc = UserManagementService(db)
            svc.update_user(self.user.id, password=new)
            print("\n✅ Mot de passe modifié.")
        pause()


# ---------------------------------------------------------------------------
# Menu Étudiant
# ---------------------------------------------------------------------------

class EtudiantMenu:
    """Menu de l'étudiant."""

    def __init__(self, user: User):
        self.user = user

    def run(self) -> None:
        actions: Dict[str, Callable[[], None]] = {
            "1": self._voir_notes,
            "2": self._telecharger_releve,
            "3": self._changer_mdp,
            "0": lambda: sys.exit(0),
        }

        while True:
            clear_screen()
            print_header(f"🎓 ÉTUDIANT — {self.user.username}")
            print_menu({
                "1": "Voir mes notes",
                "2": "Télécharger mon relevé de notes",
                "3": "Changer mon mot de passe",
                "0": "Quitter",
            })
            choice = ask("Votre choix")
            action = actions.get(choice)
            if action is None:
                print("❌ Choix invalide.")
                pause()
                continue
            try:
                action()
            except SmartExamError as e:
                print(f"\n❌ Erreur : {e}")
                pause()
            except Exception as e:
                print(f"\n❌ Erreur inattendue : {e}")
                pause()

    def _voir_notes(self) -> None:
        print_header("📊 MES NOTES")
        with session_scope() as db:
            svc = EtudiantService(db)
            notes = svc.consulter_notes(self.user.id)
            if not notes:
                print("\n  (aucune note disponible)")
            else:
                print(f"\n  {'Examen':<30} {'Matière':<15} {'Note':<12} {'%':<8} {'Statut'}")
                print("  " + "-" * 80)
                for n in notes:
                    note_val = n.get("note")
                    note_max = n.get("note_max")
                    score = f"{note_val} / {note_max}" if note_val is not None else "—"
                    pct = f"{n.get('pourcentage')}%" if n.get('pourcentage') is not None else "—"
                    statut = "✅ Validée" if n.get("valide_par_professeur") else "⏳ En attente"
                    print(f"  {(n.get('examen') or '—'):<30} {(n.get('matiere') or '—'):<15} {score:<12} {pct:<8} {statut}")
                    if n.get("commentaire"):
                        print(f"      💬 {n['commentaire']}")
        pause()

    def _telecharger_releve(self) -> None:
        print_header("📄 RELEVÉ DE NOTES")
        with session_scope() as db:
            try:
                svc = EtudiantService(db)
                path = svc.telecharger_releve(self.user.id)
                print(f"\n✅ Relevé généré : {path}")
            except Exception as e:
                print(f"\n❌ Impossible de générer le relevé : {e}")
        pause()

    def _changer_mdp(self) -> None:
        print_header("🔑 CHANGER MON MOT DE PASSE")
        old = getpass.getpass("➡️  Ancien mot de passe : ")
        if not verify_password(old, self.user.password_hash):
            print("\n❌ Ancien mot de passe incorrect.")
            pause()
            return
        new = getpass.getpass("➡️  Nouveau mot de passe : ")
        confirm = getpass.getpass("➡️  Confirmer : ")
        if new != confirm:
            print("❌ Les mots de passe ne correspondent pas.")
            pause()
            return
        with session_scope() as db:
            svc = UserManagementService(db)
            svc.update_user(self.user.id, password=new)
            print("\n✅ Mot de passe modifié.")
        pause()


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main() -> None:
    """Boucle principale : authentification puis menu par rôle."""
    while True:
        clear_screen()
        user = authenticate()
        if user is None:
            if not ask_yes_no("Réessayer ?", default=True):
                print("\n👋 À bientôt !")
                return
            continue

        print(f"\n✅ Connecté en tant que {user.username} ({user.role})")
        pause()

        role = user.role
        # Le rôle peut être stocké comme string ou Enum
        if isinstance(role, RoleUtilisateur):
            role_value = role.value
        else:
            role_value = role

        if role_value == RoleUtilisateur.ADMIN.value:
            AdminMenu(user).run()
        elif role_value == RoleUtilisateur.PROFESSEUR.value:
            ProfesseurMenu(user).run()
        elif role_value == RoleUtilisateur.ETUDIANT.value:
            EtudiantMenu(user).run()
        else:
            print(f"\n❌ Rôle inconnu : {role}")
            pause()


if __name__ == "__main__":
    main()