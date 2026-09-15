"""Next-retrain feature candidates (training side ONLY, not served).

These signals need a retrain to take effect, so they live outside
app/services/feature_engineering.py on purpose: nothing here runs in the
serving path, and the 25-feature production contract is untouched.

Promotion checklist for the next full retrain:
1. Set USE_V3_SIGNALS = True in ml/train.py (wires the columns in).
2. Set RDAP_ENABLED = True below (allows live RDAP during extraction;
   leave False and domain_age_days is a constant -1, i.e. useless).
3. Run the full train, gate the artifact, ship per the backend README.
4. On shipping a 27-feature artifact, promote the names everywhere the
   v2 batch did: append to explainability.FEATURE_NAMES (+ fallback
   weights), bump test count asserts (26 -> 28 keys), extend
   frontend features.js + copy, update docs. Serving older artifacts
   keeps working (prediction slices to n_features_in_).

EXTRA_FEATURE_NAMES are appended AFTER the 25 serving features, so stored
rows stay comparable (same append-only doctrine as v2).
"""

from app.services.feature_engineering import _parts

USE_V3_SIGNALS_DOC = "flag lives in ml/train.py"
RDAP_ENABLED = False

EXTRA_FEATURE_NAMES = ["on_free_host", "domain_age_days"]

# Registrable domains whose subdomains are user-controlled content. An apex
# hit alone (weebly.com itself) is legitimate - only subdomains count.
# Curated 2026-09; revisit from abuse-ch / Public-Suffix-adjacent feeds.
FREE_HOSTS = frozenset({
    "blogspot.com", "blogspot.co.uk", "blogspot.in", "blogger.com",
    "weebly.com", "wixsite.com", "wordpress.com", "tumblr.com",
    "github.io", "gitlab.io", "cloudclusters.net",
    "workers.dev", "pages.dev", "herokuapp.com", "vercel.app",
    "netlify.app", "firebaseapp.com", "web.app", "appspot.com",
    "azurewebsites.net", "000webhostapp.com", "glitch.me", "repl.co",
    "streamlit.app", "pythonanywhere.com", "myshopify.com",
    "bigcartel.com", "jimdo.com", "webnode.com", "000webhost.com",
    "infinityfreeapp.com",
})

# Unknown age sentinel: tree models split on it cleanly, and it can never
# collide with a real age (days >= 0). Documented wherever v3 is trained.
AGE_UNKNOWN = -1


def _registered_domain(url: str) -> str:
    try:
        parts = _parts(url)
    except Exception:
        return ""
    if not parts.domain or not parts.suffix:
        return ""
    return f"{parts.domain}.{parts.suffix}".lower()


def on_free_host(url: str) -> bool:
    """Return whether user-controlled content sits on a free host."""

    if not isinstance(url, str):
        return False
    try:
        subdomain = _parts(url).subdomain
    except Exception:
        return False
    return bool(subdomain) and _registered_domain(url) in FREE_HOSTS


def extract_extra(url: str, rdap_client=None) -> dict[str, int | float]:
    """Extract v3 candidate features (rdap_client None = age unknown)."""

    free = on_free_host(url)
    age = AGE_UNKNOWN
    if rdap_client is not None:
        try:
            resolved = rdap_client.domain_age_days(_registered_domain(url))
        except Exception:
            resolved = None
        if isinstance(resolved, int) and resolved >= 0:
            age = resolved
    return {"on_free_host": free, "domain_age_days": age}
