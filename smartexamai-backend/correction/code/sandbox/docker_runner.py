"""
Base Docker sandbox runner for executing student code securely.

Sécurité appliquée :
- Aucune capacité Linux (cap-drop ALL)
- Filesystem racine lecture seule (seul /tmp est inscriptible)
- Pas de réseau
- Utilisateur non-root (nobody)
- Limites strictes (CPU, mémoire, PIDs, fichiers, taille)
- Timeout dur avec kill forcé
- Nettoyage automatique
"""
import docker
import os
import tempfile
import time
import logging
import shutil
import signal
from typing import Optional, Tuple, List
from docker.errors import DockerException, NotFound

from configg import settings
from sandbox.execution_report import ExecutionReport
from models.exercise import Exercise, TestCase

logger = logging.getLogger(__name__)


class DockerRunner:
    """
    Classe de base pour l'exécution de code dans un conteneur Docker sécurisé.
    
    Les sous-classes (PythonRunner, PhpRunner, etc.) doivent implémenter :
    - _prepare_workspace() : prépare les fichiers nécessaires
    - _get_run_command() : retourne la commande à exécuter
    """

    # Paramètres de sécurité (valeurs par défaut, surchargées par settings)
    DEFAULT_PIDS_LIMIT = 64
    DEFAULT_CPU_LIMIT = 0.5
    DEFAULT_MEMORY_LIMIT = "256m"
    DEFAULT_TIMEOUT_SECONDS = 10
    DEFAULT_TMP_SIZE = "64m"

    def __init__(self, image: str, language: str):
        """
        Initialise le runner Docker.
        
        Args:
            image: Image Docker à utiliser (ex: 'python:3.11-slim')
            language: Langage de programmation (ex: 'python', 'php')
        """
        self.image = image
        self.language = language
        
        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as e:
            logger.error(f"Impossible de se connecter au daemon Docker : {e}")
            raise RuntimeError("Le daemon Docker n'est pas accessible.") from e

    def run(
        self,
        code: str,
        exercise: Exercise,
        test_cases: List[TestCase],
        stdin_data: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ExecutionReport:
        """
        Exécute le code dans un conteneur Docker sécurisé.
        
        Args:
            code: Code source de l'étudiant
            exercise: Détails de l'exercice
            test_cases: Liste des cas de test du professeur
            stdin_data: Entrée standard optionnelle
            timeout: Timeout en secondes (défaut: settings.sandbox_timeout_seconds)
            
        Returns:
            ExecutionReport avec les résultats
        """
        timeout = timeout or settings.sandbox_timeout_seconds
        workspace = self._create_temp_workspace()

        try:
            # 1. Préparer le workspace (code étudiant, harness, inputs)
            self._prepare_workspace(workspace, code, exercise, test_cases)

            # 2. Obtenir la commande à exécuter
            command = self._get_run_command(workspace)

            # 3. Exécuter dans Docker avec timeout dur
            start_time = time.time()
            stdout, stderr, exit_code, timed_out, oom_killed = self._execute_in_docker(
                workspace, command, stdin_data, timeout
            )
            end_time = time.time()

            execution_time_ms = (end_time - start_time) * 1000

            # 4. Construire le rapport
            return self._build_report(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time_ms=execution_time_ms,
                timed_out=timed_out,
                oom_killed=oom_killed,
                test_cases=test_cases
            )

        finally:
            # 5. Nettoyer le workspace
            self._cleanup_workspace(workspace)

    def _create_temp_workspace(self) -> str:
        """Crée un répertoire temporaire pour le workspace."""
        return tempfile.mkdtemp(prefix="smartexam_sandbox_")

    def _write_file(self, directory: str, filename: str, content: str) -> str:
        """Écrit du contenu dans un fichier avec des fins de ligne LF."""
        filepath = os.path.join(directory, filename)
        # IMPORTANT: newline='\n' force les fins de ligne LF pour les conteneurs Linux
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        return filepath

    def _execute_in_docker(
    self,
    workspace: str,
    command: str,
    stdin_data: Optional[str],
    timeout: int
) -> Tuple[str, str, int, bool, bool]:
     """
    Exécute le conteneur Docker avec timer fiable.
    
    Note : sur Docker Desktop Windows/WSL2, il y a un overhead de ~5-7s
    après le kill. Le timeout réel sera donc timeout + overhead.
    """
     import threading
    
     stdout = ""
     stderr = ""
     exit_code = -1
     timed_out = False
     oom_killed = False
     container = None

    # Paramètres de sécurité
     mem_limit = getattr(settings, 'sandbox_memory_limit', self.DEFAULT_MEMORY_LIMIT)
     cpu_limit = getattr(settings, 'sandbox_cpu_limit', self.DEFAULT_CPU_LIMIT)
     pids_limit = getattr(settings, 'sandbox_pids_limit', self.DEFAULT_PIDS_LIMIT)

     def kill_after_timeout():
        """Timer callback : kill forcé du conteneur."""
        nonlocal timed_out
        timed_out = True
        logger.warning("⏱️  Timeout (%ds) atteint, kill forcé du conteneur", timeout)
        try:
            container.kill(signal='SIGKILL')
        except Exception as e:
            logger.warning("Kill échoué : %s", e)

     try:
        logger.info(
            "Démarrage du conteneur (image=%s, timeout=%ds, lang=%s)",
            self.image, timeout, self.language
        )

        container = self.client.containers.run(
            image=self.image,
            command=command,
            working_dir="/workspace",
            
            # --- SÉCURITÉ ---
            network_disabled=True,
            read_only=True,
            tmpfs={'/tmp': f'size={self.DEFAULT_TMP_SIZE},noexec,nosuid'},
            cap_drop=['ALL'],
            security_opt=['no-new-privileges'],
            mem_limit=mem_limit,
            memswap_limit=mem_limit,
            cpu_period=100000,
            cpu_quota=int(cpu_limit * 100000),
            pids_limit=pids_limit,
            user='nobody',
            
            volumes={
                workspace: {'bind': '/workspace', 'mode': 'ro'}
            },
            
            stdin_open=bool(stdin_data),
            stdout=True,
            stderr=True,
            detach=True,
            auto_remove=False,
        )

        # Démarrer le timer
        timer = threading.Timer(timeout, kill_after_timeout)
        timer.start()

        # Attendre la fin (bloquant)
        try:
            result = container.wait(timeout=timeout + 10)  # +10s marge pour Windows
            exit_code = result.get('StatusCode', -1)
        except Exception as wait_err:
            logger.warning("wait() échoué : %s", wait_err)

        # Annuler le timer si terminé avant
        timer.cancel()

        # Vérifier OOM
        try:
            if container.attrs.get('State', {}).get('OOMKilled', False):
                oom_killed = True
        except Exception:
            pass

        # Récupérer les logs
        try:
            stdout_bytes = container.logs(stdout=True, stderr=False)
            stderr_bytes = container.logs(stdout=False, stderr=True)
            stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
            stderr_raw = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
            if stderr_raw:
                stderr = (stderr + "\n" + stderr_raw).strip() if stderr else stderr_raw
        except Exception as log_err:
            logger.warning("Logs échoués : %s", log_err)

     except Exception as e:
        err_str = str(e).lower()
        
        if "timeout" in err_str or "read timed out" in err_str:
            timed_out = True
            stderr = f"Timeout après {timeout} secondes"
        elif "oom" in err_str or "memory" in err_str:
            oom_killed = True
            stderr = "Limite de mémoire dépassée"
        else:
            stderr = f"Erreur Docker : {str(e)}"
            logger.error("Erreur Docker : %s", e, exc_info=True)

     finally:
        if container:
            try:
                container.remove(force=True)
            except NotFound:
                pass
            except Exception as e:
                logger.warning("Remove échoué : %s", e)

     if timed_out:
        stderr = f"Timeout après {timeout} secondes"

     return stdout, stderr, exit_code, timed_out, oom_killed
    def _force_kill_container(self, container) -> None:
        """Tue un conteneur de force (signal KILL)."""
        try:
            container.kill(signal='SIGKILL')
            logger.info("Conteneur tué (SIGKILL)")
        except Exception as e:
            logger.warning("Impossible de tuer le conteneur : %s", e)

    def _remove_container_safely(self, container) -> None:
        """Supprime un conteneur de manière sûre."""
        try:
            container.remove(force=True)
        except NotFound:
            pass  # Déjà supprimé
        except Exception as e:
            logger.warning("Impossible de supprimer le conteneur : %s", e)

    def _build_report(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        execution_time_ms: float,
        timed_out: bool,
        oom_killed: bool,
        test_cases: List[TestCase]
    ) -> ExecutionReport:
        """
        Construit le rapport d'exécution à partir des résultats bruts.
        Les sous-classes surchargent cette méthode pour parser les tests.
        """
        compiled = True
        executed = True

        if timed_out:
            executed = False
            stderr = "Erreur : Timeout d'exécution"
        elif oom_killed:
            executed = False
            stderr = "Erreur : Limite de mémoire dépassée"
        elif exit_code != 0:
            executed = False

        return ExecutionReport(
            compiled=compiled,
            executed=executed,
            passed_tests=0,
            failed_tests=0,
            execution_time_ms=execution_time_ms,
            memory_mb=0.0,
            stdout=stdout,
            stderr=stderr
        )

    def _cleanup_workspace(self, workspace: str) -> None:
        """Supprime le répertoire temporaire du workspace."""
        try:
            shutil.rmtree(workspace, ignore_errors=True)
        except Exception as e:
            logger.warning("Impossible de nettoyer le workspace %s : %s", workspace, e)

    # --- Méthodes abstraites pour les sous-classes ---

    def _prepare_workspace(
        self,
        workspace: str,
        code: str,
        exercise: Exercise,
        test_cases: List[TestCase]
    ) -> None:
        """
        Prépare le workspace avec les fichiers nécessaires.
        Doit être implémentée par les sous-classes.
        """
        raise NotImplementedError("Les sous-classes doivent implémenter _prepare_workspace")

    def _get_run_command(self, workspace: str) -> str:
        """
        Retourne la commande shell à exécuter dans le conteneur.
        Doit être implémentée par les sous-classes.
        """
        raise NotImplementedError("Les sous-classes doivent implémenter _get_run_command")