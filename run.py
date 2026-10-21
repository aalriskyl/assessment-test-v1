"""Local entry point. Use a virtualenv; .deps is an optional workspace fallback."""

import os
import sys
from pathlib import Path

local_dependencies = Path(__file__).parent / ".deps"
if local_dependencies.exists() and sys.prefix == sys.base_prefix:
    sys.path.insert(0, str(local_dependencies))

from procurement import create_app  # noqa: E402 -- optional workspace dependencies must load first.

app = create_app()

if __name__ == "__main__":
    from procurement.db import migrate

    if sys.argv[1:] in (["migrate"], ["init-db"]):
        with app.app_context():
            migrate()
        print("Migrations complete.")
    elif sys.argv[1:] == ["seed-demo"]:
        from procurement.seed import seed_demo

        with app.app_context():
            migrate()
            seed_demo()
        print("Demo accounts ready. Password: Demo123!")
    elif sys.argv[1:] == ["serve"]:
        from waitress import serve

        port = int(os.environ.get("PORT", "5000"))
        if not 1024 <= port <= 65535:
            raise SystemExit("PORT must be between 1024 and 65535.")
        serve(app, host="127.0.0.1", port=port)
    elif not sys.argv[1:]:
        app.run(host="127.0.0.1", port=5000, debug=False)
    else:
        raise SystemExit("Usage: python run.py [migrate|seed-demo|serve]")
