"""Auth user linking for employee password reset."""

from __future__ import annotations


def test_list_auth_users_admin_accepts_direct_list_response(monkeypatch):
    from app.db import list_auth_users_admin

    class UserObj:
        id = "auth-1"
        email = "user@industrialplantsolution.com"
        phone = None
        created_at = None

    class FakeAdmin:
        class auth:
            class admin:
                @staticmethod
                def list_users(page=None, per_page=None):
                    return [UserObj()]

    monkeypatch.setattr("app.db.get_admin_client", lambda: FakeAdmin())
    rows = list_auth_users_admin(page=1, per_page=200)
    assert len(rows) == 1
    assert rows[0]["id"] == "auth-1"
    assert rows[0]["email"] == "user@industrialplantsolution.com"


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


def test_resolve_auth_id_from_profile_id_when_auth_email_missing(monkeypatch):
    from app.db import _resolve_auth_id_from_profile_id

    pid = "1d04e3f2-c3de-4783-935b-bd4550acf307"
    email = "chance.burgess@industrialplantsolution.com"

    monkeypatch.setattr(
        "app.db.fetch_by_match_admin",
        lambda table, match, **kwargs: [{"id": pid, "email": email}],
    )
    monkeypatch.setattr(
        "app.db.get_auth_user_by_id_admin",
        lambda uid: {"id": uid, "email": None, "identities": []},
    )

    assert _resolve_auth_id_from_profile_id(pid, email) == pid


def test_auth_user_row_email_reads_identity(monkeypatch):
    from app.db import _auth_user_row_email

    row = {
        "email": None,
        "identities": [{"identity_data": {"email": "user@industrialplantsolution.com"}}],
    }
    assert _auth_user_row_email(row) == "user@industrialplantsolution.com"


def test_set_login_password_admin_recovers_from_database_error(monkeypatch):
    from app.db import set_login_password_admin

    auth_id = "1d04e3f2-c3de-4783-935b-bd4550acf307"
    email = "chance.burgess@industrialplantsolution.com"
    password_calls: list[str] = []
    profile_resolve_calls = {"n": 0}

    def fake_resolve_pid(pid: str, em: str) -> str:
        profile_resolve_calls["n"] += 1
        return auth_id if profile_resolve_calls["n"] > 1 else ""

    monkeypatch.setattr("app.db.resolve_auth_user_id", lambda **k: "")
    monkeypatch.setattr("app.db._find_auth_user_id_by_email", lambda em: "")
    monkeypatch.setattr("app.db._resolve_auth_id_from_profile_id", fake_resolve_pid)
    monkeypatch.setattr("app.db._remove_orphan_profiles_for_email", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.db.create_auth_user",
        lambda **k: (_ for _ in ()).throw(
            RuntimeError(
                f"auth.admin.create_user failed for {email!r}: AuthApiError('Database error creating new user')"
            )
        ),
    )
    monkeypatch.setattr(
        "app.db.get_auth_user_by_id_admin",
        lambda uid: {"id": uid, "email": email},
    )
    monkeypatch.setattr(
        "app.db.set_auth_user_password_admin",
        lambda **k: password_calls.append(k["auth_user_id"]),
    )
    monkeypatch.setattr("app.db._upsert_profile_for_auth", lambda **k: None)
    monkeypatch.setattr("app.db._link_employee_auth_ids", lambda **k: None)

    out = set_login_password_admin(
        email=email,
        password="secret1",
        profile_id=auth_id,
        employee_id="emp-1",
    )
    assert out == auth_id
    assert password_calls == [auth_id]
    assert profile_resolve_calls["n"] >= 2


def test_set_login_password_admin_links_via_profile_id_before_create(monkeypatch):
    from app.db import set_login_password_admin

    auth_id = "1d04e3f2-c3de-4783-935b-bd4550acf307"
    email = "chance.burgess@industrialplantsolution.com"
    created: list[str] = []

    monkeypatch.setattr("app.db.resolve_auth_user_id", lambda **k: "")
    monkeypatch.setattr("app.db._find_auth_user_id_by_email", lambda em: "")
    monkeypatch.setattr(
        "app.db._resolve_auth_id_from_profile_id",
        lambda pid, em: auth_id if pid == auth_id else "",
    )
    monkeypatch.setattr(
        "app.db.get_auth_user_by_id_admin",
        lambda uid: {"id": uid, "email": None, "identities": []},
    )
    monkeypatch.setattr(
        "app.db.set_auth_user_password_admin",
        lambda **k: created.append("pw"),
    )
    monkeypatch.setattr("app.db._upsert_profile_for_auth", lambda **k: None)
    monkeypatch.setattr("app.db._link_employee_auth_ids", lambda **k: None)
    monkeypatch.setattr(
        "app.db.create_auth_user",
        lambda **k: created.append("create") or {"id": "should-not-run"},
    )

    out = set_login_password_admin(
        email=email,
        password="secret1",
        profile_id=auth_id,
        employee_id="emp-1",
    )
    assert out == auth_id
    assert created == ["pw"]


def test_auth_user_id_from_profile_email_when_auth_email_missing(monkeypatch):
    from app.db import _auth_user_id_from_profile_email

    pid = "1d04e3f2-c3de-4783-935b-bd4550acf307"
    email = "chance.burgess@industrialplantsolution.com"

    monkeypatch.setattr(
        "app.db.fetch_by_match_admin",
        lambda table, match, **kwargs: [{"id": pid, "email": email}],
    )
    monkeypatch.setattr(
        "app.db.get_auth_user_by_id_admin",
        lambda uid: {"id": uid, "email": None, "identities": []},
    )

    assert _auth_user_id_from_profile_email(email) == pid


def test_find_auth_user_by_email_http_fallback(monkeypatch):
    from app.db import find_auth_user_by_email_admin

    monkeypatch.setattr("app.db.list_auth_users_admin", lambda **k: [])
    monkeypatch.setattr(
        "app.db._find_auth_user_by_email_http",
        lambda em: {"id": "auth-http", "email": em, "identities": []},
    )

    row = find_auth_user_by_email_admin("user@industrialplantsolution.com")
    assert row is not None
    assert row["id"] == "auth-http"


def test_find_auth_user_by_email_http_uses_filter_first(monkeypatch):
    from app.db import _find_auth_user_by_email_http

    calls: list[dict] = []

    def fake_http_list(**kwargs):
        calls.append(kwargs)
        if kwargs.get("email_filter"):
            return [{"id": "auth-filter", "email": "user@industrialplantsolution.com", "identities": []}]
        return []

    monkeypatch.setattr("app.db._http_list_auth_users_admin", fake_http_list)

    row = _find_auth_user_by_email_http("user@industrialplantsolution.com")
    assert row is not None
    assert row["id"] == "auth-filter"
    assert any(c.get("email_filter") == "user@industrialplantsolution.com" for c in calls)


def test_recover_auth_id_after_create_conflict_uses_http_filter(monkeypatch):
    from app.db import _recover_auth_id_after_create_conflict

    monkeypatch.setattr("app.db._find_auth_user_id_by_email", lambda em: "")
    monkeypatch.setattr(
        "app.db._find_auth_user_by_email_http",
        lambda em: {"id": "auth-recovered", "email": em, "identities": []},
    )

    assert (
        _recover_auth_id_after_create_conflict(
            "chance.burgess@industrialplantsolution.com",
            "1d04e3f2-c3de-4783-935b-bd4550acf307",
        )
        == "auth-recovered"
    )


def test_set_login_password_admin_recovers_via_http_filter_on_create_conflict(monkeypatch):
    from app.db import set_login_password_admin

    auth_id = "auth-recovered-99"
    email = "chance.burgess@industrialplantsolution.com"
    profile_id = "1d04e3f2-c3de-4783-935b-bd4550acf307"
    password_calls: list[str] = []
    recover_calls: list[tuple[str, str]] = []

    def fake_recover(em: str, pid: str = "") -> str:
        recover_calls.append((em, pid))
        return auth_id if len(recover_calls) >= 3 else ""

    monkeypatch.setattr("app.db.resolve_auth_user_id", lambda **k: "")
    monkeypatch.setattr("app.db._find_auth_user_id_by_email", lambda em: "")
    monkeypatch.setattr("app.db._resolve_auth_id_from_profile_id", lambda pid, em: "")
    monkeypatch.setattr("app.db._recover_auth_id_after_create_conflict", fake_recover)
    monkeypatch.setattr("app.db.get_auth_user_by_id_admin", lambda uid: None)
    monkeypatch.setattr("app.db._delete_profile_by_id_admin", lambda pid: None)
    monkeypatch.setattr("app.db._remove_orphan_profiles_for_email", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.db.create_auth_user",
        lambda **k: (_ for _ in ()).throw(
            RuntimeError(
                f"auth.admin.create_user failed for {email!r}: AuthApiError('User already registered')"
            )
        ),
    )
    monkeypatch.setattr(
        "app.db.set_auth_user_password_admin",
        lambda **k: password_calls.append(k["auth_user_id"]),
    )
    monkeypatch.setattr("app.db._upsert_profile_for_auth", lambda **k: None)
    monkeypatch.setattr("app.db._link_employee_auth_ids", lambda **k: None)

    out = set_login_password_admin(
        email=email,
        password="secret1",
        profile_id=profile_id,
        employee_id="emp-1",
    )
    assert out == auth_id
    assert password_calls == [auth_id]


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
