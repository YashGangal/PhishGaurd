"""Pure URL and HTML feature extractors used by the classifier."""

from collections import Counter
import ipaddress
import math
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import tldextract
from bs4 import BeautifulSoup

_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=None)
_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly", "shorturl.at"}
_SUSPICIOUS_TLDS = {"xyz", "top", "tk", "gq", "ml", "cf", "ga", "click", "download", "zip", "work"}
_EVENT_RE = re.compile(r"\bon(?:mouseover|load|click|error|focus|blur)\s*=", re.IGNORECASE)


def _parsed(url: str) -> Any:
    try:
        return urlparse(url)
    except (TypeError, ValueError):
        return urlparse("")


def _parts(url: str) -> Any:
    try:
        return _EXTRACTOR(url)
    except (TypeError, ValueError):
        return _EXTRACTOR("")


def url_length(url: str) -> int:
    return len(url) if isinstance(url, str) else 0


def domain_length(url: str) -> int:
    return len(_parts(url).domain)


def num_dots(url: str) -> int:
    return url.count(".") if isinstance(url, str) else 0


def num_hyphens(url: str) -> int:
    return url.count("-") if isinstance(url, str) else 0


def num_digits(url: str) -> int:
    return len(re.findall(r"[0-9]", url)) if isinstance(url, str) else 0


def num_subdomains(url: str) -> int:
    value = _parts(url).subdomain
    return len(value.split(".")) if value else 0


def has_https(url: str) -> bool:
    return _parsed(url).scheme.lower() == "https"


def has_ip_address(url: str) -> bool:
    hostname = _parsed(url).hostname
    if not hostname:
        return False
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return bool(re.fullmatch(r"(?:0x[0-9a-f]+|0[0-7]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|0[0-7]+|[0-9]+)){3}", hostname, re.IGNORECASE))


def has_at_symbol(url: str) -> bool:
    return "@" in url if isinstance(url, str) else False


def has_double_slash_redirect(url: str) -> bool:
    if not isinstance(url, str):
        return False
    remainder = url.split("://", 1)[1] if "://" in url else url
    return "//" in remainder


def is_shortened_url(url: str) -> bool:
    hostname = (_parsed(url).hostname or "").lower().rstrip(".")
    return hostname in _SHORTENERS


def num_suspicious_chars(url: str) -> int:
    return sum(url.count(char) for char in "@%_=&") if isinstance(url, str) else 0


def url_entropy(url: str) -> float:
    if not isinstance(url, str) or not url:
        return 0.0
    counts = Counter(url)
    length = len(url)
    entropy = -sum((count / length) * math.log2(count / length) for count in counts.values())
    return round(entropy, 2)


def has_suspicious_tld(url: str) -> bool:
    return _parts(url).suffix.lower() in _SUSPICIOUS_TLDS


def path_length(url: str) -> int:
    return len(_parsed(url).path)


def _extract_html_features(html: str, page_url: str) -> dict[str, Any]:
    """Parse HTML once and extract all DOM features from the parsed tree."""

    soup = BeautifulSoup(html, "html.parser")
    own_host = (_parsed(page_url).hostname or "").lower()

    has_iframe = bool(soup.find("iframe"))

    external_links = 0
    for anchor in soup.find_all("a", href=True):
        target = urlparse(urljoin(page_url, str(anchor.get("href", ""))))
        if target.hostname and target.hostname.lower() != own_host:
            external_links += 1

    form_suspicious = False
    for form in soup.find_all("form"):
        action = str(form.get("action", "")).strip()
        if not action:
            form_suspicious = True
            break
        target = urlparse(urljoin(page_url, action))
        if has_ip_address(target.geturl()) or (target.hostname and target.hostname.lower() != own_host):
            form_suspicious = True
            break

    has_javascript_events = bool(_EVENT_RE.search(html))
    has_popup = bool(re.search(r"window\s*\.\s*open\s*\(", html, re.IGNORECASE))

    styles = [str(tag.get("style", "")) for tag in soup.find_all(style=True)]
    has_hidden = any(re.search(r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\D|$)", style, re.IGNORECASE) for style in styles)

    return {
        "has_iframe": has_iframe,
        "num_external_links": external_links,
        "form_action_suspicious": form_suspicious,
        "has_javascript_events": has_javascript_events,
        "has_popup_window": has_popup,
        "has_hidden_elements": has_hidden,
    }


def extract_all(url: str, html: str | None = None, redirect_count_value: int = 0) -> dict[str, int | float | bool]:
    """Extract all 22 features plus the HTML availability flag."""

    available = html is not None
    html_value = html or ""

    features = {
        "url_length": url_length(url),
        "domain_length": domain_length(url),
        "num_dots": num_dots(url),
        "num_hyphens": num_hyphens(url),
        "num_digits": num_digits(url),
        "num_subdomains": num_subdomains(url),
        "has_https": has_https(url),
        "has_ip_address": has_ip_address(url),
        "has_at_symbol": has_at_symbol(url),
        "has_double_slash_redirect": has_double_slash_redirect(url),
        "is_shortened_url": is_shortened_url(url),
        "num_suspicious_chars": num_suspicious_chars(url),
        "url_entropy": url_entropy(url),
        "has_suspicious_tld": has_suspicious_tld(url),
        "path_length": path_length(url),
        "redirect_count": max(0, redirect_count_value),
        "html_features_available": available,
    }

    if available:
        html_features = _extract_html_features(html_value, url)
        features.update(html_features)
    else:
        features.update({
            "has_iframe": False,
            "num_external_links": 0,
            "form_action_suspicious": False,
            "has_javascript_events": False,
            "has_popup_window": False,
            "has_hidden_elements": False,
        })

    return features
