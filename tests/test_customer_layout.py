"""Layout/source tests for Customers inline Contact Detail."""

from __future__ import annotations

import inspect
import re
import unittest

from app.pages import customers as customers_page


class TestCustomerContactInlineLayout(unittest.TestCase):
    def test_contact_detail_does_not_use_split_html_wrappers(self) -> None:
        source = inspect.getsource(customers_page._render_contact_inline_detail)
        self.assertNotIn("'<div class=\"ips-inline-detail-card\">'", source)
        self.assertNotIn("st.markdown(\"</div>\", unsafe_allow_html=True)", source)

    def test_contact_detail_uses_keyed_container_and_marker(self) -> None:
        source = inspect.getsource(customers_page._render_contact_inline_detail)
        self.assertIn('key=f"inline_contact_detail_{ct_id}"', source)
        self.assertIn("ips-inline-contact-detail-marker", source)

    def test_metadata_grid_does_not_wrap_st_columns_with_split_tags(self) -> None:
        source = inspect.getsource(customers_page._inline_meta_grid)
        self.assertNotIn("st.columns", source)
        self.assertIn("ips-inline-contact-meta-marker", source)
        self.assertIn('key=f"inline_contact_meta_{section_id}"', source)
        self.assertIn("ips-inline-meta-grid-wrap", source)

    def test_header_actions_use_stable_three_column_row(self) -> None:
        source = inspect.getsource(customers_page._render_contact_inline_detail)
        self.assertIn("[8, 1, 1.35]", source)
        self.assertIn("header_content, edit_col, delete_col", source)

    def test_phone_and_mobile_render_before_location_section(self) -> None:
        source = inspect.getsource(customers_page._render_contact_inline_detail)
        phone_idx = source.index('"Phone"')
        location_idx = source.index("inline_contact_location_")
        self.assertLess(phone_idx, location_idx)

    def test_location_section_uses_keyed_container(self) -> None:
        source = inspect.getsource(customers_page._render_contact_inline_detail)
        self.assertIn("ips-inline-contact-location-marker", source)
        self.assertIn('key=f"inline_contact_location_{ct_id}"', source)

    def test_linked_sections_use_separate_wrapper(self) -> None:
        source = inspect.getsource(customers_page._render_contact_inline_detail)
        self.assertIn("ips-inline-contact-links-marker", source)
        self.assertIn("**Linked Jobs**", source)
        self.assertIn("**Linked Estimates**", source)

    def test_location_inline_detail_does_not_use_split_wrappers(self) -> None:
        source = inspect.getsource(customers_page._render_location_inline_detail)
        self.assertNotIn("ips-inline-detail-card", source)
        self.assertIn("ips-inline-location-detail-marker", source)

    def test_css_avoids_absolute_position_and_negative_margins_for_inline_contact(self) -> None:
        from app.styles import inject_customers_module_css

        css = inspect.getsource(inject_customers_module_css)
        block = css[css.index("inline_contact_detail_") : css.index(".ips-locations-table-wrap")]
        self.assertNotIn("position: absolute", block)
        self.assertNotIn("margin-top: -", block)
        self.assertNotIn("transform: translate", block)
        self.assertIn("overflow: visible", block)

    def test_css_includes_responsive_rules(self) -> None:
        from app.styles import inject_customers_module_css

        css = inspect.getsource(inject_customers_module_css)
        self.assertIn("@media (max-width: 1024px)", css)
        self.assertIn("@media (max-width: 768px)", css)

    def test_delete_contact_action_remains_available(self) -> None:
        source = inspect.getsource(customers_page._render_contact_inline_detail)
        self.assertIn("_render_delete_contact_action", source)
        self.assertIn("Delete Contact", inspect.getsource(customers_page._render_delete_contact_action))

    def test_delete_confirm_panel_uses_static_flow(self) -> None:
        from app.styles import inject_customers_module_css

        css = inspect.getsource(inject_customers_module_css)
        self.assertIn(".ips-contact-delete-confirm", css)
        self.assertIn("position: static", css)

    def test_contacts_table_uses_full_width_wrapper(self) -> None:
        from app.components.customer_contacts_table import build_customer_contacts_html_table

        html_out = build_customer_contacts_html_table(
            [
                {
                    "id": "ct-1",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "title": "PM",
                    "location_name": "Plant A",
                    "role_type": "Primary",
                    "email": "jane@example.com",
                    "phone": "555-0100",
                }
            ],
            customer_id="cust-1",
        )
        self.assertIn('class="ips-contacts-table-wrap"', html_out)
        self.assertIn('class="ips-contacts-html-table"', html_out)
        styles = inspect.getsource(__import__("app.styles", fromlist=["inject_customers_module_css"]).inject_customers_module_css)
        self.assertIn("width: 100%", styles)
        self.assertRegex(html_out, re.compile(r">555-0100<"))


if __name__ == "__main__":
    unittest.main()
