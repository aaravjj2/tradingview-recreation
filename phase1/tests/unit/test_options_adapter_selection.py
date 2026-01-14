import types

from services.options.adapter import get_options_adapter, OptionsDataAdapter


def test_get_options_adapter_falls_back_by_default(monkeypatch):
    # Ensure fresh singleton
    import services.options.adapter as mod
    mod._adapter = None

    # Patch settings to no Alpaca keys
    monkeypatch.setattr('services.options.adapter.get_settings', lambda: __import__('types').SimpleNamespace(enable_alpaca_options=False, apca_api_key_id=None, apca_api_secret_key=None))

    adapters = get_options_adapter()
    assert isinstance(adapters, OptionsDataAdapter)


def test_get_options_adapter_prefers_alpaca_when_enabled(monkeypatch):
    # Ensure fresh singleton
    import services.options.adapter as mod
    mod._adapter = None

    # Create fake settings with Alpaca enabled and keys present
    fake_settings = types.SimpleNamespace(
        enable_alpaca_options=True,
        apca_api_key_id="x",
        apca_api_secret_key="y",
    )

    monkeypatch.setattr('services.options.adapter.get_settings', lambda: fake_settings)

    adapter = get_options_adapter()
    # Adapter should be an instance of the Alpaca options adapter when available
    assert adapter is not None
    # The adapter class name should contain 'Alpaca' or provider 'alpaca' when present
    assert adapter.__class__.__name__.lower().startswith('alpaca')
