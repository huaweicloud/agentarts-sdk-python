"""Unit tests for the lazy adapter re-exports of ``agentarts.sdk.integration``."""

import pytest

from agentarts.sdk import integration


class TestIntegrationExports:
    def test_every_exported_name_resolves(self):
        assert integration.__all__
        for name in integration.__all__:
            assert getattr(integration, name) is not None

    def test_unknown_name_raises_attribute_error(self):
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = integration.NoSuchAdapter

    def test_placeholder_names_are_gone(self):
        # BaseAdapter / WrappedAgent / LangGraphAdapter were advertised in
        # __all__ but exist in no module, so importing them always failed.
        for name in ("BaseAdapter", "WrappedAgent", "LangGraphAdapter"):
            assert name not in integration.__all__
            with pytest.raises(AttributeError):
                getattr(integration, name)
