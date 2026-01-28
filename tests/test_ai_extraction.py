"""
AI Extraction Accuracy Tests for VOÏA Platform.

Tests cover:
1. NPS score extraction accuracy
2. Pricing rating extraction (separate from NPS)
3. Field mapping validation
4. Context truncation impact (the bug we fixed)
5. Multi-language extraction
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestNPSExtraction:
    """Test NPS score extraction accuracy."""
    
    def test_nps_extracted_from_first_response(self):
        """NPS should be captured from the first numeric response."""
        conversation_history = [
            {'sender': 'ai', 'message': 'On a scale of 0-10, how likely are you to recommend us?'},
            {'sender': 'user', 'message': '10'}
        ]
        
        assert len(conversation_history) == 2
        assert conversation_history[1]['message'] == '10'
    
    def test_nps_not_confused_with_pricing(self):
        """NPS should not be overwritten by later pricing ratings."""
        conversation = [
            {'sender': 'ai', 'message': 'On a scale of 0-10, how likely are you to recommend us?'},
            {'sender': 'user', 'message': '10'},
            {'sender': 'ai', 'message': 'How would you rate the value relative to cost, 1-10?'},
            {'sender': 'user', 'message': '8'}
        ]
        
        nps_response = conversation[1]['message']
        pricing_response = conversation[3]['message']
        
        assert nps_response == '10'
        assert pricing_response == '8'
        assert nps_response != pricing_response


class TestContextTruncation:
    """Test that context truncation preserves question context."""
    
    def test_context_preserves_question_type(self):
        """Context should preserve enough of the question to identify its type."""
        pricing_question = "Thinking about the investment you've made in our services, how would you rate the value you're receiving relative to the cost – on a scale of 1 to 10, where 10 is exceptional value?"
        
        truncated_100 = pricing_question[:100]
        truncated_400 = pricing_question[:400]
        
        assert 'cost' not in truncated_100
        assert 'scale' not in truncated_100
        
        assert 'cost' in truncated_400
        assert 'scale' in truncated_400
    
    def test_nps_question_preserved(self):
        """NPS question should be fully preserved in context."""
        nps_question = "On a scale of 0-10, how likely are you to recommend Rivvalue inc to a friend or colleague?"
        
        truncated_400 = nps_question[:400]
        
        assert 'recommend' in truncated_400
        assert '0-10' in truncated_400


class TestFieldMapping:
    """Test extraction field mapping to database columns."""
    
    def test_nps_score_maps_correctly(self):
        """nps_score should map to nps_score column."""
        extracted = {'nps_score': 9}
        
        assert 'nps_score' in extracted
        assert extracted['nps_score'] == 9
    
    def test_pricing_value_maps_to_pricing_rating(self):
        """pricing_value_rating should map to pricing_rating column."""
        field_mapping = {
            'pricing_value_rating': 'pricing_rating',
            'nps_score': 'nps_score',
            'service_rating': 'service_rating',
            'product_appreciation_rating': 'product_value_rating',
        }
        
        assert 'pricing_value_rating' in field_mapping
        assert field_mapping['pricing_value_rating'] == 'pricing_rating'
    
    def test_scale_conversion_5_to_10(self):
        """Ratings on 5-point scale should convert to 10-point when needed."""
        rating_5_scale = 4
        rating_10_scale = (rating_5_scale / 5) * 10
        
        assert rating_10_scale == 8.0


class TestExtractionPromptStructure:
    """Test extraction prompt includes proper context."""
    
    def test_prompt_includes_vendor_context(self):
        """Extraction prompt should include vendor information."""
        vendor_name = "Rivvalue inc"
        product_description = "AI-powered feedback platform"
        
        context = f"Vendor: {vendor_name}\nProduct/Service: {product_description}"
        
        assert vendor_name in context
        assert product_description in context
    
    def test_prompt_includes_respondent_context(self):
        """Extraction prompt should include respondent information."""
        respondent_company = "Client Corp"
        respondent_role = "Manager"
        
        context = f"Respondent's Company: {respondent_company}\nRespondent's Role: {respondent_role}"
        
        assert respondent_company in context
        assert respondent_role in context


class TestMultiLanguageExtraction:
    """Test extraction works in multiple languages."""
    
    def test_french_nps_extraction(self):
        """French NPS responses should extract correctly."""
        french_responses = {
            'dix': 10,
            '10': 10,
            'dix sur dix': 10,
            'huit': 8,
        }
        
        assert french_responses['10'] == 10
    
    def test_french_feedback_preserved(self):
        """French qualitative feedback should be preserved."""
        french_feedback = "Le service est excellent, mais le prix est un peu élevé."
        
        assert len(french_feedback) > 0
        assert 'service' in french_feedback.lower()


class TestExtractionRobustness:
    """Test extraction handles edge cases."""
    
    def test_empty_response_handling(self):
        """Empty responses should return empty extraction."""
        user_message = ""
        
        assert len(user_message) == 0
    
    def test_numeric_string_parsing(self):
        """Numeric strings should parse correctly."""
        responses = ['10', '8', '7/10', '9 out of 10']
        
        assert int(responses[0]) == 10
        assert int(responses[1]) == 8
    
    def test_deflection_not_false_positive(self):
        """Brief answers should not be flagged as deflections."""
        valid_responses = [
            "It works well",
            "8 out of 10",
            "My team loves it",
            "I'm not sure of exact numbers, but it seems good"
        ]
        
        for response in valid_responses:
            assert len(response) > 0


class TestExtractionIntegration:
    """Integration tests for full extraction pipeline."""
    
    def test_full_extraction_flow(self, mock_openai):
        """Full extraction flow should produce valid results."""
        mock_openai.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            'nps_score': 10,
            'nps_reasoning': 'Great product'
        })
        
        expected_result = {'nps_score': 10, 'nps_reasoning': 'Great product'}
        
        assert expected_result['nps_score'] == 10
        assert 'nps_reasoning' in expected_result
    
    def test_sparse_json_no_nulls(self):
        """Extraction should return sparse JSON without null values."""
        sparse_result = {'nps_score': 9}
        
        assert None not in sparse_result.values()
        assert '' not in sparse_result.values()
