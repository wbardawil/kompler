# Lovable Update 4: Demo-Ready Dashboard + Guided Upload

Copy everything below this line into Lovable:

---

## 1. Replace Dashboard Data Source

Replace all current dashboard API calls with a single call to `GET /api/v1/dashboard` (header: X-Api-Key: dev-key-1).

This returns everything the dashboard needs in one response:

```json
{
  "company_name": "Demo Manufacturing SA de CV",
  "greeting": "Good morning",
  "score": 30,
  "score_status": "critical",
  "open_items": 12,
  "audit": {
    "date": "2026-06-15",
    "days_remaining": 78,
    "certifying_body": "BSI Mexico",
    "urgency": "warning"
  },
  "frameworks": [
    {"id": "repse", "name": "REPSE", "present": 0, "required": 7, "score": 0, "status": "critical"},
    {"id": "immex", "name": "IMMEX", "present": 1, "required": 7, "score": 14, "status": "critical"},
    {"id": "iso_9001", "name": "ISO 9001:2015", "present": 7, "required": 14, "score": 50, "status": "warning"}
  ],
  "priorities": [
    {
      "severity": "critical",
      "title": "REPSE: not started",
      "description": "Missing all 7 required documents.",
      "action_label": "Start REPSE setup"
    }
  ],
  "stats": {"documents": 9, "entities": 162, "credits_used": 45, "credits_remaining": 9955},
  "next_action": {"title": "REPSE: not started", "action_label": "Start REPSE setup"}
}
```

### New Dashboard Layout:

**Top section:**
- Left: `greeting`, `company_name` and today's date
- Right: Compliance score circle (use `score` and `score_status` for color: critical=red, warning=yellow, good/excellent=green)

**Audit countdown banner** (only if `audit` is present):
- Show: "Next audit: {audit.date} — {audit.days_remaining} days remaining ({audit.certifying_body})"
- Background color based on `audit.urgency`: critical=red, warning=yellow, on_track=green
- This is a prominent banner, not hidden

**Framework readiness bars:**
For each item in `frameworks` array, show a horizontal progress bar:
- Framework name on the left
- Progress bar showing present/required
- Percentage on the right
- Bar color: red if score<40, yellow if 40-70, green if >70
- Sort order: worst first (already sorted by API)

**Top 3 Priorities section:**
Title: "Your Priorities"
Show only the items from `priorities` array (max 3). Each priority card has:
- Severity icon (red ! for critical, yellow triangle for warning)
- Title in bold
- Description in gray
- Action button with `action_label` text
- When button clicked: navigate to /actions page

**Quick Ask section** (keep existing, below priorities)

**Stats row** (small, at bottom):
- Documents: `stats.documents`
- Entities: `stats.entities`
- Credits: `stats.credits_remaining`

Remove the "Attention Required" section that fetched from /alerts — the priorities section replaces it.

## 2. Update Upload Page with Guided Upload

On the Upload page, add a section ABOVE the drop zone.

Fetch from `GET /api/v1/upload/guide` (header: X-Api-Key: dev-key-1).

Response:
```json
{
  "total_missing": 20,
  "mandatory_missing": 8,
  "message": "You need 20 more documents. Start with the 8 mandatory ones.",
  "suggestions": [
    {
      "framework_name": "IMMEX",
      "clause": "IMMEX-REG",
      "name": "IMMEX Registration Certificate",
      "mandatory": true,
      "keywords": ["IMMEX", "programa IMMEX", "registro IMMEX"],
      "tip": "Your IMMEX program number from Secretaria de Economia. Check with your customs broker."
    }
  ]
}
```

### Upload page layout:

**Top: Upload guidance banner**
- Show `message` text ("You need 20 more documents. Start with the 8 mandatory ones.")
- Below: list the first 5 suggestions as cards:
  - Each card shows: framework badge (colored), document name, [MANDATORY] badge if mandatory
  - Tip text in gray below
  - The card itself is not clickable — it just guides the user on what to upload

**Middle: Existing drop zone** (keep as is)

**Bottom: Existing "What happens when you upload" info box** (keep as is)

## 3. Fix Chat Responses

The chat now returns concise answers for compliance questions. No changes needed to the frontend — just verify that the response renders cleanly. The answer will be 3-5 lines instead of a paragraph.

## 4. Sidebar — No Changes

Keep the current sidebar order. Just make sure the Action Items badge shows `open_items` from the dashboard response.
