import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-white flex flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Kompler
        </h1>
        <p className="text-xl text-gray-600 mb-2">
          AI Document Intelligence
        </p>
        <p className="text-lg text-gray-500 mb-8">
          Make your business documents work for you. Upload documents, and AI
          finds compliance gaps, expiring certifications, contradictions, and
          relationships your team would never spot manually.
        </p>

        <div className="flex gap-4 justify-center mb-12">
          <Link
            href="/dashboard"
            className="bg-brand-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-brand-700 transition-colors"
          >
            Open Dashboard
          </Link>
          <Link
            href="/dashboard/chat"
            className="border border-brand-600 text-brand-600 px-8 py-3 rounded-lg font-medium hover:bg-brand-50 transition-colors"
          >
            Ask Your Documents
          </Link>
        </div>

        <div className="grid grid-cols-3 gap-6 text-left">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="text-2xl mb-2">&#x1f4ca;</div>
            <h3 className="font-semibold text-gray-900 mb-1">Auto-Classify</h3>
            <p className="text-sm text-gray-500">
              AI classifies every document — SOPs, certificates, invoices — automatically.
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="text-2xl mb-2">&#x1f50d;</div>
            <h3 className="font-semibold text-gray-900 mb-1">Ask Anything</h3>
            <p className="text-sm text-gray-500">
              Ask questions in plain language. Get cited answers from your documents.
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="text-2xl mb-2">&#x26a0;&#xfe0f;</div>
            <h3 className="font-semibold text-gray-900 mb-1">Proactive Alerts</h3>
            <p className="text-sm text-gray-500">
              Know when certificates expire, SOPs go stale, or compliance gaps emerge.
            </p>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-12">
          Unlimited users. Usage-based pricing. Your data stays yours.
        </p>
      </div>
    </div>
  );
}
