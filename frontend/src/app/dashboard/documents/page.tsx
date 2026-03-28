"use client";

import { useEffect, useState } from "react";
import { fetchDocuments } from "@/lib/api";
import { FileText, Search } from "lucide-react";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchDocuments(page, 20).then(setDocs).catch(console.error);
  }, [page]);

  const filteredDocs = docs?.documents?.filter((d: any) =>
    search
      ? d.filename.toLowerCase().includes(search.toLowerCase()) ||
        d.doc_type?.toLowerCase().includes(search.toLowerCase())
      : true
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Documents</h2>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Filter documents..."
            className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr className="text-left text-xs text-gray-500">
              <th className="px-6 py-3">Document</th>
              <th className="px-6 py-3">Type</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Confidence</th>
              <th className="px-6 py-3">Entities</th>
              <th className="px-6 py-3">Language</th>
              <th className="px-6 py-3">Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {filteredDocs?.map((doc: any) => (
              <tr key={doc.id} className="border-b hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <FileText size={16} className="text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                      <p className="text-xs text-gray-500">{(doc.file_size_bytes / 1024).toFixed(0)} KB</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full">
                    {doc.doc_type || "pending"}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      doc.status === "enriched"
                        ? "bg-green-50 text-green-700"
                        : doc.status === "error"
                        ? "bg-red-50 text-red-700"
                        : "bg-yellow-50 text-yellow-700"
                    }`}
                  >
                    {doc.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {doc.classification_confidence
                    ? `${(doc.classification_confidence * 100).toFixed(0)}%`
                    : "-"}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{doc.entity_count}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{doc.language || "-"}</td>
                <td className="px-6 py-4 text-xs text-gray-500">
                  {new Date(doc.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {(!filteredDocs || filteredDocs.length === 0) && (
          <div className="text-center py-12 text-gray-500">
            <FileText size={48} className="mx-auto mb-4 text-gray-300" />
            <p>No documents found. Upload your first document to get started.</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {docs && docs.total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm text-gray-600">
            Page {page} of {Math.ceil(docs.total / 20)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page * 20 >= docs.total}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
