"""
VOÏA Automated French Translation using OpenAI API (Simplified Version)
More reliable translation with smaller batches and clearer prompts
"""

import json
import os
import time
from openai import OpenAI

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def translate_single_item(english_text, item_id):
    """Translate a single text string"""
    
    prompt = f"""Translate this English text to professional French (France market):

"{english_text}"

RULES:
- Use professional business French (formal "vous")
- Preserve ALL {{variables}}, {{{{variables}}}}, and {{%...%}} EXACTLY as-is
- Keep UNCHANGED: VOÏA, NPS, API, and UPPERCASE terms
- Return ONLY the French translation, nothing else

TERMINOLOGY:
Campaign → Campagne
Survey → Enquête
Dashboard → Tableau de bord
Feedback → Retour d'information
Participant → Participant
Settings → Paramètres

French translation:"""

    try:
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional French translator. You return ONLY the translated text, no explanations or extra formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_completion_tokens=500
        )
        
        french_text = response.choices[0].message.content
        if french_text:
            # Clean up the response (remove quotes if GPT added them)
            french_text = french_text.strip()
            if french_text.startswith('"') and french_text.endswith('"'):
                french_text = french_text[1:-1]
            if french_text.startswith("'") and french_text.endswith("'"):
                french_text = french_text[1:-1]
            return french_text
        else:
            return english_text
            
    except Exception as e:
        print(f"      Error translating '{english_text[:50]}...': {e}")
        return english_text

def translate_file(filename, output_filename, batch_size=20):
    """Translate a single JSON file"""
    
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
        print(f"  Translating item by item...")
        
        # Translate each item individually for reliability
        translated_count = 0
        for i, item in enumerate(all_items):
            english_text = item.get('text', '')
            
            # Skip empty strings
            if not english_text or len(english_text.strip()) == 0:
                continue
            
            # Show progress every 10 items
            if i % 10 == 0:
                print(f"  Progress: {i}/{total_items} ({int(i/total_items*100)}%)", end='\r', flush=True)
            
            # Translate
            french_text = translate_single_item(english_text, item.get('id', ''))
            
            # Update the item
            item['text'] = french_text
            translated_count += 1
            
            # Small delay to avoid rate limits (every 5 items)
            if i % 5 == 0 and i > 0:
                time.sleep(0.3)
        
        print(f"  Progress: {total_items}/{total_items} (100%)  ")
        print(f"  ✓ Translated {translated_count} items")
        
        # Save the translated file
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
    print("VOÏA Automated French Translation v2")
    print("Using OpenAI API (GPT-5) - Simplified Approach")
    print("="*60)
    
    if not OPENAI_API_KEY:
        print("\n❌ Error: OPENAI_API_KEY not found!")
        return
    
    print("\n✓ OpenAI API key found")
    print("Starting automated translation...")
    print("\nNOTE: This translates item-by-item for maximum reliability.")
    print("It will take 5-10 minutes but ensures quality translations.\n")
    
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
    print(f"Time elapsed: {elapsed_time/60:.1f} minutes")
    
    if successful == 10:
        print("\n✓ All files translated successfully!")
        print("\nNext step: Run integration script")
        print("  python integrate_translations.py")
    elif successful > 0:
        print("\n⚠ Some files translated successfully")
        print("You can still run integration with available files:")
        print("  python integrate_translations.py")
    else:
        print("\n❌ Translation failed")

if __name__ == "__main__":
    main()
