#!/usr/bin/env python3
"""
Unit tests for OCR card detail extraction.
These test the parsing logic without making any Google API calls.
"""

import pytest
from src.utils.enhanced_card_processor import _extract_card_details_enhanced, _extract_psa_card_details


class TestCardParserBasic:
    """Test basic card extraction from OCR text"""
    
    @pytest.mark.parametrize(
        "text, player, expected",
        [
            # Modern Topps cards
            (
                "2023 TOPPS CHROME PAUL SKENES #124 RC ROOKIE CARD",
                "Paul Skenes",
                {
                    "player": "Paul Skenes",
                    "set": "Topps Chrome",
                    "year": "2023",
                    "card_number": "124",
                    "features": "Rookie, Rc"
                }
            ),
            # Panini cards
            (
                "2024 PANINI PRIZM BASKETBALL VICTOR WEMBANYAMA #1 ROOKIE",
                "Victor Wembanyama", 
                {
                    "player": "Victor Wembanyama",
                    "manufacturer": "PANINI",
                    "year": "2024",
                    "card_number": "1",
                    "features": "Rookie"
                }
            ),
            # Bowman cards
            (
                "2018 BOWMAN CHROME PROSPECTS SHOHEI OHTANI #BCP-1",
                "Shohei Ohtani",
                {
                    "player": "Shohei Ohtani",
                    "year": "2018",
                    "card_number": "BCP-1"
                }
            ),
            # Cards with parallels
            (
                "2023 TOPPS CHROME GOLD REFRACTOR RONALD ACUNA JR 15/50",
                "Ronald Acuna Jr",
                {
                    "player": "Ronald Acuna Jr",
                    "year": "2023",
                    "parallel": "15/50 Gold Refractor"
                }
            ),
            # Autograph cards
            (
                "2023 TOPPS CHROME PAUL SKENES AUTO ROOKIE PATCH #/99",
                "Paul Skenes",
                {
                    "player": "Paul Skenes",
                    "year": "2023",
                    "features": "Rookie, Auto, Patch",
                    "parallel": "Auto Rookie Patch"
                }
            )
        ]
    )
    def test_basic_extraction(self, text, player, expected):
        """Test extraction of basic card details"""
        result = _extract_card_details_enhanced(text, player)
        
        for key, expected_value in expected.items():
            actual_value = result.get(key)
            
            if key == "features":
                # Features can be in any order, check all expected features are present
                expected_features = set(f.strip().lower() for f in expected_value.split(","))
                actual_features = set(f.strip().lower() for f in (actual_value or "").split(","))
                assert expected_features.issubset(actual_features), f"Expected features {expected_features} not found in {actual_features}"
            elif key == "parallel":
                # Parallel text can vary in order - check all expected words are present
                expected_words = set(expected_value.lower().split())
                actual_words = set((actual_value or "").lower().split())
                assert expected_words.issubset(actual_words), f"Expected parallel words {expected_words} not all found in {actual_words}"
            else:
                assert actual_value == expected_value, f"For {key}: expected '{expected_value}', got '{actual_value}'"


class TestPSAGradedCards:
    """Test PSA graded card extraction"""
    
    @pytest.mark.parametrize(
        "text, player, expected",
        [
            # Standard PSA 10
            (
                "PSA 10 GEM MINT\n2018 TOPPS CHROME SHOHEI OHTANI #1 ROOKIE\nCERT #12345678",
                "Shohei Ohtani",
                {
                    "player": "Shohei Ohtani",
                    "graded": True,
                    "grade": "10",
                    "grading_company": "PSA",
                    "cert_number": "12345678",
                    "year": "2018",
                    "set": "Topps Chrome",
                    "card_number": "1"
                }
            ),
            # PSA 9
            (
                "PROFESSIONAL SPORTS AUTHENTICATOR\nGRADE: 9\n2023 BOWMAN CHROME PAUL SKENES RC\nCERTIFICATION #87654321",
                "Paul Skenes",
                {
                    "player": "Paul Skenes",
                    "graded": True,
                    "grade": "9",
                    "grading_company": "PSA",
                    "cert_number": "87654321",
                    "year": "2023"
                }
            ),
            # PSA with complex text
            (
                "PSA Authentication and Grading Services\nMINT 10\n2020 TOPPS CHROME ROOKIE CARD\nJUAN SOTO #125\nPSA #98765432",
                "Juan Soto",
                {
                    "player": "Juan Soto",
                    "graded": True,
                    "grade": "10",
                    "grading_company": "PSA",
                    "cert_number": "98765432",
                    "year": "2020",
                    "card_number": "125"
                }
            )
        ]
    )
    def test_psa_extraction(self, text, player, expected):
        """Test PSA graded card extraction"""
        result = _extract_psa_card_details(text, player)
        
        for key, expected_value in expected.items():
            actual_value = result.get(key)
            assert actual_value == expected_value, f"For {key}: expected '{expected_value}', got '{actual_value}'"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_text(self):
        """Test with empty OCR text"""
        result = _extract_card_details_enhanced("", "Test Player")
        assert result["player"] == "Test Player"
        assert result["graded"] is False
    
    def test_no_clear_data(self):
        """Test with unclear OCR text"""
        messy_text = "BLURRY TEXT 123 XYZ UNCLEAR SYMBOLS @@@ 456"
        result = _extract_card_details_enhanced(messy_text, "Unknown Player")
        assert result["player"] == "Unknown Player"
        # Should handle gracefully without crashing
        assert isinstance(result, dict)
    
    def test_multiple_years(self):
        """Test text with multiple years - should pick most recent"""
        text = "COPYRIGHT 1991 TOPPS 2023 TOPPS CHROME SERIES"
        result = _extract_card_details_enhanced(text, "Test Player")
        assert result["year"] == "2023"  # Should prefer recent year
    
    def test_physical_measurements_ignored(self):
        """Test that physical measurements aren't mistaken for card numbers"""
        text = "HEIGHT: 6'2\" WEIGHT: 185 LBS CARD #15 TOPPS 2023"
        result = _extract_card_details_enhanced(text, "Test Player")
        assert result["card_number"] == "15"  # Should find real card number, not measurements


class TestConfidenceScoring:
    """Test extraction confidence logic"""
    
    def test_high_confidence_card(self):
        """Test card with all major fields present"""
        text = "2023 TOPPS CHROME PAUL SKENES #124 RC ROOKIE CARD"
        result = _extract_card_details_enhanced(text, "Paul Skenes")
        
        # Count required fields found
        required_fields = ['player', 'set', 'year'] 
        found_fields = [k for k in required_fields if result.get(k)]
        confidence = len(found_fields) / len(required_fields)
        
        if result.get('parallel') or result.get('features'):
            confidence = min(1.0, confidence + 0.2)
            
        assert confidence >= 0.8  # Should be high confidence
    
    def test_low_confidence_card(self):
        """Test card with minimal data"""
        text = "UNCLEAR BLURRY TEXT NO CLEAR INFO"
        result = _extract_card_details_enhanced(text, "Unknown Player")
        
        required_fields = ['player', 'set', 'year']
        found_fields = [k for k in required_fields if result.get(k) and result[k] != "Unknown Player"]
        confidence = len(found_fields) / len(required_fields)
        
        assert confidence <= 0.5  # Should be low confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 