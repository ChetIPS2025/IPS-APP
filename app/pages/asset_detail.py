def _render_asset_documents_list(
    documents: list,
    *,
    key_prefix: str = "ad_doc",
    show_hint: bool = True,
    mobile_layout: bool = False,
) -> None:
    if not documents:
        st.caption("No documents uploaded yet.")
        return

    if show_hint:
        st.caption("Signed links expire after about one hour — use **Open** again if needed.")

    for i, doc in enumerate(documents):
        did = str(doc.get("id") or i)
        fp = str(doc.get("file_path") or "").strip()
        fn = str(doc.get("file_name") or "").strip() or Path(fp).name or "document"
        dt = str(doc.get("document_type") or "").strip()
        created = str(doc.get("created_at") or "")[:19]
        ctype = str(doc.get("content_type") or "").strip()

        ref = create_signed_url(fp, expires_in=3600) if fp else ""

        meta_bits = [x for x in (dt, created) if x]
        meta = " · ".join(meta_bits) if meta_bits else "—"

        c_icon, c_main, c_act = st.columns([0.55, 3.4, 1.35], gap="small")

        with c_icon:
            st.markdown(
                f'<p style="font-size:1.5rem;margin:0;">📄</p>',
                unsafe_allow_html=True,
            )

        with c_main:
            st.markdown(f"**{html.escape(fn)}**")
            st.caption(meta)

        with c_act:
            if not ref:
                st.caption("Unavailable")
            else:
                if ref.startswith("http"):
                    st.link_button("Open", url=ref)  # ← FIXED (no key)
                else:
                    p = Path(ref)
                    if p.is_file():
                        st.download_button(
                            "Download",
                            data=p.read_bytes(),
                            file_name=fn,
                            mime=ctype or "application/octet-stream",
                        )
                    else:
                        st.caption("Missing file")

        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
