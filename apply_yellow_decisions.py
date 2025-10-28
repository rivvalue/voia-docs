#!/usr/bin/env python3
"""
Apply YELLOW Decisions - Phase 4
Applies the smart auto-decisions (wrap/skip) from Phase 3
"""

import json
import re
from pathlib import Path
from datetime import datetime


class YellowApplier:
    def __init__(self, decisions_file='yellow_decisions_combined.json'):
        self.decisions_file = decisions_file
        self.decisions = {}
        self.modifications = []
        self.stats = {
            'files_modified': 0,
            'strings_wrapped': 0,
            'strings_skipped': 0,
            'errors': 0
        }
    
    def load_decisions(self):
        """Load decisions from JSON"""
        print(f"📖 Loading decisions from: {self.decisions_file}\n")
        
        with open(self.decisions_file, 'r', encoding='utf-8') as f:
            all_decisions = json.load(f)
        
        # Filter only 'wrap' decisions
        self.decisions = {k: v for k, v in all_decisions.items() if v['action'] == 'wrap'}
        
        total = len(all_decisions)
        wrap_count = len(self.decisions)
        skip_count = sum(1 for v in all_decisions.values() if v['action'] == 'skip')
        
        print(f"✅ Loaded {total} total decisions:")
        print(f"   ✅ Will wrap: {wrap_count}")
        print(f"   ⏭️  Will skip: {skip_count}\n")
    
    def wrap_string(self, text):
        """Generate wrapped version"""
        text = text.strip()
        
        # Escape single quotes in text
        if "'" in text and '"' not in text:
            return f'{{{{ _("{text}") }}}}'
        elif '"' in text and "'" not in text:
            return f"{{{{ _('{text}') }}}}"
        else:
            # Has both - escape the singles
            escaped = text.replace("'", "\\'")
            return f"{{{{ _('{escaped}') }}}}"
    
    def apply_wrap_to_line(self, line_content, decision):
        """Apply wrapping to a specific line"""
        text = decision['text']
        pattern = decision['pattern']
        context = decision['context']
        
        # Verify the line still contains the expected text
        if text not in line_content:
            return None, f"Text not found in line"
        
        try:
            wrapped = self.wrap_string(text)
            
            # Different strategies based on pattern type
            if 'ARIA' in pattern:
                # ARIA label wrapping
                new_line = re.sub(
                    f'aria-label="{re.escape(text)}"',
                    f'aria-label={wrapped}',
                    line_content,
                    count=1
                )
            
            elif 'Divs with text' in pattern:
                # Div content wrapping
                new_line = re.sub(
                    f'>{re.escape(text)}<',
                    f'>{wrapped}<',
                    line_content,
                    count=1
                )
            
            elif 'Spans' in pattern:
                # Span content wrapping
                new_line = re.sub(
                    f'>{re.escape(text)}<',
                    f'>{wrapped}<',
                    line_content,
                    count=1
                )
            
            elif 'Links' in pattern:
                # Link text wrapping
                new_line = re.sub(
                    f'>{re.escape(text)}<',
                    f'>{wrapped}<',
                    line_content,
                    count=1
                )
            
            elif 'Alt' in pattern:
                # Alt attribute wrapping
                new_line = re.sub(
                    f'alt="{re.escape(text)}"',
                    f'alt={wrapped}',
                    line_content,
                    count=1
                )
            
            else:
                # Generic wrapping
                new_line = line_content.replace(text, wrapped, 1)
            
            if new_line == line_content:
                return None, "No change detected after replacement"
            
            return new_line, None
        
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def group_by_file(self):
        """Group decisions by file"""
        by_file = {}
        for item_id, decision in self.decisions.items():
            file_path = decision['file'].strip('"')
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(decision)
        
        # Sort by line number (descending) to prevent line shifts
        for file_path in by_file:
            by_file[file_path].sort(key=lambda x: int(x['line']), reverse=True)
        
        return by_file
    
    def process_file(self, file_path, decisions):
        """Process a single file"""
        print(f"📝 Processing: {file_path} ({len(decisions)} items)")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"   ❌ Error reading: {e}")
            self.stats['errors'] += 1
            return
        
        modifications_made = 0
        skipped = 0
        
        for decision in decisions:
            line_num = int(decision['line']) - 1
            
            if line_num >= len(lines):
                print(f"   ⚠️  Line {decision['line']} out of range")
                skipped += 1
                continue
            
            original_line = lines[line_num]
            new_line, error = self.apply_wrap_to_line(original_line, decision)
            
            if error:
                print(f"   ⚠️  Line {decision['line']}: {error}")
                skipped += 1
                continue
            
            if new_line:
                lines[line_num] = new_line
                modifications_made += 1
                
                self.modifications.append({
                    'file': file_path,
                    'line': decision['line'],
                    'pattern': decision['pattern'],
                    'original': original_line.strip(),
                    'modified': new_line.strip(),
                    'text': decision['text']
                })
        
        # Write file
        if modifications_made > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"   ✅ Modified {modifications_made} lines, skipped {skipped}")
                self.stats['files_modified'] += 1
                self.stats['strings_wrapped'] += modifications_made
                self.stats['strings_skipped'] += skipped
            except Exception as e:
                print(f"   ❌ Error writing: {e}")
                self.stats['errors'] += 1
        else:
            print(f"   ⏭️  No changes made ({skipped} skipped)")
            self.stats['strings_skipped'] += skipped
    
    def run(self):
        """Execute yellow decisions application"""
        print("="*80)
        print("🟡 APPLYING YELLOW AUTO-DECISIONS - Phase 4")
        print("="*80 + "\n")
        
        # Load decisions
        self.load_decisions()
        
        # Group by file
        by_file = self.group_by_file()
        print(f"📁 Files to process: {len(by_file)}\n")
        
        # Process each file
        for file_path in sorted(by_file.keys()):
            self.process_file(file_path, by_file[file_path])
        
        # Generate report
        self.generate_report()
        
        # Save log
        self.save_log()
    
    def generate_report(self):
        """Generate final report"""
        print("\n" + "="*80)
        print("📊 YELLOW DECISIONS APPLICATION REPORT")
        print("="*80)
        
        print(f"\n✅ SUMMARY:")
        print(f"   Files modified: {self.stats['files_modified']}")
        print(f"   Strings wrapped: {self.stats['strings_wrapped']}")
        print(f"   Strings skipped: {self.stats['strings_skipped']}")
        print(f"   Errors: {self.stats['errors']}")
        
        if self.stats['strings_wrapped'] > 0:
            print(f"\n💡 NEXT STEPS:")
            print(f"   1. Review yellow_wrap_log.txt for all changes")
            print(f"   2. Test application for syntax errors")
            print(f"   3. Proceed to Phase 5: Handle RED zone items")
        
        print("="*80 + "\n")
    
    def save_log(self):
        """Save detailed modification log"""
        log_file = f"yellow_wrap_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("YELLOW DECISIONS MODIFICATION LOG\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"SUMMARY:\n")
            f.write(f"  Files modified: {self.stats['files_modified']}\n")
            f.write(f"  Strings wrapped: {self.stats['strings_wrapped']}\n")
            f.write(f"  Strings skipped: {self.stats['strings_skipped']}\n\n")
            
            f.write("="*80 + "\n")
            f.write("DETAILED MODIFICATIONS:\n")
            f.write("="*80 + "\n\n")
            
            current_file = None
            for mod in self.modifications:
                if mod['file'] != current_file:
                    current_file = mod['file']
                    f.write(f"\n{'─'*80}\n")
                    f.write(f"FILE: {current_file}\n")
                    f.write(f"{'─'*80}\n\n")
                
                f.write(f"Line {mod['line']} [{mod['pattern']}]:\n")
                f.write(f"  Text: \"{mod['text']}\"\n")
                f.write(f"  BEFORE: {mod['original']}\n")
                f.write(f"  AFTER:  {mod['modified']}\n\n")
        
        print(f"📝 Detailed log saved to: {log_file}")


def main():
    """Main execution"""
    applier = YellowApplier()
    applier.run()
    print("✅ Yellow decisions applied!\n")


if __name__ == '__main__':
    main()
