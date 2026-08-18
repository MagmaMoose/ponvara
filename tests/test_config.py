from ponvara.config import Config


def test_config_defaults_and_env(monkeypatch):
    monkeypatch.setenv("DTRACK_API_KEY", "k")
    monkeypatch.setenv("DEFECTDOJO_TOKEN", "t")
    c = Config()
    assert c.dtrack_api_key == "k"
    assert c.defectdojo_token == "t"
    assert c.dd_product_type == "Dependency-Track"
    assert "dependency-track-api-server" in c.dtrack_api_url
    assert c.verify_ssl is True


def test_config_reads_urls_from_env(monkeypatch):
    monkeypatch.setenv("DTRACK_API_KEY", "k")
    monkeypatch.setenv("DEFECTDOJO_TOKEN", "t")
    monkeypatch.setenv("DEFECTDOJO_URL", "https://dd.example.com")
    assert Config().defectdojo_url == "https://dd.example.com"
