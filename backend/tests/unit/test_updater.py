from backend.app.services.updater import UpdaterService


def test_semantic_versions_are_compared_numerically() -> None:
    assert UpdaterService._parse_version("1.10.0") > UpdaterService._parse_version("1.9.9")
