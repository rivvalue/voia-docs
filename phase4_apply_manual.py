#!/usr/bin/env python3
"""
Phase 4: Apply Manual Review Decisions
Wraps strings that were manually approved during YELLOW review
"""

import json
import re
from datetime import datetime
from pathlib import Path

def apply_manual_wraps():
    """Apply wraps from manual review decisions"""
    
    # Load decisions
    with open('manual_review_decisions.json', 'r') as f:
        decisions = json.load(f)
    
    # Filter approved wraps
    approved = {k: v for k, v in decisions.items() if v['action'] == 'wrap'}
    
    print(f"🎯 Phase 4: Applying {len(approved)} Manual Review Wraps")
    print("=" * 60)
    
    # Group by file
    from collections import defaultdict
    wraps_by_file = defaultdict(list)
    
    for key, data in approved.items():
        wraps_by_file[data['file']].append({
            'line': int(data['line']),
            'text': data['text'],
            'context': data['context'],
            'key': key
        })
    
    # Sort by line number (descending) to avoid offset issues
    for file in wraps_by_file:
        wraps_by_file[file].sort(key=lambda x: x['line'], reverse=True)
    
    stats = {
        'files_modified': 0,
        'wraps_applied': 0,
        'errors': []
    }
    
    log_entries = []
    
    # Process each file
    for filepath, wraps in wraps_by_file.items():
        print(f"\n📝 {filepath} ({len(wraps)} wraps)")
        
        try:
            # Read file
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modified_count = 0
            
            # Apply each wrap using context-based replacement
            for wrap in wraps:
                text = wrap['text']
                context = wrap['context']
                
                # Skip if already wrapped
                if f"{{{{ _('{text}'" in content or f'{{{{ _("{text}"' in content:
                    print(f"  ⏭️  Line {wrap['line']}: Already wrapped")
                    continue
                
                # Try to find and replace using context
                if context in content:
                    # Different wrapping strategies based on the context
                    
                    # Strategy 1: Text between tags (most common)
                    if f'>{text}<' in context:
                        old_pattern = f'>{text}<'
                        new_pattern = f">{{{{ _('{text}') }}}}<"
                        if old_pattern in content:
                            content = content.replace(old_pattern, new_pattern, 1)
                            modified_count += 1
                            stats['wraps_applied'] += 1
                            print(f"  ✅ Line {wrap['line']}: Wrapped between tags")
                            continue
                    
                    # Strategy 2: Text in quoted attribute
                    if f'"{text}"' in context and 'placeholder=' not in context and 'value=' not in context:
                        old_pattern = f'"{text}"'
                        new_pattern = '"{{ _(\'' + text + '\') }}"'
                        if old_pattern in content:
                            content = content.replace(old_pattern, new_pattern, 1)
                            modified_count += 1
                            stats['wraps_applied'] += 1
                            print(f"  ✅ Line {wrap['line']}: Wrapped in quotes")
                            continue
                    
                    # Strategy 3: Text with single quotes
                    if f"'{text}'" in context:
                        old_pattern = f"'{text}'"
                        new_pattern = f'{{{{ _("{text}") }}}}'
                        if old_pattern in content:
                            content = content.replace(old_pattern, new_pattern, 1)
                            modified_count += 1
                            stats['wraps_applied'] += 1
                            print(f"  ✅ Line {wrap['line']}: Wrapped single quotes")
                            continue
                    
                    print(f"  ⚠️  Line {wrap['line']}: Context found but no safe pattern matched")
                else:
                    print(f"  ⚠️  Line {wrap['line']}: Context not found in file")
            
            # Write file if modified
            if modified_count > 0:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                stats['files_modified'] += 1
                print(f"  💾 Saved {modified_count} changes")
        
        except Exception as e:
            error = f"Error processing {filepath}: {e}"
            stats['errors'].append(error)
            print(f"  ❌ {error}")
    
    # Save log
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'phase4_manual_log_{timestamp}.txt'
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Phase 4 Manual Wrap Application\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Files modified: {stats['files_modified']}\n")
        f.write(f"Wraps applied: {stats['wraps_applied']}\n")
        f.write(f"Errors: {len(stats['errors'])}\n")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 PHASE 4 SUMMARY")
    print("=" * 60)
    print(f"✅ Files modified:    {stats['files_modified']}")
    print(f"✅ Wraps applied:     {stats['wraps_applied']}")
    print(f"❌ Errors:            {len(stats['errors'])}")
    print(f"📄 Log file:          {log_file}")
    
    if stats['errors']:
        print("\n⚠️  ERRORS:")
        for error in stats['errors'][:10]:
            print(f"  - {error}")
    
    return stats

if __name__ == '__main__':
    stats = apply_manual_wraps()
    
    if stats['wraps_applied'] > 0:
        print("\n✅ Phase 4 complete! Manual review wraps applied.")
    else:
        print("\n⚠️  No wraps were applied. Check errors above.")
