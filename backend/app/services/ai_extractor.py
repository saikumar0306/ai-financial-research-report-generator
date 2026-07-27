"""
ai_extractor.py — Sends extracted document text to Google Gemini and returns
a validated, structured JSON object containing all report fields.

Design decisions:
    - Uses google-genai SDK (not deprecated google-generativeai).
    - Tries a curated list of working models in sequence (fallback chain).
    - Implements a two-pass extraction strategy:
        Pass 1: Full extraction from the complete document.
        Pass 2: Targeted retry ONLY if critical fields are missing.
    - All blocking Gemini calls are synchronous (called via run_in_executor
      from the async router to avoid blocking the event loop).
    - Detailed timing is logged for each Gemini call.
"""

import json
import re
import time
from typing import Any

import google.genai as genai
from google.genai import types

from config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Working model fallback chain (verified against this API key) ──────────────
FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
]

# ── Expected JSON schema (used for validation + defaults) ─────────────────────
DEFAULT_STRUCTURE: dict[str, Any] = {
    "company_name": "",
    "recommendation": "Not Available",
    "industry": "Not Available",
    "market_cap": "Not Available",
    "current_price": "Not Available",
    "target_price": "Not Available",
    "business_summary": "Not Available",
    "investment_thesis": "Not Available",
    "strengths": [],
    "risks": [],
    "future_outlook": "Not Available",
    "financial_tables": {
        "revenue": [],
        "ebitda": [],
        "net_profit": [],
        "eps": [],
        "roe": [],
        "debt_equity": [],
        "operating_margin": [],
        "net_margin": [],
    },
    "highlights": [],
    "shareholding": {
        "promoters": "Not Available",
        "fii": "Not Available",
        "dii": "Not Available",
        "public": "Not Available",
    },
    "valuation": "Not Available",
    "peer_comparison": [],
    "key_metrics": {},
}

# ── Primary extraction prompt ─────────────────────────────────────────────────
EXTRACTION_PROMPT = """You are an expert financial analyst specializing in equity research for Indian markets.

Your task is to perform a THOROUGH and DEEP analysis of the following financial document for: {company_name}

CRITICAL INSTRUCTIONS:
1. Read EVERY section of the document carefully — including tables, footnotes, and appendices.
2. Extract ALL numerical data from financial tables even if column headers are unclear.
3. If a value appears in multiple formats (e.g., "₹1,234 Cr" or "1234.56"), standardize it.
4. For financial tables: scan ALL years/periods mentioned across ALL pages.
5. For shareholding: look for "promoter", "FII", "DII", "institutional", "public", "retail" percentages.
6. NEVER return "Not Available" if the data can be reasonably inferred from context.
7. If exact numbers are not found, provide your best estimate based on what IS in the document.
8. Generate an investment thesis and business summary based on ALL available information.
9. Return ONLY a raw JSON object — no markdown fences, no explanation text.

DOCUMENT CONTENT:
{document_text}

Return EXACTLY this JSON structure (fill every field as completely as possible):

{{
  "company_name": "{company_name}",
  "recommendation": "BUY or SELL or HOLD or ACCUMULATE or REDUCE (choose based on financials, or Not Available)",
  "industry": "sector/industry from document",
  "market_cap": "₹X Cr (from document or estimate)",
  "current_price": "₹X.XX (CMP from document)",
  "target_price": "₹X.XX (target price from document or analyst estimate)",
  "business_summary": "3-5 sentence description of what the company does, its core business, revenue model, and market position",
  "investment_thesis": "4-6 sentences explaining WHY this is/isn't a good investment based on growth, profitability, valuation, competitive position",
  "strengths": [
    "Specific strength 1 with supporting data",
    "Specific strength 2 with supporting data",
    "Specific strength 3",
    "Specific strength 4",
    "Specific strength 5"
  ],
  "risks": [
    "Specific risk 1 with impact assessment",
    "Specific risk 2",
    "Specific risk 3",
    "Specific risk 4"
  ],
  "future_outlook": "3-4 sentences on growth prospects, upcoming catalysts, guidance, expansion plans",
  "financial_tables": {{
    "revenue":          [{{"year": "FY22", "value": 1234.5}}, {{"year": "FY23", "value": 1456.2}}, {{"year": "FY24", "value": 1678.9}}],
    "ebitda":           [{{"year": "FY22", "value": 234.5}}, {{"year": "FY23", "value": 267.3}}],
    "net_profit":       [{{"year": "FY22", "value": 123.4}}, {{"year": "FY23", "value": 145.6}}],
    "eps":              [{{"year": "FY22", "value": 12.3}}, {{"year": "FY23", "value": 14.5}}],
    "roe":              [{{"year": "FY22", "value": 18.5}}, {{"year": "FY23", "value": 20.1}}],
    "debt_equity":      [{{"year": "FY22", "value": 0.45}}, {{"year": "FY23", "value": 0.38}}],
    "operating_margin": [{{"year": "FY22", "value": 22.1}}, {{"year": "FY23", "value": 23.5}}],
    "net_margin":       [{{"year": "FY22", "value": 12.5}}, {{"year": "FY23", "value": 13.2}}]
  }},
  "highlights": [
    "Revenue grew X% YoY to ₹Y Cr in FY24",
    "EBITDA margin expanded/contracted X bps to Y%",
    "Net profit increased/decreased by X% to ₹Y Cr",
    "Debt-to-equity ratio stands at X (healthy/concerning)",
    "ROE of X% indicates strong/weak capital efficiency",
    "Dividend yield of X% provides income cushion"
  ],
  "shareholding": {{
    "promoters": "X.X%",
    "fii": "X.X%",
    "dii": "X.X%",
    "public": "X.X%"
  }},
  "valuation": "2-3 sentences on current valuation: P/E of Xx vs sector average of Xx, EV/EBITDA of Xx, whether stock is fairly/under/over valued",
  "peer_comparison": [
    {{"company": "{company_name}", "market_cap": "₹X Cr", "pe": "Xx", "revenue": "₹Y Cr", "roe": "X%"}},
    {{"company": "Peer 1 Name", "market_cap": "₹X Cr", "pe": "Xx", "revenue": "₹Y Cr", "roe": "X%"}},
    {{"company": "Peer 2 Name", "market_cap": "₹X Cr", "pe": "Xx", "revenue": "₹Y Cr", "roe": "X%"}}
  ],
  "key_metrics": {{
    "pe_ratio": "Xx",
    "pb_ratio": "Xx",
    "dividend_yield": "X.X%",
    "roce": "X.X%",
    "roe": "X.X%",
    "debt_equity": "X.Xx"
  }}
}}

RULES:
- Financial table values MUST be plain numbers (float), not strings.
- Years MUST be in FY format: FY22, FY23, FY24, FY25E, FY26E etc.
- Include AT LEAST 2-3 years of financial data wherever visible in the document.
- Use "Not Available" ONLY as a true last resort when data is completely absent.
- The response MUST be valid JSON parseable by Python's json.loads().
"""

# ── Targeted follow-up prompt (Pass 2 for missing fields) ────────────────────
FOLLOWUP_PROMPT = """You are an expert financial analyst. The following financial document was partially analyzed.

Some fields are still missing. Please focus SPECIFICALLY on extracting these fields from the document.

Company: {company_name}
Missing fields: {missing_fields}

DOCUMENT CONTENT:
{document_text}

Return ONLY a JSON object with JUST the missing fields. Example:
{{"recommendation": "BUY", "target_price": "₹550", "shareholding": {{"promoters": "52%", "fii": "18%", "dii": "15%", "public": "15%"}}}}

Extract as much as you can from context. Return valid JSON only — no markdown.
"""


def extract_financial_data_sync(company_name: str, document_text: str) -> dict:
    """
    Synchronous Gemini extraction call.

    This is a SYNCHRONOUS function and MUST be called via run_in_executor()
    from async FastAPI endpoints. It blocks the thread it runs in.

    Strategy:
        1. Build primary prompt and call Gemini (with model fallback chain).
        2. Merge with DEFAULT_STRUCTURE.
        3. If critical fields are still missing, run a second targeted pass.
        4. Return validated, merged result.

    Args:
        company_name:   The company name provided by the user.
        document_text:  Pre-extracted text content from the uploaded document.

    Returns:
        Validated dict matching DEFAULT_STRUCTURE (missing fields filled with defaults).

    Raises:
        RuntimeError: If Gemini fails on all models or returns unparseable JSON.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Please add it to backend/.env")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # ── Build model list (primary + fallbacks, no duplicates) ─────────────────
    models_to_try = [settings.GEMINI_MODEL]
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    logger.info(
        f"[AI EXTRACT ] company={company_name!r}  "
        f"doc_chars={len(document_text):,}  "
        f"models={models_to_try}"
    )

    # ── Pass 1: Full extraction ────────────────────────────────────────────────
    prompt = EXTRACTION_PROMPT.format(
        company_name=company_name,
        document_text=document_text,
    )

    raw_text, used_model = _call_gemini(client, models_to_try, prompt, pass_num=1)
    extracted = _parse_json_response(raw_text)
    validated = _merge_with_defaults(extracted, company_name)

    # ── Pass 2: Targeted retry for critical missing fields ────────────────────
    missing = _find_critical_missing(validated)
    if missing:
        logger.info(f"[AI PASS 2  ] Missing critical fields: {missing} — running targeted pass")
        followup_prompt = FOLLOWUP_PROMPT.format(
            company_name=company_name,
            missing_fields=", ".join(missing),
            document_text=document_text,
        )
        try:
            followup_raw, _ = _call_gemini(client, models_to_try, followup_prompt, pass_num=2)
            followup_data = _parse_json_response(followup_raw)
            # Merge only the missing fields from pass 2
            for field in missing:
                if field in followup_data and followup_data[field] not in (None, "", "Not Available", [], {}):
                    validated[field] = followup_data[field]
                    logger.info(f"[AI PASS 2  ] Recovered field: {field!r}")
        except Exception as exc:
            logger.warning(f"[AI PASS 2  ] Follow-up extraction failed (non-fatal): {exc}")

    logger.info(
        f"[AI EXTRACT ] Extraction complete — company={company_name!r}  "
        f"model={used_model!r}  "
        f"missing_after={_find_critical_missing(validated)}"
    )
    return validated


def _call_gemini(
    client,
    models_to_try: list[str],
    prompt: str,
    pass_num: int = 1,
) -> tuple[str, str]:
    """
    Attempt Gemini API call across model fallback chain.

    Returns:
        (raw_text, model_name_used)

    Raises:
        RuntimeError: If all models fail.
    """
    last_error = None

    for model_name in models_to_try:
        t0 = time.perf_counter()
        try:
            logger.info(f"[GEMINI     ] Pass {pass_num} — model={model_name!r}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,       # Low temp for consistent JSON
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
            elapsed = time.perf_counter() - t0
            raw_text = (response.text or "").strip()

            if raw_text:
                logger.info(
                    f"[GEMINI     ] Pass {pass_num} SUCCESS — "
                    f"model={model_name!r}  "
                    f"chars={len(raw_text):,}  "
                    f"elapsed={elapsed:.2f}s"
                )
                return raw_text, model_name
            else:
                logger.warning(f"[GEMINI     ] Pass {pass_num} — model={model_name!r} returned empty response")

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            logger.warning(
                f"[GEMINI     ] Pass {pass_num} FAILED — "
                f"model={model_name!r}  "
                f"elapsed={elapsed:.2f}s  "
                f"error={exc}"
            )
            last_error = exc

    raise RuntimeError(
        f"All Gemini models failed for pass {pass_num}. "
        f"Last error: {last_error}. "
        f"Tried: {models_to_try}"
    )


def _find_critical_missing(data: dict) -> list[str]:
    """
    Return list of critical fields that are still missing/default after pass 1.
    """
    critical = []
    if data.get("business_summary") in (None, "", "Not Available"):
        critical.append("business_summary")
    if data.get("recommendation") in (None, "", "Not Available"):
        critical.append("recommendation")
    if not data.get("strengths"):
        critical.append("strengths")
    if not data.get("financial_tables", {}).get("revenue"):
        critical.append("financial_tables.revenue")
    return critical


def _parse_json_response(raw: str) -> dict:
    """
    Attempt to parse Gemini's JSON response, stripping markdown fences if present.

    Raises:
        RuntimeError: If JSON cannot be parsed after all cleanup attempts.
    """
    if not raw:
        raise RuntimeError("Gemini returned an empty response.")

    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    # Attempt 1: Direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Extract outermost JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Attempt 3: Fix common issues (trailing commas, single quotes)
    try:
        fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)  # trailing commas
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    logger.error(f"Failed to parse Gemini JSON. Preview:\n{raw[:800]}")
    raise RuntimeError(
        "Gemini returned an invalid JSON response. "
        "Try again or use a simpler/shorter document."
    )


def _merge_with_defaults(data: dict, company_name: str) -> dict:
    """
    Deep-merge extracted data with DEFAULT_STRUCTURE.
    Ensures all required keys exist with appropriate fallback values.
    """
    import copy
    result = copy.deepcopy(DEFAULT_STRUCTURE)

    # Company name — prefer user input if AI missed it
    result["company_name"] = data.get("company_name") or company_name

    # Scalar text fields
    scalar_fields = [
        "recommendation", "industry", "market_cap", "current_price",
        "target_price", "business_summary", "investment_thesis",
        "future_outlook", "valuation",
    ]
    for field in scalar_fields:
        val = data.get(field)
        if val and str(val).strip() and str(val).strip() not in ("", "Not Available", "N/A"):
            result[field] = str(val).strip()

    # List fields (strings)
    for field in ["strengths", "risks", "highlights"]:
        val = data.get(field)
        if isinstance(val, list) and val:
            result[field] = [str(item) for item in val if item]

    # Peer comparison (list of dicts)
    pc = data.get("peer_comparison")
    if isinstance(pc, list) and pc:
        result["peer_comparison"] = pc

    # Financial tables
    ft = data.get("financial_tables", {})
    if isinstance(ft, dict):
        for metric in result["financial_tables"]:
            rows = ft.get(metric)
            if isinstance(rows, list) and rows:
                # Validate each row has year + numeric value
                valid_rows = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    y = row.get("year")
                    v = row.get("value")
                    if v is not None:
                        try:
                            v_float = float(v)
                            valid_rows.append({"year": str(y), "value": v_float})
                        except (TypeError, ValueError):
                            continue
                if valid_rows:
                    result["financial_tables"][metric] = valid_rows

    # Shareholding
    sh = data.get("shareholding", {})
    if isinstance(sh, dict):
        for key in result["shareholding"]:
            val = sh.get(key)
            if val and str(val).strip() and str(val).strip() != "Not Available":
                result["shareholding"][key] = str(val).strip()

    # Key metrics
    km = data.get("key_metrics", {})
    if isinstance(km, dict) and km:
        # Filter out empty/None values
        result["key_metrics"] = {
            k: str(v) for k, v in km.items()
            if v and str(v).strip() not in ("", "None", "Not Available", "N/A")
        }

    return result


# ── Async wrapper (called from router) ───────────────────────────────────────
async def extract_financial_data(company_name: str, document_text: str) -> dict:
    """
    Async wrapper that runs the blocking Gemini extraction in a thread pool.

    FastAPI endpoints MUST call this async function, not extract_financial_data_sync,
    to avoid blocking the event loop during Gemini API calls.
    """
    import asyncio
    import functools

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        functools.partial(extract_financial_data_sync, company_name, document_text),
    )
