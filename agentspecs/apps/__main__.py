# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Write the JSON Schema of the Appspec beside the specs: ``python -m agentspecs.apps``."""

from . import SCHEMA_PATH, schema_text

if __name__ == "__main__":
    SCHEMA_PATH.write_text(schema_text())
    print(f"wrote {SCHEMA_PATH}")
