# Playbook de réponse à incident — SmartExamAI

Cycle : **Détecter → Qualifier → Contenir → Éradiquer → Rétablir → Retour d'expérience**.

## 1. Brute force / spraying (règles 01-02)
1. **Qualifier** : filtrer `event=auth.login_failed` par `ip` ; un compte a-t-il ensuite un `auth.login_success` depuis la même IP ? (= compromission probable).
2. **Contenir** : bloquer l'IP au reverse-proxy ; forcer la réinitialisation du mot de passe des comptes touchés ; `UPDATE users SET locked_until=…`.
3. **Éradiquer** : révoquer les refresh tokens du compte (`revoke_all_for_user`).
4. **REX** : durcir le seuil, ajouter une 2FA pour admin/professeur.

## 2. Rejeu de jeton / session volée (règle 04)
1. Un `auth.refresh_rejected` signale un refresh déjà consommé : la famille est révoquée automatiquement.
2. Contacter l'utilisateur, changer son mot de passe (invalide aussi les jetons d'accès, grâce à `pwv`).
3. Chercher la cause : XSS, poste infecté, jeton dans un log (F-16).

## 3. Balayage IDOR / accès refusés (règle 05)
1. Lister les chemins ciblés (`path`) et l'utilisateur ; vérifier qu'aucune réponse 200 n'a suivi.
2. Suspendre le compte si l'intention est avérée ; corriger tout contrôle de propriété manquant.

## 4. Prompt injection (règle 06)
1. **Ne jamais valider la note automatiquement** : revue humaine obligatoire.
2. Conserver la copie comme preuve ; notifier la scolarité selon le règlement.
3. Ajouter la formulation aux motifs de `llm_guard.py` + un test dans `test_05`.

## 5. Évènement CSRF (règle 03)
Vérifier l'`origin` : si c'est une origine légitime oubliée, l'ajouter à `SMARTEXAM_CORS_ORIGINS` ; sinon, enquêter sur la page source (XSS ?).

## Contacts & preuves
Responsable sécurité · Encadrant · DPO. Conserver les logs `smartexamai.audit` ≥ 90 jours, horodatés UTC, en lecture seule.
