def test_config_loads():
    from app.core.config import settings
    assert settings is not None
    assert settings.log_level is not None
