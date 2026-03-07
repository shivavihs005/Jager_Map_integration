from config import APP
from dashboard.server import run_dashboard
from system import AutonomousCarSystem


def main():
    system = AutonomousCarSystem()
    print(f"RC-NAV-01 Mission Control listening on http://127.0.0.1:{APP.port}")
    run_dashboard(system)


if __name__ == "__main__":
    main()