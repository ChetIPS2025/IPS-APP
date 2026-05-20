from pathlib import Path

p = Path(r"c:\IPS APP\app\pages\estimates_list_view.py")
text = p.read_text(encoding="utf-8")

old_header = """    # Header card + actions
    hc1, hc2 = st.columns([5.5, 2.2], gap="small")
    with hc1:
        render_estimates_header_left_html()
    with hc2:
        st.markdown('<div style="height:1.55rem"></motion.div>', unsafe_allow_html=True)
        hb1, hb2, hb3 = st.columns(3, gap="small")
        with hb1:
            export_slot = st.empty()
        with hb2:
            if st.button("Import", key="est_hdr_import", use_container_width=True):
                on_import()
        with hb3:
            if st.button("+ New Estimate", type="primary", use_container_width=True, key="est_hdr_new"):
                on_new_estimate()
                return"""

old_header = old_header.replace("</motion.div>", "</div>")

new_header = """    export_slot = st.empty()

    with st.container(border=True):
        st.markdown('<span class="ips-est-header-anchor"></span>', unsafe_allow_html=True)
        hc1, hc2 = st.columns([4.2, 2.35], gap="medium")
        with hc1:
            render_estimates_header_left_html()
        with hc2:
            st.markdown('<span class="ips-est-hdr-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
            st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)
            _, hb_new = st.columns([1, 1], gap="small")
            with hb_new:
                if st.button("+ New Estimate", type="primary", use_container_width=True, key="est_hdr_new"):
                    on_new_estimate()
                    return"""

if old_header not in text:
  # try without motion fix
    old_header2 = old_header.replace("</motion.div>", "</div>")
    if old_header2 not in text:
        raise SystemExit("header block not found")
    text = text.replace(old_header2, new_header)
else:
    text = text.replace(old_header, new_header)

old_f5 = """        with f5:
            dr1, dr2 = st.columns(2, gap="small")
            with dr1:
                st.date_input(
                    "From",
                    key="est_list_date_from",
                    value=None,
                    label_visibility="collapsed",
                )
            with dr2:
                st.date_input(
                    "To",
                    key="est_list_date_to",
                    value=None,
                    label_visibility="collapsed",
                )"""

new_f5 = """        with f5:
            st.markdown(
                date_range_label_html(
                    st.session_state.get("est_list_date_from"),
                    st.session_state.get("est_list_date_to"),
                ),
                unsafe_allow_html=True,
            )
            dr1, dr2 = st.columns(2, gap="small")
            with dr1:
                st.date_input("From", key="est_list_date_from", value=None, label_visibility="collapsed")
            with dr2:
                st.date_input("To", key="est_list_date_to", value=None, label_visibility="collapsed")"""

if old_f5 in text:
    text = text.replace(old_f5, new_f5)

# table row anchors
text = text.replace(
    'st.markdown(\n                    f\'<span class="ips-est-row-marker{marker}"',
    'st.markdown(\'<span class="ips-est-table-row" aria-hidden="true"></span>\', unsafe_allow_html=True)\n                st.markdown(\n                    f\'<span class="ips-est-row-marker{marker}"',
)
text = text.replace(
    "with rc[0]:\n                st.markdown(",
    "with rc[0]:\n                st.markdown('<span class=\"ips-est-quote-anchor\"></span>', unsafe_allow_html=True)\n                st.markdown(",
    1,
)

# sort headers
text = text.replace(
    "with col:\n                if st.button(lbl, key=f\"est_sort_{scol}\"",
    "with col:\n                st.markdown('<span class=\"ips-est-sort-anchor\"></span>', unsafe_allow_html=True)\n                if st.button(lbl + \" ↕\", key=f\"est_sort_{scol}\"",
)

text = text.replace(
    "with rc[8]:\n                a1, a2 = st.columns(2, gap=\"small\")",
    "with rc[8]:\n                st.markdown('<span class=\"ips-est-act-anchor\"></span>', unsafe_allow_html=True)\n                a1, a2 = st.columns(2, gap=\"small\")",
)

# export label
text = text.replace('                "Export",', '                "⬇ Export",')

# detail header
old_det = """        top_l, top_m, top_r = st.columns([2.4, 2.2, 1.6], gap="medium")
        with top_l:
            st.markdown(
                f'<p class="ips-est-detail-title">{html.escape(qn)}</p>'
                f"{estimate_status_badge_html(status)}"
                f'<p class="ips-est-detail-meta"><strong>{html.escape(title)}</strong><br>'
                f"Customer: {html.escape(cust)}</p>",
                unsafe_allow_html=True,
            )"""

new_det = """        st.markdown(
            f'<div class="ips-est-detail-head"><div>'
            f'<div class="ips-est-detail-id-row">'
            f'<span class="ips-est-detail-title">{html.escape(qn)}</span> '
            f"{estimate_status_badge_html(status)}</div>"
            f'<p class="ips-est-detail-project">{html.escape(title)}</p>'
            f'<p class="ips-est-detail-customer">{html.escape(cust)}</p></div></div>',
            unsafe_allow_html=True,
        )
        top_m, top_r = st.columns([2.4, 2], gap="medium")
        with top_m:
            st.markdown('<div class="ips-est-detail-meta-row">', unsafe_allow_html=True)"""

if old_det in text:
    text = text.replace(old_det, new_det)
    text = text.replace(
        """        with top_m:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(meta_block_html("Estimate Date", _fmt_date(_estimate_date_value(row))), unsafe_allow_html=True)
            with m2:
                st.markdown(meta_block_html("Expiration Date", _fmt_date(_expiration_date_value(row))), unsafe_allow_html=True)
            with m3:
                st.markdown(meta_block_html("Created By", _created_by_label(row)), unsafe_allow_html=True)
        with top_r:""",
        """            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(meta_block_html("Estimate Date", _fmt_date(_estimate_date_value(row))), unsafe_allow_html=True)
            with m2:
                st.markdown(meta_block_html("Expiration Date", _fmt_date(_expiration_date_value(row))), unsafe_allow_html=True)
            with m3:
                st.markdown(meta_block_html("Created By", _created_by_label(row)), unsafe_allow_html=True)
            st.markdown("</motion.div>", unsafe_allow_html=True)
        with top_r:""",
    )
    text = text.replace('st.markdown("</motion.div>", unsafe_allow_html=True)', 'st.markdown("</div>", unsafe_allow_html=True)')

# tabs with icons
text = text.replace(
    '        tabs = st.tabs(\n            [\n                "Overview",\n                "Line Items",\n                "Labor",\n                "Materials",\n                "Equipment",\n                "Attachments",\n                "Notes",\n                "Activity",\n            ]\n        )',
    '        tabs = st.tabs(\n            [\n                "Overview",\n                "Line Items",\n                "Labor",\n                "Materials",\n                "Equipment",\n                "Attachments",\n                "Notes",\n                "Activity",\n            ]\n        )',
)

old_tabs = """        tabs = st.tabs(
            [
                "Overview",
                "Line Items",
                "Labor",
                "Materials",
                "Equipment",
                "Attachments",
                "Notes",
                "Activity",
            ]
        )"""
new_tabs = """        tabs = st.tabs(
            [
                "Overview",
                "Line Items",
                "Labor",
                "Materials",
                "Equipment",
                "Attachments",
                "Notes",
                "Activity",
            ]
        )"""
# icons in tabs - streamlit 1.33 supports emoji in tab names
new_tabs_icons = """        tabs = st.tabs(
            [
                "Overview",
                "Line Items",
                "Labor",
                "Materials",
                "Equipment",
                "Attachments",
                "Notes",
                "Activity",
            ]
        )"""
# Actually use unicode/simple labels from mockup
new_tabs_icons = """        tabs = st.tabs(
            [
                "Overview",
                "Line Items",
                "Labor",
                "Materials",
                "Equipment",
                "Attachments",
                "Notes",
                "Activity",
            ]
        )"""

# detail buttons
text = text.replace(
    'if st.button("Edit", key=f"est_det_edit_{eid}"',
    'if st.button("✎ Edit", key=f"est_det_edit_{eid}"',
)
text = text.replace(
    'if st.button("Send", key=f"est_det_send_{eid}"',
    'if st.button("Send Estimate", key=f"est_det_send_{eid}", type="primary"',
)
text = text.replace(
    'if st.button("⌄", key=f"est_det_collapse_{eid}"',
    'if st.button("▲", key=f"est_det_collapse_{eid}"',
)

# line items header
text = text.replace(
    '    st.markdown("##### Top line items")',
    '    st.markdown(\n        \'<div class="ips-est-line-items-head"><h4>Top Line Items</h4></motion.div>\',\n        unsafe_allow_html=True,\n    )'.replace("<motion.", "<").replace("</motion.", "</"),
)
text = text.replace(
    '        if st.button("View All Line Items", key=f"est_view_all_li_{row.get(\'id\')}", use_container_width=True):',
    '        st.markdown(\'<a class="ips-est-view-all-link" href="#">View All Line Items</a>\', unsafe_allow_html=True)\n        if st.button("View all", key=f"est_view_all_li_{row.get(\'id\')}", label_visibility="collapsed"):',
)

p.write_text(text, encoding="utf-8")
print("patched")
