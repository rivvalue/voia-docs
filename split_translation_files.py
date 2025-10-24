"""
Split the large translation JSON into 10 smaller files for ChatGPT
"""

import json
import math

def split_json():
    """Split voila_strings_to_translate.json into 10 manageable parts"""
    
    with open('voila_strings_to_translate.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data['metadata']
    instructions = data['instructions']
    
    # Split templates into 8 parts (~237 strings each)
    templates = data['templates']
    template_chunk_size = math.ceil(len(templates) / 8)
    
    print(f"Total templates: {len(templates)}")
    print(f"Splitting into 8 parts of ~{template_chunk_size} strings each")
    
    # Create 8 template files
    for i in range(8):
        start_idx = i * template_chunk_size
        end_idx = min((i + 1) * template_chunk_size, len(templates))
        chunk = templates[start_idx:end_idx]
        
        file_data = {
            "metadata": {
                **metadata,
                "file_number": i + 1,
                "total_files": 10,
                "part_description": f"Templates Part {i + 1}/8"
            },
            "instructions": instructions,
            "templates": chunk,
            "flash_messages": [],
            "email_templates": []
        }
        
        filename = f"translate_part_{i + 1:02d}_templates.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Created {filename}: {len(chunk)} templates")
    
    # Create flash messages file (part 9)
    file_data = {
        "metadata": {
            **metadata,
            "file_number": 9,
            "total_files": 10,
            "part_description": "Flash Messages"
        },
        "instructions": instructions,
        "templates": [],
        "flash_messages": data['flash_messages'],
        "email_templates": []
    }
    
    filename = "translate_part_09_flash_messages.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(file_data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Created {filename}: {len(data['flash_messages'])} flash messages")
    
    # Create email templates file (part 10)
    file_data = {
        "metadata": {
            **metadata,
            "file_number": 10,
            "total_files": 10,
            "part_description": "Email Templates"
        },
        "instructions": instructions,
        "templates": [],
        "flash_messages": [],
        "email_templates": data['email_templates']
    }
    
    filename = "translate_part_10_email_templates.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(file_data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Created {filename}: {len(data['email_templates'])} email templates")
    
    print("\n" + "="*60)
    print("✓ Successfully split into 10 files!")
    print("="*60)
    print("\nFiles created:")
    for i in range(1, 9):
        print(f"  - translate_part_{i:02d}_templates.json")
    print(f"  - translate_part_09_flash_messages.json")
    print(f"  - translate_part_10_email_templates.json")
    
    print("\nNext step: Translate each file with ChatGPT")

if __name__ == "__main__":
    split_json()
