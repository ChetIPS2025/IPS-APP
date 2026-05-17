from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

try:
    from app.asset_responsive import inject_asset_workflow_mobile_css
    from app.ui.page_shell import render_page_header
    from app.services.asset_qr import decode_qr_image_bytes, find_asset_id_by_scan
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from asset_responsive import inject_asset_workflow_mobile_css  # type: ignore
    from branding import render_header  # type: ignore
    from services.asset_qr import decode_qr_image_bytes, find_asset_id_by_scan  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

# Camera → full reload with ?qr=…; Streamlit picks it up on next run.
_SCANNER_HTML = """
<div id="ips-qr-reader" style="max-width:420px;margin:0 auto;"></div>
<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
<script>
(function () {
  var el = document.getElementById("ips-qr-reader");
  if (typeof Html5Qrcode === "undefined") {
    el.textContent = "QR camera library failed to load. Use manual entry below.";
    return;
  }
  var h = new Html5Qrcode("ips-qr-reader");
  h.start(
    { facingMode: "environment" },
    { fps: 8, qrbox: { width: 260, height: 260 } },
    function (decodedText) {
      try {
        var u = new URL(window.top.location.href);
        u.searchParams.set("qr", decodedText);
        window.top.location.href = u.toString();
      } catch (e) {
        window.top.location.href =
          window.top.location.pathname + "?qr=" + encodeURIComponent(decodedText);
      }
    },
    function () {}
  ).catch(function () {
    el.textContent = "Camera unavailable. Use manual entry below.";
  });
})();
</script>
"""


def _pop_qr_query_param() -> None:
    try:
        if "qr" in st.query_params:
            del st.query_params["qr"]
    except Exception:
        pass


def _go_to_asset_detail(aid: str) -> None:
    st.session_state["asset_detail_id"] = aid
    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
    _pop_qr_query_param()
    st.rerun()


def render() -> None:
    render_page_header("Asset Scanner", "Scan asset QR codes in the field.")
    inject_asset_workflow_mobile_css()
    qp = st.query_params
    if "qr" in qp:
        raw = qp.get("qr", "")
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        if raw:
            aid = find_asset_id_by_scan(str(raw))
            if aid:
                _go_to_asset_detail(aid)
            else:
                st.error("No asset matched that code. Try again or use Asset Database.")
                _pop_qr_query_param()

    st.markdown("##### Photo scan")
    st.caption(
        "Mobile-friendly: take a picture with your camera or upload a photo of the QR label, then decode. "
        "Allow camera access when your browser asks."
    )
    cam = st.camera_input("Camera", key="asset_scan_photo_input", help="On phones, use the rear camera and hold steady.")
    up = st.file_uploader(
        "Or upload an image",
        type=["png", "jpg", "jpeg", "webp"],
        key="asset_scan_upload_qr",
        accept_multiple_files=False,
    )
    img_bytes: bytes | None = None
    if cam is not None:
        img_bytes = cam.getvalue()
    elif up is not None:
        img_bytes = up.getvalue()

    if st.button(
        "Decode QR and open asset",
        type="primary",
        use_container_width=True,
        key="asset_scan_decode_img",
    ):
        if not img_bytes:
            st.warning("Take a photo or upload an image first.")
        else:
            decoded = decode_qr_image_bytes(img_bytes)
            if not decoded:
                st.error(
                    "No QR code found in that image (or image decoding is unavailable). "
                    "Try better lighting, a closer shot, the live scanner below, or manual entry."
                )
            else:
                aid = find_asset_id_by_scan(decoded)
                if aid:
                    _go_to_asset_detail(aid)
                else:
                    st.error(f"No asset matched the decoded value: {decoded[:200]!r}")

    st.markdown("##### Live camera (browser)")
    components.html(_SCANNER_HTML, height=440, scrolling=False)

    st.markdown("##### Manual entry")
    st.caption("Paste text from an external scanner app (e.g. IPS-AST-0001).")
    manual = st.text_input("QR / asset code", key="asset_scanner_manual", placeholder="IPS-AST-0001")
    if st.button("Open asset", type="primary", use_container_width=True, key="asset_scanner_open"):
        if not manual.strip():
            st.warning("Enter a code first.")
        else:
            aid = find_asset_id_by_scan(manual)
            if aid:
                _go_to_asset_detail(aid)
            else:
                st.error("No asset matched that code.")
