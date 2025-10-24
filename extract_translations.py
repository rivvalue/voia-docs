"""
VOÏA String Extraction Script for French Translation
Extracts all translatable strings from templates, Python files, and emails
Outputs structured JSON for ChatGPT translation
"""

import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup, Comment

# Configuration
TEMPLATES_DIR = "templates"
PYTHON_FILES = [
    "routes.py",
    "campaign_routes.py",
    "participant_routes.py",
    "business_auth_routes.py",
    "email_service.py"
]

def extract_text_from_html(html_content, filename):
    """Extract translatable text from HTML templates"""
    soup = BeautifulSoup(html_content, 'html.parser')
    strings = []
    string_id = 1
    
    # Remove script and style tags
    for tag in soup(['script', 'style', 'code']):
        tag.decompose()
    
    # Extract from common text elements
    text_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'button', 'label', 'th', 'td', 'span', 'div', 'li', 'option']
    
    for tag in soup.find_all(text_tags):
        # Get direct text only (not nested)
        text = tag.find(text=True, recursive=False)
        if text and isinstance(text, str):
            text = text.strip()
            # Skip if empty, just whitespace, or Jinja2 template code
            if text and not re.match(r'^\{[{%].*[}%]\}$', text) and len(text) > 1:
                # Skip if it's just a variable
                if not text.startswith('{{') and not text.startswith('{%'):
                    strings.append({
                        "id": f"{Path(filename).stem}_{string_id}",
                        "file": filename,
                        "element": tag.name,
                        "text": text
                    })
                    string_id += 1
    
    # Extract placeholder text
    for tag in soup.find_all(['input', 'textarea']):
        placeholder = tag.get('placeholder')
        if placeholder and not placeholder.startswith('{{'):
            strings.append({
                "id": f"{Path(filename).stem}_placeholder_{string_id}",
                "file": filename,
                "element": f"{tag.name}[placeholder]",
                "text": placeholder
            })
            string_id += 1
    
    # Extract title attributes
    for tag in soup.find_all(title=True):
        title = tag.get('title')
        if title and not title.startswith('{{') and len(title.strip()) > 1:
            strings.append({
                "id": f"{Path(filename).stem}_title_{string_id}",
                "file": filename,
                "element": f"{tag.name}[title]",
                "text": title.strip()
            })
            string_id += 1
    
    # Extract aria-label attributes
    for tag in soup.find_all(attrs={'aria-label': True}):
        aria_label = tag.get('aria-label')
        if aria_label and not aria_label.startswith('{{') and len(aria_label.strip()) > 1:
            strings.append({
                "id": f"{Path(filename).stem}_aria_{string_id}",
                "file": filename,
                "element": f"{tag.name}[aria-label]",
                "text": aria_label.strip()
            })
            string_id += 1
    
    return strings

def extract_flash_messages(file_path):
    """Extract flash messages from Python files"""
    messages = []
    message_id = 1
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern: flash('message', 'category')
    pattern = r"flash\(['\"](.+?)['\"](?:,\s*['\"][^'\"]+['\"])?\)"
    matches = re.findall(pattern, content)
    
    for match in matches:
        # Skip if it contains Jinja2 or f-string formatting
        if not '{' in match or match.count('{') <= 2:  # Allow simple {variable}
            messages.append({
                "id": f"{Path(file_path).stem}_flash_{message_id}",
                "file": file_path,
                "type": "flash_message",
                "text": match
            })
            message_id += 1
    
    return messages

def extract_email_templates():
    """Extract hardcoded email template strings from email_service.py"""
    emails = [
        {
            "id": "email_subject",
            "file": "email_service.py",
            "type": "email_template",
            "context": "Email subject line for survey invitations",
            "text": "Your feedback is requested: {campaign_name}",
            "note": "Keep {campaign_name} variable unchanged"
        },
        {
            "id": "email_intro",
            "file": "email_service.py",
            "type": "email_template",
            "context": "Email introduction paragraph",
            "text": "{business_account_name} is requesting your valuable feedback through our Voice of Client system.",
            "note": "Keep {business_account_name} variable unchanged"
        },
        {
            "id": "email_cta_text",
            "file": "email_service.py",
            "type": "email_template",
            "context": "Call-to-action button text",
            "text": "Complete Your Survey"
        },
        {
            "id": "email_closing",
            "file": "email_service.py",
            "type": "email_template",
            "context": "Email closing message (before footer)",
            "text": "Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.\n\nThank you for your time and valuable insights!"
        },
        {
            "id": "email_footer",
            "file": "email_service.py",
            "type": "email_template",
            "context": "Email footer disclaimer",
            "text": "This is an automated message. If you have any questions, please contact the organization that sent this survey."
        },
        {
            "id": "email_reminder_subject",
            "file": "email_service.py",
            "type": "email_template",
            "context": "Subject line for reminder emails",
            "text": "Reminder: Your feedback is still needed - {campaign_name}",
            "note": "Keep {campaign_name} variable unchanged"
        },
        {
            "id": "email_reminder_intro",
            "file": "email_service.py",
            "type": "email_template",
            "context": "Reminder email introduction",
            "text": "This is a friendly reminder that {business_account_name} is still looking forward to your feedback.",
            "note": "Keep {business_account_name} variable unchanged"
        }
    ]
    
    return emails

def main():
    """Main extraction process"""
    all_strings = {
        "metadata": {
            "project": "VOÏA - Voice Of Client",
            "source_language": "English",
            "target_language": "French",
            "extraction_date": "2025-10-24",
            "total_files": 0,
            "total_strings": 0
        },
        "instructions": {
            "overview": "Translate all 'text' field values from English to French (France market, professional SaaS tone)",
            "rules": [
                "Translate ONLY the 'text' field values",
                "Keep all other fields (id, file, type, element, etc.) UNCHANGED",
                "Preserve {variables}, {{variables}}, and {%...%} syntax exactly as-is",
                "Use professional business French suitable for SaaS platform",
                "Maintain consistent terminology throughout",
                "Keep technical terms like 'NPS', 'API', 'VOÏA' unchanged unless noted"
            ]
        },
        "templates": [],
        "flash_messages": [],
        "email_templates": [],
        "navigation": [],
        "buttons": [],
        "forms": [],
        "errors": []
    }
    
    # Extract from all HTML templates
    print("Extracting from templates...")
    template_count = 0
    for root, dirs, files in os.walk(TEMPLATES_DIR):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    strings = extract_text_from_html(html_content, file_path)
                    if strings:
                        all_strings["templates"].extend(strings)
                        template_count += 1
                        print(f"  ✓ {file_path}: {len(strings)} strings")
                except Exception as e:
                    print(f"  ✗ Error processing {file_path}: {e}")
    
    # Extract flash messages
    print("\nExtracting flash messages...")
    for py_file in PYTHON_FILES:
        if os.path.exists(py_file):
            try:
                messages = extract_flash_messages(py_file)
                if messages:
                    all_strings["flash_messages"].extend(messages)
                    print(f"  ✓ {py_file}: {len(messages)} messages")
            except Exception as e:
                print(f"  ✗ Error processing {py_file}: {e}")
    
    # Extract email templates
    print("\nExtracting email templates...")
    email_strings = extract_email_templates()
    all_strings["email_templates"].extend(email_strings)
    print(f"  ✓ email_service.py: {len(email_strings)} templates")
    
    # Update metadata
    all_strings["metadata"]["total_files"] = template_count + len(PYTHON_FILES) + 1
    all_strings["metadata"]["total_strings"] = (
        len(all_strings["templates"]) +
        len(all_strings["flash_messages"]) +
        len(all_strings["email_templates"])
    )
    
    # Write to JSON file
    output_file = "voila_strings_to_translate.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_strings, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✓ Extraction complete!")
    print(f"{'='*60}")
    print(f"Total files processed: {all_strings['metadata']['total_files']}")
    print(f"Total strings extracted: {all_strings['metadata']['total_strings']}")
    print(f"  - Templates: {len(all_strings['templates'])}")
    print(f"  - Flash messages: {len(all_strings['flash_messages'])}")
    print(f"  - Email templates: {len(all_strings['email_templates'])}")
    print(f"\nOutput file: {output_file}")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"1. Review {output_file}")
    print(f"2. Send to ChatGPT for translation")
    print(f"3. Return translated JSON for integration")

if __name__ == "__main__":
    main()
