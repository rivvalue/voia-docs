#!/usr/bin/env python3
"""
Automated Translation Wrapper - Phase 2
Surgically wraps GREEN-classified strings with {{ _('...') }}
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime


class AutoWrapper:
    def __init__(self, green_file='green_auto_fix.json', dry_run=False):
        self.green_file = green_file
        self.dry_run = dry_run
        self.modifications = []
        self.errors = []
        self.stats = {
            'files_modified': 0,
            'strings_wrapped': 0,
            'skipped': 0,
            'errors': 0
        }
        
    def load_green_items(self):
        """Load GREEN items approved for auto-fixing"""
        print(f"📖 Loading auto-fix items from: {self.green_file}")
        
        with open(self.green_file, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        print(f"✅ Loaded {len(items)} items for auto-wrapping\n")
        return items
    
    def group_by_file(self, items):
        """Group items by file for efficient processing"""
        by_file = {}
        for item in items:
            file_path = item['file'].strip('"')
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(item)
        
        # Sort items by line number (descending) for each file
        # This prevents line number shifts when modifying
        for file_path in by_file:
            by_file[file_path].sort(key=lambda x: int(x['line']), reverse=True)
        
        return by_file
    
    def wrap_string(self, text, pattern):
        """Generate wrapped version based on pattern type"""
        text = text.strip()
        
        # Already has quotes? Use them
        if text.startswith('"') and text.endswith('"'):
            inner = text[1:-1]
            return f"{{{{ _('{inner}') }}}}"
        if text.startswith("'") and text.endswith("'"):
            inner = text[1:-1]
            return f'{{{{ _("{inner}") }}}}'
        
        # Escape single quotes in text
        if "'" in text and '"' not in text:
            return f'{{{{ _("{text}") }}}}'
        elif '"' in text and "'" not in text:
            return f"{{{{ _('{text}') }}}}"
        else:
            # Has both - escape the singles
            escaped = text.replace("'", "\\'")
            return f"{{{{ _('{escaped}') }}}}"
    
    def create_replacement(self, context, text, pattern):
        """Create the replacement for the context"""
        
        # For element content (th, h1-6, p, label, button)
        if pattern in ['Table headers (th)', 'Headings (h1-h6)', 'Paragraphs', 'Labels', 'Buttons']:
            # Find the text between tags
            wrapped_text = self.wrap_string(text, pattern)
            # Replace the text content but keep the tags
            new_context = context.replace(f'>{text}<', f'>{wrapped_text}<')
            return new_context
        
        # For attributes (placeholder, title, alt)
        elif pattern in ['Placeholder attributes', 'Title attributes', 'Alt attributes']:
            # Extract attribute name
            attr_match = re.search(r'(placeholder|title|alt)="([^"]*)"', context)
            if attr_match:
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2)
                wrapped_value = self.wrap_string(attr_value, pattern)
                # Replace attribute value
                old_attr = f'{attr_name}="{attr_value}"'
                new_attr = f'{attr_name}={wrapped_value}'
                new_context = context.replace(old_attr, new_attr)
                return new_context
        
        # Fallback: try simple text replacement
        wrapped_text = self.wrap_string(text, pattern)
        new_context = context.replace(text, wrapped_text)
        return new_context
    
    def apply_wrap_to_line(self, line_content, item):
        """Apply wrapping to a specific line"""
        text = item['text']
        context = item['context']
        pattern = item['pattern']
        
        # Verify the line still contains the expected text
        if text not in line_content and context not in line_content:
            return None, f"Line content changed - skipping for safety"
        
        # Create replacement
        try:
            if pattern in ['Table headers (th)', 'Headings (h1-h6)', 'Paragraphs', 'Labels', 'Buttons']:
                # Element content wrapping
                wrapped = self.wrap_string(text, pattern)
                new_line = line_content.replace(f'>{text}<', f'>{wrapped}<', 1)
            
            elif pattern in ['Placeholder attributes', 'Title attributes', 'Alt attributes']:
                # Attribute wrapping
                attr_name = pattern.split()[0].lower()
                if attr_name == 'placeholder':
                    attr_pattern = f'placeholder="{re.escape(text)}"'
                    wrapped = self.wrap_string(text, pattern)
                    new_line = re.sub(attr_pattern, f'placeholder={wrapped}', line_content)
                elif attr_name == 'title':
                    attr_pattern = f'title="{re.escape(text)}"'
                    wrapped = self.wrap_string(text, pattern)
                    new_line = re.sub(attr_pattern, f'title={wrapped}', line_content)
                elif attr_name == 'alt':
                    attr_pattern = f'alt="{re.escape(text)}"'
                    wrapped = self.wrap_string(text, pattern)
                    new_line = re.sub(attr_pattern, f'alt={wrapped}', line_content)
                else:
                    new_line = line_content
            else:
                # Fallback
                wrapped = self.wrap_string(text, pattern)
                new_line = line_content.replace(text, wrapped, 1)
            
            if new_line == line_content:
                return None, f"No change detected - pattern might not match"
            
            return new_line, None
        
        except Exception as e:
            return None, f"Error creating replacement: {str(e)}"
    
    def process_file(self, file_path, items):
        """Process a single file with multiple wrapping operations"""
        print(f"📝 Processing: {file_path} ({len(items)} items)")
        
        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            error_msg = f"Error reading {file_path}: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)
            self.stats['errors'] += 1
            return
        
        # Apply modifications (from bottom to top to preserve line numbers)
        modifications_made = 0
        skipped = 0
        
        for item in items:
            line_num = int(item['line']) - 1  # Convert to 0-indexed
            
            if line_num >= len(lines):
                print(f"   ⚠️  Line {item['line']} out of range - skipping")
                skipped += 1
                continue
            
            original_line = lines[line_num]
            new_line, error = self.apply_wrap_to_line(original_line, item)
            
            if error:
                print(f"   ⚠️  Line {item['line']}: {error}")
                skipped += 1
                continue
            
            if new_line:
                lines[line_num] = new_line
                modifications_made += 1
                
                self.modifications.append({
                    'file': file_path,
                    'line': item['line'],
                    'pattern': item['pattern'],
                    'original': original_line.strip(),
                    'modified': new_line.strip(),
                    'text': item['text']
                })
        
        # Write file if not dry run
        if not self.dry_run and modifications_made > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"   ✅ Modified {modifications_made} lines, skipped {skipped}")
                self.stats['files_modified'] += 1
                self.stats['strings_wrapped'] += modifications_made
                self.stats['skipped'] += skipped
            except Exception as e:
                error_msg = f"Error writing {file_path}: {e}"
                print(f"   ❌ {error_msg}")
                self.errors.append(error_msg)
                self.stats['errors'] += 1
        else:
            if self.dry_run:
                print(f"   🔍 DRY RUN: Would modify {modifications_made} lines, skip {skipped}")
            self.stats['strings_wrapped'] += modifications_made
            self.stats['skipped'] += skipped
    
    def run(self):
        """Execute auto-wrapping"""
        print("="*80)
        print("🤖 AUTO-WRAPPER - Phase 2")
        print("="*80)
        
        if self.dry_run:
            print("\n🔍 DRY RUN MODE - No files will be modified\n")
        
        # Load items
        items = self.load_green_items()
        
        # Group by file
        by_file = self.group_by_file(items)
        print(f"📁 Files to process: {len(by_file)}\n")
        
        # Process each file
        for file_path in sorted(by_file.keys()):
            self.process_file(file_path, by_file[file_path])
        
        # Generate report
        self.generate_report()
        
        # Save log
        if not self.dry_run:
            self.save_log()
    
    def generate_report(self):
        """Generate final report"""
        print("\n" + "="*80)
        print("📊 AUTO-WRAPPING REPORT")
        print("="*80)
        
        print(f"\n✅ SUMMARY:")
        print(f"   Files modified: {self.stats['files_modified']}")
        print(f"   Strings wrapped: {self.stats['strings_wrapped']}")
        print(f"   Skipped: {self.stats['skipped']}")
        print(f"   Errors: {self.stats['errors']}")
        
        if self.errors:
            print(f"\n❌ ERRORS:")
            for error in self.errors:
                print(f"   - {error}")
        
        if self.stats['strings_wrapped'] > 0:
            print(f"\n💡 NEXT STEPS:")
            print(f"   1. Review auto_wrap_log.txt for all changes")
            print(f"   2. Test application for syntax errors")
            print(f"   3. Proceed to Phase 3: Manual review of {250} YELLOW items")
        
        print("="*80 + "\n")
    
    def save_log(self):
        """Save detailed modification log"""
        log_file = f"auto_wrap_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("AUTO-WRAPPER MODIFICATION LOG\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"SUMMARY:\n")
            f.write(f"  Files modified: {self.stats['files_modified']}\n")
            f.write(f"  Strings wrapped: {self.stats['strings_wrapped']}\n")
            f.write(f"  Skipped: {self.stats['skipped']}\n")
            f.write(f"  Errors: {self.stats['errors']}\n\n")
            
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
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auto-wrap GREEN-classified strings for translation'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--input',
        default='green_auto_fix.json',
        help='Input JSON file with GREEN items'
    )
    
    args = parser.parse_args()
    
    # Backup reminder
    if not args.dry_run:
        print("\n⚠️  IMPORTANT: Make sure you have a git backup before proceeding!")
        print("   Recommended: git add -A && git commit -m 'Pre-translation checkpoint'\n")
        
        response = input("Continue with auto-wrapping? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Aborted")
            return
    
    # Run wrapper
    wrapper = AutoWrapper(green_file=args.input, dry_run=args.dry_run)
    wrapper.run()
    
    print("✅ Auto-wrapper complete!\n")


if __name__ == '__main__':
    main()
