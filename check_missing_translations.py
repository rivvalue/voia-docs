#!/usr/bin/env python3
"""
VOÏA Translation Coverage Analyzer
Read-only script to identify missing, fuzzy, and duplicate French translations
Does NOT modify any files - only generates reports
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


class TranslationAnalyzer:
    def __init__(self, po_file_path):
        self.po_file_path = Path(po_file_path)
        self.entries = []
        self.stats = {
            'total': 0,
            'translated': 0,
            'untranslated': 0,
            'fuzzy': 0,
            'duplicates': 0,
            'empty_msgid': 0
        }
        self.untranslated_entries = []
        self.fuzzy_entries = []
        self.duplicate_entries = []
        self.msgid_map = defaultdict(list)
        
    def parse_po_file(self):
        """Parse .po file and extract all translation entries"""
        if not self.po_file_path.exists():
            print(f"❌ Error: File not found: {self.po_file_path}")
            sys.exit(1)
        
        print(f"📖 Reading: {self.po_file_path}")
        
        with open(self.po_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into entries (separated by blank lines)
        entries_raw = re.split(r'\n\n+', content)
        
        current_entry = None
        line_num = 1
        
        for entry_text in entries_raw:
            if not entry_text.strip() or entry_text.startswith('#') and 'msgid' not in entry_text:
                line_num += entry_text.count('\n') + 2
                continue
            
            entry = self._parse_entry(entry_text, line_num)
            if entry and entry['msgid']:
                self.entries.append(entry)
                self.msgid_map[entry['msgid']].append(entry)
            
            line_num += entry_text.count('\n') + 2
    
    def _parse_entry(self, entry_text, start_line):
        """Parse a single translation entry"""
        entry = {
            'line': start_line,
            'msgid': '',
            'msgstr': '',
            'fuzzy': False,
            'comments': []
        }
        
        lines = entry_text.split('\n')
        current_field = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check for fuzzy marker
            if line.startswith('#') and 'fuzzy' in line:
                entry['fuzzy'] = True
                continue
            
            # Comments
            if line.startswith('#'):
                entry['comments'].append(line)
                continue
            
            # msgid
            if line.startswith('msgid '):
                current_field = 'msgid'
                entry['msgid'] = self._extract_string(line)
                continue
            
            # msgstr
            if line.startswith('msgstr '):
                current_field = 'msgstr'
                entry['msgstr'] = self._extract_string(line)
                continue
            
            # Continuation lines (quoted strings)
            if line.startswith('"') and current_field:
                entry[current_field] += self._extract_string(line)
        
        return entry
    
    def _extract_string(self, line):
        """Extract string content from msgid/msgstr line"""
        # Remove msgid/msgstr prefix if present
        if line.startswith('msgid ') or line.startswith('msgstr '):
            line = line.split(' ', 1)[1]
        
        # Extract content between quotes
        match = re.search(r'"(.*)"', line)
        if match:
            # Unescape special characters
            content = match.group(1)
            content = content.replace('\\n', '\n')
            content = content.replace('\\"', '"')
            content = content.replace('\\\\', '\\')
            return content
        
        return ''
    
    def analyze(self):
        """Analyze all entries and categorize them"""
        print("🔍 Analyzing translations...")
        
        for entry in self.entries:
            msgid = entry['msgid']
            msgstr = entry['msgstr']
            
            # Skip empty msgid (header entry)
            if not msgid:
                self.stats['empty_msgid'] += 1
                continue
            
            self.stats['total'] += 1
            
            # Check if translated
            if not msgstr or msgstr == msgid:
                self.stats['untranslated'] += 1
                self.untranslated_entries.append(entry)
            else:
                self.stats['translated'] += 1
            
            # Check if fuzzy
            if entry['fuzzy']:
                self.stats['fuzzy'] += 1
                self.fuzzy_entries.append(entry)
        
        # Check for duplicates
        for msgid, entries in self.msgid_map.items():
            if len(entries) > 1 and msgid:  # Ignore empty msgid
                self.stats['duplicates'] += len(entries) - 1
                self.duplicate_entries.extend(entries[1:])  # All except first
    
    def generate_report(self, detailed=False, export_csv=False):
        """Generate comprehensive report"""
        print("\n" + "="*70)
        print("📊 VOÏA TRANSLATION COVERAGE REPORT")
        print("="*70)
        
        # Overall statistics
        total = self.stats['total']
        translated = self.stats['translated']
        untranslated = self.stats['untranslated']
        coverage = (translated / total * 100) if total > 0 else 0
        
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Total strings:        {total:>6}")
        print(f"   ✅ Translated:        {translated:>6} ({coverage:.1f}%)")
        print(f"   ❌ Untranslated:      {untranslated:>6} ({100-coverage:.1f}%)")
        print(f"   ⚠️  Fuzzy:             {self.stats['fuzzy']:>6}")
        print(f"   🔁 Duplicates:        {self.stats['duplicates']:>6}")
        
        # Coverage bar
        bar_length = 50
        filled = int(coverage / 100 * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\n   Progress: [{bar}] {coverage:.1f}%")
        
        # Detailed sections
        if detailed:
            self._print_untranslated_section()
            self._print_fuzzy_section()
            self._print_duplicate_section()
        else:
            print(f"\n💡 Run with --detailed flag to see full lists")
        
        # Export option
        if export_csv:
            self._export_csv()
        
        print("\n" + "="*70)
        
        # Return status code
        return 0 if untranslated == 0 else 1
    
    def _print_untranslated_section(self):
        """Print detailed untranslated strings"""
        if not self.untranslated_entries:
            print(f"\n✅ No untranslated strings found!")
            return
        
        print(f"\n❌ UNTRANSLATED STRINGS ({len(self.untranslated_entries)}):")
        print("-" * 70)
        
        for i, entry in enumerate(self.untranslated_entries[:50], 1):  # Limit to 50
            msgid_display = entry['msgid'][:60]
            if len(entry['msgid']) > 60:
                msgid_display += "..."
            print(f"   {i:3d}. Line {entry['line']:>5} | {msgid_display}")
        
        if len(self.untranslated_entries) > 50:
            remaining = len(self.untranslated_entries) - 50
            print(f"\n   ... and {remaining} more untranslated strings")
    
    def _print_fuzzy_section(self):
        """Print fuzzy (questionable) translations"""
        if not self.fuzzy_entries:
            return
        
        print(f"\n⚠️  FUZZY TRANSLATIONS ({len(self.fuzzy_entries)}):")
        print("-" * 70)
        print("   (These translations may be outdated or uncertain)")
        
        for i, entry in enumerate(self.fuzzy_entries[:20], 1):  # Limit to 20
            msgid_display = entry['msgid'][:60]
            if len(entry['msgid']) > 60:
                msgid_display += "..."
            print(f"   {i:3d}. Line {entry['line']:>5} | {msgid_display}")
        
        if len(self.fuzzy_entries) > 20:
            remaining = len(self.fuzzy_entries) - 20
            print(f"\n   ... and {remaining} more fuzzy translations")
    
    def _print_duplicate_section(self):
        """Print duplicate entries"""
        if not self.duplicate_entries:
            return
        
        print(f"\n🔁 DUPLICATE ENTRIES ({len(self.duplicate_entries)}):")
        print("-" * 70)
        print("   (These msgids appear multiple times - only first is used)")
        
        for i, entry in enumerate(self.duplicate_entries[:20], 1):
            msgid_display = entry['msgid'][:60]
            if len(entry['msgid']) > 60:
                msgid_display += "..."
            print(f"   {i:3d}. Line {entry['line']:>5} | {msgid_display}")
        
        if len(self.duplicate_entries) > 20:
            remaining = len(self.duplicate_entries) - 20
            print(f"\n   ... and {remaining} more duplicates")
    
    def _export_csv(self):
        """Export untranslated strings to CSV"""
        csv_file = self.po_file_path.parent / 'missing_translations.csv'
        
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("Line,Type,Original English,Current Translation,Status\n")
            
            for entry in self.untranslated_entries:
                msgid = entry['msgid'].replace('"', '""')  # Escape quotes
                msgstr = entry['msgstr'].replace('"', '""')
                status = "Fuzzy" if entry['fuzzy'] else "Untranslated"
                f.write(f'{entry["line"]},Untranslated,"{msgid}","{msgstr}",{status}\n')
            
            for entry in self.duplicate_entries:
                msgid = entry['msgid'].replace('"', '""')
                f.write(f'{entry["line"]},Duplicate,"{msgid}","","Duplicate"\n')
        
        print(f"\n💾 Exported to: {csv_file}")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze VOÏA translation coverage (read-only)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed lists of missing/fuzzy/duplicate translations'
    )
    parser.add_argument(
        '--csv',
        action='store_true',
        help='Export missing translations to CSV file'
    )
    parser.add_argument(
        '--file',
        default='translations/fr/LC_MESSAGES/messages.po',
        help='Path to .po file (default: translations/fr/LC_MESSAGES/messages.po)'
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = TranslationAnalyzer(args.file)
    
    # Parse .po file
    analyzer.parse_po_file()
    
    # Analyze entries
    analyzer.analyze()
    
    # Generate report
    exit_code = analyzer.generate_report(
        detailed=args.detailed,
        export_csv=args.csv
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
