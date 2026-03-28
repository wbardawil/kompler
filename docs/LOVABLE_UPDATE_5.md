# Lovable Update 5: Replace Knowledge Graph with Compliance Map

Copy everything below this line into Lovable:

---

## Replace Knowledge Graph Page Entirely

Remove the force-directed graph visualization. Replace with a Compliance Map — a clause-by-clause evidence view that shows exactly what's covered, missing, expiring, or needs verification.

Rename the sidebar item from "Knowledge Graph" to "Compliance Map" and change the icon to a clipboard-check or shield-check icon.

### Data Source

Fetch from `GET /api/v1/compliance/map` (header: X-Api-Key: dev-key-1)

Response structure:
```json
{
  "summary": {
    "total_requirements": 28,
    "covered": 3,
    "missing": 20,
    "unverified": 2,
    "expiring_or_expired": 3,
    "overall_coverage": 11
  },
  "frameworks": [
    {
      "id": "repse",
      "name": "REPSE",
      "score": 0,
      "total": 7,
      "status_counts": {"missing": 7},
      "clauses": [
        {
          "clause": "REPSE-REG",
          "name": "REPSE Registration Certificate",
          "description": "Active REPSE registration number from STPS",
          "status": "missing",
          "document": null,
          "mandatory": true,
          "keywords": ["REPSE", "registro REPSE", "STPS"],
          "action": {
            "type": "upload",
            "label": "Upload document",
            "tip": "Your REPSE number from STPS. Check with your legal or HR department."
          }
        },
        {
          "clause": "5.2",
          "name": "Quality Policy",
          "status": "covered",
          "document": {
            "id": "abc-123",
            "filename": "Quality_Policy_2026.pdf",
            "doc_type": "policy",
            "summary": "Quality policy for manufacturing operations..."
          },
          "match_type": "doc_type",
          "action": {"type": "none", "label": "No action needed"}
        },
        {
          "clause": "8.6",
          "name": "Product Conformity Records",
          "status": "unverified",
          "document": {
            "id": "def-456",
            "filename": "SOP-042 Quality Inspection.txt",
            "doc_type": "sop"
          },
          "match_type": "filename_keyword",
          "action": {
            "type": "verify",
            "label": "Verify this match",
            "description": "AI matched this document. Please confirm it satisfies this requirement."
          }
        }
      ]
    }
  ]
}
```

### Page Layout

**Top: Summary bar**
Show overall coverage as a large stat:
- "3 of 28 requirements covered (11%)"
- Four small stat cards in a row:
  - ✅ Covered: 3 (green)
  - ❌ Missing: 20 (red)
  - 🔍 Unverified: 2 (blue)
  - ⚠️ Expiring: 3 (yellow)

**Framework tabs or sections:**
For each framework in the `frameworks` array, show as a tab or collapsible section:
- Framework name with score badge (e.g. "REPSE 0%" in red, "ISO 9001 50%" in yellow)
- Progress bar showing coverage

**Clause list within each framework:**
Each clause is a row showing:

| Status Icon | Clause | Requirement Name | Evidence | Action |
|-------------|--------|-------------------|----------|--------|

Status icons and colors:
- ✅ `covered` — green checkmark, light green background
- ⚠️ `expiring` — yellow warning, light yellow background
- ❌ `expired` — red X, light red background
- 🔍 `unverified` — blue question mark, light blue background
- ⬜ `missing` — gray empty box, white background

For each row:
- **Clause column**: show `clause` value (e.g., "5.2", "REPSE-REG")
- **Name column**: show `name` (e.g., "Quality Policy"). If `mandatory` is true, show a small "Required" badge
- **Evidence column**:
  - If `document` exists: show document filename as a link
  - If `status` is "unverified": show filename + small "AI-matched" badge in blue
  - If missing: show "(no document)" in gray
- **Action column**:
  - If missing: "Upload" button (links to /upload page)
  - If unverified: "Verify" button (shows a confirmation dialog: "Does [filename] satisfy [requirement name]?" with Yes/No buttons. On Yes, call `PUT /api/v1/compliance/map/{framework_id}/{clause}/verify`)
  - If expiring/expired: "Renew" button (links to /upload page)
  - If covered: green checkmark, no button

**When a clause row is clicked/expanded:**
Show additional details:
- Full description of the requirement
- If document matched: document summary
- If missing: the `tip` from the action object ("Your REPSE number from STPS. Check with your legal or HR department.")
- Keywords to search for in your files (from `keywords` array)

### Design Notes

- Sort order comes from the API (missing mandatory first, then expired, expiring, unverified, covered last)
- Each framework section shows its own progress bar
- The page should feel like a checklist you're working through, not a data dashboard
- Clean, minimal design — every row is either "done" (green) or "needs action" (with a clear button)
- Mobile responsive: on mobile, collapse evidence and action into expandable rows

### Sidebar Update

Change "Knowledge Graph" to "Compliance Map" with a shield-check or clipboard-check icon. Keep it in the same position in the nav.
