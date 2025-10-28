#!/usr/bin/env python3
"""
Revert Phase 4 Changes
Undoes the 115 YELLOW string wraps while keeping Phase 2 (170 GREEN wraps)
"""

import re
from pathlib import Path


def parse_log_file(log_path):
    """Parse the modification log to extract reversions"""
    print(f"📖 Reading log file: {log_path}\n")
    
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    reversions = []
    current_file = None
    
    # Split by file sections
    file_sections = re.split(r'─{80}\nFILE: (.+?)\n─{80}', content)
    
    for i in range(1, len(file_sections), 2):
        file_path = file_sections[i]
        modifications = file_sections[i + 1]
        
        # Extract each modification
        mod_pattern = r'Line (\d+) \[.+?\]:\n  Text: "(.+?)"\n  BEFORE: (.+?)\n  AFTER:  (.+?)\n'
        
        for match in re.finditer(mod_pattern, modifications, re.DOTALL):
            line_num = int(match.group(1))
            text = match.group(2)
            before = match.group(3)
            after = match.group(4)
            
            reversions.append({
                'file': file_path,
                'line': line_num,
                'text': text,
                'before': before.strip(),
                'after': after.strip()
            })
    
    print(f"✅ Found {len(reversions)} modifications to revert\n")
    return reversions


def revert_modifications(reversions):
    """Revert all modifications"""
    files_by_path = {}
    
    # Group by file
    for rev in reversions:
        file_path = rev['file']
        if file_path not in files_by_path:
            files_by_path[file_path] = []
        files_by_path[file_path].append(rev)
    
    # Sort by line number descending (to avoid line shifts)
    for file_path in files_by_path:
        files_by_path[file_path].sort(key=lambda x: x['line'], reverse=True)
    
    total_reverted = 0
    
    # Process each file
    for file_path in sorted(files_by_path.keys()):
        print(f"📝 Reverting: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"   ❌ Error reading: {e}")
            continue
        
        reverted_count = 0
        
        for rev in files_by_path[file_path]:
            line_num = rev['line'] - 1  # Convert to 0-indexed
            
            if line_num >= len(lines):
                print(f"   ⚠️  Line {rev['line']} out of range")
                continue
            
            current_line = lines[line_num].strip()
            expected_after = rev['after']
            
            # Verify this line matches what we expect
            if current_line == expected_after:
                # Restore original
                original_indent = lines[line_num][:len(lines[line_num]) - len(lines[line_num].lstrip())]
                lines[line_num] = original_indent + rev['before'] + '\n'
                reverted_count += 1
            else:
                print(f"   ⚠️  Line {rev['line']} doesn't match expected state (skipping)")
        
        # Write file back
        if reverted_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"   ✅ Reverted {reverted_count} changes")
            total_reverted += reverted_count
        else:
            print(f"   ⏭️  No changes reverted")
    
    return total_reverted


def main():
    log_file = 'yellow_wrap_log_20251028_163146.txt'
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    print("="*80)
    print("🔄 REVERTING PHASE 4 CHANGES")
    print("="*80 + "\n")
    
    # Parse log
    reversions = parse_log_file(log_file)
    
    # Revert
    total = revert_modifications(reversions)
    
    print("\n" + "="*80)
    print("📊 REVERSION COMPLETE")
    print("="*80)
    print(f"\n✅ Reverted {total} modifications")
    print(f"\n💡 Phase 2 changes (170 GREEN strings) remain intact")
    print(f"   Phase 4 changes (115 YELLOW strings) have been undone")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()
