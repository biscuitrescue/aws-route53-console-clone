"""Print the OpenAPI schema as JSON; the frontend generates its API types from it.

Run with ``python -m app.export_openapi``. No database is touched.
"""

import json
import sys

from app.config import Settings
from app.main import create_app


def main() -> None:
    app = create_app(Settings(database_url="sqlite://"))
    json.dump(app.openapi(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
