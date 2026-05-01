from __future__ import annotations

import argparse
from datetime import date


def main() -> int:
    p = argparse.ArgumentParser(description="IPS email notification runner (Resend/SendGrid provider).")
    p.add_argument("--daily", action="store_true", help="Send daily supervisor report summaries + missing reminders.")
    p.add_argument("--weekly", action="store_true", help="Send weekly Friday customer updates (runs only on Friday).")
    p.add_argument("--date", default="", help="Target date for daily sends (YYYY-MM-DD).")
    args = p.parse_args()

    from app.services.email_notifications import (
        run_daily_supervisor_report_emails,
        run_weekly_friday_customer_updates,
    )

    td = None
    if args.date.strip():
        td = date.fromisoformat(args.date.strip())

    if not args.daily and not args.weekly:
        # Default: do both.
        args.daily = True
        args.weekly = True

    if args.daily:
        res = run_daily_supervisor_report_emails(target_date=td)
        print("daily:", res)
    if args.weekly:
        res = run_weekly_friday_customer_updates(friday=td)
        print("weekly:", res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

