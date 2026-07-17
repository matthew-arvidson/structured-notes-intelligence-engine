import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Structured Notes Intelligence Engine",
  description: "RAG-powered structured note analysis and audit",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="flex flex-col h-screen min-h-0 bg-[#141516] text-gray-300">
        <main className="flex-1 flex flex-col min-h-0">{children}</main>
        <footer className="flex-shrink-0 bg-[#042341] px-2 py-1 text-xs text-gray-500 text-center">
          Structured Notes Intelligence Engine — internal use only
        </footer>
      </body>
    </html>
  );
}
