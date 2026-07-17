"use client";

import { useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import { StructuredNote } from "@/types";

ModuleRegistry.registerModules([AllCommunityModule]);

const TIER_COLORS: Record<string, string> = {
  high:   "text-red-400",
  medium: "text-yellow-400",
  low:    "text-green-400",
};

type GridProps = {
  notes: StructuredNote[];
  onCusipClick?: (cusip: string) => void;
};

export default function Grid({ notes, onCusipClick }: GridProps) {
  const gridRef = useRef<AgGridReact<StructuredNote>>(null);

  const columnDefs: ColDef<StructuredNote>[] = [
    {
      field: "cusip",
      headerName: "CUSIP",
      flex: 1,
      cellRenderer: (params: { value: string }) => (
        <button
          className="text-blue-400 hover:underline hover:text-blue-300 font-mono"
          onClick={() => onCusipClick?.(params.value)}
        >
          {params.value}
        </button>
      ),
    },
    { field: "issuer",          headerName: "Issuer",        flex: 2 },
    { field: "note_type",       headerName: "Type",          flex: 1.5 },
    {
      field: "risk_tier",
      headerName: "Tier",
      flex: 0.8,
      cellRenderer: (params: { value: string }) => (
        <span className={`font-semibold uppercase text-xs ${TIER_COLORS[params.value] ?? ""}`}>
          {params.value}
        </span>
      ),
    },
    {
      field: "barrier_level",
      headerName: "Barrier",
      flex: 0.8,
      valueFormatter: (p) => p.value != null ? `${p.value}%` : "—",
    },
    { field: "settlement_date", headerName: "Settlement",    flex: 1 },
    { field: "maturity_date",   headerName: "Maturity",      flex: 1 },
    {
      field: "has_worst_of",
      headerName: "Worst-of",
      flex: 0.7,
      valueFormatter: (p) => p.value ? "Yes" : "—",
    },
  ];

  return (
    <div className="flex-1 min-h-0 flex flex-col w-full">
      <div className="ag-theme-quartz-dark flex-1 min-h-0 w-full">
        <AgGridReact
          ref={gridRef}
          rowData={notes}
          columnDefs={columnDefs}
          rowHeight={32}
          defaultColDef={{ sortable: true, filter: true, resizable: true }}
        />
      </div>
    </div>
  );
}
