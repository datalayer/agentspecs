# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Agentspecs: the YAML catalogue of Datalayer agents, models, tools and teams.

The specs are data: the catalogues under this package (`agents`, `models`,
`teams`, ...) are read by their consumers, `agent-runtimes` first. Importing
the package itself must stay free of dependencies, so that
`from agentspecs.models import list_models` works wherever it is installed.
"""

from .__version__ import __version__

__all__ = ["__version__"]
