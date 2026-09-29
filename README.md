# Support tickets

A lightweight Streamlit app for creating and managing support tickets. This first MVP replaces the starter demo's random, session-only sample data with a small SQLite-backed workflow.

## Features

- Create tickets with a subject, description, requester, email, priority, and optional assignee.
- Search and filter by text, status, and priority.
- Update status, priority, and assignee.
- Add timestamped internal notes to a ticket.
- View a small dashboard of total, active, urgent, and resolved tickets.
- Keep tickets between local app restarts using SQLite.

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app creates `support_tickets.db` in the working directory on first run. To use a different database file, set `SUPPORT_TICKETS_DB` before starting Streamlit, for example:

```bash
SUPPORT_TICKETS_DB=/path/to/tickets.sqlite3 streamlit run streamlit_app.py
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

## MVP limitations

This version is local-first and has no sign-in, role permissions, email notifications, file attachments, or multi-user database setup. Do not expose it publicly or store sensitive customer data until authentication and a suitable persistent database are added. A local SQLite file may not persist across redeploys on hosted app platforms.
