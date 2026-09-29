"""A lightweight, local-first support ticket tracker."""

import streamlit as st

from ticket_store import (
    PRIORITIES,
    STATUSES,
    add_comment,
    create_ticket,
    init_db,
    list_comments,
    list_tickets,
    update_ticket,
)

st.set_page_config(page_title="Support tickets", page_icon="🎫", layout="wide")
init_db()

st.title("🎫 Support tickets")
st.caption("A small ticket tracker with local SQLite storage. No demo tickets are preloaded.")

all_tickets = list_tickets()
active = [ticket for ticket in all_tickets if ticket["status"] not in ("Resolved", "Closed")]
urgent = [ticket for ticket in active if ticket["priority"] == "Urgent"]
resolved = [ticket for ticket in all_tickets if ticket["status"] == "Resolved"]

metric_cols = st.columns(4)
metric_cols[0].metric("Total tickets", len(all_tickets))
metric_cols[1].metric("Active", len(active))
metric_cols[2].metric("Urgent active", len(urgent))
metric_cols[3].metric("Resolved", len(resolved))

home_tab, create_tab, tickets_tab = st.tabs(["Overview", "Create ticket", "Tickets"])

with home_tab:
    st.subheader("Recent tickets")
    if not all_tickets:
        st.info("No tickets yet. Create one to start tracking requests.")
    else:
        recent = all_tickets[:8]
        st.dataframe(
            [
                {
                    "ID": f"#{ticket['id']}",
                    "Subject": ticket["title"],
                    "Requester": ticket["requester"] or "—",
                    "Priority": ticket["priority"],
                    "Status": ticket["status"],
                    "Assignee": ticket["assigned_to"] or "Unassigned",
                    "Updated (UTC)": ticket["updated_at"],
                }
                for ticket in recent
            ],
            hide_index=True,
            use_container_width=True,
        )

with create_tab:
    st.subheader("Create a ticket")
    with st.form("create_ticket_form", clear_on_submit=True):
        title = st.text_input("Subject *", max_chars=160)
        requester_col, email_col = st.columns(2)
        requester = requester_col.text_input("Requester")
        requester_email = email_col.text_input("Requester email", placeholder="name@example.com")
        priority_col, assignee_col = st.columns(2)
        priority = priority_col.selectbox("Priority", PRIORITIES, index=1)
        assigned_to = assignee_col.text_input("Assign to (optional)")
        description = st.text_area("Description *", height=140)
        submitted = st.form_submit_button("Create ticket", type="primary")

    if submitted:
        try:
            ticket_id = create_ticket(
                title=title,
                description=description,
                requester=requester,
                requester_email=requester_email,
                priority=priority,
                assigned_to=assigned_to,
            )
            st.success(f"Ticket #{ticket_id} created.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

with tickets_tab:
    st.subheader("Find and manage tickets")
    filter_cols = st.columns([2, 1, 1])
    search = filter_cols[0].text_input("Search", placeholder="Subject, requester, or details")
    status_filter = filter_cols[1].selectbox("Status", ["All"] + list(STATUSES))
    priority_filter = filter_cols[2].selectbox("Priority", ["All"] + list(PRIORITIES))

    filtered_tickets = list_tickets(
        status=None if status_filter == "All" else status_filter,
        priority=None if priority_filter == "All" else priority_filter,
        search=search,
    )
    st.caption(f"{len(filtered_tickets)} ticket(s)")
    if not filtered_tickets:
        st.info("No matching tickets.")
    else:
        st.dataframe(
            [
                {
                    "ID": f"#{ticket['id']}",
                    "Subject": ticket["title"],
                    "Requester": ticket["requester"] or "—",
                    "Priority": ticket["priority"],
                    "Status": ticket["status"],
                    "Assignee": ticket["assigned_to"] or "Unassigned",
                    "Created (UTC)": ticket["created_at"],
                }
                for ticket in filtered_tickets
            ],
            hide_index=True,
            use_container_width=True,
        )

        ticket_by_id = {int(ticket["id"]): ticket for ticket in filtered_tickets}
        selected_id = st.selectbox(
            "Open ticket",
            list(ticket_by_id),
            format_func=lambda ticket_id: (
                f"#{ticket_id} — {ticket_by_id[ticket_id]['title']}"
            ),
        )
        ticket = ticket_by_id[selected_id]
        st.divider()
        st.markdown(f"### #{ticket['id']} · {ticket['title']}")
        st.write(ticket["description"])
        st.caption(
            f"Requester: {ticket['requester'] or '—'} · "
            f"Email: {ticket['requester_email'] or '—'} · "
            f"Created: {ticket['created_at']} UTC"
        )

        with st.form(f"update_ticket_{selected_id}"):
            update_cols = st.columns(3)
            new_status = update_cols[0].selectbox(
                "Status",
                STATUSES,
                index=STATUSES.index(ticket["status"]),
                key=f"status_{selected_id}",
            )
            new_priority = update_cols[1].selectbox(
                "Priority",
                PRIORITIES,
                index=PRIORITIES.index(ticket["priority"]),
                key=f"priority_{selected_id}",
            )
            new_assignee = update_cols[2].text_input(
                "Assignee",
                value=str(ticket["assigned_to"]),
                key=f"assignee_{selected_id}",
            )
            update_submitted = st.form_submit_button("Save changes")
        if update_submitted:
            update_ticket(selected_id, new_status, new_priority, new_assignee)
            st.success("Ticket updated.")
            st.rerun()

        st.markdown("#### Internal notes")
        comments = list_comments(selected_id)
        if comments:
            for comment in comments:
                st.markdown(f"**{comment['author']}** · {comment['created_at']} UTC")
                st.write(comment["body"])
        else:
            st.caption("No notes yet.")
        with st.form(f"add_comment_{selected_id}", clear_on_submit=True):
            comment_author = st.text_input("Your name", value="Support team")
            comment_body = st.text_area("Add an internal note")
            comment_submitted = st.form_submit_button("Add note")
        if comment_submitted:
            try:
                add_comment(selected_id, comment_author, comment_body)
                st.success("Internal note added.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
