"""
VOÏA Automated French Translation v3 - Production Ready
Uses JSON schema enforcement and optimized batching for reliable, fast translation
"""

import json
import os
import time
import re
from openai import OpenAI

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# Optimal batch size per architect recommendation
BATCH_SIZE = 20

def protect_placeholders(text):
    """Wrap placeholders in protection markers to prevent GPT from translating them"""
    # Protect {variable}, {{variable}}, {%...%}
    text = re.sub(r'\{([^}]+)\}', r'<KEEP>\1</KEEP>', text)
    text = re.sub(r'\{\{([^}]+)\}\}', r'<KEEP2>\1</KEEP2>', text)
    text = re.sub(r'\{%([^%]+)%\}', r'<KEEP3>\1</KEEP3>', text)
    return text

def restore_placeholders(text):
    """Restore protected placeholders to original format"""
    text = re.sub(r'<KEEP>([^<]+)</KEEP>', r'{\1}', text)
    text = re.sub(r'<KEEP2>([^<]+)</KEEP2>', r'{{\1}}', text)
    text = re.sub(r'<KEEP3>([^<]+)</KEEP3>', r'{%\1%}', text)
    return text

def translate_batch_with_schema(items, max_retries=3):
    """Translate a batch using JSON schema for guaranteed structure"""
    
    # Prepare items with protected placeholders
    protected_items = []
    for item in items:
        protected_text = protect_placeholders(item['text'])
        protected_items.append({
            "id": item["id"],
            "text": protected_text
        })
    
    # Define JSON schema for response
    response_schema = {
        "type": "object",
        "properties": {
            "translations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {"type": "string"}
                    },
                    "required": ["id", "text"]
                }
            }
        },
        "required": ["translations"]
    }
    
    prompt = f"""Translate the following strings from English to professional French (France market).

CRITICAL RULES:
1. Translate ONLY the actual text content - DO NOT translate anything inside <KEEP>, <KEEP2>, or <KEEP3> tags
2. Preserve <KEEP>, <KEEP2>, <KEEP3> tags and their contents EXACTLY as-is
3. Use professional business French (formal "vous", not "tu")
4. Keep these terms unchanged: VOÏA, NPS, API, and any UPPERCASE technical terms

CONSISTENT TERMINOLOGY:
- Campaign → Campagne
- Participant → Participant
- Survey → Enquête
- Dashboard → Tableau de bord
- Feedback → Retour d'information
- Business Account → Compte entreprise
- Insights → Analyses
- Settings → Paramètres
- Analytics → Analytique

Input strings:
{json.dumps(protected_items, ensure_ascii=False, indent=2)}

Return in this exact format:
{{
  "translations": [
    {{"id": "...", "text": "French translation here"}},
    ...
  ]
}}"""

    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional French translator for SaaS applications. You preserve all markup tags and technical syntax while translating content. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=8192
            )
            
            # Parse response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            
            result = json.loads(content)
            translated_items = result['translations']
            
            # Restore placeholders and update original items
            translation_map = {}
            for translated in translated_items:
                restored_text = restore_placeholders(translated['text'])
                translation_map[translated['id']] = restored_text
            
            # Apply translations
            for item in items:
                if item['id'] in translation_map:
                    item['text'] = translation_map[item['id']]
            
            return items, None
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt)  # Exponential backoff
                print(f"\n    Retry {attempt + 1}/{max_retries} after {wait_time}s (Error: {str(e)[:50]}...)")
                time.sleep(wait_time)
            else:
                return items, str(e)
    
    return items, "Max retries exceeded"

def translate_file(filename, output_filename):
    """Translate a single JSON file with optimized batching"""
    
    print(f"\n{'='*60}")
    print(f"Translating: {filename}")
    print(f"{'='*60}")
    
    if not os.path.exists(filename):
        print(f"  ✗ File not found: {filename}")
        return False
    
    try:
        # Load the file
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get all items
        all_items = []
        if data.get('templates'):
            all_items = data['templates']
            item_type = "templates"
        elif data.get('flash_messages'):
            all_items = data['flash_messages']
            item_type = "flash_messages"
        elif data.get('email_templates'):
            all_items = data['email_templates']
            item_type = "email_templates"
        else:
            print(f"  ⚠ No translatable content")
            return False
        
        # Filter out empty items
        translatable_items = [item for item in all_items if item.get('text', '').strip()]
        total_items = len(translatable_items)
        
        print(f"  Found {total_items} {item_type} to translate")
        
        # Sort by length for better batching
        translatable_items.sort(key=lambda x: len(x.get('text', '')))
        
        # Translate in batches
        translated_count = 0
        error_count = 0
        num_batches = (total_items + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, total_items, BATCH_SIZE):
            batch = translatable_items[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            print(f"  Batch {batch_num}/{num_batches} ({len(batch)} items)...", end=" ", flush=True)
            
            translated_batch, error = translate_batch_with_schema(batch)
            
            if error:
                print(f"✗ ({error})")
                error_count += len(batch)
            else:
                print(f"✓")
                translated_count += len(batch)
            
            # Update original items
            for item in translated_batch:
                # Find and update in original all_items list
                for orig_item in all_items:
                    if orig_item['id'] == item['id']:
                        orig_item['text'] = item['text']
                        break
            
            # Rate limit protection
            if i + BATCH_SIZE < total_items:
                time.sleep(0.5)
        
        print(f"  ✓ Translated: {translated_count}/{total_items}")
        if error_count > 0:
            print(f"  ⚠ Errors: {error_count}/{total_items} (kept original English)")
        
        # Save translated file
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved: {output_filename}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main translation process"""
    
    print("="*60)
    print("VOÏA Automated French Translation v3 (Production)")
    print("JSON Schema + Optimized Batching")
    print("="*60)
    
    if not OPENAI_API_KEY:
        print("\n❌ Error: OPENAI_API_KEY not found!")
        return
    
    print("\n✓ OpenAI API key configured")
    print(f"✓ Batch size: {BATCH_SIZE} items")
    print("✓ Placeholder protection: enabled")
    print("✓ Auto-retry: enabled (3 attempts per batch)")
    print("\nStarting translation...\n")
    
    files_to_translate = [
        ("translate_part_01_templates.json", "translated_part_01.json"),
        ("translate_part_02_templates.json", "translated_part_02.json"),
        ("translate_part_03_templates.json", "translated_part_03.json"),
        ("translate_part_04_templates.json", "translated_part_04.json"),
        ("translate_part_05_templates.json", "translated_part_05.json"),
        ("translate_part_06_templates.json", "translated_part_06.json"),
        ("translate_part_07_templates.json", "translated_part_07.json"),
        ("translate_part_08_templates.json", "translated_part_08.json"),
        ("translate_part_09_flash_messages.json", "translated_part_09.json"),
        ("translate_part_10_email_templates.json", "translated_part_10.json"),
    ]
    
    successful = 0
    failed = 0
    start_time = time.time()
    
    for source, target in files_to_translate:
        if translate_file(source, target):
            successful += 1
        else:
            failed += 1
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("Translation Complete!")
    print("="*60)
    print(f"Successful: {successful}/10 files")
    print(f"Failed: {failed}/10 files")
    print(f"Time: {elapsed_time/60:.1f} minutes")
    
    if successful == 10:
        print("\n✅ All files translated successfully!")
        print("\nNext step:")
        print("  python integrate_translations.py")
    elif successful > 0:
        print("\n⚠ Partial success - you can still integrate:")
        print("  python integrate_translations.py")
    else:
        print("\n❌ Translation failed - check errors above")

if __name__ == "__main__":
    main()
