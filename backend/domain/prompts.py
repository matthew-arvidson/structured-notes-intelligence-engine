"""
Prompt library for the Structured Notes Intelligence Engine.

Ported and restructured from Prompts_v2.txt (structured-notes-final).
Each prompt is a Python string constant — import and use directly in nodes.

Prompts are ordered to match the pipeline:
  1. EXTRACT      — full-scope field extraction (Prompt 1 from v2)
  2. CLASSIFY     — multi-tag structure classification (Prompt 2)
  3. CONFIDENCE   — per-field confidence scoring (Prompt 3)
  4. CONFLICTS    — inconsistency / ambiguity detection (Prompt 4)
  5. SCHEMA_MAP   — map to UEQSN schema (Prompt 5)
  6. REPORT       — analyst markdown report (Prompt 6)

Usage:
    from backend.domain.prompts import EXTRACT_PROMPT, CLASSIFY_PROMPT
    messages = [{"role": "system", "content": EXTRACT_PROMPT}, ...]
"""

# ─── Prompt 1: Full-Scope Feature Extraction ──────────────────────────────────

EXTRACT_PROMPT = """You are a structured product analyst. Read the following term sheet excerpt and extract all relevant features used in the classification and downstream structuring of equity-linked structured notes.

Extract and return a JSON object using the fields below, filling in null if not available or clearly defined in the provided text. Do not infer values not explicitly stated.

Return ONLY a valid JSON object with no markdown wrappers, no commentary.

Fields to extract:

CORE STRUCTURE:
  Issuer, TradeDate, SettlementDate, MaturityDate, Notional, Currency,
  Underlying, UnderlyingAsset, StartingValue

OBSERVATIONS / SCHEDULES:
  ObservationDates, CallSchedule, CallPaymentDates, ContingentPaymentDates

COUPON FEATURES:
  CouponType (Contingent / Fixed / Digital / Range Accrual / None),
  CouponRate, CouponFrequency, CouponBarrier, CouponMemory, CouponFormula,
  MinimumCoupon, MaximumCoupon

CALL FEATURES:
  CallType (Auto-callable / Issuer Callable / None),
  CallLevel, CallPremium, CallAmount, CallPayoutStructure, CallSettlementLag

BARRIER / TRIGGER:
  BarrierType (Knock-In / Knock-Out / European / American / Bermudan / None),
  BarrierLevel, BarrierCondition, ThresholdValue, KnockInType, KnockOutType

PAYOFF STRUCTURE:
  FinalRedemptionLogic, RedemptionType, RedemptionLogic, RedemptionStructure,
  DownsideRiskDescription, KnockConditions

PROTECTION / PARTICIPATION:
  PrincipalProtectionPercentage, ParticipationRate

ACCRUAL (Range/Step):
  AccrualRangeLower, AccrualRangeUpper, AccrualFrequency

OTHER:
  CalculationAgent, ObservationTiming, InitialEstimatedValue,
  SecurityIdentifier (CUSIP, ISIN), IssuerCreditRating, GuarantorCreditRating,
  TaxCharacterization, StructuringNotes

Term sheet excerpt:
{text}"""


# Core-only extraction for MEDIUM risk tier (fewer fields, lower token cost)
EXTRACT_CORE_PROMPT = """You are a structured product analyst. Extract only the core identity and risk fields from the following term sheet excerpt.

Return ONLY a valid JSON object with no markdown wrappers.

Fields to extract:
  Issuer, TradeDate, SettlementDate, MaturityDate, Underlying, UnderlyingAsset,
  CouponType, CouponBarrier, BarrierType, BarrierLevel, CallType,
  PrincipalProtectionPercentage, SecurityIdentifier (CUSIP, ISIN),
  FinalRedemptionLogic, DownsideRiskDescription

Term sheet excerpt:
{text}"""


# Metadata-only extraction for LOW risk tier
EXTRACT_META_PROMPT = """Extract only the basic identifying information from the following term sheet excerpt.

Return ONLY a valid JSON object with no markdown wrappers.

Fields: Issuer, TradeDate, SettlementDate, MaturityDate, Underlying, SecurityIdentifier (CUSIP, ISIN)

Term sheet excerpt:
{text}"""


# ─── Prompt 2: Multi-Tag Classification ───────────────────────────────────────

CLASSIFY_PROMPT = """Based on the following extracted features from a structured note, determine the note's structural profile using a multi-tag classification system.

Assign as many tags as necessary to fully describe the structure. Tags should represent distinct structural features such as:
- Payoff type: Phoenix, Reverse Convertible, Digital, AutoCallable, Range Accrual, Principal Protected
- Coupon logic: Contingent Coupon, Memory Feature, Fixed Coupon, Range Accrual
- Call mechanics: Auto-callable, Issuer Callable, No Call
- Downside features: Knock-In, Principal-at-Risk, Principal Protected, Equity Delivery
- Underlying exposure: Worst-of, Basket, Single Asset

Return ONLY a valid JSON object:
{{
  "structure_tags": ["Phoenix", "Issuer Callable", "Contingent Coupon"],
  "tag_confidence_scores": {{"Phoenix": 98, "Issuer Callable": 95, "Contingent Coupon": 100}},
  "tag_rationale": {{"Phoenix": "rationale only required if confidence < 95"}}
}}

Extracted features:
{extracted_features_json}"""


# ─── Prompt 3: Confidence Quantification ──────────────────────────────────────

CONFIDENCE_PROMPT = """Review the structured note features below. For each key field, assign a confidence score and a brief reason explaining that score.

Score from 0 to 100 based on:
- Clarity of the source text
- Likelihood the extracted value is correct
- Alignment with the identified structure type

Return ONLY a valid JSON object mapping each field name to an object with "score" (integer) and "reason" (one concise sentence):
{{
  "CouponRate": {{"score": 95, "reason": "Explicitly stated as 10.00% per annum in the Coupon section."}},
  "BarrierLevel": {{"score": 72, "reason": "Percentage stated but it is unclear whether this is observed continuously or at maturity only."}},
  "CallSchedule": {{"score": 88, "reason": "Dates listed but payment lag not confirmed in the schedule table."}},
  "FinalRedemptionLogic": {{"score": 61, "reason": "Redemption description is ambiguous — two interpretations are possible based on barrier breach wording."}}
}}

Include only fields that were actually extracted (non-null values).
Keep reasons concise and analyst-facing — one sentence maximum.

Extracted features:
{extracted_features_json}

Structure tags: {structure_tags}"""


# ─── Prompt 4: Conflict & Ambiguity Detection ─────────────────────────────────

CONFLICTS_PROMPT = """Analyze the following structured note features and structure tags. Identify any inconsistencies, contradictions, or ambiguities that require analyst attention.

Look for:
- Tag conflicts (e.g., "Principal Protected" AND "Principal-at-Risk" both tagged)
- Missing required fields for identified structure types
- Fields with low confidence (<90) that affect material terms
- Logical contradictions (e.g., KnockInType present but BarrierType is None)
- Ambiguous redemption logic that could be interpreted multiple ways

Return ONLY a valid JSON array. Return an empty array [] if no conflicts found:
[
  {{
    "issue": "description of the conflict or ambiguity",
    "fields_involved": ["field1", "field2"],
    "severity": "high | medium | low",
    "recommendation": "suggested analyst action"
  }}
]

Extracted features:
{extracted_features_json}

Structure tags: {structure_tags}

Confidence scores: {confidence_scores_json}"""


# ─── Prompt 5: Schema Mapping ─────────────────────────────────────────────────

SCHEMA_MAP_PROMPT = """Map the extracted features and structure tags into the Universal Equity Structured Note (UEQSN) schema format.

Rules:
- Use null only for fields that are genuinely absent from the structure (not just missing from the text)
- Place all known fields in their correct schema section
- Include structure_tags at the top level
- Do not fabricate values not present in the input

Return ONLY a valid JSON object matching the UEQSN schema structure.

Structure tags: {structure_tags}
Extracted features: {extracted_features_json}"""


# ─── Prompt 6: Analyst Report Generation ──────────────────────────────────────

REPORT_PROMPT = """You are an equity structured note analyst. Generate a comprehensive markdown analyst report based on the extracted features, structure tags, confidence scores, and any detected conflicts.

Confidence status icons:
  ✅  >= 98%  High confidence
  ⚠️  90-97%  Moderate confidence — flag for review
  ❌  < 90%   Low confidence — requires analyst validation
  ➖  N/A     Structurally null — not applicable for this note type

Rule: Do NOT mark a field ❌ if it is structurally null for this note type — use ➖ instead.

Use the following markdown structure:

---
## Structured Note Analyst Report

### Simple Summary
[2-3 sentence plain-language description of the note's mechanics, risks, and return profile — suitable for non-technical stakeholders]

**Product Title**: [title or descriptor]
**Issuer**: [Issuer] | **Guarantor**: [if applicable]
**CUSIP**: [CUSIP] | **ISIN**: [ISIN]
**Structure Type**: [primary tag]

### Key Dates
| Event | Date |
|---|---|
| Trade Date | |
| Settlement Date | |
| Maturity Date | |

### Underlying Asset(s)
[List each underlier with ticker, name, starting value. Note if Worst-of or Basket.]

### Coupon / Yield Structure
| Feature | Value | Confidence | Status |
|---|---|---|---|
| Type | | | |
| Rate | | | |
| Frequency | | | |
| Barrier | | | |
| Memory Feature | | | |

### Call Mechanics
| Feature | Value | Confidence | Status |
|---|---|---|---|
| Type | | | |
| Schedule | | | |
| Call Level | | | |

### Barrier / Trigger Structure
| Feature | Value | Confidence | Status |
|---|---|---|---|
| Type | | | |
| Level | | | |
| Condition | | | |

### Redemption Logic
[Describe final redemption. Include downside exposure. State if Principal Protected, At Risk, or Contingent.]

### Structure Tags
| Tag | Confidence | Rationale |
|---|---|---|

### Conflict & Ambiguity Review
[List any conflicts or mark "No conflicts detected."]

---

Always use formal, concise language suitable for an internal structuring or risk analyst.

Input data:
Extracted features: {extracted_features_json}
Structure tags: {structure_tags_json}
Confidence scores: {confidence_scores_json}
Conflicts: {conflicts_json}"""
