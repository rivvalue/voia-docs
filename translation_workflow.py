#!/usr/bin/env python3
"""
Hybrid AI + Human Translation Workflow Tool
Extracts untranslated strings, prepares for AI translation, and merges results back
"""

import re
import json
from pathlib import Path

class TranslationWorkflow:
    def __init__(self, po_file='translations/fr/LC_MESSAGES/messages.po'):
        self.po_file = po_file
        self.entries = []
        
    def parse_po_file(self):
        """Parse .po file and extract all entries"""
        with open(self.po_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into entries (each starts with #:)
        entries = re.split(r'\n(?=#:)', content)
        
        parsed_entries = []
        for entry in entries:
            if not entry.strip() or entry.startswith('#'):
                continue
                
            # Extract components
            location_match = re.search(r'#: (.+)', entry)
            msgid_match = re.search(r'msgid "(.+?)"', entry, re.DOTALL)
            msgstr_match = re.search(r'msgstr "(.+?)"', entry, re.DOTALL)
            
            if msgid_match:
                msgid = msgid_match.group(1)
                msgstr = msgstr_match.group(1) if msgstr_match else ""
                location = location_match.group(1) if location_match else ""
                
                parsed_entries.append({
                    'location': location,
                    'msgid': msgid,
                    'msgstr': msgstr,
                    'needs_translation': msgstr == ""
                })
        
        self.entries = parsed_entries
        return parsed_entries
    
    def get_untranslated(self):
        """Get all untranslated entries"""
        return [e for e in self.entries if e['needs_translation']]
    
    def categorize_strings(self, untranslated):
        """Categorize strings for better context"""
        categories = {
            'forms': [],
            'buttons': [],
            'headers': [],
            'messages': [],
            'labels': [],
            'placeholders': [],
            'general': []
        }
        
        for entry in untranslated:
            msgid = entry['msgid']
            location = entry['location'].lower()
            
            # Categorize based on content and context
            if any(word in msgid.lower() for word in ['email', 'password', 'name', 'phone', 'address']):
                categories['forms'].append(entry)
            elif any(word in msgid.lower() for word in ['save', 'cancel', 'submit', 'delete', 'add', 'edit']):
                categories['buttons'].append(entry)
            elif any(word in msgid for word in ['Dashboard', 'Settings', 'Admin', 'Campaign']):
                categories['headers'].append(entry)
            elif any(word in msgid.lower() for word in ['success', 'error', 'warning', 'loading']):
                categories['messages'].append(entry)
            elif len(msgid) > 50:
                categories['messages'].append(entry)
            else:
                categories['general'].append(entry)
        
        return categories
    
    def export_for_translation(self, output_file='untranslated.json'):
        """Export untranslated strings in format for AI translation"""
        untranslated = self.get_untranslated()
        
        export_data = []
        for entry in untranslated:
            export_data.append({
                'english': entry['msgid'],
                'french': '',  # To be filled
                'context': entry['location'][:100]  # First 100 chars of location
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(export_data)} strings to {output_file}")
        return export_data
    
    def import_translations(self, translation_file='translations_fr.json'):
        """Import AI-generated translations and update .po file"""
        with open(translation_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        # Read original .po file
        with open(self.po_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create translation lookup
        trans_lookup = {t['english']: t['french'] for t in translations if t['french']}
        
        # Replace empty msgstr with translations
        updated_count = 0
        for english, french in trans_lookup.items():
            # Escape special characters
            english_escaped = english.replace('\\', '\\\\').replace('"', '\\"')
            french_escaped = french.replace('\\', '\\\\').replace('"', '\\"')
            
            # Pattern to match msgid + empty msgstr
            pattern = f'(msgid "{english_escaped}"\\nmsgstr )"'
            replacement = f'\\1"{french_escaped}"'
            
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                updated_count += 1
        
        # Write back to file
        with open(self.po_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated {updated_count} translations in {self.po_file}")
        return updated_count
    
    def generate_statistics(self):
        """Generate translation statistics"""
        total = len(self.entries)
        untranslated = len(self.get_untranslated())
        translated = total - untranslated
        
        print(f"\n📊 TRANSLATION STATISTICS")
        print(f"=" * 60)
        print(f"Total entries:      {total}")
        print(f"Translated:         {translated} ({translated/total*100:.1f}%)")
        print(f"Untranslated:       {untranslated} ({untranslated/total*100:.1f}%)")
        
        if untranslated > 0:
            categories = self.categorize_strings(self.get_untranslated())
            print(f"\n📋 Untranslated by category:")
            for cat, items in categories.items():
                if items:
                    print(f"  {cat:15s}: {len(items):3d}")
        
        return {
            'total': total,
            'translated': translated,
            'untranslated': untranslated,
            'percentage': translated/total*100
        }


def main():
    print("🔄 HYBRID TRANSLATION WORKFLOW")
    print("=" * 60)
    
    workflow = TranslationWorkflow()
    
    print("\n1️⃣  Parsing .po file...")
    workflow.parse_po_file()
    
    print("\n2️⃣  Generating statistics...")
    stats = workflow.generate_statistics()
    
    if stats['untranslated'] > 0:
        print("\n3️⃣  Exporting untranslated strings...")
        workflow.export_for_translation('untranslated.json')
        
        print("\n" + "=" * 60)
        print("📝 NEXT STEPS:")
        print("=" * 60)
        print("1. Review untranslated.json")
        print("2. Use AI or manual translation to fill 'french' fields")
        print("3. Save as translations_fr.json")
        print("4. Run: python translation_workflow.py --import")
        print("5. Compile: pybabel compile -d translations")
    else:
        print("\n✅ All strings are translated!")
        print("\nTo compile translations:")
        print("  pybabel compile -d translations")

if __name__ == '__main__':
    import sys
    
    if '--import' in sys.argv:
        if len(sys.argv) > 2:
            file = sys.argv[2]
        else:
            file = 'translations_fr.json'
        
        workflow = TranslationWorkflow()
        workflow.parse_po_file()
        workflow.import_translations(file)
        print("\n✅ Import complete! Now compile with:")
        print("  pybabel compile -d translations")
    else:
        main()
