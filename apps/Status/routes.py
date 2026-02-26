import os
import time
import requests as http_requests
from datetime import datetime, timezone
from flask import render_template_string

from apps.Status import status_bp


# ---------------------------------------------------------------------------
# Health check helpers
# ---------------------------------------------------------------------------

def check_pocketbase():
    api_base = os.getenv('POCKETBASE_API', '')
    url = f"{api_base}/api/health"

    start = time.monotonic()
    try:
        resp = http_requests.get(url, timeout=5)
        elapsed_ms = round((time.monotonic() - start) * 1000)
        operational = resp.status_code == 200
        return {
            'operational': operational,
            'response_time_ms': elapsed_ms,
            'error': None if operational else f"HTTP {resp.status_code}",
        }
    except http_requests.exceptions.Timeout:
        return {'operational': False, 'response_time_ms': None, 'error': 'Timeout after 5s'}
    except http_requests.exceptions.RequestException as exc:
        return {'operational': False, 'response_time_ms': None, 'error': str(exc)}


def check_env_var(var_name):
    return bool(os.getenv(var_name, '').strip())


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

STATUS_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EversAPIs — Status</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background: #f5f5f5;
      color: #1a1a1a;
      min-height: 100vh;
    }

    .banner {
      padding: 40px 24px;
      text-align: center;
      color: #fff;
      background: {{ banner_color }};
    }
    .banner h1 {
      font-size: 1.6rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .banner p {
      margin-top: 6px;
      font-size: 0.875rem;
      opacity: 0.8;
    }

    .container {
      max-width: 640px;
      margin: 40px auto;
      padding: 0 16px;
    }

    .card {
      background: #fff;
      border-radius: 10px;
      border: 1px solid #e5e5e5;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }

    .card-header {
      padding: 14px 20px;
      border-bottom: 1px solid #e5e5e5;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #999;
    }

    .service-row {
      display: flex;
      align-items: center;
      padding: 15px 20px;
      border-bottom: 1px solid #f2f2f2;
      gap: 12px;
    }
    .service-row:last-child { border-bottom: none; }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .dot-green  { background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,0.15); }
    .dot-red    { background: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.15); }
    .dot-yellow { background: #f59e0b; box-shadow: 0 0 0 3px rgba(245,158,11,0.15); }

    .service-name {
      flex: 1;
      font-size: 0.925rem;
      font-weight: 500;
    }

    .service-meta {
      font-size: 0.775rem;
      color: #bbb;
      font-variant-numeric: tabular-nums;
    }

    .service-status {
      font-size: 0.775rem;
      font-weight: 600;
      min-width: 80px;
      text-align: right;
    }
    .status-ok       { color: #16a34a; }
    .status-degraded { color: #d97706; }
    .status-down     { color: #dc2626; }

    .footer {
      text-align: center;
      margin: 24px 0 48px;
      font-size: 0.75rem;
      color: #bbb;
    }
  </style>
</head>
<body>

  <div class="banner">
    <h1>{{ banner_text }}</h1>
    <p>EversAPIs Infrastructure</p>
  </div>

  <div class="container">
    <div class="card">
      <div class="card-header">Services</div>

      {% for svc in services %}
      <div class="service-row">
        <span class="dot dot-{{ svc.dot }}"></span>
        <span class="service-name">{{ svc.name }}</span>
        {% if svc.response_time_ms is not none %}
          <span class="service-meta">{{ svc.response_time_ms }}ms</span>
        {% endif %}
        <span class="service-status status-{{ svc.css_status }}">{{ svc.label }}</span>
      </div>
      {% endfor %}

    </div>

    <div class="footer">Last checked {{ checked_at }} UTC</div>
  </div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@status_bp.route('/status', methods=['GET'])
def status_page():
    pb = check_pocketbase()
    deepseek_ok = check_env_var('DEEPSEEK_API_KEY')
    google_ok = check_env_var('GOOGLE_APPLICATION_CREDENTIALS_BASE64')
    resend_ok = check_env_var('RESEND_API')

    def build_service(name, operational, response_time_ms=None):
        if operational:
            return {
                'name': name,
                'dot': 'green',
                'css_status': 'ok',
                'label': 'Operational',
                'response_time_ms': response_time_ms,
            }
        return {
            'name': name,
            'dot': 'red',
            'css_status': 'down',
            'label': 'Unavailable',
            'response_time_ms': response_time_ms,
        }

    services = [
        build_service('PocketBase (Database)', pb['operational'], pb['response_time_ms']),
        build_service('DeepSeek (AI)', deepseek_ok),
        build_service('Google Text-to-Speech', google_ok),
        build_service('Resend (Email)', resend_ok),
    ]

    all_operational = all(s['dot'] == 'green' for s in services)
    banner_text = 'All Systems Operational' if all_operational else 'Degraded Performance'
    banner_color = '#16a34a' if all_operational else '#d97706'
    checked_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    html = render_template_string(
        STATUS_PAGE_HTML,
        services=services,
        banner_text=banner_text,
        banner_color=banner_color,
        checked_at=checked_at,
    )

    return html, 200 if all_operational else 503, {'Content-Type': 'text/html'}
