"""
Helper script to migrate templates to use Flask-Babel gettext markers
This script helps convert hardcoded text to {{ _('text') }} format
"""

import json
import os
import re
from pathlib import Path

def load_all_translations():
    """Load all translations to get English originals"""
    english_to_french = {}
    french_to_english = {}
    
    files = [
        'translated_part_01.json', 'translated_part_02.json', 'translated_part_03.json',
        'translated_part_04.json', 'translated_part_05.json', 'translated_part_06.json',
        'translated_part_07.json', 'translated_part_08a.json', 'translated_part_08b2.json',
        'translated_part_09.json', 'translated_part_10.json'
    ]
    
    for filename in files:
        if not os.path.exists(filename):
            continue
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data.get('templates', []):
            if 'original_text' in item and 'text' in item:
                eng = item['original_text']
                fr = item['text']
                if eng and fr and eng != fr:
                    english_to_french[eng] = fr
                    french_to_english[fr] = eng
    
    return english_to_french, french_to_english

def find_french_texts_in_template(template_path, french_to_english):
    """Find French text in template that we can map back to English"""
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    found_translations = []
    
    # Find all potential text content (between > and <, or in attributes)
    for french_text, english_text in french_to_english.items():
        if french_text in content:
            found_translations.append({
                'french': french_text,
                'english': english_text,
                'count': content.count(french_text)
            })
    
    return found_translations

def wrap_with_gettext(text):
    """Wrap text with gettext marker"""
    # Escape single quotes for Jinja2
    text_escaped = text.replace("'", "\\'")
    return f"{{{{ _('{text_escaped}') }}}}"

def migrate_template(template_path, french_to_english, dry_run=True):
    """Migrate a single template to use gettext markers"""
    print(f"\n{'='*60}")
    print(f"Migrating: {template_path}")
    print(f"{'='*60}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    replacements = 0
    
    # Sort by length (longest first) to avoid partial replacements
    items = sorted(french_to_english.items(), key=lambda x: len(x[0]), reverse=True)
    
    for french_text, english_text in items:
        if french_text in content and len(french_text) > 3:  # Skip very short strings
            # Replace French with English wrapped in _()
            wrapped = wrap_with_gettext(english_text)
            
            # Be careful not to replace inside {% %} or {{ }} blocks
            # Simple heuristic: only replace plain text
            old_count = content.count(french_text)
            content = content.replace(french_text, wrapped)
            new_count = content.count(french_text)
            
            if old_count != new_count:
                replacements += 1
                print(f"  ✓ Replaced: {french_text[:50]}... → {english_text[:50]}...")
    
    print(f"\n📊 Total replacements: {replacements}")
    
    if not dry_run and replacements > 0:
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Saved {template_path}")
    elif dry_run:
        print(f"🔍 DRY RUN - no changes written")
    
    return replacements

if __name__ == '__main__':
    print("="*60)
    print("Template Migration Helper")
    print("="*60)
    
    # Load translations
    print("\n📥 Loading translations...")
    english_to_french, french_to_english = load_all_translations()
    print(f"✓ Loaded {len(french_to_english)} French→English mappings")
    
    # Demo templates to migrate
    demo_templates = [
        'templates/index.html',
        'templates/demo_intro.html',
        'templates/dashboard.html'
    ]
    
    print("\n" + "="*60)
    print("Analyzing demo templates...")
    print("="*60)
    
    for template in demo_templates:
        if os.path.exists(template):
            found = find_french_texts_in_template(template, french_to_english)
            print(f"\n📄 {template}:")
            print(f"   Found {len(found)} translatable French strings")
            for item in found[:5]:  # Show first 5
                print(f"   - {item['french'][:50]}... ({item['count']}x)")
    
    print("\n" + "="*60)
    print("Ready to migrate. Use --apply to actually modify files.")
    print("="*60)
