import re

def _normalize_value(value_str, text_context=""):
    """
    Cleans a numeric string (removes commas, handles parentheses for negatives)
    and applies multipliers (thousands, millions, billions) based on context.
    """
    value = value_str.replace(",", "").strip()

    # Handle negative numbers in parentheses e.g., (1,000) -> -1000
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]

    try:
        numeric_value = float(value)
    except ValueError:
        return None # Could not convert to float

    # Look for common multipliers in the text context around the number
    # We search the original text context, not just the extracted value string
    text_context_lower = text_context.lower()
    
    # Check for "in thousands", "000s", "K", "k"
    if re.search(r'\b(in thousands|\d{3}s?|k)\b', text_context_lower):
        numeric_value *= 1_000
    # Check for "in millions", "MM", "M"
    elif re.search(r'\b(in millions|mm|m)\b', text_context_lower) and not re.search(r'\bper square metre\b', text_context_lower): # Avoid "m" for meter
        numeric_value *= 1_000_000
    # Check for "in billions", "B", "Bn"
    elif re.search(r'\b(in billions|bn|b)\b', text_context_lower):
        numeric_value *= 1_000_000_000
    
    return numeric_value

def extract_kpis_from_text(text):
    kpis = {}
    ratios = {}

    # Define patterns with a wider capture group to include potential multipliers
    # The (?:...) is a non-capturing group.
    # We try to capture some context around the number for multiplier detection.
    # The number itself is in the last capturing group ([\d,\.]+)
    patterns = {
        "Total Assets": r"(?:Total assets|Assets, total|Total Current and Non-current Assets)\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?",
        "Total Liabilities": r"(?:Total liabilities|Liabilities, total|Total Current and Non-current Liabilities)\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?",
        "Equity": r"(?:Shareholders' equity|Total equity|Equity attributable to(?: parent| owners)?)\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?",
        "Cash": r"Cash (?:and cash equivalents)?\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?",
        "Net Profit": r"(?:Net income|Profit(?: and loss)?|Net earnings)\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?",
        "Revenue": r"(?:Total net sales|Revenue|Sales)\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?",
        "Current Assets": r"(?:Total current assets|Current assets, total)\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?",
        "Current Liabilities": r"(?:Total current liabilities|Current liabilities, total)\b[^:\d\n]*[:\s$₹]*([\d,\.]+)(?:\s*(?:in\s+thousands|millions|billions|MM|M|B|Bn|K)\b)?"
    }

    for key, pattern in patterns.items():
        # Using finditer to get all matches and their span for context
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value_str_raw = match.group(1)
            # Extract context for multiplier detection: e.g., the line containing the match
            # This is a simple context; a more advanced approach might use a fixed window around the match
            line_start = text.rfind('\n', 0, match.start()) + 1
            line_end = text.find('\n', match.end())
            if line_end == -1: line_end = len(text)
            context_for_multiplier = text[line_start:line_end] # Capture the whole line or segment

            normalized_value = _normalize_value(value_str_raw, context_for_multiplier)
            if normalized_value is not None:
                kpis[key] = normalized_value
                # Assuming first match is usually the most relevant or desired
                break 

    # Derived Ratios
    try:
        if "Total Liabilities" in kpis and "Equity" in kpis and kpis["Equity"] != 0:
            ratios["Debt-to-Equity"] = round(kpis["Total Liabilities"] / kpis["Equity"], 2)
        else:
            ratios["Debt-to-Equity"] = "N/A (Equity is zero or not found)"

        if "Current Assets" in kpis and "Current Liabilities" in kpis and kpis["Current Liabilities"] != 0:
            ratios["Current Ratio"] = round(kpis["Current Assets"] / kpis["Current Liabilities"], 2)
        else:
            ratios["Current Ratio"] = "N/A (Current Liabilities is zero or not found)"
            
        if "Current Assets" in kpis and "Current Liabilities" in kpis:
            ratios["Working Capital"] = round(kpis["Current Assets"] - kpis["Current Liabilities"], 2)
        else:
            ratios["Working Capital"] = "N/A (Current Assets or Liabilities not found)"

        if "Net Profit" in kpis and "Revenue" in kpis and kpis["Revenue"] != 0:
            ratios["Net Profit Margin (%)"] = round((kpis["Net Profit"] / kpis["Revenue"]) * 100, 2)
        else:
            ratios["Net Profit Margin (%)"] = "N/A (Revenue is zero or Net Profit/Revenue not found)"

    except ZeroDivisionError as e: # Specific exception for division by zero
        print(f"Warning: Division by zero encountered when calculating ratio: {e}")
        # Ratios that cause ZeroDivisionError will already be set to "N/A" by the checks above.
    except Exception as e:
        print(f"Error calculating financial ratios: {e}")
        # Keep existing ratios if possible, or mark them N/A

    return kpis, ratios