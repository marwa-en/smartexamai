"""
SmartExamAI — Dépendances RBAC par ressource.

Vérifie qu'un utilisateur n'accède qu'aux ressources qu'il possède :
- Admin : accès total
- Professeur : uniquement ses examens (professeur_id == user.id)
- Étudiant : uniquement ses copies/résultats (etudiant_id == user.id)
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from modelss.enums import RoleUtilisateur
from modelss.user import User
from modelss.exam import Examen
from modelss.copie import CopieExamen


def _not_found(detail: str = "Ressource introuvable.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _forbidden(detail: str = "Accès refusé.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def verify_examen_ownership(
    examen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Examen:
    """Vérifie que l'utilisateur a le droit d'accéder à un examen.

    - Admin : accès total
    - Professeur : uniquement si examen.professeur_id == user.id
    - Étudiant : accès lecture si l'examen concerne sa classe
    """
    examen = db.get(Examen, examen_id)
    if examen is None:
        raise _not_found("Examen introuvable.")

    # Admin : accès total
    if current_user.role == RoleUtilisateur.ADMIN.value:
        return examen

    # Professeur : uniquement ses examens
    if current_user.role == RoleUtilisateur.PROFESSEUR.value:
        if examen.professeur_id == current_user.id:
            return examen
        raise _forbidden("Vous n'êtes pas le professeur assigné à cet examen.")

    # Étudiant : accès lecture si l'examen est dans sa classe
    if current_user.role == RoleUtilisateur.ETUDIANT.value:
        if examen.classe_id == current_user.classe_id:
            return examen
        raise _forbidden("Cet examen ne concerne pas votre classe.")

    raise _forbidden()


def verify_copie_ownership(
    copie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopieExamen:
    """Vérifie que l'utilisateur a le droit d'accéder à une copie.

    - Admin : accès total
    - Professeur : accès si c'est son examen
    - Étudiant : uniquement ses propres copies
    """
    copie = db.get(CopieExamen, copie_id)
    if copie is None:
        raise _not_found("Copie introuvable.")

    # Admin : accès total
    if current_user.role == RoleUtilisateur.ADMIN.value:
        return copie

    # Professeur : accès si c'est son examen
    if current_user.role == RoleUtilisateur.PROFESSEUR.value:
        examen = db.get(Examen, copie.examen_id)
        if examen and examen.professeur_id == current_user.id:
            return copie
        raise _forbidden("Cette copie ne fait pas partie de vos examens.")

    # Étudiant : uniquement ses propres copies
    if current_user.role == RoleUtilisateur.ETUDIANT.value:
        if copie.etudiant_id == current_user.id:
            return copie
        raise _forbidden("Cette copie ne vous appartient pas.")

    raise _forbidden()


def verify_resultat_ownership(
    resultat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vérifie que l'utilisateur a le droit d'accéder à un résultat."""
    from modelss.resultat import Resultat

    resultat = db.get(Resultat, resultat_id)
    if resultat is None:
        raise _not_found("Résultat introuvable.")

    # Admin : accès total
    if current_user.role == RoleUtilisateur.ADMIN.value:
        return resultat

    # Professeur : accès si c'est son examen
    if current_user.role == RoleUtilisateur.PROFESSEUR.value:
        examen = db.get(Examen, resultat.examen_id)
        if examen and examen.professeur_id == current_user.id:
            return resultat
        raise _forbidden("Ce résultat ne fait pas partie de vos examens.")

    # Étudiant : uniquement ses propres résultats
    if current_user.role == RoleUtilisateur.ETUDIANT.value:
        if resultat.etudiant_id == current_user.id:
            return resultat
        raise _forbidden("Ce résultat ne vous appartient pas.")

    raise _forbidden()