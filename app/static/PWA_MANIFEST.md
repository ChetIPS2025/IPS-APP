# PWA manifest

The web app manifest is **not** edited by hand in production.

| Delivery | Source |
|----------|--------|
| In-app install (primary) | `app/pwa.py` → `inject_pwa_support()` injects a blob from `build_web_manifest()` |
| `GET …/manifest.json` (PWA static patch) | `app/streamlit_pwa_static_patch.py` → `manifest_json_bytes()` |
| Streamlit static file (optional) | `app/static/manifest.json` — sync only; may be stale if not regenerated |

`build_web_manifest()` sets `id`, `start_url`, `scope`, and icon URLs from `APP_VERSION` / `IPS_APP_VERSION` and `server.baseUrlPath`.

Regenerate the on-disk fallback after version or base-path changes:

```powershell
python scripts/sync_pwa_manifest.py
```

Do not commit real secrets; this folder only holds public PWA assets.
