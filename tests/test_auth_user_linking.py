"""Auth user linking for employee password reset."""

from __future__ import annotations


def test_find_auth_user_id_by_email_from_list_users(monkeypatch):
    from app.db import _find_auth_user_id_by_email

    monkeypatch.setattr(
        "app.db.find_auth_user_by_email_admin",
        lambda em: {"id": "auth-99", "email": "user@industrialplantsolution.com"},
    )
    monkeypatch.setattr(
        "app.db.get_auth_user_by_id_admin",
        lambda uid: {"id": uid, "email": "user@industrialplantsolution.com"},
    )
    monkeypatch.setattr("app.db._auth_user_id_from_profile_email", lambda em: "")

    assert _find_auth_user_id_by_email("user@industrialplantsolution.com") == "auth-99"


def test_create_auth_user_removes_orphan_profile_before_create(monkeypatch):
    from app.db import create_auth_user

    deleted: list[str] = []

    def fake_fetch(table, match, **kwargs):
        if table == "profiles":
            return [{"id": "orphan-profile", "email": "new@industrialplantsolution.com"}]
        return []

    monkeypatch.setattr("app.db.fetch_by_match_admin", fake_fetch)
    monkeypatch.setattr("app.db.get_auth_user_by_id_admin", lambda uid: None)
    monkeypatch.setattr("app.db._find_auth_user_id_by_email", lambda em: "")
    monkeypatch.setattr(
        "app.db._delete_profile_by_id_admin",
        lambda pid: deleted.append(pid),
    )

    class FakeAdmin:
        class auth:
            class admin:
                @staticmethod
                def create_user(payload):
                    class R:
                        user = {"id": "auth-new", "email": payload["email"]}
                    return R()

        @staticmethod
        def table(name):
            class T:
                @staticmethod
                def insert(_payload):
                    class E:
                        @staticmethod
                        def execute():
                            return None
                    return E()
            return T()

    monkeypatch.setattr("app.db.get_admin_client", lambda: FakeAdmin())
    monkeypatch.setattr("app.db.fetch_one", lambda table, match: None)
    monkeypatch.setattr("app.db.update_rows_admin", lambda *a, **k: None)
    monkeypatch.setattr("app.db.fetch_table_admin", lambda *a, **k: [])
    monkeypatch.setattr("app.db._link_employee_auth_ids", lambda **k: None)

    out = create_auth_user(
        email="new@industrialplantsolution.com",
        password="secret1",
        employee_id="emp-1",
    )
    assert out["id"] == "auth-new"
    assert deleted == ["orphan-profile"]


def test_resolve_employee_auth_login_marks_unlinked(monkeypatch):
    from app.services.users_service import resolve_employee_auth_login

    monkeypatch.setattr(
        "app.services.users_service._employee_row",
        lambda eid: {"id": eid, "email": "user@industrialplantsolution.com"},
    )
    monkeypatch.setattr(
        "app.services.users_service._find_profile_for_employee",
        lambda eid, email="": {"id": "orphan-profile", "email": email},
    )
    monkeypatch.setattr("app.services.users_service.resolve_auth_user_id", lambda **k: "")
    monkeypatch.setattr(
        "app.db._find_auth_user_id_by_email",
        lambda em: "auth-77",
    )

    login = resolve_employee_auth_login("emp-1")
    assert login["auth_unlinked"] is True
    assert login["has_login"] is False
    assert login["auth_user_id"] == "auth-77"
