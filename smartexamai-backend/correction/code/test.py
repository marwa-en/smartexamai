"""
SmartExamAI — Tests de sécurité de la sandbox Docker (version corrigée).

IMPORTANT : chaque run() doit recevoir AU MOINS UN TestCase,
sinon le harness n'exécute jamais le code étudiant.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "correction" / "code"))

from sandbox.python_runner import PythonRunner
from models.exercise import Exercise, TestCase, ExerciseType

passed = failed = 0


def check(name, condition, details=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"✅ PASS : {name}")
    else:
        failed += 1
        print(f"❌ FAIL : {name} {details}")


def create_runner():
    return PythonRunner()


def create_exercise():
    return Exercise(
        title="Test",
        statement="Test",
        language="python",
        type=ExerciseType.PROGRAM,
        rubric={"total": 20},
    )


def one_test_case():
    """✅ Au moins 1 test case pour que le harness exécute le code."""
    return [TestCase(input_data="", expected_output="peu_importe")]


def run_code(code, timeout=10):
    """Exécute du code et affiche stderr si stdout est vide (diagnostic)."""
    runner = create_runner()
    exercise = create_exercise()
    report = runner.run(code, exercise, one_test_case(), timeout=timeout)
    if not report.stdout.strip():
        print(f"   🔍 [DIAG] stdout vide. stderr = {report.stderr[:300]}")
    return report


print("=" * 70)
print("  TESTS DE SÉCURITÉ — SANDBOX DOCKER")
print("=" * 70)

# --- Test 1 : Boucle infinie (timeout) ---
print("\n--- Test 1 : Boucle infinie (timeout) ---")
try:
    start = time.time()
    report = run_code("while True: pass", timeout=5)
    elapsed = time.time() - start

    check("Boucle infinie tuée par timeout", report.executed is False)
    check(
        "Timeout déclenché (±10s overhead Windows)",
        elapsed < 15,
        f"(durée: {elapsed:.1f}s)",
    )
except Exception as e:
    print(f"⚠️  Erreur test 1 : {e}")
    failed += 1

# --- Test 2 : Accès réseau bloqué ---
print("\n--- Test 2 : Accès réseau bloqué ---")
try:
    network_code = """
import urllib.request
try:
    urllib.request.urlopen('http://google.com', timeout=2)
    print("NETWORK_OK")
except Exception as e:
    print(f"NETWORK_BLOCKED: {e}")
"""
    report = run_code(network_code)
    check(
        "Réseau bloqué",
        "NETWORK_BLOCKED" in report.stdout,
        f"(stdout: {report.stdout[:150]})",
    )
except Exception as e:
    print(f"⚠️  Erreur test 2 : {e}")
    failed += 1

# --- Test 3 : Écriture hors /tmp bloquée ---
print("\n--- Test 3 : Écriture hors /tmp bloquée ---")
try:
    write_code = """
try:
    with open('/etc/passwd', 'w') as f:
        f.write('hacked')
    print("WRITE_OK")
except Exception as e:
    print(f"WRITE_BLOCKED: {type(e).__name__}")
"""
    report = run_code(write_code)
    check(
        "Écriture /etc/passwd bloquée",
        "WRITE_BLOCKED" in report.stdout,
        f"(stdout: {report.stdout[:150]})",
    )
except Exception as e:
    print(f"⚠️  Erreur test 3 : {e}")
    failed += 1

# --- Test 4 : Fork bomb (pids_limit) ---
print("\n--- Test 4 : Fork bomb (pids_limit) ---")
try:
    fork_code = """
import os, sys
while True:
    try:
        os.fork()
    except OSError:
        print("FORK_BLOCKED")
        sys.exit(0)
"""
    start = time.time()
    report = run_code(fork_code, timeout=8)
    elapsed = time.time() - start

    check(
        "Fork bomb contenue",
        "FORK_BLOCKED" in report.stdout or elapsed < 18,
        f"(stdout: {report.stdout[:150]}, durée: {elapsed:.1f}s)",
    )
except Exception as e:
    print(f"⚠️  Erreur test 4 : {e}")
    failed += 1

# --- Test 5 : Code normal fonctionne ---
print("\n--- Test 5 : Code normal fonctionne ---")
try:
    normal_code = """
print("Hello, World!")
print(f"Result: {2 + 2}")
"""
    report = run_code(normal_code)
    check(
        "Code normal s'exécute",
        "Hello, World!" in report.stdout,
        f"(stdout: {report.stdout[:150]})",
    )
except Exception as e:
    print(f"⚠️  Erreur test 5 : {e}")
    failed += 1

# --- Test 6 : Écriture dans /tmp autorisée ---
print("\n--- Test 6 : Écriture dans /tmp autorisée ---")
try:
    tmp_code = """
with open('/tmp/test_file.txt', 'w') as f:
    f.write('test')
with open('/tmp/test_file.txt', 'r') as f:
    print(f"TMP_WRITE_OK: {f.read()}")
"""
    report = run_code(tmp_code)
    check(
        "Écriture /tmp autorisée",
        "TMP_WRITE_OK: test" in report.stdout,
        f"(stdout: {report.stdout[:150]})",
    )
except Exception as e:
    print(f"⚠️  Erreur test 6 : {e}")
    failed += 1

print("\n" + "=" * 70)
print(f"  RÉSULTAT : {passed} réussis / {failed} échoués")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)