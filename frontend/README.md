# DocuVault AI — Frontend

## Tech Stack (Phase 4)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Next.js 14+ (App Router) | SSR, API routes, Vercel/AWS deploy |
| PDF Viewer | react-pdf or @embedpdf/react | In-browser document rendering |
| Graph Viz | Cytoscape.js | Knowledge graph explorer |
| Charts | Recharts / Tremor | Dashboards and reporting |
| UI Components | shadcn/ui + Tailwind CSS | Composable, accessible |
| Data Fetching | TanStack Query | Caching, optimistic updates |
| State | Zustand | Lightweight, no boilerplate |
| Streaming | SSE (Server-Sent Events) | Chat response streaming |

## 6 Views

1. **Document List / Explorer** (Phase 2) — browse, filter, sort, search
2. **Document Viewer** (Phase 2-3) — in-browser PDF + metadata sidebar + entity highlights
3. **Chat / Q&A** (Phase 2) — streaming responses, citations, confidence, cache indicator
4. **Knowledge Graph Explorer** (Phase 4) — interactive force-directed graph, entity navigation
5. **Admin Console** (Phase 4) — users, API keys, usage dashboard, billing, entity patterns
6. **Embeddable Widget** (Phase 4) — drop search/Q&A into any web app, 10 lines of code

## Phasing

- Phase 2: Streamlit prototype for chat + document list (validate UX before investing in Next.js)
- Phase 3: Next.js MVP with chat + document list + basic viewer
- Phase 4: Full Next.js with graph explorer, admin console, embeddable widget
