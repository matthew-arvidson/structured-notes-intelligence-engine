"use client";

import { useState, useEffect, useCallback } from "react";
import Header from "./Components/HeaderSubComponents/header";
import CusipFilter from "./Components/HeaderSubComponents/CusipFilter";
import Grid from "./Components/IndexGridComponents/Grid";
import ImportPanel from "./Components/ImportComponents/ImportPanel";
import SelectedCusipDetails from "./Components/CusipDetailsPanel/SelectedCusipDetails";
import { StructuredNote, StructuredNoteDetail } from "@/types";

const API = "";

export default function HomePage() {
  const [notes,          setNotes]          = useState<StructuredNote[]>([]);
  const [issuers,        setIssuers]        = useState<string[]>([]);
  const [search,         setSearch]         = useState("");
  const [selectedIssuer, setSelectedIssuer] = useState("");
  const [riskTier,       setRiskTier]       = useState("");
  const [isImportOpen,   setIsImportOpen]   = useState(false);
  const [importKey,      setImportKey]      = useState(0);
  const [selectedCusip,  setSelectedCusip]  = useState<string | null>(null);
  const [cusipDetail,    setCusipDetail]    = useState<StructuredNoteDetail | null>(null);
  const [loading,        setLoading]        = useState(false);

  const fetchNotes = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedIssuer) params.set("issuer", selectedIssuer);
      if (riskTier)       params.set("risk_tier", riskTier);
      const r = await fetch(`${API}/api/notes?${params}`);
      const d = await r.json();
      const rows: StructuredNote[] = d.notes ?? [];
      setNotes(rows);
      // Build issuer list from results (deduplicated)
      const seen = new Set<string>();
      rows.forEach((n) => { if (n.issuer) seen.add(n.issuer); });
      setIssuers((prev) => {
        const merged = new Set([...prev, ...seen]);
        return Array.from(merged).sort();
      });
    } catch (e) {
      console.error("Failed to fetch notes", e);
    } finally {
      setLoading(false);
    }
  }, [selectedIssuer, riskTier]);

  useEffect(() => { fetchNotes(); }, [fetchNotes]);

  const fetchCusipDetail = useCallback(async (cusip: string) => {
    try {
      const r = await fetch(`${API}/api/notes/${cusip}`);
      const d = await r.json();
      setCusipDetail(d);
    } catch (e) {
      console.error("Failed to fetch note detail", e);
    }
  }, []);

  useEffect(() => {
    if (!selectedCusip) { setCusipDetail(null); return; }
    fetchCusipDetail(selectedCusip);
  }, [selectedCusip, fetchCusipDetail]);

  // Client-side CUSIP search filter
  const filtered = search
    ? notes.filter(
        (n) =>
          n.cusip.toLowerCase().includes(search.toLowerCase()) ||
          (n.issuer ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : notes;

  const sidePanelOpen = isImportOpen || (!!selectedCusip && !!cusipDetail);

  return (
    <div className="flex flex-col h-full min-h-0">
      <Header onImportClick={() => { setSelectedCusip(null); setImportKey((k) => k + 1); setIsImportOpen(true); }}>
        <CusipFilter
          search={search}
          onSearchChange={setSearch}
          issuers={issuers}
          selectedIssuer={selectedIssuer}
          onIssuerChange={setSelectedIssuer}
          riskTier={riskTier}
          onRiskTierChange={setRiskTier}
        />
      </Header>

      {/* Status bar */}
      <div className="px-3 py-0.5 text-xs text-gray-500 bg-[#1a1b1c] shrink-0">
        {loading ? "Loading…" : `${filtered.length} note${filtered.length !== 1 ? "s" : ""}`}
      </div>

      {/* Grid + Side Panel */}
      <div className="flex flex-1 gap-2 min-h-0 p-1">
        <div className={`flex flex-col flex-1 min-h-0 transition-all duration-300 ${sidePanelOpen ? "basis-3/5" : "basis-full"}`}>
          <Grid
            notes={filtered}
            onCusipClick={(cusip) => { setIsImportOpen(false); setSelectedCusip(cusip); }}
          />
        </div>

        {sidePanelOpen && (
          <div className="flex flex-col basis-2/5 min-h-0 transition-all duration-300 rounded shadow overflow-hidden">
            {isImportOpen ? (
              <ImportPanel
                key={importKey}
                onClose={() => setIsImportOpen(false)}
                onIngestComplete={(cusip?: string) => {
                  fetchNotes();
                  if (cusip && selectedCusip === cusip) fetchCusipDetail(cusip);
                }}
                onOpenNote={(cusip) => { setIsImportOpen(false); setSelectedCusip(cusip); }}
              />
            ) : cusipDetail ? (
              <SelectedCusipDetails
                key={cusipDetail.cusip}
                note={cusipDetail}
                onClose={() => setSelectedCusip(null)}
              />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
