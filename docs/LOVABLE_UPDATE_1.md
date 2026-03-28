# Lovable Update: Add Compliance Action Tracker

Copy everything below into Lovable as an update to the existing app:

---

## New API Endpoints Available

```
GET  /api/v1/compliance/score          — compliance score (0-100)
GET  /api/v1/compliance/actions        — list of action items with resolution options
PUT  /api/v1/compliance/actions/{id}   — update an action item
POST /api/v1/compliance/scan           — re-scan documents and generate new items
GET  /api/v1/compliance/completeness?framework=iso_9001  — what's required vs what exists
GET  /api/v1/compliance/frameworks     — available frameworks (ISO 9001, IMMEX, REPSE)
```

All requests need header: `X-Api-Key: dev-key-1`
Base URL: `https://kompler-production.up.railway.app`

## Changes to Dashboard

Replace the current compliance score calculation with the real API score:

Fetch `GET /api/v1/compliance/score` which returns:
```json
{
  "score": 82,
  "total_items": 12,
  "open_items": 4,
  "resolved_items": 8,
  "by_severity": {"critical": 0, "warning": 2, "info": 2},
  "resolution_rate": 66.7,
  "status": "good"
}
```

Use `score` for the circular gauge. Use `status` for the label below it (excellent/good/needs_attention/critical). Show `open_items` count as a badge on the "Action Items" nav link.

## New Page: Action Items (route: /actions)

This is the core of the product — a compliance todo list. Add "Action Items" to the sidebar navigation between "Documents" and "Upload", with a shield or clipboard icon. Show a badge with the number of open items from the score endpoint.

### Page Layout:

**Top bar:**
- Title: "Compliance Action Items"
- Compliance score gauge on the right (small version)
- "Scan Now" button that calls `POST /api/v1/compliance/scan` and refreshes the list
- Filter tabs: All | Critical | Warnings | Open | Resolved

**Action items list:**
Fetch from `GET /api/v1/compliance/actions`

Each action item is a card with:

Left side:
- Severity icon: red circle with ! for critical, yellow triangle for warning, blue circle for info
- Title in bold
- Message in gray below the title
- Created date in small text
- Status badge: "New" (blue), "In Progress" (yellow), "Resolved" (green), "Dismissed" (gray)

Right side:
- Resolution action buttons from the `resolution_options` array in the API response
- Each button shows the `label` text and matches the `icon` field
- Button styling: outlined/ghost style, small size, grouped vertically or horizontally depending on space

### When user clicks a resolution button:

Show a slide-out panel or modal with:

1. **Action title** at the top (e.g., "Mark as reviewed — still current")
2. **Notes field** (always shown, optional unless `requires_notes: true` then required) — text area with placeholder "Add notes about what you did..."
3. **Date picker** (only shown if `requires_date: true`) — with label "Set date"
4. **Assign to** field (always shown, optional) — text input with placeholder "Name or email"
5. **Confirm button** — "Update" or the specific action label

On confirm, call:
```
PUT /api/v1/compliance/actions/{action_id}
Body: {
  "status": "{sets_status from the resolution option}",
  "notes": "user's notes",
  "assigned_to": "name if provided",
  "due_date": "YYYY-MM-DD if date was set"
}
```

The API returns `new_score` — update the compliance score gauge with animation.

### Status transitions:
- When an item is resolved, show a brief success message: "Item resolved. Score updated to {new_score}."
- Move resolved items to the bottom of the list or behind the "Resolved" filter tab
- When an item is in_progress, show the assigned person and due date if set

### Visual states for action item cards:
- **New**: white background, full opacity, resolution buttons visible
- **In Progress**: light yellow background, show assigned to + due date, resolution buttons still visible
- **Resolved**: light green background, show who resolved it + when + notes, resolution buttons hidden, show "Reopen" link
- **Dismissed**: light gray background, show dismissal reason in notes, show "Reopen" link

## Update the Chat

When the chat responds to compliance questions (questions about "what needs attention", "issues", "compliance", "risks", etc.), add a link at the bottom of the response:

"View your compliance action items →" linking to /actions

## Update Sidebar Navigation

Add these nav items in this order:
1. Dashboard (home icon)
2. Action Items (shield or clipboard-check icon) — with badge showing open item count
3. Documents (file icon)
4. Upload (upload icon)
5. Ask AI (message circle icon)
6. Knowledge Graph (network icon)
7. Usage (bar chart icon)

Action Items should be the SECOND item because it's the core of the product — the thing users come back to every day.
