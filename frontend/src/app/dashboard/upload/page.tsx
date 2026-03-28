"use client";

import { useState, useCallback } from "react";
import { uploadDocument } from "@/lib/api";
import { Upload, CheckCircle, XCircle, Loader2 } from "lucide-react";

interface UploadResult {
  filename: string;
  status: "uploading" | "success" | "error";
  message: string;
  docType?: string;
}

export default function UploadPage() {
  const [results, setResults] = useState<UploadResult[]>([]);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(async (files: FileList) => {
    for (const file of Array.from(files)) {
      const idx = results.length;
      setResults((prev) => [
        ...prev,
        { filename: file.name, status: "uploading", message: "Processing..." },
      ]);

      try {
        const result = await uploadDocument(file);
        setResults((prev) =>
          prev.map((r, i) =>
            r.filename === file.name
              ? {
                  ...r,
                  status: "success",
                  message: result.message,
                  docType: result.doc_type,
                }
              : r
          )
        );
      } catch (err: any) {
        setResults((prev) =>
          prev.map((r) =>
            r.filename === file.name
              ? { ...r, status: "error", message: err.message || "Upload failed" }
              : r
          )
        );
      }
    }
  }, [results.length]);

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Upload Documents</h2>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
        }}
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
          dragOver
            ? "border-brand-500 bg-brand-50"
            : "border-gray-300 hover:border-gray-400"
        }`}
      >
        <Upload size={48} className="mx-auto mb-4 text-gray-400" />
        <p className="text-lg font-medium text-gray-700 mb-2">
          Drop files here or click to upload
        </p>
        <p className="text-sm text-gray-500 mb-4">
          PDF, DOCX, XLSX, TXT, CSV, images — up to 100MB each
        </p>
        <label className="inline-block bg-brand-600 text-white px-6 py-2.5 rounded-lg font-medium cursor-pointer hover:bg-brand-700 transition-colors">
          Select Files
          <input
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.docx,.xlsx,.pptx,.txt,.csv,.png,.jpg,.jpeg"
            onChange={(e) => {
              if (e.target.files?.length) handleFiles(e.target.files);
            }}
          />
        </label>
      </div>

      {/* Upload Results */}
      {results.length > 0 && (
        <div className="mt-6 space-y-3">
          <h3 className="font-semibold text-gray-900">Upload Results</h3>
          {results.map((r, i) => (
            <div
              key={i}
              className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg p-4"
            >
              {r.status === "uploading" && (
                <Loader2 size={18} className="text-blue-500 animate-spin" />
              )}
              {r.status === "success" && (
                <CheckCircle size={18} className="text-green-500" />
              )}
              {r.status === "error" && (
                <XCircle size={18} className="text-red-500" />
              )}
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{r.filename}</p>
                <p className="text-xs text-gray-500">{r.message}</p>
              </div>
              {r.docType && (
                <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full">
                  {r.docType}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="mt-8 bg-blue-50 border border-blue-100 rounded-xl p-6">
        <h3 className="font-semibold text-blue-900 mb-2">What happens when you upload?</h3>
        <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
          <li>Text is extracted from your document</li>
          <li>AI classifies the document type (SOP, certificate, invoice, etc.)</li>
          <li>Entities are extracted (people, organizations, dates, regulations)</li>
          <li>Relationships are added to your knowledge graph</li>
          <li>Document becomes searchable and queryable via AI chat</li>
        </ol>
        <p className="text-xs text-blue-600 mt-3">
          Classification costs 0.5 credits. Entity extraction costs 2.0 credits. Q&A is always free.
        </p>
      </div>
    </div>
  );
}
