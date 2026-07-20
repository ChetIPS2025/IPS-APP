"""Secure customer contact deletion tests."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.customer_permissions import CustomerPermissions
from app.pages import customers as customers_page
from app.services.repository import ServiceResult


def _perms(*, role: str, can_delete: bool) -> CustomerPermissions:
    return CustomerPermissions(
        role=role,
        user_id="user-1",
        user_name="Test User",
        can_create=can_delete,
        can_edit_customer=can_delete,
        can_edit_location=can_delete,
        can_edit_contact=can_delete,
        can_delete=can_delete,
        can_view_documents=can_delete,
    )


class TestContactDeleteValidation(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_admin_and_manager_validation_passes(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-1", "full_name": "Jane Doe"}
        customer = {"id": "cust-1"}
        for role in ("admin", "manager"):
            with self.subTest(role=role):
                perms = _perms(role=role, can_delete=True)
                self.assertIsNone(
                    customers_page._validate_contact_delete(
                        contact,
                        customer=customer,
                        permissions=perms,
                    )
                )

    def test_supervisor_office_employee_denied(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-1"}
        customer = {"id": "cust-1"}
        for role in ("supervisor", "office", "employee"):
            with self.subTest(role=role):
                perms = _perms(role=role, can_delete=False)
                err = customers_page._validate_contact_delete(
                    contact,
                    customer=customer,
                    permissions=perms,
                )
                self.assertEqual(err, "You do not have permission to delete contacts.")

    def test_contact_from_other_customer_rejected(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-other"}
        customer = {"id": "cust-1"}
        perms = _perms(role="admin", can_delete=True)
        err = customers_page._validate_contact_delete(
            contact,
            customer=customer,
            permissions=perms,
        )
        self.assertEqual(err, "You do not have permission to delete contacts.")

    def test_demo_contact_rejected(self) -> None:
        contact = {"id": "demo-ct-1", "customer_id": "cust-1"}
        customer = {"id": "cust-1"}
        perms = _perms(role="admin", can_delete=True)
        err = customers_page._validate_contact_delete(
            contact,
            customer=customer,
            permissions=perms,
        )
        self.assertEqual(err, "Sample contacts cannot be deleted.")


class TestContactDeleteVisibility(unittest.TestCase):
    def test_delete_action_checks_can_delete(self) -> None:
        src = inspect.getsource(customers_page._render_delete_contact_action)
        self.assertIn("permissions.can_delete", src)

    def test_contacts_table_has_no_delete_button(self) -> None:
        from app.components.customer_contacts_table import build_customer_contacts_html_table

        html_table = build_customer_contacts_html_table(
            [{"id": "ct-1", "full_name": "Jane Doe", "title": "Mgr"}],
            customer_id="cust-1",
        )
        self.assertNotIn("Delete Contact", html_table)
        self.assertNotIn("delete", html_table.lower())


class TestContactDeleteConfirmation(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_confirm_key_is_contact_specific(self) -> None:
        self.assertEqual(
            customers_page._contact_delete_confirm_key("ct-42"),
            "ips_delete_contact_confirm_ct-42",
        )

    def test_initial_delete_click_does_not_call_service(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-1", "full_name": "Jane Doe"}
        perms = _perms(role="admin", can_delete=True)
        with patch.object(customers_page, "delete_customer_contact_record") as delete_mock:
            with patch.object(customers_page.st, "button", return_value=True):
                customers_page._render_delete_contact_action(
                    contact,
                    customer={"id": "cust-1"},
                    permissions=perms,
                    inline=True,
                    render="button",
                )
        delete_mock.assert_not_called()
        self.assertTrue(st.session_state[customers_page._contact_delete_confirm_key("ct-1")])

    def test_confirm_panel_shows_contact_name(self) -> None:
        src = inspect.getsource(customers_page._render_contact_delete_confirm_panel)
        self.assertIn("_contact_delete_display_name", src)
        self.assertIn("html.escape", src)

    def test_cancel_clears_confirm_only(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-1", "full_name": "Jane Doe"}
        confirm_key = customers_page._contact_delete_confirm_key("ct-1")
        st.session_state[confirm_key] = True
        st.session_state[customers_page._selected_customer_contact_key("cust-1")] = "ct-1"
        st.session_state[customers_page._show_customer_contact_detail_key("cust-1")] = True
        perms = _perms(role="admin", can_delete=True)
        with patch.object(customers_page, "delete_customer_contact_record") as delete_mock:
            with patch.object(customers_page.st, "button", side_effect=[False, True]):
                with patch.object(customers_page.st, "rerun") as rerun_mock:
                    customers_page._render_contact_delete_confirm_panel(
                        contact,
                        customer={"id": "cust-1"},
                        permissions=perms,
                        inline=True,
                    )
        delete_mock.assert_not_called()
        self.assertNotIn(confirm_key, st.session_state)
        self.assertEqual(st.session_state[customers_page._selected_customer_contact_key("cust-1")], "ct-1")
        rerun_mock.assert_called_once()

    def test_confirm_calls_service_once(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-1", "full_name": "Jane Doe"}
        perms = _perms(role="admin", can_delete=True)
        with patch.object(
            customers_page,
            "delete_customer_contact_record",
            return_value=ServiceResult(ok=True),
        ) as delete_mock:
            with patch.object(customers_page, "invalidate_customers_directory_cache"):
                with patch.object(customers_page, "get_customer_detail", return_value={"id": "cust-1"}):
                    with patch.object(customers_page, "put_customer_in_modal_cache"):
                        with patch.object(customers_page, "ips_app_rerun"):
                            with patch.object(customers_page.st, "success"):
                                customers_page._execute_contact_delete(
                                    contact,
                                    customer={"id": "cust-1"},
                                    permissions=perms,
                                    inline=True,
                                )
        delete_mock.assert_called_once_with("ct-1")


class TestContactDeleteSuccessFlow(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_success_clears_state_and_invalidates_cache(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-1", "full_name": "Jane Doe"}
        st.session_state[customers_page._CONTACTS_CACHE_KEY] = {"ct-1": contact}
        st.session_state[customers_page._selected_customer_contact_key("cust-1")] = "ct-1"
        st.session_state[customers_page._show_customer_contact_detail_key("cust-1")] = True
        st.session_state[customers_page._contact_delete_confirm_key("ct-1")] = True
        st.session_state[customers_page._CUSTOMER_DETAIL_ACTIVE_TAB_KEY] = "Overview"
        st.query_params[customers_page.contact_detail_query_key()] = "ct-1"
        perms = _perms(role="admin", can_delete=True)

        with patch.object(
            customers_page,
            "delete_customer_contact_record",
            return_value=ServiceResult(ok=True),
        ):
            with patch.object(customers_page, "invalidate_customers_directory_cache") as invalidate_mock:
                with patch.object(
                    customers_page,
                    "get_customer_detail",
                    return_value={"id": "cust-1", "contact_count": 0},
                ):
                    with patch.object(customers_page, "put_customer_in_modal_cache") as cache_mock:
                        with patch.object(customers_page, "ips_app_rerun") as rerun_mock:
                            with patch.object(customers_page.st, "success") as success_mock:
                                customers_page._execute_contact_delete(
                                    contact,
                                    customer={"id": "cust-1"},
                                    permissions=perms,
                                    inline=True,
                                )

        invalidate_mock.assert_called_once_with("cust-1")
        cache_mock.assert_called_once()
        self.assertNotIn("ct-1", st.session_state[customers_page._CONTACTS_CACHE_KEY])
        self.assertIsNone(st.session_state[customers_page._selected_customer_contact_key("cust-1")])
        self.assertFalse(st.session_state[customers_page._show_customer_contact_detail_key("cust-1")])
        self.assertNotIn(customers_page._contact_delete_confirm_key("ct-1"), st.session_state)
        self.assertNotIn(customers_page.contact_detail_query_key(), st.query_params)
        self.assertEqual(st.session_state[customers_page._CUSTOMER_DETAIL_ACTIVE_TAB_KEY], "Contacts")
        success_mock.assert_called_once_with("Contact deleted.")
        rerun_mock.assert_called_once()


class TestContactDeleteFailureFlow(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_service_failure_keeps_detail_open(self) -> None:
        contact = {"id": "ct-1", "customer_id": "cust-1", "full_name": "Jane Doe"}
        st.session_state[customers_page._selected_customer_contact_key("cust-1")] = "ct-1"
        st.session_state[customers_page._show_customer_contact_detail_key("cust-1")] = True
        perms = _perms(role="admin", can_delete=True)

        with patch.object(
            customers_page,
            "delete_customer_contact_record",
            return_value=ServiceResult(ok=False, error="db failure"),
        ):
            with patch.object(customers_page, "invalidate_customers_directory_cache") as invalidate_mock:
                with patch.object(customers_page.st, "error") as error_mock:
                    with patch.object(customers_page, "ips_app_rerun") as rerun_mock:
                        customers_page._execute_contact_delete(
                            contact,
                            customer={"id": "cust-1"},
                            permissions=perms,
                            inline=True,
                        )

        invalidate_mock.assert_not_called()
        rerun_mock.assert_not_called()
        error_mock.assert_called_once()
        self.assertEqual(st.session_state[customers_page._selected_customer_contact_key("cust-1")], "ct-1")

    def test_linked_record_error_is_friendly(self) -> None:
        msg = customers_page._contact_delete_feedback(
            ServiceResult(ok=False, error="23503 foreign key violation"),
            success="Contact deleted.",
        )
        self.assertFalse(msg[0])
        self.assertIn("linked to another record", msg[1])


class TestContactDeleteContexts(unittest.TestCase):
    def test_inline_and_modal_use_shared_delete_helper(self) -> None:
        inline_src = inspect.getsource(customers_page._render_contact_inline_detail)
        modal_src = inspect.getsource(customers_page.render_contact_detail_dialog)
        self.assertIn("_render_delete_contact_action", inline_src)
        self.assertIn("_render_delete_contact_action", modal_src)

    def test_modal_success_closes_modal_state(self) -> None:
        contact = {"id": "ct-9", "customer_id": "cust-1", "full_name": "Sam Smith"}
        st.session_state[customers_page.SELECTED_CONTACT_KEY] = "ct-9"
        st.session_state[customers_page.SHOW_CONTACT_MODAL_KEY] = True
        st.session_state[customers_page._CONTACT_MODAL_KEY] = "ct-9"
        st.session_state[customers_page._CONTACTS_CACHE_KEY] = {"ct-9": contact}
        perms = _perms(role="manager", can_delete=True)

        with patch.object(
            customers_page,
            "delete_customer_contact_record",
            return_value=ServiceResult(ok=True),
        ):
            with patch.object(customers_page, "invalidate_customers_directory_cache"):
                with patch.object(customers_page, "clear_record_modal") as clear_modal_mock:
                    with patch.object(customers_page, "ips_app_rerun"):
                        with patch.object(customers_page.st, "success"):
                            customers_page._execute_contact_delete(
                                contact,
                                customer={"id": "cust-1"},
                                permissions=perms,
                                inline=False,
                            )

        self.assertIsNone(st.session_state[customers_page.SELECTED_CONTACT_KEY])
        self.assertFalse(st.session_state[customers_page.SHOW_CONTACT_MODAL_KEY])
        self.assertNotIn("ct-9", st.session_state[customers_page._CONTACTS_CACHE_KEY])
        clear_modal_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
