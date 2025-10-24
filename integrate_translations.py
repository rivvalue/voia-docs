"""
VOÏA Translation Integration Script
Takes translated JSON from ChatGPT and integrates French text into codebase
"""

import json
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

def integrate_template_translations(translations_file):
    """Integrate translated strings back into HTML templates"""
    
    with open(translations_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Group translations by file
    by_file = {}
    for item in data['templates']:
        file_path = item['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(item)
    
    print(f"Processing {len(by_file)} template files...")
    
    # Process each file
    for file_path, strings in by_file.items():
        if not os.path.exists(file_path):
            print(f"  ⚠ File not found: {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace each string
            for item in strings:
                english_text = item['text']
                french_text = item.get('text', english_text)  # If translation failed, keep English
                
                # Simple text replacement (case-sensitive, whole word)
                if english_text in content:
                    content = content.replace(english_text, french_text)
            
            # Only write if content changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ Updated: {file_path}")
            else:
                print(f"  - No changes: {file_path}")
                
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}")

def integrate_flash_messages(translations_file):
    """Integrate translated flash messages into Python files"""
    
    with open(translations_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Group by file
    by_file = {}
    for item in data['flash_messages']:
        file_path = item['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(item)
    
    print(f"\nProcessing {len(by_file)} Python files for flash messages...")
    
    for file_path, messages in by_file.items():
        if not os.path.exists(file_path):
            print(f"  ⚠ File not found: {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace flash messages
            for item in messages:
                english_text = item['text']
                french_text = item.get('text', english_text)
                
                # Replace in flash() calls - handle both single and double quotes
                patterns = [
                    f"flash('{english_text}'",
                    f'flash("{english_text}"'
                ]
                replacements = [
                    f"flash('{french_text}'",
                    f'flash("{french_text}"'
                ]
                
                for pattern, replacement in zip(patterns, replacements):
                    if pattern in content:
                        content = content.replace(pattern, replacement)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ Updated: {file_path}")
            else:
                print(f"  - No changes: {file_path}")
                
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}")

def integrate_email_templates(translations_file):
    """Integrate translated email templates into email_service.py"""
    
    with open(translations_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\nProcessing email templates in email_service.py...")
    
    if not os.path.exists('email_service.py'):
        print("  ✗ email_service.py not found")
        return
    
    try:
        with open('email_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Create mapping of English to French for email templates
        email_translations = {}
        for item in data['email_templates']:
            english_text = item['text']
            french_text = item.get('text', english_text)
            email_translations[english_text] = french_text
        
        # Replace in defaults dictionary
        for english, french in email_translations.items():
            # Escape special regex characters but keep newlines
            english_escaped = english.replace('\\n', '\n')
            
            # Try to find and replace in the defaults dict
            if english_escaped in content:
                content = content.replace(english_escaped, french)
        
        if content != original_content:
            with open('email_service.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Updated email_service.py")
        else:
            print(f"  - No changes in email_service.py")
            
    except Exception as e:
        print(f"  ✗ Error processing email_service.py: {e}")

def main():
    """Main integration process"""
    
    translations_file = "voila_strings_translated.json"
    
    if not os.path.exists(translations_file):
        print(f"❌ Error: {translations_file} not found!")
        print(f"\nPlease ensure you have:")
        print(f"1. Translated the JSON file using ChatGPT")
        print(f"2. Saved the result as '{translations_file}'")
        print(f"3. Placed it in the same directory as this script")
        return
    
    print("="*60)
    print("VOÏA Translation Integration")
    print("="*60)
    
    # Integrate translations
    integrate_template_translations(translations_file)
    integrate_flash_messages(translations_file)
    integrate_email_templates(translations_file)
    
    print("\n" + "="*60)
    print("✓ Integration complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Test the application to ensure translations display correctly")
    print("2. Check for any broken layouts or formatting issues")
    print("3. Review translations in context")
    print("4. Make any necessary adjustments")

if __name__ == "__main__":
    main()
