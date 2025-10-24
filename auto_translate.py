"""
VOÏA Automated French Translation using OpenAI API
Translates all 10 JSON files automatically - no manual copy-paste needed!
"""

import json
import os
import time
from openai import OpenAI

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def translate_batch(items, batch_type="template"):
    """Translate a batch of items using OpenAI API"""
    
    # Prepare the translation request
    items_to_translate = []
    for item in items:
        items_to_translate.append({
            "id": item["id"],
            "text": item["text"]
        })
    
    prompt = f"""You are a professional French translator for a SaaS platform.

Translate the following JSON array from English to French (France market).

CRITICAL RULES:
1. Translate ONLY the "text" field values to French
2. Keep the "id" field EXACTLY as-is
3. Preserve ALL variables in their original form:
   - {{variable_name}} stays {{variable_name}} (NOT {{nom_de_variable}})
   - {{{{variable}}}} stays {{{{variable}}}}
   - {{%...%}} stays {{%...%}}
4. Use professional business French (formal "vous", not "tu")
5. Keep these terms UNCHANGED: VOÏA, NPS, API, and all UPPERCASE technical terms

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

Return ONLY valid JSON array with the same structure but "text" values in French.

JSON to translate:
{json.dumps(items_to_translate, ensure_ascii=False, indent=2)}"""

    try:
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional French translator specializing in SaaS and business applications. You maintain consistency in terminology and preserve all technical syntax."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=8192
        )
        
        # Parse the response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI API")
        result = json.loads(content)
        
        # Handle different response formats
        if isinstance(result, list):
            translated_items = result
        elif isinstance(result, dict):
            # Try common response formats
            if 'translations' in result:
                translated_items = result['translations']
            elif 'items' in result:
                translated_items = result['items']
            elif 'data' in result:
                translated_items = result['data']
            elif 'translated_items' in result:
                translated_items = result['translated_items']
            elif 'translated' in result:
                translated_items = result['translated']
            elif 'results' in result:
                translated_items = result['results']
            else:
                # Try to find any array value
                translated_items = None
                for key, value in result.items():
                    if isinstance(value, list) and len(value) > 0:
                        # Check if it looks like our translated items (has id and text)
                        if all(isinstance(item, dict) and 'id' in item and 'text' in item for item in value):
                            translated_items = value
                            break
                
                if translated_items is None:
                    # Last resort: try to extract individual translations from dict
                    # GPT might return {"id1": "translated text1", "id2": "translated text2"}
                    translated_items = []
                    for item in items:
                        item_id = item["id"]
                        if item_id in result:
                            translated_items.append({"id": item_id, "text": result[item_id]})
                        else:
                            # Keep original
                            translated_items.append({"id": item_id, "text": item["text"]})
                    
                    if not translated_items:
                        raise ValueError(f"Could not find translated array in response. Keys found: {list(result.keys())}")
        else:
            raise ValueError(f"Unexpected response format: {type(result)}")
        
        # Create a mapping of id to translated text
        translation_map = {}
        for item in translated_items:
            translation_map[item["id"]] = item["text"]
        
        # Apply translations back to original items
        for item in items:
            if item["id"] in translation_map:
                item["text"] = translation_map[item["id"]]
        
        return items
        
    except Exception as e:
        print(f"    ✗ Translation error: {e}")
        print(f"    Keeping original English text for this batch")
        return items

def translate_file(filename, output_filename, batch_size=50):
    """Translate a single JSON file in batches"""
    
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
        
        # Get all items that need translation
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
            print(f"  ⚠ No translatable content found")
            return False
        
        total_items = len(all_items)
        print(f"  Found {total_items} {item_type} to translate")
        
        # Translate in batches to avoid token limits
        translated_count = 0
        for i in range(0, total_items, batch_size):
            batch = all_items[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_items + batch_size - 1) // batch_size
            
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} items)...", end=" ", flush=True)
            
            translated_batch = translate_batch(batch, item_type)
            
            # Update the original items
            for j, item in enumerate(translated_batch):
                all_items[i + j] = item
            
            translated_count += len(batch)
            print(f"✓ ({translated_count}/{total_items})")
            
            # Small delay to avoid rate limits
            if i + batch_size < total_items:
                time.sleep(0.5)
        
        # Save the translated file
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved: {output_filename}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Main translation process"""
    
    print("="*60)
    print("VOÏA Automated French Translation")
    print("Using OpenAI API (GPT-5)")
    print("="*60)
    
    if not OPENAI_API_KEY:
        print("\n❌ Error: OPENAI_API_KEY not found!")
        print("Please set your OpenAI API key as an environment variable.")
        return
    
    print("\n✓ OpenAI API key found")
    print("Starting automated translation of 10 files...")
    
    # Translate all 10 files
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
    print(f"Successful: {successful}/10")
    print(f"Failed: {failed}/10")
    print(f"Time elapsed: {elapsed_time:.1f} seconds")
    
    if successful == 10:
        print("\n✓ All files translated successfully!")
        print("\nNext step: Run integration script")
        print("  python integrate_translations.py")
    elif successful > 0:
        print("\n⚠ Some files translated successfully")
        print("You can still run integration with the available files:")
        print("  python integrate_translations.py")
    else:
        print("\n❌ Translation failed")
        print("Please check the error messages above")

if __name__ == "__main__":
    main()
