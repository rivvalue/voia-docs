"""
Merge original English JSON files with translated French JSON files
Creates new files with both original_text and text fields
"""

import json
import os

def merge_translations():
    """Merge original and translated files by matching IDs"""
    
    # Mapping of translated files to original files
    file_mappings = [
        ('translated_part_01.json', 'translate_part_01_templates.json'),
        ('translated_part_02.json', 'translate_part_02_templates.json'),
        ('translated_part_03.json', 'translate_part_03_templates.json'),
        ('translated_part_04.json', 'translate_part_04_templates.json'),
        ('translated_part_05.json', 'translate_part_05_templates.json'),
        ('translated_part_06.json', 'translate_part_06_templates.json'),
        ('translated_part_07.json', 'translate_part_07_templates.json'),
        ('translated_part_08a.json', 'translate_part_08a_templates.json'),
        ('translated_part_08b1.json', 'translate_part_08b_templates.json'),  # Both b1 and b2 came from 08b
        ('translated_part_08b2.json', 'translate_part_08b_templates.json'),
        ('translated_part_09.json', 'translate_part_09_flash.json'),
        ('translated_part_10.json', 'translate_part_10_email.json'),
    ]
    
    for translated_file, original_file in file_mappings:
        if not os.path.exists(translated_file):
            print(f"⚠ {translated_file} not found - skipping")
            continue
        if not os.path.exists(original_file):
            print(f"⚠ {original_file} not found - skipping")
            continue
        
        try:
            # Load both files
            with open(translated_file, 'r', encoding='utf-8') as f:
                translated_data = json.load(f)
            with open(original_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            # Create lookup by ID for original data
            for section in ['templates', 'flash_messages', 'email_templates']:
                if section in original_data and section in translated_data:
                    original_by_id = {item['id']: item for item in original_data[section]}
                    
                    # Add original_text to translated items
                    for item in translated_data[section]:
                        item_id = item.get('id')
                        if item_id in original_by_id:
                            item['original_text'] = original_by_id[item_id].get('text', '')
            
            # Write merged file
            with open(translated_file, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Merged {translated_file}")
            
        except Exception as e:
            print(f"✗ Error merging {translated_file}: {e}")

if __name__ == '__main__':
    print("Merging original English with translated French...")
    print("="*60)
    merge_translations()
    print("="*60)
    print("✓ Merge complete!")
