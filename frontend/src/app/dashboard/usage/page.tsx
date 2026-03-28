"use client";

import { useEffect, useState } from "react";
import { fetchUsage, fetchTransactions } from "@/lib/api";

export default function UsagePage() {
  const [usage, setUsage] = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);

  useEffect(() => {
    fetchUsage().then(setUsage).catch(console.error);
    fetchTransactions(50).then(setTransactions).catch(console.error);
  }, []);

  if (!usage) {
    return <div className="text-gray-500">Loading usage data...</div>;
  }

  const creditPercent = (usage.credits_used / usage.credits_included) * 100;
  const storagePercent = (usage.storage_used_gb / usage.storage_limit_gb) * 100;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Usage & Billing</h2>

      {/* Plan Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="font-semibold text-gray-900 text-lg capitalize">
              {usage.tier} Plan
            </h3>
            <p className="text-sm text-gray-500">
              {usage.credits_included.toLocaleString()} credits/month included
            </p>
          </div>
          <button className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700">
            Upgrade Plan
          </button>
        </div>

        {/* Credit Usage */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Credits</span>
            <span className="text-gray-900 font-medium">
              {usage.credits_used.toFixed(1)} / {usage.credits_included.toLocaleString()}
            </span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${
                creditPercent > 90
                  ? "bg-red-500"
                  : creditPercent > 70
                  ? "bg-yellow-500"
                  : "bg-brand-500"
              }`}
              style={{ width: `${Math.min(100, creditPercent)}%` }}
            />
          </div>
        </div>

        {/* Storage Usage */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Index Storage</span>
            <span className="text-gray-900 font-medium">
              {usage.storage_used_gb.toFixed(2)} / {usage.storage_limit_gb} GB
            </span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${
                storagePercent > 90 ? "bg-red-500" : "bg-blue-500"
              }`}
              style={{ width: `${Math.min(100, storagePercent)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-2xl font-bold text-gray-900">{usage.document_count}</p>
          <p className="text-sm text-gray-500">Documents indexed</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-2xl font-bold text-gray-900">{usage.entity_count}</p>
          <p className="text-sm text-gray-500">Entities discovered</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-2xl font-bold text-green-600">FREE</p>
          <p className="text-sm text-gray-500">Q&A queries (unlimited)</p>
        </div>
      </div>

      {/* Credit Costs Reference */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 mb-6">
        <h3 className="font-semibold text-blue-900 mb-3">Credit Costs</h3>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-blue-800">Classification (LIGHT)</span>
            <span className="font-medium text-blue-900">0.5 credits</span>
          </div>
          <div className="flex justify-between">
            <span className="text-blue-800">Entity Extraction (STANDARD)</span>
            <span className="font-medium text-blue-900">2.0 credits</span>
          </div>
          <div className="flex justify-between">
            <span className="text-blue-800">Deep Analysis (DEEP)</span>
            <span className="font-medium text-blue-900">5.0 credits</span>
          </div>
          <div className="flex justify-between">
            <span className="text-blue-800">Search & Q&A</span>
            <span className="font-medium text-green-700">FREE</span>
          </div>
        </div>
      </div>

      {/* Transaction History */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Recent Transactions</h3>
        {transactions.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b">
                <th className="pb-2">Action</th>
                <th className="pb-2">Credits</th>
                <th className="pb-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t: any, i: number) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-2 text-sm capitalize text-gray-900">{t.action}</td>
                  <td className="py-2 text-sm text-gray-600">{t.credits.toFixed(1)}</td>
                  <td className="py-2 text-xs text-gray-500">
                    {new Date(t.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-gray-500">No transactions yet.</p>
        )}
      </div>
    </div>
  );
}
