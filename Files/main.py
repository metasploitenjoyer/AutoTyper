"""AutoTyper entry point.  Development:  python main.py"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))  # lets `import autotyper` work from a checkout


def main():
    if "--self-test" in sys.argv:
        from autotyper.selftest import run_self_test
        return run_self_test()
    try:
        from autotyper.app import run
    except ModuleNotFoundError as exc:
        if (exc.name or "").startswith("PySide6"):
            sys.stderr.write("PySide6 is not installed. Run:  pip install -r requirements.txt\n")
            return 1
        raise
    return run()


if __name__ == "__main__":
    sys.exit(main())
