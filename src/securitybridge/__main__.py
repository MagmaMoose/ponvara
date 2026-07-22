"""Console entry point — Phase 0 stub.

Resolves the ``securitybridge`` console script declared in ``pyproject.toml`` so the
package installs cleanly. The service is not implemented yet — see ``docs/DESIGN.md``
for the design and the phased build plan.
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write(
        "securitybridge is a Phase 0 scaffold and is not implemented yet.\n"
        "See docs/DESIGN.md for the design and the phased build plan.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
