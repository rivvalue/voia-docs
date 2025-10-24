#!/usr/bin/env python3
"""
Fix broken HTML ID attributes in dashboard.html

This script fixes IDs that were incorrectly wrapped with {{ _() }} translation markers,
which breaks JavaScript functionality when the page language changes.

IDs must stay in English (they're code identifiers), while content can be translated.
"""

import re
import sys
from datetime import datetime

# Mapping of broken IDs to their fixed versions
# Format: (broken_pattern, fixed_id, line_number_for_verification)
ID_FIXES = [
    # Critical KPI IDs (JavaScript updates these values)
    {
        'pattern': r'id="total\{\{ _\(\'Responses\'\) \}\}"',
        'replacement': 'id="totalResponses"',
        'line': 398,
        'priority': 'CRITICAL',
        'reason': 'JavaScript updates KPI value (line 1224 in dashboard.js)'
    },
    {
        'pattern': r'id="total\{\{ _\(\'Responses\'\) \}\}Trend"',
        'replacement': 'id="totalResponsesTrend"',
        'line': 400,
        'priority': 'LOW',
        'reason': 'Consistency (no JS reference found)'
    },
    {
        'pattern': r'id="recent\{\{ _\(\'Responses\'\) \}\}"',
        'replacement': 'id="recentResponses"',
        'line': 405,
        'priority': 'CRITICAL',
        'reason': 'JavaScript updates KPI value (line 1226 in dashboard.js)'
    },
    {
        'pattern': r'id="recent\{\{ _\(\'Responses\'\) \}\}Trend"',
        'replacement': 'id="recentResponsesTrend"',
        'line': 407,
        'priority': 'LOW',
        'reason': 'Consistency (no JS reference found)'
    },
    
    # Critical Modal IDs (Bootstrap + JavaScript)
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}Modal"',
        'replacement': 'id="companyResponsesModal"',
        'line': 879,
        'priority': 'CRITICAL',
        'reason': 'Bootstrap modal initialization (line 4118 in dashboard.js)'
    },
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}ModalLabel"',
        'replacement': 'id="companyResponsesModalLabel"',
        'line': 884,
        'priority': 'LOW',
        'reason': 'Bootstrap aria-labelledby reference'
    },
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}Loading"',
        'replacement': 'id="companyResponsesLoading"',
        'line': 923,
        'priority': 'CRITICAL',
        'reason': 'JavaScript toggles loading state (line 4129 in dashboard.js)'
    },
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}Content"',
        'replacement': 'id="companyResponsesContent"',
        'line': 931,
        'priority': 'CRITICAL',
        'reason': 'JavaScript toggles content visibility (line 4130 in dashboard.js)'
    },
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}TableBody"',
        'replacement': 'id="companyResponsesTableBody"',
        'line': 943,
        'priority': 'CRITICAL',
        'reason': 'JavaScript populates table rows (line 4181 in dashboard.js)'
    },
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}PaginationInfo"',
        'replacement': 'id="companyResponsesPaginationInfo"',
        'line': 952,
        'priority': 'CRITICAL',
        'reason': 'JavaScript updates pagination info (line 4273 in dashboard.js)'
    },
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}Pagination"',
        'replacement': 'id="companyResponsesPagination"',
        'line': 955,
        'priority': 'CRITICAL',
        'reason': 'JavaScript renders pagination controls (line 4277 in dashboard.js)'
    },
    {
        'pattern': r'id="company\{\{ _\(\'Responses\'\) \}\}NoData"',
        'replacement': 'id="companyResponsesNoData"',
        'line': 963,
        'priority': 'CRITICAL',
        'reason': 'JavaScript toggles no-data message (line 4131 in dashboard.js)'
    },
]

def backup_file(filepath):
    """Create a timestamped backup of the file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{filepath}.backup_ids_{timestamp}"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return backup_path

def apply_fixes(content):
    """Apply all ID fixes and track changes"""
    changes = []
    fixed_content = content
    
    for fix in ID_FIXES:
        pattern = fix['pattern']
        replacement = fix['replacement']
        
        # Find all matches
        matches = list(re.finditer(pattern, fixed_content))
        
        if matches:
            # Apply replacement
            fixed_content = re.sub(pattern, replacement, fixed_content)
            
            changes.append({
                'pattern': pattern,
                'replacement': replacement,
                'count': len(matches),
                'line': fix['line'],
                'priority': fix['priority'],
                'reason': fix['reason']
            })
    
    return fixed_content, changes

def verify_template_syntax(content):
    """Basic Jinja2 syntax validation"""
    try:
        from jinja2 import Template
        Template(content)
        return True, "Template syntax valid"
    except Exception as e:
        return False, f"Template syntax error: {str(e)}"

def show_diff_preview(original, fixed, changes):
    """Show a preview of changes"""
    print("\n" + "="*80)
    print("PREVIEW OF CHANGES")
    print("="*80)
    
    critical_count = sum(1 for c in changes if c['priority'] == 'CRITICAL')
    low_count = sum(1 for c in changes if c['priority'] == 'LOW')
    
    print(f"\n📊 Summary:")
    print(f"   - CRITICAL fixes: {critical_count} (breaks JavaScript)")
    print(f"   - LOW priority fixes: {low_count} (consistency)")
    print(f"   - Total fixes: {len(changes)}")
    
    print(f"\n📝 Changes:\n")
    for i, change in enumerate(changes, 1):
        priority_icon = "🔴" if change['priority'] == 'CRITICAL' else "⚠️"
        print(f"{priority_icon} Fix #{i} (Line ~{change['line']}) - {change['priority']}")
        print(f"   Reason: {change['reason']}")
        print(f"   Pattern: {change['pattern'][:60]}...")
        print(f"   Fixed:   {change['replacement']}")
        print(f"   Matches: {change['count']}")
        print()

def main():
    filepath = 'templates/dashboard.html'
    
    print("="*80)
    print("FIX BROKEN HTML ID ATTRIBUTES")
    print("="*80)
    print(f"\nTarget file: {filepath}")
    print(f"Total fixes to apply: {len(ID_FIXES)}")
    
    # Read original file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: {filepath} not found")
        return 1
    
    # Create backup
    print("\n📦 Creating backup...")
    backup_path = backup_file(filepath)
    print(f"   ✅ Backup saved: {backup_path}")
    
    # Apply fixes
    print("\n🔧 Applying fixes...")
    fixed_content, changes = apply_fixes(original_content)
    
    if not changes:
        print("   ⚠️ No changes needed - all IDs already correct")
        return 0
    
    # Show preview
    show_diff_preview(original_content, fixed_content, changes)
    
    # Verify template syntax
    print("="*80)
    print("TEMPLATE VALIDATION")
    print("="*80)
    is_valid, message = verify_template_syntax(fixed_content)
    
    if is_valid:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
        print("\n⚠️ Aborting - template has syntax errors")
        return 1
    
    # Show before/after examples
    print("\n" + "="*80)
    print("BEFORE/AFTER EXAMPLES")
    print("="*80)
    
    examples = [
        ("totalResponses", "Line 398 - KPI Value"),
        ("recentResponses", "Line 405 - KPI Value"),
        ("companyResponsesModal", "Line 879 - Modal Container"),
    ]
    
    for id_name, description in examples:
        # Find in original
        orig_pattern = rf'id="[^"]*\{{\{{ _\([^)]+\)[^"]*{id_name[7:] if "Responses" in id_name else id_name[7:]}'
        orig_match = re.search(rf'id="[^"]*\{{\{{ _\([^)]+\).*?"', original_content)
        
        print(f"\n{description}:")
        print(f"   BEFORE: id=\"company{{{{ _('Responses') }}}}Modal\"")
        print(f"   AFTER:  id=\"{id_name}\"")
    
    # Prompt for confirmation
    print("\n" + "="*80)
    print("READY TO APPLY")
    print("="*80)
    print(f"✅ {len(changes)} fixes ready")
    print(f"✅ Template syntax validated")
    print(f"✅ Backup created: {backup_path}")
    
    response = input("\n👉 Apply fixes? (yes/no): ").strip().lower()
    
    if response == 'yes':
        # Write fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("\n✅ SUCCESS! Fixes applied.")
        print("\n📋 Next steps:")
        print("   1. Restart Flask application")
        print("   2. Test dashboard in English - verify KPIs load")
        print("   3. Switch to French - verify KPIs still load")
        print("   4. Test company responses modal")
        print(f"\n💾 Rollback command if needed:")
        print(f"   cp {backup_path} {filepath}")
        
        return 0
    else:
        print("\n❌ Cancelled - no changes made")
        return 1

if __name__ == '__main__':
    sys.exit(main())
