"""
Tests for Semantic Validation Layer
"""
import pytest
from src.utils.semantic_validator import SemanticValidator, validate_claims_file


class TestSemanticValidator:
    """Test suite for semantic validation"""
    
    def test_valid_mechanism(self):
        """Test that valid mechanisms pass"""
        valid, error = SemanticValidator.validate_mechanism('inheritance')
        assert valid
        assert error == ""
    
    def test_invalid_mechanism(self):
        """Test that invalid mechanisms fail"""
        valid, error = SemanticValidator.validate_mechanism('magic')
        assert not valid
        assert 'not in controlled vocabulary' in error
    
    def test_empty_mechanism(self):
        """Test that empty mechanism fails"""
        valid, error = SemanticValidator.validate_mechanism('')
        assert not valid
        assert 'empty' in error.lower()
    
    def test_vacuous_null_hypothesis(self):
        """Test that vacuous null hypotheses fail"""
        vacuous_examples = [
            "This may not be intentional",
            "This might not be coordinated",
            "Perhaps not planned",
        ]
        
        for example in vacuous_examples:
            valid, error = SemanticValidator.validate_null_hypothesis(example)
            assert not valid, f"Should reject vacuous: {example}"
            assert 'vacuous' in error.lower()
    
    def test_null_hypothesis_without_structural_element(self):
        """Test that null hypothesis without structural explanation fails"""
        invalid = "This pattern exists because people wanted it to exist and made it happen."
        valid, error = SemanticValidator.validate_null_hypothesis(invalid)
        assert not valid
        assert 'structural alternative' in error.lower()
    
    def test_null_hypothesis_too_short(self):
        """Test that short null hypotheses fail"""
        short = "Alternative explanation exists."
        valid, error = SemanticValidator.validate_null_hypothesis(short)
        assert not valid
        assert 'too short' in error.lower()
    
    def test_valid_null_hypothesis(self):
        """Test that valid null hypotheses pass"""
        valid_example = (
            "This continuity may emerge from institutional inertia and path dependence, "
            "where decentralized actors independently preserve structures due to aligned incentives, "
            "not coordinated intent."
        )
        valid, error = SemanticValidator.validate_null_hypothesis(valid_example)
        assert valid
        assert error == ""
    
    def test_valid_claim(self):
        """Test that valid claims pass"""
        claim = {
            'id': 'test_001',
            'mechanism': 'inheritance',
            'null_hypothesis': (
                "This pattern may result from institutional path dependence, "
                "where structural incentives independently align actors without coordination."
            )
        }
        valid, errors = SemanticValidator.validate_claim(claim)
        assert valid
        assert len(errors) == 0
    
    def test_invalid_claim_both_fields(self):
        """Test that claims with both invalid fields fail with both errors"""
        claim = {
            'id': 'test_002',
            'mechanism': 'conspiracy',
            'null_hypothesis': 'Maybe not'
        }
        valid, errors = SemanticValidator.validate_claim(claim)
        assert not valid
        assert len(errors) == 2
        assert any('mechanism' in e.lower() for e in errors)
        assert any('null hypothesis' in e.lower() for e in errors)
    
    def test_validate_claims_file(self):
        """Test validation of multiple claims"""
        claims = [
            {
                'id': 'valid_001',
                'mechanism': 'succession',
                'null_hypothesis': (
                    "Continuity emerges from institutional inertia and decentralized "
                    "incentive alignment, not coordinated strategy."
                )
            },
            {
                'id': 'invalid_001',
                'mechanism': 'magic',
                'null_hypothesis': 'This may not be intentional'
            }
        ]
        
        all_valid, errors = validate_claims_file(claims)
        assert not all_valid
        assert 'invalid_001' in errors
        assert 'valid_001' not in errors
        assert len(errors['invalid_001']) == 2
