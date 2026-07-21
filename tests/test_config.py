"""Тесты чтения конфигурации из окружения."""

from __future__ import annotations

import pytest

from bot.config import (
    BotMode,
    Config,
    ConfigError,
    parse_admin_ids,
    parse_mode,
    parse_port,
    validate_secret,
    webhook_from_env,
)

# Все переменные, которые читает конфигурация; чистим их перед каждым тестом,
# чтобы окружение разработчика не влияло на результат.
ENV_KEYS = (
    "BOT_TOKEN",
    "BOT_MODE",
    "LOG_LEVEL",
    "ADMIN_IDS",
    "WEBHOOK_URL",
    "WEBHOOK_HOST",
    "WEBHOOK_PORT",
    "WEBHOOK_PATH",
    "WEBHOOK_SECRET",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Убирает переменные бота из окружения и отключает чтение `.env`."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("bot.config.load_dotenv", lambda *a, **kw: False)


class TestParseMode:
    """Разбор BOT_MODE."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("polling", BotMode.POLLING),
            ("webhook", BotMode.WEBHOOK),
            ("  WEBHOOK  ", BotMode.WEBHOOK),
        ],
    )
    def test_valid(self, raw: str, expected: BotMode) -> None:
        assert parse_mode(raw) is expected

    def test_unknown_mode_is_rejected(self) -> None:
        with pytest.raises(ConfigError, match="Неизвестный BOT_MODE"):
            parse_mode("longpoll")


class TestParsePort:
    """Разбор WEBHOOK_PORT."""

    def test_valid(self) -> None:
        assert parse_port("9000") == 9000

    @pytest.mark.parametrize("raw", ["abc", "", "8080.5"])
    def test_not_a_number(self, raw: str) -> None:
        with pytest.raises(ConfigError, match="должен быть числом"):
            parse_port(raw)

    @pytest.mark.parametrize("raw", ["0", "65536", "-1"])
    def test_out_of_range(self, raw: str) -> None:
        with pytest.raises(ConfigError, match="вне допустимого диапазона"):
            parse_port(raw)


class TestValidateSecret:
    """Проверка WEBHOOK_SECRET по требованиям MAX."""

    def test_empty_is_allowed(self) -> None:
        assert validate_secret("") is None

    @pytest.mark.parametrize("secret", ["s3cret", "a" * 256, "with-dash-123"])
    def test_valid(self, secret: str) -> None:
        assert validate_secret(secret) == secret

    @pytest.mark.parametrize("secret", ["abcd", "a" * 257])
    def test_wrong_length(self, secret: str) -> None:
        with pytest.raises(ConfigError, match="длиной от"):
            validate_secret(secret)

    @pytest.mark.parametrize("secret", ["секрет", "with space", "under_score", "sym!bol"])
    def test_forbidden_characters(self, secret: str) -> None:
        with pytest.raises(ConfigError, match="латиницу, цифры и дефис"):
            validate_secret(secret)


class TestWebhookFromEnv:
    """Сборка настроек webhook."""

    def test_requires_url(self) -> None:
        with pytest.raises(ConfigError, match="WEBHOOK_URL"):
            webhook_from_env()

    @pytest.mark.parametrize("url", ["http://example.com/hook", "example.com/hook", "/hook"])
    def test_rejects_non_https(self, url: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEBHOOK_URL", url)

        with pytest.raises(ConfigError, match="HTTPS"):
            webhook_from_env()

    def test_path_is_derived_from_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com/max/hook")

        config = webhook_from_env()

        assert config.path == "/max/hook"
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.secret is None

    def test_root_path_when_url_has_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com")

        assert webhook_from_env().path == "/"

    def test_explicit_path_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com/max/hook")
        monkeypatch.setenv("WEBHOOK_PATH", "hook")

        assert webhook_from_env().path == "/hook"

    def test_full_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com/hook")
        monkeypatch.setenv("WEBHOOK_HOST", "127.0.0.1")
        monkeypatch.setenv("WEBHOOK_PORT", "9443")
        monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")

        config = webhook_from_env()

        assert (config.host, config.port, config.secret) == ("127.0.0.1", 9443, "s3cret")


class TestConfigFromEnv:
    """Сборка конфигурации целиком."""

    def test_requires_token(self) -> None:
        with pytest.raises(ConfigError, match="BOT_TOKEN"):
            Config.from_env()

    def test_defaults_to_polling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BOT_TOKEN", "token")

        config = Config.from_env()

        assert config.mode is BotMode.POLLING
        assert config.webhook is None
        assert config.log_level == "INFO"
        assert config.admin_ids == frozenset()

    def test_polling_ignores_webhook_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BOT_TOKEN", "token")
        monkeypatch.setenv("BOT_MODE", "polling")
        monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com/hook")

        assert Config.from_env().webhook is None

    def test_webhook_mode_is_assembled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BOT_TOKEN", "token")
        monkeypatch.setenv("BOT_MODE", "webhook")
        monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com/hook")
        monkeypatch.setenv("LOG_LEVEL", "debug")
        monkeypatch.setenv("ADMIN_IDS", "1,2")

        config = Config.from_env()

        assert config.mode is BotMode.WEBHOOK
        assert config.webhook is not None
        assert config.webhook.url == "https://bot.example.com/hook"
        assert config.log_level == "DEBUG"
        assert config.admin_ids == frozenset({1, 2})

    def test_webhook_mode_without_url_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BOT_TOKEN", "token")
        monkeypatch.setenv("BOT_MODE", "webhook")

        with pytest.raises(ConfigError, match="WEBHOOK_URL"):
            Config.from_env()

    def test_config_is_immutable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BOT_TOKEN", "token")
        config = Config.from_env()

        with pytest.raises(AttributeError):
            config.bot_token = "another"  # type: ignore[misc]


class TestParseAdminIds:
    """Разбор ADMIN_IDS."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("", frozenset()),
            ("1", frozenset({1})),
            (" 1 , 2 ,, 3 ", frozenset({1, 2, 3})),
            ("1,abc,2", frozenset({1, 2})),
        ],
    )
    def test_parsing(self, raw: str, expected: frozenset[int]) -> None:
        assert parse_admin_ids(raw) == expected
