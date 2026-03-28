# Lovable Update 2: Action Items Page + Visual Knowledge Graph

Copy everything below this line into Lovable as one prompt:

---

Make these changes to the app:

## 1. Add Action Items Page (route: /actions)

Add "Action Items" to the sidebar navigation as the SECOND item (between Dashboard and Documents), with a clipboard-check icon and a red badge showing the number of open items.

Fetch action items from `GET /api/v1/compliance/actions` (header: X-Api-Key: dev-key-1).

Response format:
```json
{
  "actions": [
    {
      "id": "uuid",
      "type": "missing_review",
      "severity": "warning",
      "title": "6 controlled documents have no review date",
      "message": "Set review dates to enable automatic review reminders",
      "status": "new",
      "created_at": "2026-03-28T...",
      "resolution_options": [
        {"action": "set_review_date", "label": "Set review date", "icon": "calendar", "sets_status": "resolved", "requires_date": true},
        {"action": "set_annual_review", "label": "Set annual review (12 months)", "icon": "calendar", "sets_status": "resolved"}
      ]
    }
  ],
  "total": 4,
  "score": {"score": 98, "open_items": 4, "resolved_items": 0, "status": "excellent"}
}
```

### Page layout:

**Top section:**
- Title: "Compliance Action Items"
- Small compliance score circle on the right (from the score object in the response)
- "Scan Now" button that calls `POST /api/v1/compliance/scan` and refreshes the list
- Filter tabs: All | Critical | Warnings | Open | Resolved

**Action items list:**
Each item is a card showing:
- Left: severity icon (red ! for critical, yellow triangle for warning, blue i for info)
- Title in bold, message below in gray
- Status badge: New (blue), In Progress (yellow), Resolved (green), Dismissed (gray)
- Created date
- Resolution buttons from the `resolution_options` array — show as small outlined buttons with the label text

**When user clicks a resolution button:**
Open a slide-out panel or modal:
- Title of the action being taken
- Notes text area (placeholder: "Describe what you did or what's planned...")
- If the resolution option has `requires_date: true`: show a date picker
- Assign to field (optional text input)
- Confirm button

On confirm, call:
```
PUT /api/v1/compliance/actions/{action_id}
Headers: X-Api-Key: dev-key-1, Content-Type: application/json
Body: {"status": "resolved", "notes": "User's notes", "assigned_to": "Name", "due_date": "2026-04-15"}
```
Use the `sets_status` value from the resolution option as the status.

After update, show success toast: "Updated. Compliance score: {new_score}" and refresh the list.

**Card visual states:**
- New: white background, resolution buttons visible
- In Progress: light yellow/amber background, show assigned person and due date if set
- Resolved: light green background, show resolution notes, hide action buttons, show small "Reopen" link
- Dismissed: light gray, show dismissal reason

## 2. Replace Knowledge Graph Page with Visual Graph

Remove the current knowledge graph page content. Replace with an interactive force-directed graph visualization.

Install the `react-force-graph` npm package. Use the `ForceGraph2D` component.

Fetch from `GET /api/v1/graph` (header: X-Api-Key: dev-key-1).

Response contains:
- `nodes`: array of `{id, label, type, subtype, size}` — type is "document" or "entity"
- `edges`: array of `{source, target}` — connections between nodes
- `stats`: `{entity_count, document_count, total_edges, cross_document_entities}`

### Graph rendering:

Configure ForceGraph2D with:
- `graphData={{nodes: data.nodes, links: data.edges}}`
- `nodeLabel="label"`
- `linkColor={() => "rgba(200,200,210,0.3)"}`
- `linkWidth={0.5}`
- `nodeRelSize={4}`
- `enableZoomInteraction={true}`
- `enablePanInteraction={true}`
- `enableNodeDrag={true}`

Node colors by subtype using a `nodeColor` function:
- document: #3B82F6 (blue)
- person: #8B5CF6 (purple)
- organization: #10B981 (green)
- regulation: #F59E0B (yellow)
- standard: #F59E0B (yellow)
- certificate: #EF4444 (red)
- date: #6B7280 (gray)
- location: #EC4899 (pink)
- product: #06B6D4 (cyan)
- process: #14B8A6 (teal)
- default: #9CA3AF (gray)

Node size using `nodeVal` function: return 8 if type is "document", otherwise return 2 + Math.min(node.size, 4)

Custom node rendering using `nodeCanvasObject`: draw a filled circle with the node color, and draw the label text below only for document nodes or if the node is hovered.

Track hovered node with `onNodeHover` and highlight its connections.

### Page layout:

**Top bar:**
- Title: "Knowledge Graph"
- Subtitle: "{entity_count} entities, {document_count} documents, {cross_document_entities} cross-document links"
- Search input that filters/highlights nodes matching the search text
- Legend showing colored dots for each entity type

**Main area:**
- Full-height ForceGraph2D component (calculate height as viewport height minus header)
- White background with rounded corners and border

**Right panel (shown when a node is clicked):**
- Node name and type badge
- If entity node: fetch `GET /api/v1/graph/entity/{encodeURIComponent(node.label)}` and show:
  - "Found in X documents" with list of document names
  - "Related entities" as colored pills that can be clicked to navigate to that entity
- If document node: show doc_type, summary if available
- Close button to dismiss the panel

## 3. Update Dashboard

Replace the client-side compliance score with the real API score.

Fetch `GET /api/v1/compliance/score` and use `score` for the gauge number, `status` for the text label, `open_items` for the alert count.

Add below the "Attention Required" section a link: "View all action items →" that navigates to /actions.

## 4. Updated Sidebar Order

1. Dashboard (home icon)
2. Action Items (clipboard-check icon) — with red badge showing open_items count
3. Documents (file icon)
4. Upload (upload icon)
5. Ask AI (message-circle icon)
6. Knowledge Graph (network icon)
7. Usage (bar-chart icon)
