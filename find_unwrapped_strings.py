#!/usr/bin/env python3
"""
Quick Regex Scanner for Unwrapped Translation Strings
Finds hardcoded English text in HTML templates that should be wrapped in {{ _('...') }}
"""

import re
import os
from pathlib import Path
from collections import defaultdict


class UnwrappedStringFinder:
    def __init__(self, templates_dir='templates'):
        self.templates_dir = Path(templates_dir)
        self.findings = defaultdict(list)
        
        # Patterns to detect unwrapped strings
        self.patterns = [
            # HTML elements with text content
            {
                'name': 'Headings (h1-h6)',
                'pattern': r'<(h[1-6])[^>]*>([^{<][^<]*)</\1>',
                'group': 2,
                'min_length': 2
            },
            {
                'name': 'Buttons',
                'pattern': r'<button[^>]*>([^{<][^<]*)</button>',
                'group': 1,
                'min_length': 2
            },
            {
                'name': 'Labels',
                'pattern': r'<label[^>]*>([^{<][^<]*)</label>',
                'group': 1,
                'min_length': 2
            },
            {
                'name': 'Links (a tags)',
                'pattern': r'<a[^>]*>([^{<][^<]*)</a>',
                'group': 1,
                'min_length': 3
            },
            {
                'name': 'Paragraphs',
                'pattern': r'<p[^>]*>([^{<][^<]*)</p>',
                'group': 1,
                'min_length': 10  # Longer to avoid false positives
            },
            {
                'name': 'Spans',
                'pattern': r'<span[^>]*>([^{<][^<]*)</span>',
                'group': 1,
                'min_length': 3
            },
            {
                'name': 'Divs with text',
                'pattern': r'<div[^>]*>([^{<][^<]+)</div>',
                'group': 1,
                'min_length': 5
            },
            {
                'name': 'Table headers (th)',
                'pattern': r'<th[^>]*>([^{<][^<]*)</th>',
                'group': 1,
                'min_length': 2
            },
            # Attributes
            {
                'name': 'Placeholder attributes',
                'pattern': r'placeholder="([^"]*[A-Za-z]{3,}[^"]*)"',
                'group': 1,
                'min_length': 3
            },
            {
                'name': 'Title attributes',
                'pattern': r'title="([^"]*[A-Za-z]{3,}[^"]*)"',
                'group': 1,
                'min_length': 3
            },
            {
                'name': 'Alt attributes',
                'pattern': r'alt="([^"]*[A-Za-z]{3,}[^"]*)"',
                'group': 1,
                'min_length': 3
            },
            {
                'name': 'ARIA labels',
                'pattern': r'aria-label="([^"]*[A-Za-z]{3,}[^"]*)"',
                'group': 1,
                'min_length': 3
            },
            {
                'name': 'Value attributes (buttons/inputs)',
                'pattern': r'value="([^"]*[A-Za-z]{3,}[^"]*)"',
                'group': 1,
                'min_length': 3
            }
        ]
        
        # Patterns to IGNORE (false positives)
        self.ignore_patterns = [
            r'^\s*$',                    # Empty/whitespace only
            r'^[0-9\s\.\,\-\+]+$',      # Numbers only
            r'^#[a-fA-F0-9]{3,6}$',     # Color codes
            r'^https?://',               # URLs
            r'^/',                       # Paths
            r'^\w+\.\w+$',              # Filenames
            r'^[\{\}%\(\)\[\]]+$',      # Jinja/template syntax
            r'^\$',                      # Variables
            r'^var\-\-',                # CSS variables
            r'^fa\-',                   # Font Awesome classes
            r'^btn\-',                  # Bootstrap classes
            r'^\.',                     # CSS classes
            r'^@',                      # Email/mentions
            r'^\d+px$',                 # CSS sizes
            r'^(true|false|null)$',     # Literals
            r'^(GET|POST|PUT|DELETE)$', # HTTP methods
        ]
    
    def should_ignore(self, text):
        """Check if text should be ignored"""
        text = text.strip()
        
        # Empty
        if not text:
            return True
        
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Must contain at least one letter
        if not re.search(r'[A-Za-z]', text):
            return True
        
        # Too short (single char)
        if len(text) < 2:
            return True
        
        return False
    
    def has_translation_wrapper(self, text):
        """Check if text is already wrapped in translation function"""
        # Look for {{ _('...') }} or {{ _("...") }}
        if re.search(r'\{\{\s*_\(', text):
            return True
        # Look for {% trans %} blocks
        if re.search(r'\{%\s*trans\s*%\}', text):
            return True
        return False
    
    def scan_file(self, filepath):
        """Scan a single template file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into lines for line number tracking
            lines = content.split('\n')
            
            file_findings = []
            
            for pattern_def in self.patterns:
                pattern = pattern_def['pattern']
                group_idx = pattern_def['group']
                min_length = pattern_def.get('min_length', 2)
                pattern_name = pattern_def['name']
                
                # Find all matches
                for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                    matched_text = match.group(group_idx).strip()
                    
                    # Skip if should ignore
                    if self.should_ignore(matched_text):
                        continue
                    
                    # Skip if too short
                    if len(matched_text) < min_length:
                        continue
                    
                    # Skip if already wrapped
                    full_match = match.group(0)
                    if self.has_translation_wrapper(full_match):
                        continue
                    
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    file_findings.append({
                        'line': line_num,
                        'text': matched_text,
                        'context': full_match[:100],
                        'pattern': pattern_name
                    })
            
            return file_findings
            
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")
            return []
    
    def scan_all_templates(self):
        """Scan all template files"""
        if not self.templates_dir.exists():
            print(f"❌ Templates directory not found: {self.templates_dir}")
            return
        
        print(f"🔍 Scanning templates in: {self.templates_dir}")
        
        # Find all HTML files
        html_files = list(self.templates_dir.rglob('*.html'))
        
        print(f"📄 Found {len(html_files)} template files\n")
        
        total_findings = 0
        
        for filepath in sorted(html_files):
            findings = self.scan_file(filepath)
            
            if findings:
                rel_path = filepath.relative_to(self.templates_dir.parent)
                self.findings[str(rel_path)] = findings
                total_findings += len(findings)
        
        return total_findings
    
    def generate_report(self, detailed=False, limit=None):
        """Generate report of findings"""
        print("="*80)
        print("🔍 UNWRAPPED TRANSLATION STRINGS REPORT")
        print("="*80)
        
        if not self.findings:
            print("\n✅ No unwrapped strings found!")
            print("   All visible text appears to be properly wrapped for translation.")
            return
        
        total_files = len(self.findings)
        total_strings = sum(len(f) for f in self.findings.values())
        
        print(f"\n📊 SUMMARY:")
        print(f"   Files with issues: {total_files}")
        print(f"   Total unwrapped strings: {total_strings}")
        
        if not detailed:
            print(f"\n💡 Run with --detailed flag to see full findings")
            print(f"   Example: python find_unwrapped_strings.py --detailed")
        else:
            self._print_detailed_findings(limit)
        
        print("\n" + "="*80)
    
    def _print_detailed_findings(self, limit=None):
        """Print detailed findings"""
        print(f"\n📋 DETAILED FINDINGS:\n")
        
        for filepath in sorted(self.findings.keys()):
            findings = self.findings[filepath]
            
            print(f"\n{'─'*80}")
            print(f"📄 {filepath}")
            print(f"   {len(findings)} unwrapped string(s) found")
            print(f"{'─'*80}")
            
            # Group by pattern type for cleaner output
            by_pattern = defaultdict(list)
            for finding in findings:
                by_pattern[finding['pattern']].append(finding)
            
            displayed = 0
            for pattern_name, pattern_findings in sorted(by_pattern.items()):
                print(f"\n   [{pattern_name}]")
                
                for finding in sorted(pattern_findings, key=lambda x: x['line']):
                    if limit and displayed >= limit:
                        remaining = len(findings) - displayed
                        print(f"\n   ... and {remaining} more findings")
                        break
                    
                    line = finding['line']
                    text = finding['text'][:60]
                    if len(finding['text']) > 60:
                        text += "..."
                    
                    print(f"   Line {line:>4}: \"{text}\"")
                    displayed += 1
                
                if limit and displayed >= limit:
                    break
    
    def export_csv(self, output_file='unwrapped_strings.csv'):
        """Export findings to CSV"""
        if not self.findings:
            print("ℹ️  No findings to export")
            return
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("File,Line,Pattern Type,Unwrapped Text,Context\n")
            
            for filepath, findings in sorted(self.findings.items()):
                for finding in sorted(findings, key=lambda x: x['line']):
                    text = finding['text'].replace('"', '""')  # Escape quotes
                    context = finding['context'].replace('"', '""').replace('\n', ' ')
                    
                    f.write(f'"{filepath}",{finding["line"]},"{finding["pattern"]}","{text}","{context}"\n')
        
        print(f"\n💾 Exported to: {output_file}")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Find unwrapped translation strings in HTML templates',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed findings for each file'
    )
    parser.add_argument(
        '--csv',
        action='store_true',
        help='Export findings to CSV file'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of findings shown per file (default: show all)'
    )
    parser.add_argument(
        '--dir',
        default='templates',
        help='Templates directory to scan (default: templates)'
    )
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = UnwrappedStringFinder(templates_dir=args.dir)
    
    # Scan all templates
    total = scanner.scan_all_templates()
    
    # Generate report
    scanner.generate_report(detailed=args.detailed, limit=args.limit)
    
    # Export if requested
    if args.csv:
        scanner.export_csv()
    
    # Exit code
    import sys
    sys.exit(0 if total == 0 else 1)


if __name__ == '__main__':
    main()
