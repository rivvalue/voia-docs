#!/usr/bin/env python3
"""
Extract JavaScript translations from .po files and generate static JSON files
Reduces inline translation payload from ~150KB to cacheable JSON files
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List

# Define translation namespaces and their keys
NAMESPACES = {
    "common": [
        # Campaign Status
        "Draft", "Ready", "Active", "Completed", "Unknown",
        
        # Time/Date Display
        "days left", "days ago", "month", "months", "ago", "year", "years",
        
        # Loading Messages
        "Loading...", "Loading comparison...", "Loading comparison data...",
        
        # Basic UI
        "Previous", "Next", "View Details", "Close",
        "Showing", "of",
        
        # Common Labels
        "N/A", "Satisfaction", "Service", "Pricing",
        "NPS", "Responses", "Companies",
    ],
    
    "dashboard": [
        # Campaign Filter UI
        "Filtered by:", "Clear filter", 
        "Select first campaign", "Select second campaign",
        
        # Error Messages
        "Failed to fetch comparison data",
        "Error Loading Comparison",
        "Failed to load comparison data. Please try again.",
        "No campaign data available",
        "Error loading KPI overview data",
        "Error loading dashboard data:",
        "Failed to load campaign options",
        "Error loading account intelligence",
        "Error loading responses.",
        "Network error loading tenure data",
        "Network error loading company data",
        
        # Chart Labels & Metrics
        "Product Value", "Average Rating", "Critical Risk", "Product",
        
        # Table Content & Empty States
        "No tenure data available yet",
        "No company data available yet",
        
        # Pagination Text
        "tenure groups", "companies", "responses", "accounts",
        
        # NPS Category Labels
        "Promoters (9-10)", "Passives (7-8)", "Detractors (0-6)",
        
        # Accessibility Attributes
        "Authentication required",
        "View Full Response",
    ],
    
    "campaign-insights": [
        # All dashboard keys (campaign insights uses same translations)
        # Plus segmentation-specific strings
        "NPS Score", "NPS by Role", "NPS by Region",
    ],
}

def parse_po_file(po_file_path: str) -> Dict[str, str]:
    """Parse a .po file and extract msgid -> msgstr mappings"""
    translations = {}
    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('#') or not line:
                if current_msgid and current_msgstr is not None:
                    translations[current_msgid] = current_msgstr
                    current_msgid = None
                    current_msgstr = None
                in_msgid = False
                in_msgstr = False
                continue
            
            # Start of msgid
            if line.startswith('msgid "'):
                if current_msgid and current_msgstr is not None:
                    translations[current_msgid] = current_msgstr
                current_msgid = line[7:-1]  # Remove 'msgid "' and '"'
                in_msgid = True
                in_msgstr = False
                current_msgstr = None
            
            # Start of msgstr
            elif line.startswith('msgstr "'):
                current_msgstr = line[8:-1]  # Remove 'msgstr "' and '"'
                in_msgid = False
                in_msgstr = True
            
            # Continuation of multiline string
            elif line.startswith('"') and line.endswith('"'):
                text = line[1:-1]  # Remove quotes
                if in_msgid and current_msgid is not None:
                    current_msgid += text
                elif in_msgstr and current_msgstr is not None:
                    current_msgstr += text
        
        # Don't forget the last entry
        if current_msgid and current_msgstr is not None:
            translations[current_msgid] = current_msgstr
    
    return translations

def extract_translations_for_namespace(
    namespace: str, 
    keys: List[str], 
    translations: Dict[str, str],
    locale: str
) -> Dict[str, str]:
    """Extract specific keys for a namespace"""
    result = {}
    
    for key in keys:
        # For English, msgstr is empty, so use msgid
        if locale == 'en':
            result[key] = key
        else:
            # Use translated string, fallback to key if not found
            result[key] = translations.get(key, key)
    
    # Also include keys from other namespaces if this is campaign-insights
    if namespace == "campaign-insights":
        # Inherit all dashboard keys
        for key in NAMESPACES["dashboard"]:
            if locale == 'en':
                result[key] = key
            else:
                result[key] = translations.get(key, key)
    
    # All namespaces get common keys
    if namespace != "common":
        for key in NAMESPACES["common"]:
            if locale == 'en':
                result[key] = key
            else:
                result[key] = translations.get(key, key)
    
    return result

def generate_json_files():
    """Generate JSON translation files for all namespaces and locales"""
    base_dir = Path(__file__).parent.parent
    translations_dir = base_dir / "translations"
    output_dir = base_dir / "static" / "i18n"
    
    locales = ['en', 'fr']
    
    for locale in locales:
        print(f"\n📦 Processing locale: {locale}")
        
        # Parse .po file
        po_file = translations_dir / locale / "LC_MESSAGES" / "messages.po"
        if not po_file.exists():
            print(f"  ⚠️  .po file not found: {po_file}")
            # For English, we can still generate with keys as values
            translations = {}
        else:
            translations = parse_po_file(str(po_file))
            print(f"  ✅ Parsed {len(translations)} translations from .po file")
        
        # Create output directory
        locale_dir = output_dir / locale
        locale_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate JSON for each namespace
        for namespace, keys in NAMESPACES.items():
            namespace_translations = extract_translations_for_namespace(
                namespace, keys, translations, locale
            )
            
            # Write JSON file (minified)
            output_file = locale_dir / f"{namespace}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(namespace_translations, f, ensure_ascii=False, separators=(',', ':'))
            
            file_size = output_file.stat().st_size
            print(f"  ✅ Generated {namespace}.json ({file_size:,} bytes, {len(namespace_translations)} keys)")
    
    print(f"\n✅ JSON translation files generated successfully!")
    print(f"📁 Output directory: {output_dir}")
    
    # Calculate total size savings
    print(f"\n📊 Size Analysis:")
    for locale in locales:
        total_size = sum((output_dir / locale / f"{ns}.json").stat().st_size 
                        for ns in NAMESPACES.keys())
        print(f"  {locale.upper()}: {total_size:,} bytes (~{total_size/1024:.1f} KB)")

if __name__ == "__main__":
    print("🚀 Extracting JavaScript translations from .po files...")
    generate_json_files()
    print("\n✅ Done!")
