#!/usr/bin/env python3
"""
Smart Auto-Decision Tool for YELLOW Items
Uses conservative logic to automatically classify most YELLOW items
User only needs to review edge cases flagged for manual attention
"""

import json
import re
from collections import defaultdict


class SmartDecider:
    def __init__(self, yellow_file='yellow_review_queue.json'):
        self.yellow_file = yellow_file
        self.items = []
        self.auto_decisions = {}
        self.needs_review = {}
        self.stats = {
            'auto_wrap': 0,
            'auto_skip': 0,
            'needs_manual': 0,
            'total': 0
        }
    
    def load_items(self):
        """Load YELLOW items"""
        print(f"📖 Loading YELLOW items from: {self.yellow_file}\n")
        with open(self.yellow_file, 'r', encoding='utf-8') as f:
            self.items = json.load(f)
        print(f"✅ Loaded {len(self.items)} items for smart analysis\n")
    
    def analyze_item(self, item):
        """Analyze a YELLOW item and make smart decision"""
        pattern = item['pattern']
        text = item['text'].strip()
        context = item['context']
        file_path = item['file']
        
        # ARIA labels - generally safe to wrap (accessibility)
        if 'ARIA' in pattern:
            return self._decide_aria(text, context)
        
        # Value attributes - most complex
        if 'Value attributes' in pattern:
            return self._decide_value_attr(text, context, file_path)
        
        # Spans - check for JS dependencies
        if 'Spans' in pattern:
            return self._decide_span(text, context, file_path)
        
        # Divs with text - check for dynamic use
        if 'Divs with text' in pattern:
            return self._decide_div(text, context, file_path)
        
        # Links - check if email/URL
        if 'Links' in pattern:
            return self._decide_link(text, context)
        
        # Alt attributes - generally safe
        if 'Alt' in pattern:
            return self._decide_alt(text, context)
        
        # Default: needs manual review
        return 'manual', 'Unknown pattern type - requires review'
    
    def _decide_aria(self, text, context):
        """Decide on ARIA labels"""
        # ARIA labels should always be translated for screen readers
        # Exception: If it contains technical/programmatic values
        
        technical_keywords = ['id', 'class', 'data-', 'href', 'src']
        if any(kw in text.lower() for kw in technical_keywords):
            return 'manual', 'ARIA label contains technical keywords'
        
        # Very short ARIA labels might be technical
        if len(text) <= 3:
            return 'manual', 'Very short ARIA label - verify not technical'
        
        # Safe to wrap for accessibility
        return 'wrap', 'ARIA label - safe for translation (accessibility)'
    
    def _decide_value_attr(self, text, context, file_path):
        """Decide on form value attributes"""
        text_lower = text.lower()
        
        # Known backend dependencies - DO NOT WRAP
        backend_values = [
            'conversational', 'traditional',  # Survey types
            'trial', 'core', 'plus', 'enterprise',  # License types
            'active', 'inactive', 'pending', 'scheduled', 'completed',  # Status
            'smtp', 'ses', 'aws', 'aws_ses',  # Provider types
            'true', 'false', 'yes', 'no',  # Boolean
            'asc', 'desc',  # Sort order
            'and', 'or', 'not',  # Logic operators
        ]
        
        if text_lower in backend_values:
            return 'skip', f'Known backend value: "{text}" - must not be translated'
        
        # AWS region codes (us-east-1, eu-west-2, etc.)
        if re.match(r'^[a-z]{2}-[a-z]+-\d+$', text_lower):
            return 'skip', 'AWS region code - technical value'
        
        # Port numbers
        if text.isdigit() and int(text) in [25, 465, 587, 2525, 443, 80, 8080]:
            return 'skip', 'Port number - technical value'
        
        # Technical patterns (snake_case, kebab-case with underscores/hyphens)
        if '_' in text or (len(text) > 1 and '-' in text and not ' ' in text):
            return 'skip', f'Technical identifier pattern: {text}'
        
        # Check if in form submission context
        if 'name=' in context and '<input' in context or '<select' in context:
            # If it's a radio/checkbox value, likely backend dependency
            if 'type="radio"' in context or 'type="checkbox"' in context:
                return 'manual', 'Radio/checkbox value - verify backend dependency'
            
            # If it's a button/submit, might be display text
            if 'type="submit"' in context or 'type="button"' in context:
                return 'wrap', 'Button value - display text safe to wrap'
        
        # Option values in selects - check if technical
        if '<option' in context:
            # If value looks like an ID/code (numbers, underscores)
            if re.match(r'^[\d_\-]+$', text):
                return 'skip', 'Option value looks like ID/code'
            
            # If value is short and lowercase (likely backend key)
            if len(text) <= 10 and text.islower():
                return 'manual', 'Short lowercase option value - verify backend use'
            
            # Otherwise, display text
            return 'wrap', 'Option display text - safe to wrap'
        
        # Default for value attributes: manual review
        return 'manual', 'Value attribute - verify backend dependency'
    
    def _decide_span(self, text, context, file_path):
        """Decide on span elements"""
        # Check for badge/status indicators
        if any(cls in context for cls in ['badge', 'status', 'tag', 'label']):
            # Status badges might be read by JS
            status_words = ['active', 'inactive', 'pending', 'completed', 'failed', 'success']
            if text.lower() in status_words:
                return 'manual', 'Status badge - verify JS dependencies'
            
            # Display badges are safe
            return 'wrap', 'Display badge - safe to wrap'
        
        # Check for data attributes (JS dependencies)
        if 'data-' in context:
            return 'manual', 'Span with data attributes - verify JS use'
        
        # Check for count/number displays
        if any(word in text.lower() for word in ['remaining', 'total', 'count', 'days']):
            return 'wrap', 'Count/metric display - safe to wrap'
        
        # Statistical/display text
        if any(word in text.lower() for word in ['expiration', 'no ', 'not ', 'n/a', 'none']):
            return 'wrap', 'Display text - safe to wrap'
        
        # Default: needs review
        return 'manual', 'Span element - verify not used by JavaScript'
    
    def _decide_div(self, text, context, file_path):
        """Decide on div text content"""
        # Very long text is likely static content
        if len(text) > 50:
            return 'wrap', 'Long text content - safe display text'
        
        # Check for label/description classes
        label_classes = ['label', 'title', 'description', 'help-text', 'subtitle']
        if any(cls in context.lower() for cls in label_classes):
            return 'wrap', 'Label/description div - safe to wrap'
        
        # Check if it's in a card/container
        if any(cls in context.lower() for cls in ['card', 'container', 'panel']):
            return 'wrap', 'Card/panel content - safe to wrap'
        
        # Very short might be dynamic
        if len(text) <= 10:
            return 'manual', 'Short div content - verify not dynamic'
        
        # Default: wrap if it looks like prose
        if ' ' in text and len(text) > 15:
            return 'wrap', 'Prose content - safe to wrap'
        
        return 'manual', 'Div content - verify usage'
    
    def _decide_link(self, text, context):
        """Decide on link text"""
        # Email addresses - don't wrap
        if '@' in text or 'mailto:' in context:
            return 'skip', 'Email address - technical value'
        
        # URLs - don't wrap
        if text.startswith('http') or text.startswith('www.'):
            return 'skip', 'URL - technical value'
        
        # Display text in links - wrap
        return 'wrap', 'Link display text - safe to wrap'
    
    def _decide_alt(self, text, context):
        """Decide on alt attributes"""
        # Alt text should be translated for accessibility
        # Unless it's empty or contains Jinja (already filtered in RED)
        return 'wrap', 'Alt text - safe for translation (accessibility)'
    
    def process_all(self):
        """Process all YELLOW items"""
        print("🧠 SMART AUTO-DECISION ANALYSIS")
        print("="*80 + "\n")
        
        for item in self.items:
            decision, reason = self.analyze_item(item)
            item_id = f"{item['file']}:{item['line']}"
            
            if decision == 'manual':
                self.needs_review[item_id] = {
                    'action': None,
                    'suggested_action': 'skip',  # Conservative default
                    'reason': reason,
                    'file': item['file'],
                    'line': item['line'],
                    'pattern': item['pattern'],
                    'text': item['text'],
                    'context': item['context']
                }
                self.stats['needs_manual'] += 1
            else:
                self.auto_decisions[item_id] = {
                    'action': decision,
                    'reason': reason,
                    'file': item['file'],
                    'line': item['line'],
                    'pattern': item['pattern'],
                    'text': item['text'],
                    'context': item['context']
                }
                
                if decision == 'wrap':
                    self.stats['auto_wrap'] += 1
                elif decision == 'skip':
                    self.stats['auto_skip'] += 1
            
            self.stats['total'] += 1
        
        print(f"✅ Analysis complete!\n")
    
    def generate_report(self):
        """Generate analysis report"""
        print("="*80)
        print("📊 SMART AUTO-DECISION REPORT")
        print("="*80)
        
        total = self.stats['total']
        auto_wrap = self.stats['auto_wrap']
        auto_skip = self.stats['auto_skip']
        manual = self.stats['needs_manual']
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Total YELLOW items: {total}")
        print(f"\n   ✅ Auto-wrap (safe): {auto_wrap} ({auto_wrap/total*100:.1f}%)")
        print(f"   ⏭️  Auto-skip (technical): {auto_skip} ({auto_skip/total*100:.1f}%)")
        print(f"   ⚠️  Needs manual review: {manual} ({manual/total*100:.1f}%)")
        
        # Breakdown by pattern
        print(f"\n📋 BY PATTERN TYPE:")
        pattern_stats = defaultdict(lambda: {'wrap': 0, 'skip': 0, 'manual': 0})
        
        for item in self.auto_decisions.values():
            pattern_stats[item['pattern']][item['action']] += 1
        
        for item in self.needs_review.values():
            pattern_stats[item['pattern']]['manual'] += 1
        
        for pattern in sorted(pattern_stats.keys()):
            stats = pattern_stats[pattern]
            print(f"\n   {pattern}:")
            print(f"      ✅ Wrap: {stats['wrap']}  ⏭️ Skip: {stats['skip']}  ⚠️ Manual: {stats['manual']}")
        
        # Show manual review examples
        if manual > 0:
            print(f"\n⚠️  ITEMS REQUIRING MANUAL REVIEW:")
            print(f"   (Showing first 10 examples)\n")
            
            for i, (item_id, item) in enumerate(list(self.needs_review.items())[:10]):
                file_short = item['file'].replace('templates/', '').replace('"', '')
                print(f"   {i+1}. {file_short}:{item['line']}")
                print(f"      Text: \"{item['text'][:60]}\"")
                print(f"      Reason: {item['reason']}\n")
            
            if manual > 10:
                print(f"   ... and {manual - 10} more items\n")
        
        print("\n" + "="*80)
        print(f"\n💡 NEXT STEPS:")
        print(f"   1. Review {manual} flagged items in review tool (if needed)")
        print(f"   2. Auto-decisions saved to: auto_yellow_decisions.json")
        print(f"   3. Manual review items saved to: manual_review_needed.json")
        print(f"   4. Merge both and proceed to Phase 4")
        print("="*80 + "\n")
    
    def export_decisions(self):
        """Export auto-decisions and manual review items"""
        # Export auto-decisions
        with open('auto_yellow_decisions.json', 'w', encoding='utf-8') as f:
            json.dump(self.auto_decisions, f, indent=2)
        
        print(f"✅ Exported {len(self.auto_decisions)} auto-decisions to: auto_yellow_decisions.json")
        
        # Export manual review needed
        if self.needs_review:
            with open('manual_review_needed.json', 'w', encoding='utf-8') as f:
                json.dump(self.needs_review, f, indent=2)
            
            print(f"⚠️  Exported {len(self.needs_review)} items needing review to: manual_review_needed.json")
        
        # Create combined decisions file (conservative: skip all manual items for now)
        combined = {}
        combined.update(self.auto_decisions)
        
        # Add manual items with conservative 'skip' decision
        for item_id, item in self.needs_review.items():
            combined[item_id] = {
                'action': 'skip',
                'reason': f"Manual review needed: {item['reason']} (conservatively skipped)",
                'file': item['file'],
                'line': item['line'],
                'pattern': item['pattern'],
                'text': item['text'],
                'context': item['context'],
                'needs_review': True
            }
        
        with open('yellow_decisions_combined.json', 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=2)
        
        print(f"📦 Exported combined decisions to: yellow_decisions_combined.json")
        print(f"   (Manual review items conservatively set to 'skip')\n")


def main():
    """Main execution"""
    decider = SmartDecider()
    
    # Load items
    decider.load_items()
    
    # Process all
    decider.process_all()
    
    # Generate report
    decider.generate_report()
    
    # Export files
    decider.export_decisions()
    
    print("✅ Smart auto-decision complete!\n")


if __name__ == '__main__':
    main()
