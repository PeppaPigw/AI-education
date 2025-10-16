import pytest
import tools.language_handler as lh


@pytest.fixture
def temp_config_path(tmp_path, monkeypatch):
    config = tmp_path / "user_config.json"
    monkeypatch.setattr(lh, "CONFIG_PATH", str(config))
    return config
