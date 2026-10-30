# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Write the JSON Schema of the scene spec beside the specs, and its reference
in the documentation when the checkout has one: ``python -m agentspecs.scenes``."""

from . import SCHEMA_PATH, schema_text
from .reference import REFERENCE_PATH, reference_markdown

if __name__ == "__main__":
    SCHEMA_PATH.write_text(schema_text())
    print(f"wrote {SCHEMA_PATH}")
    if REFERENCE_PATH.parent.is_dir():
        REFERENCE_PATH.write_text(reference_markdown())
        print(f"wrote {REFERENCE_PATH}")
