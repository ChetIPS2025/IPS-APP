"""Patch Streamlit so PWA assets are served at ``/static/*`` with correct MIME types.

**Tornado (default ``server.useStarlette``):** In production, Streamlit registers a
catch-all ``StaticFileHandler`` with ``default_filename=index.html``, so
``GET /static/sw.js`` returns HTML. This module inserts explicit Tornado routes for the
known files under ``app/static/`` immediately before that catch-all block.

**Starlette** (``server.useStarlette=true``): The root static mount uses SPA fallback;
we register ``static/{path:path}`` routes before the ``static-assets`` mount.

Call :func:`install` from ``run_app.py`` **before** importing ``streamlit.web.cli`` so
patches apply before the HTTP server is constructed.
"""

from __future__ import annotations

import os
import sys
import threading
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

_STARLETTE_PATCH_ATTR = "_ips_pwa_starlette_route_patch_installed"
_TORNADO_PATCH_ATTR = "_ips_pwa_tornado_route_patch_installed"

_tls = threading.local()

_ALLOWED_FILES: Final[frozenset[str]] = frozenset(
    ("sw.js", "manifest.json", "icon-192.png", "icon-512.png")
)

_MEDIA_TYPES: Final[dict[str, str]] = {
    "sw.js": "application/javascript",
    "manifest.json": "application/manifest+json",
    "icon-192.png": "image/png",
    "icon-512.png": "image/png",
}

_ROUTE_TEMPLATE: Final[str] = "static/{path:path}"

_PWA_STATIC_URL_RE: Final[str] = r"static/(?P<pwa_name>sw\.js|manifest\.json|icon-192\.png|icon-512\.png)"


def _pwa_tornado_route_tuple(main_script_path: str, base: str | None) -> tuple[Any, ...]:
    import tornado.web

    from streamlit import file_util
    from streamlit.path_security import is_unsafe_path_pattern
    from streamlit.web.server.app_static_file_handler import MAX_APP_STATIC_FILE_SIZE
    from streamlit.web.server.server_util import make_url_path_regex

    root = file_util.get_app_static_dir(main_script_path)

    class IpsPwaTornadoHandler(tornado.web.RequestHandler):
        def initialize(self, root: str) -> None:
            self._root = os.path.abspath(os.path.realpath(root))

        def set_default_headers(self) -> None:
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("X-Content-Type-Options", "nosniff")

        def get(self, pwa_name: str) -> None:
            if pwa_name not in _ALLOWED_FILES:
                raise tornado.web.HTTPError(404)
            if is_unsafe_path_pattern(pwa_name):
                raise tornado.web.HTTPError(400)

            full = os.path.abspath(os.path.join(self._root, pwa_name))
            if os.path.commonpath([full, self._root]) != self._root:
                raise tornado.web.HTTPError(404)
            if not os.path.isfile(full):
                raise tornado.web.HTTPError(404)
            if os.path.getsize(full) > MAX_APP_STATIC_FILE_SIZE:
                raise tornado.web.HTTPError(404)

            self.set_header("Content-Type", _MEDIA_TYPES[pwa_name])
            if pwa_name == "sw.js":
                self.set_header("Service-Worker-Allowed", "/")
                self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
            elif pwa_name == "manifest.json":
                self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
            with open(full, "rb") as f:
                self.write(f.read())

        def options(self, pwa_name: str) -> None:  # noqa: ARG002
            self.set_status(204)
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.set_header("Access-Control-Allow-Headers", "Content-Type")

    return (
        make_url_path_regex(base, _PWA_STATIC_URL_RE),
        IpsPwaTornadoHandler,
        {"root": root},
    )


def _is_streamlit_production_static_tail(handlers: list[Any]) -> bool:
    from streamlit.web.server.routes import AddSlashHandler, RemoveSlashHandler, StaticFileHandler

    if len(handlers) < 3:
        return False
    return (
        handlers[-3][1] is RemoveSlashHandler
        and handlers[-2][1] is StaticFileHandler
        and handlers[-1][1] is AddSlashHandler
    )


def _inject_pwa_into_tornado_handlers(handlers: list[Any] | None, main_script_path: str) -> list[Any] | None:
    if not handlers:
        return handlers

    from streamlit import config

    base = config.get_option("server.baseUrlPath")
    pwa_tuple = _pwa_tornado_route_tuple(main_script_path, base)
    out = list(handlers)

    if _is_streamlit_production_static_tail(out):
        idx = len(out) - 3
        out[idx:idx] = [pwa_tuple]
        return out

    if config.get_option("global.developmentMode"):
        out.append(pwa_tuple)
    return out


def _install_tornado() -> None:
    import tornado.web

    from streamlit.web.server import server as server_mod

    if getattr(tornado.web.Application, _TORNADO_PATCH_ATTR, False):
        return

    _orig_app_init = tornado.web.Application.__init__

    def _patched_application_init(
        self: Any,
        handlers: list[Any] | None = None,
        default_host: str | None = None,
        transforms: Any = None,
        **settings: Any,
    ) -> None:
        srv = getattr(_tls, "server", None)
        if srv is not None and handlers is not None:
            handlers = _inject_pwa_into_tornado_handlers(list(handlers), srv.main_script_path)
        _orig_app_init(self, handlers, default_host=default_host, transforms=transforms, **settings)

    _orig_server_create_app = getattr(server_mod.Server, "_create_app", None)
    if _orig_server_create_app is None:
        return

    def _patched_server_create_app(self: Any) -> Any:
        _tls.server = self
        try:
            return _orig_server_create_app(self)
        finally:
            if hasattr(_tls, "server"):
                delattr(_tls, "server")

    tornado.web.Application.__init__ = _patched_application_init
    server_mod.Server._create_app = _patched_server_create_app
    setattr(tornado.web.Application, _TORNADO_PATCH_ATTR, True)


def _create_pwa_static_routes(main_script_path: str | None, base_url: str | None) -> list:
    from anyio import Path as AsyncPath
    from starlette.exceptions import HTTPException
    from starlette.responses import FileResponse, Response
    from starlette.routing import Route

    from streamlit import file_util
    from streamlit.web.server.app_static_file_handler import MAX_APP_STATIC_FILE_SIZE
    from streamlit.web.server.component_file_utils import build_safe_abspath
    from streamlit.web.server.starlette.starlette_routes import _with_base

    app_static_root = (
        os.path.realpath(file_util.get_app_static_dir(main_script_path))
        if main_script_path
        else None
    )

    async def _pwa_static_get(request: Request) -> Response:
        if not app_static_root:
            raise HTTPException(status_code=404, detail="File not found")

        name = request.path_params.get("path", "")
        if name not in _ALLOWED_FILES:
            raise HTTPException(status_code=404, detail="File not found")

        safe_path = build_safe_abspath(app_static_root, name)
        if safe_path is None:
            raise HTTPException(status_code=400, detail="Bad Request")

        async_path = AsyncPath(safe_path)
        if not await async_path.exists() or await async_path.is_dir():
            raise HTTPException(status_code=404, detail="File not found")

        file_stat = await async_path.stat()
        if file_stat.st_size > MAX_APP_STATIC_FILE_SIZE:
            raise HTTPException(status_code=404, detail="File is too large")

        media_type = _MEDIA_TYPES.get(name, "application/octet-stream")
        response = FileResponse(safe_path, media_type=media_type)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if name == "sw.js":
            response.headers["Service-Worker-Allowed"] = "/"
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        elif name == "manifest.json":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    async def _pwa_static_options(_request: Request) -> Response:
        response = Response(status_code=204)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    path = _with_base(_ROUTE_TEMPLATE, base_url)
    return [
        Route(path, _pwa_static_get, methods=["GET"]),
        Route(path, _pwa_static_options, methods=["OPTIONS"]),
    ]


def _patched_create_streamlit_routes(runtime: Any) -> list:
    from starlette.routing import Mount

    from streamlit import config
    from streamlit.web.server.starlette import starlette_app as sa

    routes = sa._ips_pwa_static_orig_create_streamlit_routes(runtime)
    base_url = config.get_option("server.baseUrlPath")
    main_script_path = getattr(runtime, "_main_script_path", None)
    pwa_routes = _create_pwa_static_routes(main_script_path, base_url)

    if routes and isinstance(routes[-1], Mount) and getattr(routes[-1], "name", None) == "static-assets":
        return routes[:-1] + pwa_routes + routes[-1:]
    return routes + pwa_routes


def _install_starlette() -> None:
    from streamlit.web.server.starlette import starlette_app as sa

    if getattr(sa, _STARLETTE_PATCH_ATTR, False):
        return
    setattr(sa, _STARLETTE_PATCH_ATTR, True)
    sa._ips_pwa_static_orig_create_streamlit_routes = sa.create_streamlit_routes
    sa.create_streamlit_routes = _patched_create_streamlit_routes


def install() -> None:
    # Optional compatibility patch. Streamlit internals change across versions,
    # so do not let PWA static routing prevent the app from starting.
    try:
        _install_tornado()
    except Exception as exc:
        print(f"Warning: skipped Streamlit Tornado PWA patch: {exc}", file=sys.stderr)
    try:
        _install_starlette()
    except Exception as exc:
        print(f"Warning: skipped Streamlit Starlette PWA patch: {exc}", file=sys.stderr)
