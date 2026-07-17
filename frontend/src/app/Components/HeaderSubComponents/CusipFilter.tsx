"use client";

export default function CusipFilter({
  search,
  onSearchChange,
  issuers,
  selectedIssuer,
  onIssuerChange,
  riskTier,
  onRiskTierChange,
}: {
  search: string;
  onSearchChange: (v: string) => void;
  issuers: string[];
  selectedIssuer: string;
  onIssuerChange: (v: string) => void;
  riskTier: string;
  onRiskTierChange: (v: string) => void;
}) {
  return (
    <div className="w-full py-1 px-4 flex flex-wrap items-center gap-3">
      <input
        type="text"
        placeholder="Search CUSIP or issuer…"
        className="input input-bordered input-sm w-56 text-white bg-[#141516]"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />

      <select
        className="select select-sm select-bordered bg-[#141516] text-white w-44"
        value={selectedIssuer}
        onChange={(e) => onIssuerChange(e.target.value)}
      >
        <option value="">All Issuers</option>
        {issuers.map((i) => (
          <option key={i} value={i}>{i}</option>
        ))}
      </select>

      <select
        className="select select-sm select-bordered bg-[#141516] text-white w-36"
        value={riskTier}
        onChange={(e) => onRiskTierChange(e.target.value)}
      >
        <option value="">All Tiers</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>
    </div>
  );
}
