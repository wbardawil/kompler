# Lovable Update 3: Settings, Onboarding, Smart Roadmap

Copy everything below this line into Lovable:

---

## 1. Add Settings Page (route: /settings)

Add "Settings" to the sidebar at the bottom, with a gear icon.

### Company Profile Section

Fetch current profile from `GET /api/v1/compliance/profile`

Show editable form:
- Company name (text input)
- Country (dropdown: Mexico, United States, Colombia, Brazil, Other)
- State/Region (text input)
- Entity type (dropdown: SA de CV, S de RL de CV, LLC, Corp, Other)
- Industry (dropdown: Manufacturing, Automotive, Aerospace, Medical Devices, Healthcare, Tax/Accounting, Legal, Other)
- Employee count (dropdown: 1-50, 50-200, 200-500, 500+)
- Primary document language (dropdown: Spanish, English, Both)

Save button calls `POST /api/v1/onboarding/company` with body:
```json
{
  "company_name": "...",
  "country": "Mexico",
  "state": "Nuevo Leon",
  "entity_type": "SA de CV",
  "industry": "manufacturing",
  "employee_count": "50-200",
  "language": "es"
}
```

After save, show the `suggested_frameworks` from the response as a recommendation banner.

### Compliance Frameworks Section

Show each framework as a card with toggle switch:

Fetch available frameworks from `GET /api/v1/compliance/frameworks`

Each card shows:
- Framework name and full name
- Required documents count + required records count
- Toggle switch (on/off)
- If recommended by the system based on profile, show a "Recommended" badge

The currently active frameworks come from `GET /api/v1/compliance/profile` → `frameworks` array.

When user toggles frameworks, save by calling:
```
POST /api/v1/onboarding/frameworks
Body: {
  "frameworks": ["iso_9001", "immex", "repse"],
  "next_audit_date": "2026-06-15",
  "certifying_body": "BSI Mexico"
}
```

### Audit Information Section
- Next audit date (date picker)
- Certifying body (text input, e.g. "BSI Mexico")

These are included in the frameworks save call above.

### After Saving Frameworks
Show a banner: "Frameworks updated. Run a compliance scan to update your action items and score." with a "Scan Now" button that calls `POST /api/v1/compliance/scan`.

## 2. Replace Action Items with Roadmap View

Change the Action Items page to fetch from `GET /api/v1/compliance/roadmap` instead of `GET /api/v1/compliance/actions`.

The roadmap response has this structure:
```json
{
  "score": {"score": 0, "open_items": 15, "status": "critical", "by_severity": {"critical": 6, "warning": 7, "info": 1}},
  "frameworks": {
    "iso_9001": {"name": "ISO 9001:2015", "score": 50, "present": 7, "required": 14},
    "immex": {"name": "IMMEX", "score": 14, "present": 1, "required": 7},
    "repse": {"name": "REPSE", "score": 0, "present": 0, "required": 7}
  },
  "summary": {"next_step": "You have 6 critical items. Address these immediately."},
  "urgent": {"title": "Urgent — Fix These First", "items": [...], "count": 6},
  "start_here": {"title": "Start Here — Highest Impact", "items": [...], "count": 8},
  "warnings": {"title": "Needs Attention", "items": [...], "count": 7},
  "recommended": {"title": "Recommended", "items": [...], "count": 12},
  "in_progress": {"title": "In Progress", "items": [...], "count": 0},
  "completed": {"title": "Completed", "items": [...], "count": 0}
}
```

### Page Layout:

**Top banner:**
Next step recommendation text from `summary.next_step` on a colored background:
- Critical status: red background
- Needs attention: yellow background
- Good: green background

**Framework progress bars:**
For each framework in the `frameworks` object, show:
- Framework name
- Progress bar: present/required
- Percentage score
- Color: red if <40%, yellow if 40-70%, green if >70%

Example:
```
ISO 9001:2015    ████████░░░░░░░░  7/14 (50%)
IMMEX            ██░░░░░░░░░░░░░░  1/7  (14%)
REPSE            ░░░░░░░░░░░░░░░░  0/7  (0%)
```

**Sections:**
Render each non-empty section as a collapsible card group:

🔴 **Urgent — Fix These First** (red left border)
Only show if `urgent.count > 0`. Each item shows severity icon, title, message, and resolution_options buttons.

⭐ **Start Here — Highest Impact** (blue left border)
These are mandatory missing documents. Each shows:
- Document name needed
- Framework badge (ISO 9001, IMMEX, or REPSE)
- Clause reference
- Keywords to search for (from the `keywords` array)
- "Upload" button and "Not applicable" button

⚠️ **Needs Attention** (yellow left border)
Warning items with resolution buttons.

💡 **Recommended** (gray left border, collapsed by default)
Optional improvements. Show as a simpler list.

🔄 **In Progress** (blue left border)
Show assigned person, due date, notes.

✅ **Completed** (green left border, collapsed by default)
Show resolved items with notes.

Hide any section where count is 0.

**Resolving items:**
When user clicks a resolution button on any item, show the same slide-out panel as before (notes, date, assignee). Call `PUT /api/v1/compliance/actions/{id}` with the appropriate status. After resolving, refresh the roadmap to see the score update and the item move to Completed.

For "Start Here" items (missing documents), the "Upload" button should navigate to the /upload page. After uploading, the user returns to the roadmap and runs "Scan Now" to see the updated completeness.

## 3. Update Dashboard

Add framework progress bars to the dashboard below the compliance score:

Fetch from `GET /api/v1/compliance/roadmap` and show the `frameworks` object as small horizontal progress bars with labels.

Also show the `summary.next_step` text as a banner between the score and the Quick Ask section.

## 4. Sidebar Updates

Final sidebar order:
1. Dashboard (home icon)
2. Action Items (clipboard-check icon) — badge showing `score.open_items`
3. Documents (file icon)
4. Upload (upload icon)
5. Ask AI (message-circle icon)
6. Knowledge Graph (network icon)
7. Usage (bar-chart icon)
8. Settings (gear icon) — at the bottom, separated by a divider
