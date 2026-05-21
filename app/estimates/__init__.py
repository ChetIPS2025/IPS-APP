"""Estimating module — modular UI and business logic for estimates / quotes.

Package layout
--------------
queries.py       Read-only DB fetches (cached where safe).
services.py      Session-state management and estimate lifecycle helpers.
calculations.py  Re-exports from app.estimate.calculations.
utils.py         Display formatters and shared helpers.
components.py    Streamlit rendering functions (list, table, cards, totals).
dialogs.py       Import dialogs and action wrappers.
page.py          Top-level render() entry point.
"""
