import pytest
import structlog

from six_hats.observability.logging import configure_logging
from six_hats.security.input_validation import InputError, validate_request
from six_hats.security.redaction import REDACTED, redact_text, redact_value


def test_redacts_keys_and_patterns():
    assert redact_text("key sk-abcdefgh12345") == f"key {REDACTED}"
    assert redact_text("Authorization: Bearer abc.def.ghi123") == f"Authorization: {REDACTED}"
    out = redact_value({"api_key": "x", "nested": {"token": "y", "ok": "fine"}})
    assert out == {"api_key": REDACTED, "nested": {"token": REDACTED, "ok": "fine"}}


def test_logging_redacts(capsys):
    configure_logging("INFO", json=True)
    structlog.get_logger().info("evt", api_key="sk-abcdefgh12345", note="sk-zzzzzzzzzz1")
    err = capsys.readouterr().err
    assert "sk-abcdefgh" not in err and "sk-zzzzzzzz" not in err
    assert REDACTED in err


def test_validate_strips_control_chars():
    assert validate_request("hi\x00 there\x1b", 100) == "hi there"


@pytest.mark.parametrize("bad", ["", "   \n", "\x00\x01"])
def test_validate_rejects_empty(bad):
    with pytest.raises(InputError):
        validate_request(bad, 100)


def test_validate_rejects_too_long():
    with pytest.raises(InputError):
        validate_request("a" * 101, 100)
