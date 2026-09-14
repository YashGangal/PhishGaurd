"""Unit tests for all 25 feature extractors."""

import pytest

from app.services.feature_engineering import (
    domain_in_top_list, domain_length, extract_all, has_at_symbol, has_auth_keyword,
    has_double_slash_redirect, has_https, has_ip_address, has_suspicious_tld,
    is_shortened_url, keyword_domain_mismatch, num_digits, num_dots,
    num_hyphens, num_subdomains, num_suspicious_chars, path_length, url_entropy, url_length,
)

URL = "https://login.secure-example.xyz/path-123?a=1&b=2"
HTML = '<iframe></iframe><a href="https://external.test">x</a><form action=""></form><div onclick="x()" style="display:none"></div><script>window.open("x")</script>'


@pytest.mark.parametrize("extractor", [url_length, domain_length, num_dots, num_hyphens, num_digits, num_subdomains, has_https, has_ip_address, has_at_symbol, has_double_slash_redirect, is_shortened_url, num_suspicious_chars, url_entropy, has_suspicious_tld, path_length, domain_in_top_list, has_auth_keyword, keyword_domain_mismatch])
def test_url_extractors_return_safe_values(extractor):
    """Each URL extractor handles a normal URL and malformed input."""

    assert extractor(URL) is not None
    assert extractor("") is not None


def test_reputation_and_keyword_signals():
    """Reputation exonerates top domains; brand mismatch flags spoofed lures."""

    assert domain_in_top_list("https://github.com/login") is True
    assert domain_in_top_list("https://evil-bank-login.xyz/auth") is False
    assert has_auth_keyword("https://github.com/login") is True
    assert has_auth_keyword("https://example.com/about") is False
    assert keyword_domain_mismatch("https://evil.com/paypal-login/verify") is True
    assert keyword_domain_mismatch("https://paypal.com/signin") is False
    assert keyword_domain_mismatch("https://github.com/login") is False


def test_html_extractors():
    """Each HTML signal is identified from a parsed document."""

    features = extract_all(URL, HTML)
    assert features["html_features_available"] is True
    assert features["has_iframe"] is True
    assert features["num_external_links"] == 1
    assert features["form_action_suspicious"] is True
    assert features["has_javascript_events"] is True
    assert features["has_popup_window"] is True
    assert features["has_hidden_elements"] is True


def test_extract_all_contains_contract():
    """The aggregate extractor returns all 25 features and availability."""

    result = extract_all(URL, HTML, redirect_count_value=1)
    assert len(result) == 26
    assert result["html_features_available"] is True
    assert result["redirect_count"] == 1
