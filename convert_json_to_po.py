"""
Convert VOÏA JSON translations to Flask-Babel .po format
"""

import json
import os
from datetime import datetime

def create_po_header():
    """Create standard .po file header"""
    return f'''# French translations for VOÏA.
# Copyright (C) 2025 Rivvalue Inc
# This file is distributed under the same license as the VOÏA project.
#
msgid ""
msgstr ""
"Project-Id-Version: VOÏA 1.0\\n"
"Report-Msgid-Bugs-To: support@rivvalue.com\\n"
"POT-Creation-Date: {datetime.now().strftime('%Y-%m-%d %H:%M%z')}\\n"
"PO-Revision-Date: {datetime.now().strftime('%Y-%m-%d %H:%M%z')}\\n"
"Last-Translator: Rivvalue Team\\n"
"Language: fr\\n"
"Language-Team: French\\n"
"Plural-Forms: nplurals=2; plural=(n > 1);\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=utf-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: convert_json_to_po.py\\n"

'''

def escape_po_string(text):
    """Escape special characters for .po format"""
    if not text:
        return '""'
    
    # Escape backslashes first
    text = text.replace('\\', '\\\\')
    # Escape quotes
    text = text.replace('"', '\\"')
    # Handle newlines
    text = text.replace('\n', '\\n')
    
    return f'"{text}"'

def convert_json_to_po():
    """Convert all JSON translation files to a single .po file"""
    
    print("="*60)
    print("Converting JSON translations to .po format")
    print("="*60)
    
    all_translations = {}
    
    # Load all translated JSON files
    files = [
        'translated_part_01.json', 'translated_part_02.json', 'translated_part_03.json',
        'translated_part_04.json', 'translated_part_05.json', 'translated_part_06.json',
        'translated_part_07.json', 'translated_part_08a.json', 'translated_part_08b2.json',
        'translated_part_09.json', 'translated_part_10.json'
    ]
    
    for filename in files:
        if not os.path.exists(filename):
            print(f"  ⚠ {filename} not found - skipping")
            continue
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process templates
            for item in data.get('templates', []):
                if 'original_text' in item and 'text' in item:
                    msgid = item['original_text']
                    msgstr = item['text']
                    
                    # Skip if same or empty
                    if msgid and msgstr and msgid != msgstr:
                        all_translations[msgid] = msgstr
            
            # Process flash messages
            for item in data.get('flash_messages', []):
                if 'original_text' in item and 'text' in item:
                    msgid = item['original_text']
                    msgstr = item['text']
                    
                    if msgid and msgstr and msgid != msgstr:
                        all_translations[msgid] = msgstr
            
            # Process email templates
            for item in data.get('email_templates', []):
                if 'original_text' in item and 'text' in item:
                    msgid = item['original_text']
                    msgstr = item['text']
                    
                    if msgid and msgstr and msgid != msgstr:
                        all_translations[msgid] = msgstr
            
            print(f"  ✓ Loaded {filename}")
            
        except Exception as e:
            print(f"  ✗ Error loading {filename}: {e}")
    
    print(f"\n📊 Total unique translations: {len(all_translations)}")
    
    # Create .po file for French
    po_content = create_po_header()
    
    for msgid, msgstr in sorted(all_translations.items()):
        po_content += f"\nmsgid {escape_po_string(msgid)}\n"
        po_content += f"msgstr {escape_po_string(msgstr)}\n"
    
    # Write French .po file
    os.makedirs('translations/fr/LC_MESSAGES', exist_ok=True)
    with open('translations/fr/LC_MESSAGES/messages.po', 'w', encoding='utf-8') as f:
        f.write(po_content)
    
    print(f"✅ Created translations/fr/LC_MESSAGES/messages.po")
    
    # Create empty English .po file (English is the source)
    en_po_content = create_po_header().replace('Language: fr', 'Language: en').replace('French', 'English')
    
    os.makedirs('translations/en/LC_MESSAGES', exist_ok=True)
    with open('translations/en/LC_MESSAGES/messages.po', 'w', encoding='utf-8') as f:
        f.write(en_po_content)
    
    print(f"✅ Created translations/en/LC_MESSAGES/messages.po (empty - English is source)")
    
    print("\n" + "="*60)
    print("✓ Conversion complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Compile .po files to .mo: pybabel compile -d translations")
    print("2. Update templates with {{ _('text') }} markers")
    print("3. Add language switcher to UI")

if __name__ == '__main__':
    convert_json_to_po()
