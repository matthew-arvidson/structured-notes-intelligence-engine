"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface HeaderProps {
  children?: React.ReactNode;
  onImportClick?: () => void;
}

export default function Header({ children, onImportClick }: HeaderProps) {
  const pathname = usePathname();

  return (
    <header className="bg-[#2E3436] text-white flex flex-row items-center justify-between px-4 py-1 shrink-0">
      {/* Brand */}
      <section className="flex items-center gap-3">
        <div className="text-blue-400 font-bold text-lg tracking-tight">SNIE</div>
        <div className="hidden sm:block text-gray-400 text-xs">Structured Notes Intelligence Engine</div>
      </section>

      {/* Filters (injected by page) */}
      <section className="flex-1">{children}</section>

      {/* Nav actions */}
      <section className="flex gap-2 items-center">
        <Link href="/">
          <button className={`btn btn-sm ${pathname === "/" ? "btn-primary" : "btn-ghost"}`}>
            Notes
          </button>
        </Link>
        <Link href="/query">
          <button className={`btn btn-sm ${pathname === "/query" ? "btn-primary" : "btn-ghost"}`}>
            Ask a Question
          </button>
        </Link>
        {onImportClick && (
          <button className="btn btn-sm btn-outline" onClick={onImportClick}>
            + Ingest PDF
          </button>
        )}
      </section>
    </header>
  );
}
