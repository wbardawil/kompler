import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kompler — AI Document Intelligence",
  description: "Make your business documents work for you",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
