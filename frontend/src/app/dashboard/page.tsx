"use client";

import { useEffect, useState } from "react";
import { fetchUsage, fetchAlerts, fetchDocuments } from "@/lib/api";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  Info,
  MessageCircle,
  Search,
  TrendingUp,
  FileText,
  Shield,
  ChevronRight,
  Zap,
} from "lucide-react";

export default function DashboardPage() {
  const [usage, setUsage] = useState<any>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [docs, setDocs] = useState<any>(null);
  const [question, setQuestion] = useState("");

  useEffect(() => {
    fetchUsage().then(setUsage).catch(console.error);
    fetchAlerts().then(setAlerts).catch(console.error);
    fetchDocuments(1, 5).then(setDocs).catch(console.error);
  }, []);

  const complianceScore = calculateComplianceScore(alerts, usage);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <p className="text-sm text-gray-500">
          {new Date().toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </p>
        <h2 className="text-2xl font-bold text-gray-900 mt-1">
          Good {getTimeOfDay()}, here's your briefing
        </h2>
      </div>

      {/* Compliance Score + Quick Ask */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Compliance Score */}
        <div className="col-span-1 bg-white rounded-2xl border border-gray-200 p-6 flex flex-col items-center justify-center">
          <div className="relative w-28 h-28 mb-3">
            <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
              <circle
                cx="50" cy="50" r="42"
                fill="none" stroke="#F3F4F6" strokeWidth="8"
              />
              <circle
                cx="50" cy="50" r="42"
                fill="none"
                stroke={complianceScore >= 80 ? "#10B981" : complianceScore >= 60 ? "#F59E0B" : "#EF4444"}
                strokeWidth="8"
                strokeDasharray={`${complianceScore * 2.64} 264`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold text-gray-900">{complianceScore}</span>
              <span className="text-[10px] text-gray-500 uppercase tracking-wider">score</span>
            </div>
          </div>
          <p className="text-sm font-medium text-gray-700">Compliance Health</p>
          <p className="text-xs text-gray-500 mt-1">
            {complianceScore >= 80 ? "Looking good" : complianceScore >= 60 ? "Needs attention" : "Action required"}
          </p>
        </div>

        {/* Quick Ask */}
        <div className="col-span-2 bg-gradient-to-br from-brand-600 to-brand-700 rounded-2xl p-6 text-white flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Zap size={18} />
              <h3 className="font-semibold">Ask your documents anything</h3>
            </div>
            <p className="text-sm text-brand-100 mb-4">
              Free, unlimited. Get cited answers from all your documents instantly.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. What compliance risks do I have?"
              className="flex-1 bg-white/15 backdrop-blur border border-white/20 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-white/40"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && question.trim()) {
                  window.location.href = `/dashboard/chat?q=${encodeURIComponent(question)}`;
                }
              }}
            />
            <Link
              href={question ? `/dashboard/chat?q=${encodeURIComponent(question)}` : "/dashboard/chat"}
              className="bg-white text-brand-700 px-4 py-2.5 rounded-xl font-medium text-sm hover:bg-brand-50 transition-colors flex items-center gap-1"
            >
              <MessageCircle size={16} />
              Ask
            </Link>
          </div>
          <div className="flex gap-2 mt-3">
            {["What certificates expire soon?", "Summarize my SOPs", "Any compliance gaps?"].map((q) => (
              <button
                key={q}
                onClick={() => (window.location.href = `/dashboard/chat?q=${encodeURIComponent(q)}`)}
                className="text-[11px] bg-white/10 hover:bg-white/20 border border-white/15 rounded-full px-3 py-1 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Alerts — The Core Value */}
      {alerts && alerts.alerts.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Shield size={18} className="text-brand-600" />
              Attention Required
            </h3>
            {alerts.critical > 0 && (
              <span className="text-xs bg-red-100 text-red-700 px-2.5 py-1 rounded-full font-medium">
                {alerts.critical} critical
              </span>
            )}
          </div>
          <div className="space-y-2">
            {alerts.alerts
              .filter((a: any) => a.type !== "entity_summary" && a.type !== "top_entities")
              .map((alert: any, i: number) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 p-4 rounded-xl transition-colors cursor-pointer ${
                    alert.severity === "critical"
                      ? "bg-red-50 hover:bg-red-100 border border-red-100"
                      : alert.severity === "warning"
                      ? "bg-amber-50 hover:bg-amber-100 border border-amber-100"
                      : "bg-gray-50 hover:bg-gray-100 border border-gray-100"
                  }`}
                >
                  {alert.severity === "critical" ? (
                    <AlertCircle size={20} className="text-red-500 mt-0.5 flex-shrink-0" />
                  ) : alert.severity === "warning" ? (
                    <AlertTriangle size={20} className="text-amber-500 mt-0.5 flex-shrink-0" />
                  ) : (
                    <Info size={20} className="text-blue-500 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{alert.title}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{alert.message}</p>
                  </div>
                  <ChevronRight size={16} className="text-gray-400 flex-shrink-0 mt-1" />
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Three Columns: Stats + Intelligence */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Documents */}
        <Link
          href="/dashboard/documents"
          className="bg-white rounded-2xl border border-gray-200 p-5 hover:border-brand-300 hover:shadow-sm transition-all group"
        >
          <FileText size={20} className="text-blue-500 mb-3" />
          <p className="text-2xl font-bold text-gray-900">{usage?.document_count ?? "..."}</p>
          <p className="text-sm text-gray-500">Documents indexed</p>
          <p className="text-xs text-brand-600 mt-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
            View all <ChevronRight size={12} />
          </p>
        </Link>

        {/* Entities / Knowledge Graph */}
        <Link
          href="/dashboard/graph"
          className="bg-white rounded-2xl border border-gray-200 p-5 hover:border-brand-300 hover:shadow-sm transition-all group"
        >
          <TrendingUp size={20} className="text-purple-500 mb-3" />
          <p className="text-2xl font-bold text-gray-900">{usage?.entity_count ?? "..."}</p>
          <p className="text-sm text-gray-500">Entities discovered</p>
          <div className="flex flex-wrap gap-1 mt-2">
            {alerts?.alerts
              ?.find((a: any) => a.type === "entity_summary")
              ?.entity_counts &&
              Object.entries(
                alerts.alerts.find((a: any) => a.type === "entity_summary").entity_counts
              )
                .slice(0, 3)
                .map(([type, count]) => (
                  <span
                    key={type}
                    className="text-[10px] bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded"
                  >
                    {count as number} {type}s
                  </span>
                ))}
          </div>
        </Link>

        {/* Credits */}
        <Link
          href="/dashboard/usage"
          className="bg-white rounded-2xl border border-gray-200 p-5 hover:border-brand-300 hover:shadow-sm transition-all group"
        >
          <Search size={20} className="text-green-500 mb-3" />
          <p className="text-sm font-medium text-gray-900">Q&A is FREE</p>
          <p className="text-xs text-gray-500 mt-1">Unlimited questions, always</p>
          {usage && (
            <div className="mt-3">
              <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                <span>AI credits</span>
                <span>{usage.credits_used.toFixed(1)} / {usage.credits_included}</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div
                  className="bg-green-500 h-1.5 rounded-full"
                  style={{
                    width: `${Math.min(100, (usage.credits_used / usage.credits_included) * 100)}%`,
                  }}
                />
              </div>
            </div>
          )}
        </Link>
      </div>

      {/* Recent Activity */}
      {docs?.documents?.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Recent Documents</h3>
            <Link href="/dashboard/documents" className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
              View all <ChevronRight size={12} />
            </Link>
          </div>
          <div className="space-y-2">
            {docs.documents.map((doc: any) => (
              <div
                key={doc.id}
                className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors"
              >
                <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText size={14} className="text-blue-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                  <p className="text-xs text-gray-500">{doc.summary?.slice(0, 80) || doc.doc_type || "Processing..."}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {doc.doc_type && (
                    <span className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                      {doc.doc_type}
                    </span>
                  )}
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full ${
                      doc.status === "enriched"
                        ? "bg-green-50 text-green-700"
                        : "bg-yellow-50 text-yellow-700"
                    }`}
                  >
                    {doc.entity_count > 0 ? `${doc.entity_count} entities` : doc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function getTimeOfDay() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}

function calculateComplianceScore(alerts: any, usage: any): number {
  if (!alerts || !usage) return 0;

  let score = 100;

  for (const alert of alerts.alerts || []) {
    if (alert.severity === "critical") score -= 15;
    else if (alert.severity === "warning") score -= 8;
    else if (alert.type === "missing_review") score -= alert.count * 2;
    else if (alert.type === "unclassified") score -= alert.count * 1;
  }

  // Bonus for having documents enriched
  if (usage.document_count > 0) score = Math.max(score, 30);

  return Math.max(0, Math.min(100, Math.round(score)));
}
