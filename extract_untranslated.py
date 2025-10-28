#!/usr/bin/env python3
"""
Simple tool to extract untranslated strings from .po file
"""

import re
import json

def extract_untranslated(po_file='translations/fr/LC_MESSAGES/messages.po'):
    """Extract all msgid/msgstr pairs where msgstr is empty"""
    
    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    untranslated = []
    
    # Simple pattern: msgid followed by empty msgstr
    # Split content into blocks
    blocks = content.split('\nmsgid ')
    
    for block in blocks[1:]:  # Skip first empty block
        lines = block.split('\n')
        
        # Get msgid (first line)
        msgid_line = lines[0]
        msgid_match = re.match(r'"(.+?)"', msgid_line)
        
        if not msgid_match:
            continue
            
        msgid = msgid_match.group(1)
        
        # Skip empty msgid
        if not msgid:
            continue
        
        # Find msgstr in subsequent lines
        msgstr = None
        for line in lines[1:]:
            if line.startswith('msgstr "'):
                msgstr_match = re.match(r'msgstr "(.*)\"', line)
                if msgstr_match:
                    msgstr = msgstr_match.group(1)
                break
        
        # If msgstr is empty, this needs translation
        if msgstr == "":
            untranslated.append({
                'english': msgid,
                'french': ''
            })
    
    return untranslated

def main():
    print("🔍 EXTRACTING UNTRANSLATED STRINGS")
    print("=" * 70)
    
    untranslated = extract_untranslated()
    
    print(f"\n✅ Found {len(untranslated)} untranslated strings")
    
    # Save to JSON
    output_file = 'untranslated.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(untranslated, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Saved to: {output_file}")
    
    # Show sample
    print(f"\n📋 Sample (first 10):")
    for i, item in enumerate(untranslated[:10], 1):
        print(f"  {i}. {item['english'][:60]}...")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"1. I'll use AI to translate these {len(untranslated)} strings")
    print(f"2. Review and merge translations back into .po file")
    print(f"3. Compile with: pybabel compile -d translations")

if __name__ == '__main__':
    main()
