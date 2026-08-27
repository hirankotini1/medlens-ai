import re
import os
import sys

# Add path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from disease_prediction.api.report_extractor import PARAMETER_ALIASES, CANONICAL_REF_RANGES, normalize_param_name, is_metadata_or_header_field

test_lines = [
    "Hemoglobin | 14.8 | g/dL | 13.0–17.0 | Normal",
    "RBC Count | 5.0 | million/uL | 4.5–5.9 | Normal",
    "WBC Count | 6800 | /uL | 4000–11000 | Normal",
    "Platelet Count | 230000 | /uL | 150000–450000 | Normal",
    "Total Bilirubin | 1.1 | mg/dL | 0.2–1.2 | Normal",
    "Direct Bilirubin | 0.3 | mg/dL | 0.0–0.3 | Normal",
    "ALT | 95 | U/L | 10–40 | High",
    "AST | 82 | U/L | 10–40 | High",
    "ALP | 105 | U/L | 44–147 | Normal",
    "Total Protein | 7.3 | g/dL | 6.0–8.3 | Normal",
    "Albumin | 4.0 | g/dL | 3.5–5.0 | Normal",
    "Ferritin | 1250 | ng/mL | 30–400 | High",
    "Serum Iron | 220 | ug/dL | 60–170 | High",
    "Transferrin Saturation | 78 | % | 20–50 | High",
    "TIBC | 280 | ug/dL | 250–450 | Normal",
    "CRP | 2.0 | mg/L | 0–5 | Normal",
    "Ceruloplasmin | 28 | mg/dL | 20–40 | Normal",
    "Serum Copper | 100 | ug/dL | 70–140 | Normal",
    "24-Hour Urinary Copper | 35 | ug/24h | 10–60 | Normal",
    "LDH | 210 | U/L | 140–280 | Normal",
    "Haptoglobin | 120 | mg/dL | 30–200 | Normal",
    "Reticulocyte Count | 1.2 | % | 0.5–2.5 | Normal",
    "TSH | 2.0 | uIU/mL | 0.40–4.20 | Normal",
    "T3 | 1.2 | ng/mL | 0.8–2.0 | Normal",
    "T4 | 8.0 | ug/dL | 4.5–12.0 | Normal",
    "T3 Resin Uptake | 32 | % | 24–39 | Normal"
]

def parse_line_advanced(line_clean, sorted_aliases):
    if not line_clean or line_clean.startswith("=") or line_clean.startswith("-"):
        return None
    if is_metadata_or_header_field(line_clean):
        return None

    # 1. Multi-column check (pipe, tab, or multi-space >= 2)
    col_candidates = None
    if "|" in line_clean:
        parts = [p.strip() for p in line_clean.split("|") if p.strip()]
        if len(parts) >= 2:
            col_candidates = parts
    elif "\t" in line_clean:
        parts = [p.strip() for p in line_clean.split("\t") if p.strip()]
        if len(parts) >= 2:
            col_candidates = parts
    elif len(re.split(r'\s{2,}', line_clean.strip())) >= 3:
        parts = [p.strip() for p in re.split(r'\s{2,}', line_clean.strip()) if p.strip()]
        if len(parts) >= 2:
            col_candidates = parts

    if col_candidates:
        cand_name = col_candidates[0]
        c_key, meta = normalize_param_name(cand_name)
        if c_key:
            # col 1 is observed val
            val_raw = col_candidates[1] if len(col_candidates) > 1 else ""
            m_v = re.search(r'[-+]?\d*\.?\d+', val_raw)
            if m_v:
                val_f = float(m_v.group(0))
                unit_f = col_candidates[2] if len(col_candidates) > 2 else ""
                ref_f = col_candidates[3] if len(col_candidates) > 3 else ""
                status_f = col_candidates[4] if len(col_candidates) > 4 else ""
                return {
                    "parameter": cand_name,
                    "canonical_key": c_key,
                    "value": val_f,
                    "unit": unit_f,
                    "reference_range": ref_f,
                    "status": status_f
                }

    # 2. Free-text inline regex matching
    matched_alias = None
    matched_c_key = None
    alias_span = None

    for alias in sorted_aliases:
        pattern = rf'(?i)(?:^|[\s\(])({re.escape(alias)})(?:[\s\)]|$|[:=\t\-])'
        m = re.search(pattern, line_clean)
        if m:
            matched_alias = alias
            matched_c_key = PARAMETER_ALIASES[alias]
            alias_span = m.span(1)
            break

    if not matched_alias or not alias_span:
        return None

    # Suffix strictly after matched biomarker name
    suffix = line_clean[alias_span[1]:].lstrip(":= \t-")
    if not suffix:
        return None

    # Extract ref range
    m_ref = re.search(r'\(?(\d+\.?\d*\s*(?:-|to|–|—)\s*\d+\.?\d*\s*%?)\)?', suffix)
    if not m_ref:
        m_ref = re.search(r'\(?(<\s*\d+\.?\d*|>\s*\d+\.?\d*|100%|\d+\.?\d*\s*%)\)?', suffix)
    ref_found = m_ref.group(1).strip() if m_ref else ""

    # Extract status
    m_status = re.search(r'\b(LOW|HIGH|NORMAL|CRITICAL|CRITICAL LOW|CRITICAL HIGH|ABNORMAL)\b', suffix, re.IGNORECASE)
    status_found = m_status.group(1).upper() if m_status else ""

    clean_suffix = suffix
    if ref_found:
        clean_suffix = clean_suffix.replace(ref_found, " ")
    if status_found:
        clean_suffix = re.sub(rf'\b{re.escape(status_found)}\b', " ", clean_suffix, flags=re.IGNORECASE)

    m_val = re.search(r'[-+]?\d*\.?\d+', clean_suffix)
    if not m_val:
        return None

    val_float = float(m_val.group(0))
    val_end = m_val.end()
    after_val = clean_suffix[val_end:].strip()
    m_unit = re.match(r'^[a-zA-Z/%^0-9\-_µ]+(?:\/[a-zA-Z0-9\-_µ]+)?', after_val)
    unit_str = m_unit.group(0) if m_unit else ""

    return {
        "parameter": matched_alias,
        "canonical_key": matched_c_key,
        "value": val_float,
        "unit": unit_str,
        "reference_range": ref_found,
        "status": status_found
    }

sorted_aliases = sorted(PARAMETER_ALIASES.keys(), key=len, reverse=True)
print(f"Testing {len(test_lines)} test rows:")
for idx, line in enumerate(test_lines, 1):
    res = parse_line_advanced(line, sorted_aliases)
    print(f"[{idx:02d}] {line[:30]:<30} => Name: {res['parameter']:<24} | Val: {res['value']:<8} | Unit: {res['unit']:<10} | Ref: {res['reference_range']:<10}")
