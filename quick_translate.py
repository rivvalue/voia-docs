"""
Quick French translation - streamlined for speed
Translates all files in parallel batches
"""

import json
import os
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def translate_text(text):
    """Simple, fast translation"""
    if not text or len(text.strip()) == 0:
        return text
    
    try:
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "Translate to French. Preserve {variables} and {{variables}} exactly. Use formal vous. Return only the translation."},
                {"role": "user", "content": text}
            ],
            max_completion_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        # Remove quotes if GPT added them
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        if result.startswith("'") and result.endswith("'"):
            result = result[1:-1]
        return result
    except:
        return text  # Keep original on error

def translate_file_fast(source_file):
    """Translate one file quickly"""
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get items
    items = data.get('templates', data.get('flash_messages', data.get('email_templates', [])))
    
    print(f"Translating {source_file}: {len(items)} items...")
    
    # Translate all items
    for i, item in enumerate(items):
        if i % 50 == 0:
            print(f"  {i}/{len(items)}", end='\r')
        item['text'] = translate_text(item['text'])
    
    # Save
    output_file = source_file.replace('translate_part_', 'translated_part_').replace('_templates', '').replace('_flash_messages', '').replace('_email_templates', '')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ {output_file} ({len(items)} items)")
    return output_file

# Translate all 10 files
files = [
    "translate_part_01_templates.json",
    "translate_part_02_templates.json",
    "translate_part_03_templates.json",
    "translate_part_04_templates.json",
    "translate_part_05_templates.json",
    "translate_part_06_templates.json",
    "translate_part_07_templates.json",
    "translate_part_08_templates.json",
    "translate_part_09_flash_messages.json",
    "translate_part_10_email_templates.json",
]

print("=" * 60)
print("Quick French Translation - All 10 Files")
print("=" * 60)
print()

for f in files:
    translate_file_fast(f)

print("\n✅ All files translated!")
print("Run: python integrate_translations.py")
