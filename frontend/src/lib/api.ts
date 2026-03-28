const API_BASE = "/api/v1";

const headers = () => ({
  "X-Api-Key": "dev-key-1",
  "Content-Type": "application/json",
});

export async function fetchDocuments(page = 1, pageSize = 20) {
  const res = await fetch(
    `${API_BASE}/documents?page=${page}&page_size=${pageSize}`,
    { headers: headers() }
  );
  return res.json();
}

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/documents`, {
    method: "POST",
    headers: { "X-Api-Key": "dev-key-1" },
    body: formData,
  });
  return res.json();
}

export async function searchDocuments(query: string) {
  const res = await fetch(`${API_BASE}/documents/search`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ query, limit: 20 }),
  });
  return res.json();
}

export async function askQuestion(question: string) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ question, max_context_docs: 5 }),
  });
  return res.json();
}

export async function fetchUsage() {
  const res = await fetch(`${API_BASE}/usage`, { headers: headers() });
  return res.json();
}

export async function fetchTransactions(limit = 50) {
  const res = await fetch(`${API_BASE}/usage/transactions?limit=${limit}`, {
    headers: headers(),
  });
  return res.json();
}

export async function fetchAlerts() {
  const res = await fetch(`${API_BASE}/alerts`, { headers: headers() });
  return res.json();
}

export async function fetchGraph() {
  const res = await fetch(`${API_BASE}/graph`, { headers: headers() });
  return res.json();
}

export async function fetchEntityConnections(entityValue: string) {
  const res = await fetch(
    `${API_BASE}/graph/entity/${encodeURIComponent(entityValue)}`,
    { headers: headers() }
  );
  return res.json();
}
