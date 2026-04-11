from __future__ import annotations

from pathlib import Path
import sys

from streamlit.web import cli as stcli


def main() -> None:
    app_path = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app_path)]
    stcli.main()


if __name__ == "__main__":
    main()
