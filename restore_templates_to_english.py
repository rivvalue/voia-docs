"""
Restore all templates to English with Flask-Babel {{ _() }} markers
Uses original_text from translation JSON files
"""

import json
import os
import re
from pathlib import Path
import shutil

def load_french_to_english_mapping():
    """Load complete French → English mapping from all translation files"""
    mapping = {}
    
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
        
        # Process all sections
        for section in ['templates', 'flash_messages', 'email_templates']:
            for item in data.get(section, []):
                original = item.get('original_text', '').strip()
                french = item.get('text', '').strip()
                
                if original and french and original != french:
                    mapping[french] = original
    
    print(f"✓ Loaded {len(mapping)} French → English mappings")
    return mapping

def restore_template(template_path, fr_to_en, dry_run=False):
    """Restore a single template to English with {{ _() }} markers"""
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    replacements = 0
    
    # Sort by length (longest first) to avoid partial replacements
    sorted_mappings = sorted(fr_to_en.items(), key=lambda x: len(x[0]), reverse=True)
    
    for french_text, english_text in sorted_mappings:
        if len(french_text) < 4:  # Skip very short strings to avoid false matches
            continue
        
        if french_text in content:
            # Escape single quotes for Jinja2
            escaped_english = english_text.replace("'", "\\'")
            
            # Check if it's already wrapped in {{ _() }}
            pattern = re.escape(french_text)
            
            # Only replace if NOT already inside {% %} or {{ }}
            # Simple approach: replace standalone occurrences
            before_count = content.count(french_text)
            
            # Replace French with {{ _('English') }}
            content = content.replace(french_text, f"{{{{ _('{escaped_english}') }}}}")
            
            after_count = content.count(french_text)
            
            if before_count > after_count:
                replacements += before_count - after_count
    
    if replacements > 0 and not dry_run:
        # Create backup
        backup_path = f"{template_path}.backup"
        shutil.copy2(template_path, backup_path)
        
        # Write restored content
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return replacements, True
    
    return replacements, False

def main():
    print("=" * 70)
    print("RESTORING TEMPLATES TO ENGLISH")
    print("=" * 70)
    
    # Load mappings
    print("\n📥 Loading translation mappings...")
    fr_to_en = load_french_to_english_mapping()
    
    # Find all templates
    print("\n📁 Finding templates...")
    templates = []
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                templates.append(os.path.join(root, file))
    
    print(f"✓ Found {len(templates)} templates")
    
    # Process templates
    print("\n🔄 Restoring templates...")
    print("-" * 70)
    
    processed = 0
    modified = 0
    total_replacements = 0
    
    for template_path in sorted(templates):
        replacements, was_modified = restore_template(template_path, fr_to_en, dry_run=False)
        
        if was_modified:
            modified += 1
            total_replacements += replacements
            print(f"✓ {template_path}: {replacements} replacements")
        
        processed += 1
    
    print("-" * 70)
    print(f"\n📊 SUMMARY:")
    print(f"  Templates processed: {processed}")
    print(f"  Templates modified: {modified}")
    print(f"  Total replacements: {total_replacements}")
    print(f"\n✅ Templates restored to English with Flask-Babel markers")
    print(f"💾 Backups saved as *.backup")

if __name__ == '__main__':
    main()
