#!/usr/bin/env python3
"""
Script to reprocess existing survey responses with the corrected AI classification logic.
This will fix misclassified data where problems were incorrectly marked as opportunities.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import SurveyResponse
from app import app, db
from task_queue import add_analysis_task
import json

def reprocess_misclassified_data():
    """Find and reprocess responses that have misclassified opportunities"""
    
    with app.app_context():
        # Find responses that might have misclassified data
        responses = SurveyResponse.query.all()
        
        reprocessed_count = 0
        problem_keywords = ['problem', 'issue', 'poor', 'bad', 'fail', 'broken', 'error', 'bug', 'complaint', 'dissatisfied', 'unhappy', 'frustrat', 'difficult', 'hard', 'confusing', 'wrong', 'missing', 'lack', 'without', 'slow', 'delayed']
        
        for response in responses:
            needs_reprocessing = False
            
            # Check growth opportunities for problem keywords
            if response.growth_opportunities:
                try:
                    opportunities = json.loads(response.growth_opportunities)
                    for opp in opportunities:
                        if isinstance(opp, dict):
                            opp_text = (str(opp.get('type', '')) + ' ' + str(opp.get('description', ''))).lower()
                            if any(keyword in opp_text for keyword in problem_keywords):
                                print(f"Found misclassified opportunity in {response.company_name}: {opp.get('type', '')}")
                                needs_reprocessing = True
                                break
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Error parsing opportunities for {response.company_name}: {e}")
            
            if needs_reprocessing:
                print(f"Reprocessing response {response.id} for {response.company_name}")
                add_analysis_task(response.id)
                reprocessed_count += 1
        
        print(f"Queued {reprocessed_count} responses for reprocessing")
        return reprocessed_count

if __name__ == "__main__":
    print("Starting reprocessing of misclassified data...")
    count = reprocess_misclassified_data()
    print(f"Completed. {count} responses queued for reanalysis.")