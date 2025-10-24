"""Utilities for working with Elasticsearch connections."""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.conf import settings
from elasticsearch_dsl import connections


def _normalise_hosts(config: Dict[str, Any]) -> Dict[str, Any]:
    hosts = config.get("hosts")
    if isinstance(hosts, str) and hosts and not hosts.startswith(("http://", "https://", "es+")):
        # Elasticsearch client expects a scheme in single host strings.
        return {**config, "hosts": f"http://{hosts}"}
    return config


def create_default_connection() -> None:
    """Create the default Elasticsearch connection if configuration is provided."""

    config: Optional[Dict[str, Any]] = getattr(settings, "ELASTICSEARCH_DSL", {}).get("default")
    if not config:
        return
    if not config.get("hosts"):
        return
    connections.create_connection(**_normalise_hosts(config))


__all__ = ["create_default_connection"]
