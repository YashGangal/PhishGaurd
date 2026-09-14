/* Canonical 22-feature split shared by ScanURL and Report.
   Import from here — do not copy these lists into pages. */
export const URL_FEATURES = [
  'url_length', 'domain_length', 'num_dots', 'num_hyphens', 'num_digits',
  'num_subdomains', 'has_https', 'has_ip_address', 'has_at_symbol',
  'has_double_slash_redirect', 'is_shortened_url', 'num_suspicious_chars',
  'url_entropy', 'has_suspicious_tld', 'path_length',
]
export const HTML_FEATURES = [
  'has_iframe', 'redirect_count', 'num_external_links', 'form_action_suspicious',
  'has_javascript_events', 'has_popup_window', 'has_hidden_elements',
]
