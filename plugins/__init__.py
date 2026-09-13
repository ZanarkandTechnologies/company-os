"""Company OS connector sources alongside installed Hermes plugins.

Hermes also ships a top-level ``plugins`` package. Extend the namespace so
source commands/tests resolve these connectors without hiding Hermes modules.
Runtime directory plugins are loaded under Hermes' own isolated namespace.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
