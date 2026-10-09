import sys
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def run_step(name, cmd):
    print(f"=== Running {name} ===")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"[FAIL] {name} FAILED with return code {res.returncode}")
        return False
    print(f"[OK] {name} PASSED\n")
    return True

def main():
    root = Path(__file__).resolve().parent.parent
    src_dir = root / "src"
    
    py_files = list(src_dir.rglob("*.py"))
    syntax_ok = True
    for py_file in py_files:
        res = subprocess.run([sys.executable, "-m", "py_compile", str(py_file)], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Syntax Error in {py_file}:\n{res.stderr}")
            syntax_ok = False
    
    if not syntax_ok:
        sys.exit(1)
    print("All Python files passed syntax check.\n")

    pytest_cmd = f'"{sys.executable}" -m pytest src/tests/unit/ -v'
    if not run_step("Unit Tests (Pytest)", pytest_cmd):
        sys.exit(1)

    print("QA CHECKS PASSED SUCCESSFULLY")
    sys.exit(0)

if __name__ == "__main__":
    main()
