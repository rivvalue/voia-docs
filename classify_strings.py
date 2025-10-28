#!/usr/bin/env python3
"""
Risk Classification System for Translation String Wrapping
Categorizes 660 unwrapped strings into GREEN/YELLOW/RED risk levels
"""

import csv
import re
import json
from collections import defaultdict


class StringClassifier:
    def __init__(self, input_csv='unwrapped_strings.csv'):
        self.input_csv = input_csv
        self.findings = []
        self.stats = {
            'green': 0,
            'yellow': 0,
            'red': 0,
            'total': 0
        }
        
    def classify_risk(self, row):
        """Classify a string finding into risk level"""
        file_path = row['File']
        line = row['Line']
        pattern = row['Pattern Type']
        text = row['Unwrapped Text']
        context = row['Context']
        
        # RED: Critical - Manual only
        if self._is_critical_red(text, context, pattern):
            return 'red', self._get_red_reason(text, context, pattern)
        
        # YELLOW: Review required
        if self._needs_review_yellow(pattern, text, context):
            return 'yellow', self._get_yellow_reason(pattern, text, context)
        
        # GREEN: Auto-fixable
        return 'green', 'Safe display text - auto-wrappable'
    
    def _is_critical_red(self, text, context, pattern):
        """Check if item is critical RED zone"""
        
        # Jinja variables (false positives from scanner)
        if '{{' in text or '{%' in text:
            return True
        
        # Jinja logic keywords
        jinja_keywords = ['endif', 'else', 'elif', 'endfor', 'endblock']
        if any(keyword in text.lower() for keyword in jinja_keywords):
            return True
        
        # CSRF tokens
        if 'csrf_token' in text.lower():
            return True
        
        # Technical values that backend depends on
        technical_values = [
            'true', 'false', 'null', 'none',
            'get', 'post', 'put', 'delete', 'patch',
            'conversational', 'traditional',  # Survey types
            'trial', 'core', 'plus', 'enterprise',  # License types
            'active', 'inactive', 'pending',  # Status values
            'smtp', 'ses',  # Email provider types
        ]
        if text.lower().strip() in technical_values:
            return True
        
        # Numeric-only or single char
        if re.match(r'^[\d\s\.\,\-\+]+$', text.strip()):
            return True
        
        # Too short (likely technical)
        if len(text.strip()) <= 2:
            return True
        
        # Contains only special chars
        if not re.search(r'[A-Za-z]', text):
            return True
        
        return False
    
    def _get_red_reason(self, text, context, pattern):
        """Get specific reason for RED classification"""
        if '{{' in text or '{%' in text:
            return 'Contains Jinja syntax - false positive from scanner'
        if 'csrf_token' in text.lower():
            return 'CSRF token - must not be wrapped'
        if re.match(r'^[\d\s\.\,\-\+]+$', text.strip()):
            return 'Numeric value - likely technical'
        if len(text.strip()) <= 2:
            return 'Too short - likely technical identifier'
        if not re.search(r'[A-Za-z]', text):
            return 'No alphabetic characters - technical value'
        
        # Check for known technical values
        text_lower = text.lower().strip()
        if text_lower in ['conversational', 'traditional']:
            return 'Survey type value - backend dependency'
        if text_lower in ['trial', 'core', 'plus', 'enterprise']:
            return 'License type value - backend dependency'
        if text_lower in ['active', 'inactive', 'pending']:
            return 'Status value - backend dependency'
        if text_lower in ['smtp', 'ses']:
            return 'Email provider value - backend dependency'
        
        return 'Requires manual review - potential backend dependency'
    
    def _needs_review_yellow(self, pattern, text, context):
        """Check if item needs manual review"""
        
        # Value attributes always need review
        if 'Value attributes' in pattern:
            return True
        
        # ARIA labels need accessibility validation
        if 'ARIA' in pattern:
            return True
        
        # Spans might be read by JavaScript
        if 'Spans' in pattern:
            return True
        
        # Divs with text - could be dynamic
        if 'Divs with text' in pattern:
            return True
        
        # Links - could be email/URL
        if 'Links' in pattern:
            return True
        
        # Alt attributes with Jinja
        if 'Alt' in pattern and '{{' in context:
            return True
        
        return False
    
    def _get_yellow_reason(self, pattern, text, context):
        """Get specific reason for YELLOW classification"""
        if 'Value attributes' in pattern:
            return 'Form value - verify not used by backend logic'
        if 'ARIA' in pattern:
            return 'Accessibility label - needs screen reader testing'
        if 'Spans' in pattern:
            return 'Span element - check for JavaScript dependencies'
        if 'Divs with text' in pattern:
            return 'Div content - verify not used dynamically'
        if 'Links' in pattern:
            return 'Link text - verify not email/URL'
        if 'Alt' in pattern:
            return 'Alt text with variables - verify safe to wrap'
        return 'Needs manual review'
    
    def process_csv(self):
        """Process input CSV and classify all findings"""
        print(f"📖 Reading: {self.input_csv}")
        
        with open(self.input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                risk_level, reason = self.classify_risk(row)
                
                self.findings.append({
                    'file': row['File'],
                    'line': row['Line'],
                    'pattern': row['Pattern Type'],
                    'text': row['Unwrapped Text'],
                    'context': row['Context'],
                    'risk_level': risk_level,
                    'reason': reason,
                    'auto_fixable': risk_level == 'green'
                })
                
                self.stats[risk_level] += 1
                self.stats['total'] += 1
        
        print(f"✅ Processed {self.stats['total']} findings\n")
    
    def generate_report(self):
        """Generate classification summary report"""
        print("="*80)
        print("📊 RISK CLASSIFICATION REPORT")
        print("="*80)
        
        total = self.stats['total']
        green = self.stats['green']
        yellow = self.stats['yellow']
        red = self.stats['red']
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Total strings analyzed: {total}")
        print(f"\n   🟢 GREEN (Auto-fix):    {green:>3} ({green/total*100:>5.1f}%)")
        print(f"   🟡 YELLOW (Review):     {yellow:>3} ({yellow/total*100:>5.1f}%)")
        print(f"   🔴 RED (Manual):        {red:>3} ({red/total*100:>5.1f}%)")
        
        # Breakdown by pattern
        print(f"\n📋 BY PATTERN TYPE:")
        pattern_stats = defaultdict(lambda: {'green': 0, 'yellow': 0, 'red': 0})
        
        for finding in self.findings:
            pattern = finding['pattern']
            risk = finding['risk_level']
            pattern_stats[pattern][risk] += 1
        
        for pattern in sorted(pattern_stats.keys()):
            stats = pattern_stats[pattern]
            total_pattern = stats['green'] + stats['yellow'] + stats['red']
            print(f"\n   {pattern}:")
            print(f"      🟢 {stats['green']:>3}  🟡 {stats['yellow']:>3}  🔴 {stats['red']:>3}  Total: {total_pattern}")
        
        # Breakdown by file (top 10)
        print(f"\n📁 TOP 10 FILES (by total findings):")
        file_stats = defaultdict(lambda: {'green': 0, 'yellow': 0, 'red': 0})
        
        for finding in self.findings:
            file_path = finding['file']
            risk = finding['risk_level']
            file_stats[file_path][risk] += 1
        
        # Sort by total
        sorted_files = sorted(
            file_stats.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True
        )[:10]
        
        for file_path, stats in sorted_files:
            total_file = stats['green'] + stats['yellow'] + stats['red']
            clean_path = file_path.replace('templates/', '').strip('"')
            print(f"   {clean_path:50s} 🟢 {stats['green']:>2} 🟡 {stats['yellow']:>2} 🔴 {stats['red']:>2}")
        
        print("\n" + "="*80)
        print(f"\n✅ Next Steps:")
        print(f"   1. Review classification in: classified_strings.csv")
        print(f"   2. Adjust rules if needed and re-run")
        print(f"   3. Proceed to Phase 2: Auto-wrap {green} GREEN items")
        print("="*80 + "\n")
    
    def export_classified_csv(self, output_file='classified_strings.csv'):
        """Export classified findings to CSV"""
        print(f"💾 Exporting to: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['Risk', 'File', 'Line', 'Pattern', 'Text', 'Context', 'Reason', 'Auto-Fixable']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for finding in self.findings:
                writer.writerow({
                    'Risk': finding['risk_level'].upper(),
                    'File': finding['file'],
                    'Line': finding['line'],
                    'Pattern': finding['pattern'],
                    'Text': finding['text'][:100],  # Truncate for readability
                    'Context': finding['context'][:100],
                    'Reason': finding['reason'],
                    'Auto-Fixable': 'YES' if finding['auto_fixable'] else 'NO'
                })
        
        print(f"✅ Exported {len(self.findings)} classified findings\n")
    
    def export_green_only(self, output_file='green_auto_fix.json'):
        """Export only GREEN items for auto-fixing"""
        green_items = [f for f in self.findings if f['risk_level'] == 'green']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(green_items, f, indent=2)
        
        print(f"💚 Exported {len(green_items)} auto-fixable items to: {output_file}")
    
    def export_yellow_review(self, output_file='yellow_review_queue.json'):
        """Export YELLOW items for manual review"""
        yellow_items = [f for f in self.findings if f['risk_level'] == 'yellow']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(yellow_items, f, indent=2)
        
        print(f"🟡 Exported {len(yellow_items)} review items to: {output_file}")
    
    def export_red_manual(self, output_file='red_manual_review.json'):
        """Export RED items for careful manual handling"""
        red_items = [f for f in self.findings if f['risk_level'] == 'red']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(red_items, f, indent=2)
        
        print(f"🔴 Exported {len(red_items)} manual review items to: {output_file}")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Classify unwrapped strings by risk level'
    )
    parser.add_argument(
        '--input',
        default='unwrapped_strings.csv',
        help='Input CSV from find_unwrapped_strings.py'
    )
    
    args = parser.parse_args()
    
    # Initialize classifier
    classifier = StringClassifier(input_csv=args.input)
    
    # Process CSV
    classifier.process_csv()
    
    # Generate report
    classifier.generate_report()
    
    # Export files
    classifier.export_classified_csv()
    classifier.export_green_only()
    classifier.export_yellow_review()
    classifier.export_red_manual()
    
    print("✅ Classification complete!\n")


if __name__ == '__main__':
    main()
