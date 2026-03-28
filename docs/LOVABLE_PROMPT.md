# Lovable Build Instructions for Kompler Frontend

Copy everything below this line into Lovable:

---

Build a compliance intelligence dashboard for "Kompler" — an AI platform that tells companies what's wrong with their document compliance before auditors find it.

## API Connection

Base URL: `https://kompler-production.up.railway.app`
Auth: Every API request needs header `X-Api-Key: dev-key-1`

Available endpoints:
- `GET /health` — health check
- `GET /api/v1/usage` — credit balance, document count, entity count, storage
- `GET /api/v1/alerts` — proactive compliance alerts (expiry, stale, missing)
- `GET /api/v1/documents?page=1&page_size=20` — list documents
- `GET /api/v1/documents/{id}` — single document detail
- `POST /api/v1/documents` — upload file (multipart form, field name "file")
- `POST /api/v1/documents/search` — search (body: {"query": "...", "limit": 20})
- `POST /api/v1/chat` — ask questions (body: {"question": "..."}) — always free
- `GET /api/v1/graph` — knowledge graph (nodes, edges, stats, cross-doc connections)
- `GET /api/v1/graph/entity/{entity_value}` — entity detail with related docs
- `GET /api/v1/usage/transactions?limit=50` — credit transaction history

## Design Style

- Clean, modern, professional SaaS dashboard
- Color scheme: deep blue primary (#3B5BDB), white backgrounds, gray-50 for sections
- Font: Inter or system-ui
- Rounded corners (xl), subtle shadows, plenty of whitespace
- Think: Linear, Notion, or Vercel dashboard — minimal, elegant, focused
- Mobile responsive

## Pages to Build

### 1. LANDING PAGE (route: /)

Hero section:
- Headline: "Stop getting surprised at audits"
- Subheadline: "AI agents monitor your documents 24/7 and tell you what needs attention before auditors find it."
- Two buttons: "Open Dashboard" (links to /dashboard) and "See How It Works"
- Below: three feature cards:
  - "Auto-Classify" — AI classifies every document automatically
  - "Proactive Alerts" — Know when certificates expire, SOPs go stale, or compliance gaps emerge
  - "Ask Anything" — Ask questions in plain language, get cited answers. Always free.
- Bottom: "Unlimited users. Usage-based pricing. Your data stays yours."

### 2. DASHBOARD (route: /dashboard) — THE MOST IMPORTANT PAGE

This is the "daily briefing" — what the user sees every morning. Layout:

**Top section — greeting + compliance score:**
- Left: "Good morning, here's your briefing" with today's date
- Right: Circular compliance score gauge (0-100). Green if >80, yellow if 60-80, red if <60
- Calculate score from alerts: start at 100, subtract 15 per critical, 8 per warning, 2 per info-type "missing_review"

**Middle section — two columns:**
- Left (wide): "Quick Ask" — branded search box with placeholder "Ask your documents anything..." and example questions as clickable pills below it ("What certificates expire soon?", "Summarize my SOPs", "Any compliance gaps?"). Links to /chat with the question pre-filled.
- Right: Stats cards — Documents indexed, Entities discovered, Credits remaining

**Alert section:**
- Header: "Attention Required" with count badge
- Fetch from `GET /api/v1/alerts`
- Show each alert as a card with icon (red circle for critical, yellow triangle for warning, blue info for info)
- Show title + message for each alert
- Filter out alerts with type "entity_summary" and "top_entities" from the main list (those are informational)

**Bottom: Recent Documents**
- Fetch from `GET /api/v1/documents?page=1&page_size=5`
- Show filename, doc_type badge, status badge (green for enriched, yellow for pending), entity count
- Link each to /documents/{id}

### 3. UPLOAD PAGE (route: /upload)

- Large drag-and-drop zone with file icon
- Text: "Drop files here or click to upload"
- Subtitle: "PDF, DOCX, XLSX, TXT — up to 100MB"
- "Select Files" button
- Accepts multiple files
- Upload each file via `POST /api/v1/documents` as multipart form data
- Show upload progress for each file with status (uploading spinner, success checkmark, error X)
- After success, show the returned status and doc_type classification
- Info box at bottom: "What happens when you upload?" with steps:
  1. Text is extracted from your document
  2. AI classifies the document type
  3. Entities are extracted (people, organizations, dates, regulations)
  4. Connections are added to your knowledge graph
  5. Document becomes searchable via AI chat

### 4. DOCUMENTS PAGE (route: /documents)

- Search/filter bar at top
- Table with columns: Document name, Type (badge), Status (badge), Confidence %, Entities, Language, Uploaded date
- Fetch from `GET /api/v1/documents?page={page}&page_size=20`
- Pagination controls
- Click a row to show document detail panel (sidebar or modal):
  - Document metadata (filename, type, status, confidence, language)
  - Summary (from API field "summary")
  - Entity list (if available)
  - Compliance tags
  - Expiry date and review due date (if set)

### 5. ASK AI / CHAT PAGE (route: /chat)

- Full-height chat interface
- Header: "Ask Your Documents" with subtitle "Free — 0 credits. Ask anything about your uploaded documents."
- Initial bot message with example questions
- User types question, sends via `POST /api/v1/chat` with body `{"question": "user's question"}`
- Show AI response with:
  - Answer text
  - Citations section (list of source documents with relevant text snippets)
  - Flags section (compliance concerns if any, shown as yellow warning pills)
  - Confidence indicator
- "AI-generated response. Verify critical information against authoritative sources." disclaimer at bottom
- Support pre-filled question from URL query param ?q=...

### 6. KNOWLEDGE GRAPH PAGE (route: /graph)

- Fetch from `GET /api/v1/graph`
- Left panel (scrollable, 1/3 width):
  - Stats: total entities, total documents, total connections, cross-doc links
  - Search box to filter entities
  - Entity type legend with colored dots (person=purple, organization=green, regulation=yellow, certificate=red, date=gray, location=pink, product=cyan, document=blue)
  - Entity list grouped by type, sorted by frequency
  - Cross-document connections section (entities appearing in multiple documents) highlighted in amber
  - Click any entity to show detail in right panel
- Right panel (2/3 width):
  - When no entity selected: "Click an entity to explore connections"
  - When entity selected: show entity name + type, list of documents mentioning it (with filename, doc_type, summary), related entities (other entities co-occurring in same documents) as clickable pills
  - Fetch entity detail from `GET /api/v1/graph/entity/{entity_value}`

### 7. USAGE PAGE (route: /usage)

- Plan info card: tier name, credits included/used/remaining with progress bar, storage used/limit with progress bar
- "Upgrade Plan" button (non-functional for now)
- Three stat cards: Documents indexed, Entities discovered, "Q&A is FREE" highlight
- Credit costs reference table: Classification 0.5cr, Entity Extraction 2.0cr, Deep Analysis 5.0cr, Search & Q&A FREE
- Transaction history table from `GET /api/v1/usage/transactions?limit=50`: action, credits, date

### 8. SIDEBAR NAVIGATION

- Logo: "Kompler" with subtitle "Document Intelligence"
- Nav items with icons: Dashboard (home), Documents (file), Upload (upload), Ask AI (message circle), Knowledge Graph (network), Usage (bar chart)
- Active state: highlighted background
- Bottom: tenant name "Demo Company" and plan "Pro Plan"

## Important Notes

- All API calls need the header: `X-Api-Key: dev-key-1`
- The chat endpoint (POST /api/v1/chat) returns JSON, not streaming
- Q&A is always free — display this prominently (it's a selling point)
- Mobile responsive — sidebar collapses to hamburger menu
- Use real data from the API — don't use mock data
- The compliance score is calculated client-side from alerts data
- Landing page should feel like a marketing site. Dashboard should feel like a SaaS app.
