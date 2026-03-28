"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FileText,
  MessageCircle,
  BarChart3,
  Upload,
  Home,
  Network,
} from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/dashboard/documents", label: "Documents", icon: FileText },
  { href: "/dashboard/upload", label: "Upload", icon: Upload },
  { href: "/dashboard/chat", label: "Ask AI", icon: MessageCircle },
  { href: "/dashboard/graph", label: "Knowledge Graph", icon: Network },
  { href: "/dashboard/usage", label: "Usage", icon: BarChart3 },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen p-4 flex flex-col">
      <div className="mb-8 px-3">
        <h1 className="text-xl font-bold text-brand-700">Kompler</h1>
        <p className="text-xs text-gray-500 mt-1">Document Intelligence</p>
      </div>

      <nav className="flex-1 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-gray-200 pt-4 mt-4 px-3">
        <p className="text-xs text-gray-400">Demo Company</p>
        <p className="text-xs text-gray-400">Pro Plan</p>
      </div>
    </aside>
  );
}
