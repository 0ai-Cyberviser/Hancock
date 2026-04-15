"""Tests for the enhanced hancock_constants module."""

from pathlib import Path
import re

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib
import pytest
import yaml

from hancock_constants import (
    VERSION,
    MODE_DEFAULTS,
    ALL_MODES,
    DEFAULT_RATE_LIMIT,
    RATE_LIMIT_WINDOW_SECONDS,
    MAX_RATE_LIMIT_ENTRIES,
    DEFAULT_PORT,
    HEADER_RATE_LIMIT,
    HEADER_RATE_REMAINING,
    HEADER_RATE_WINDOW,
    HEADER_REQUEST_ID,
    WEBHOOK_SIGNATURE_HEADER,
    WEBHOOK_SIGNATURE_PREFIX,
    require_openai,
    OPENAI_IMPORT_ERROR_MSG,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


class TestVersion:
    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3
        for p in parts:
            assert p.isdigit()


class TestModeDefaults:
    def test_all_modes_have_defaults(self):
        for mode in ALL_MODES:
            assert mode in MODE_DEFAULTS

    def test_defaults_contain_required_keys(self):
        required = {"temperature", "max_tokens", "top_p"}
        for mode, defaults in MODE_DEFAULTS.items():
            assert required.issubset(defaults.keys()), f"{mode} missing keys"

    def test_temperature_range(self):
        for mode, defaults in MODE_DEFAULTS.items():
            assert 0.0 <= defaults["temperature"] <= 1.0, (
                f"{mode} temperature out of range: {defaults['temperature']}"
            )

    def test_max_tokens_positive(self):
        for mode, defaults in MODE_DEFAULTS.items():
            assert defaults["max_tokens"] > 0, f"{mode} max_tokens <= 0"

    def test_code_mode_low_temperature(self):
        assert MODE_DEFAULTS["code"]["temperature"] <= 0.3

    def test_soc_mode_moderate_temperature(self):
        assert MODE_DEFAULTS["soc"]["temperature"] <= 0.5


class TestRateLimits:
    def test_default_rate_limit_positive(self):
        assert DEFAULT_RATE_LIMIT > 0

    def test_window_positive(self):
        assert RATE_LIMIT_WINDOW_SECONDS > 0

    def test_max_entries_positive(self):
        assert MAX_RATE_LIMIT_ENTRIES > 0


class TestHeaders:
    def test_rate_limit_headers_prefixed(self):
        assert HEADER_RATE_LIMIT.startswith("X-RateLimit")
        assert HEADER_RATE_REMAINING.startswith("X-RateLimit")
        assert HEADER_RATE_WINDOW.startswith("X-RateLimit")

    def test_request_id_header(self):
        assert HEADER_REQUEST_ID == "X-Request-ID"


class TestWebhook:
    def test_signature_header(self):
        assert WEBHOOK_SIGNATURE_HEADER == "X-Hancock-Signature"

    def test_signature_prefix(self):
        assert WEBHOOK_SIGNATURE_PREFIX == "sha256="


class TestRequireOpenai:
    def test_raises_on_none(self):
        with pytest.raises(ImportError, match="OpenAI client not installed"):
            require_openai(None)

    def test_no_raise_on_class(self):
        class FakeOpenAI:
            pass
        require_openai(FakeOpenAI)  # should not raise


class TestDefaultPort:
    def test_default_port(self):
        assert DEFAULT_PORT == 5000


class TestReleaseVersionSync:
    def test_runtime_version_matches_source_of_truth(self):
        import hancock_agent

        assert hancock_agent.VERSION == VERSION

    def test_python_package_versions_match_source_of_truth(self):
        pyproject = tomllib.loads(_read_text("pyproject.toml"))
        assert pyproject["project"]["version"] == VERSION

        init_text = _read_text("clients/python/__init__.py")
        match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
        assert match and match.group(1) == VERSION

    def test_openapi_version_matches_source_of_truth(self):
        openapi = yaml.safe_load(_read_text("docs/openapi.yaml"))
        assert openapi["info"]["version"] == VERSION

    @pytest.mark.parametrize(
        "path, expected",
        [
            ("docker-compose.yml", f"com.cyberviser.version={VERSION}"),
            ("deploy/docker/docker-compose.yml", f"com.cyberviser.version={VERSION}"),
            ("deploy/docker/Dockerfile", f'org.opencontainers.image.version="{VERSION}"'),
            ("deploy/kubernetes/hancock-deployment.yaml", f'version: "{VERSION}"'),
            ("deploy/k8s/deployment.yaml", f'app.kubernetes.io/version: "{VERSION}"'),
            ("deploy/helm/Chart.yaml", f'version: "{VERSION}"'),
            ("deploy/helm/Chart.yaml", f'appVersion: "{VERSION}"'),
            ("deploy/helm/hancock/Chart.yaml", f"version: {VERSION}"),
            ("deploy/helm/hancock/Chart.yaml", f'appVersion: "{VERSION}"'),
            ("docs/deployment.md", f"ghcr.io/cyberviser/hancock:v{VERSION}"),
            ("docs/deployment.md", f"--set image.tag=v{VERSION}"),
        ],
    )
    def test_release_surfaces_contain_current_version(self, path, expected):
        assert expected in _read_text(path)
