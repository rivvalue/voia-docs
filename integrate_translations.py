"""
VOÏA Translation Integration Script
Takes 10 translated JSON files from ChatGPT and integrates French text into codebase
"""

import json
import os
import re
from pathlib import Path

def load_all_translations():
    """Load and merge all translated JSON files"""
    
    all_data = {
        'templates': [],
        'flash_messages': [],
        'email_templates': []
    }
    
    # Load parts 1-7
    for i in range(1, 8):
        filename = f"translated_part_{i:02d}.json"
        
        if not os.path.exists(filename):
            print(f"  ⚠ Warning: {filename} not found - skipping")
            continue
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Merge data
            all_data['templates'].extend(data.get('templates', []))
            all_data['flash_messages'].extend(data.get('flash_messages', []))
            all_data['email_templates'].extend(data.get('email_templates', []))
            
            print(f"  ✓ Loaded {filename}")
            
        except Exception as e:
            print(f"  ✗ Error loading {filename}: {e}")
    
    # Load part 8a, 8b1, 8b2 (split files)
    for part in ['08a', '08b1', '08b2']:
        filename = f"translated_part_{part}.json"
        
        if not os.path.exists(filename):
            print(f"  ⚠ Warning: {filename} not found - skipping")
            continue
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Merge data
            all_data['templates'].extend(data.get('templates', []))
            all_data['flash_messages'].extend(data.get('flash_messages', []))
            all_data['email_templates'].extend(data.get('email_templates', []))
            
            print(f"  ✓ Loaded {filename}")
            
        except Exception as e:
            print(f"  ✗ Error loading {filename}: {e}")
    
    # Load parts 9-10
    for i in range(9, 11):
        filename = f"translated_part_{i:02d}.json"
        
        if not os.path.exists(filename):
            print(f"  ⚠ Warning: {filename} not found - skipping")
            continue
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Merge data
            all_data['templates'].extend(data.get('templates', []))
            all_data['flash_messages'].extend(data.get('flash_messages', []))
            all_data['email_templates'].extend(data.get('email_templates', []))
            
            print(f"  ✓ Loaded {filename}")
            
        except Exception as e:
            print(f"  ✗ Error loading {filename}: {e}")
    
    print(f"\nTotal loaded:")
    print(f"  - Templates: {len(all_data['templates'])}")
    print(f"  - Flash messages: {len(all_data['flash_messages'])}")
    print(f"  - Email templates: {len(all_data['email_templates'])}")
    
    return all_data

def integrate_template_translations(data):
    """Integrate translated strings back into HTML templates"""
    
    # Group translations by file
    by_file = {}
    for item in data['templates']:
        file_path = item['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(item)
    
    print(f"\nProcessing {len(by_file)} template files...")
    
    updated_count = 0
    
    # Process each file
    for file_path, strings in by_file.items():
        if not os.path.exists(file_path):
            print(f"  ⚠ File not found: {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            replacements = 0
            
            # Replace each string
            for item in strings:
                english_text = item.get('original_text', item.get('text', ''))
                french_text = item.get('text', english_text)
                
                # Skip if translation is the same as original
                if french_text == english_text:
                    continue
                
                # Simple text replacement (case-sensitive)
                if english_text in content:
                    content = content.replace(english_text, french_text)
                    replacements += 1
            
            # Only write if content changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ Updated: {file_path} ({replacements} replacements)")
                updated_count += 1
            else:
                print(f"  - No changes: {file_path}")
                
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}")
    
    return updated_count

def integrate_flash_messages(data):
    """Integrate translated flash messages into Python files"""
    
    # Group by file
    by_file = {}
    for item in data['flash_messages']:
        file_path = item['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(item)
    
    print(f"\nProcessing {len(by_file)} Python files for flash messages...")
    
    updated_count = 0
    
    for file_path, messages in by_file.items():
        if not os.path.exists(file_path):
            print(f"  ⚠ File not found: {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            replacements = 0
            
            # Replace flash messages
            for item in messages:
                english_text = item.get('original_text', item.get('text', ''))
                french_text = item.get('text', english_text)
                
                # Skip if same
                if french_text == english_text:
                    continue
                
                # Replace in flash() calls - handle both single and double quotes
                # Be careful with escaping
                english_escaped = english_text.replace("'", "\\'")
                french_escaped = french_text.replace("'", "\\'")
                
                patterns = [
                    f"flash('{english_text}'",
                    f'flash("{english_text}"',
                    f"flash(f'{english_text}'",
                    f'flash(f"{english_text}"'
                ]
                replacements_patterns = [
                    f"flash('{french_text}'",
                    f'flash("{french_text}"',
                    f"flash(f'{french_text}'",
                    f'flash(f"{french_text}"'
                ]
                
                for pattern, replacement in zip(patterns, replacements_patterns):
                    if pattern in content:
                        content = content.replace(pattern, replacement)
                        replacements += 1
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ Updated: {file_path} ({replacements} replacements)")
                updated_count += 1
            else:
                print(f"  - No changes: {file_path}")
                
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}")
    
    return updated_count

def integrate_email_templates(data):
    """Integrate translated email templates into email_service.py"""
    
    print(f"\nProcessing email templates in email_service.py...")
    
    if not os.path.exists('email_service.py'):
        print("  ✗ email_service.py not found")
        return 0
    
    try:
        with open('email_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replacements = 0
        
        # Create mapping of English to French for email templates
        for item in data['email_templates']:
            english_text = item.get('original_text', item.get('text', ''))
            french_text = item.get('text', english_text)
            
            # Skip if same
            if french_text == english_text:
                continue
            
            # Replace in the defaults dict
            if english_text in content:
                content = content.replace(english_text, french_text)
                replacements += 1
        
        if content != original_content:
            with open('email_service.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Updated email_service.py ({replacements} replacements)")
            return 1
        else:
            print(f"  - No changes in email_service.py")
            return 0
            
    except Exception as e:
        print(f"  ✗ Error processing email_service.py: {e}")
        return 0

def main():
    """Main integration process"""
    
    print("="*60)
    print("VOÏA Translation Integration (10 Files)")
    print("="*60)
    
    # Check if translated files exist
    found_files = 0
    for i in range(1, 11):
        if os.path.exists(f"translated_part_{i:02d}.json"):
            found_files += 1
    
    if found_files == 0:
        print(f"\n❌ Error: No translated files found!")
        print(f"\nPlease ensure you have translated all 10 files and saved them as:")
        for i in range(1, 11):
            print(f"  - translated_part_{i:02d}.json")
        print(f"\nSee FRENCH_TRANSLATION_GUIDE.md for instructions")
        return
    
    if found_files < 10:
        print(f"\n⚠ Warning: Only found {found_files}/10 translated files")
        print(f"Will integrate what's available...\n")
    
    # Load all translations
    data = load_all_translations()
    
    # Integrate translations
    templates_updated = integrate_template_translations(data)
    flash_updated = integrate_flash_messages(data)
    email_updated = integrate_email_templates(data)
    
    total_updated = templates_updated + flash_updated + email_updated
    
    print("\n" + "="*60)
    print("✓ Integration complete!")
    print("="*60)
    print(f"\nFiles updated: {total_updated}")
    print(f"  - Template files: {templates_updated}")
    print(f"  - Python files: {flash_updated}")
    print(f"  - Email service: {email_updated}")
    
    print("\nNext steps:")
    print("1. Test the application to ensure translations display correctly")
    print("2. Check for any broken layouts or formatting issues")
    print("3. Review translations in context")
    print("4. Make any necessary adjustments")

if __name__ == "__main__":
    main()
