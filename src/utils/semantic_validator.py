"""
Semantic Validation Layer
Prevents semantically vacuous claims from passing CI
"""
import re
from typing import Dict, List, Tuple


class SemanticValidator:
    """Validates semantic content of claims"""
    
    # Controlled vocabulary for mechanisms
    VALID_MECHANISMS = {
        'inheritance', 'appointment', 'election', 'succession',
        'acquisition', 'merger', 'transfer', 'delegation',
        'designation', 'nomination', 'selection', 'promotion'
    }
    
    # Patterns that indicate vacuous null hypotheses
    VACUOUS_PATTERNS = [
        r'^this may not be',
        r'^this might not',
        r'^possibly not',
        r'^perhaps not',
        r'^maybe not',
        r'^could be unintentional',
    ]
    
    # Required structural elements in null hypothesis
    REQUIRED_ELEMENTS = [
        'alternative',
        'structural',
        'institutional',
        'incentive',
        'path dependence',
        'inertia',
        'decentralized',
        'emergent',
    ]
    
    @classmethod
    def validate_mechanism(cls, mechanism: str) -> Tuple[bool, str]:
        """
        Validate that mechanism is from controlled vocabulary
        
        Returns:
            (is_valid, error_message)
        """
        if not mechanism:
            return False, "Mechanism is empty"
        
        mechanism_lower = mechanism.lower().strip()
        
        if mechanism_lower not in cls.VALID_MECHANISMS:
            return False, f"Mechanism '{mechanism}' not in controlled vocabulary. Valid: {sorted(cls.VALID_MECHANISMS)}"
        
        return True, ""
    
    @classmethod
    def validate_null_hypothesis(cls, null_hypothesis: str) -> Tuple[bool, str]:
        """
        Validate that null hypothesis is not semantically vacuous
        
        Returns:
            (is_valid, error_message)
        """
        if not null_hypothesis:
            return False, "Null hypothesis is empty"
        
        null_lower = null_hypothesis.lower().strip()
        
        # Check for vacuous patterns
        for pattern in cls.VACUOUS_PATTERNS:
            if re.match(pattern, null_lower):
                return False, f"Null hypothesis is vacuous (matches pattern: {pattern})"
        
        # Check for required structural elements
        has_structural_element = any(
            element in null_lower 
            for element in cls.REQUIRED_ELEMENTS
        )
        
        if not has_structural_element:
            return False, f"Null hypothesis lacks structural alternative. Must contain one of: {cls.REQUIRED_ELEMENTS}"
        
        # Check minimum length (substantive explanation required)
        if len(null_hypothesis) < 50:
            return False, f"Null hypothesis too short ({len(null_hypothesis)} chars). Minimum 50 chars required for substantive explanation."
        
        return True, ""
    
    @classmethod
    def validate_claim(cls, claim: Dict) -> Tuple[bool, List[str]]:
        """
        Validate entire claim for semantic validity
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate mechanism
        mechanism = claim.get('mechanism', '')
        mech_valid, mech_error = cls.validate_mechanism(mechanism)
        if not mech_valid:
            errors.append(f"Mechanism: {mech_error}")
        
        # Validate null hypothesis
        null_hyp = claim.get('null_hypothesis', '')
        null_valid, null_error = cls.validate_null_hypothesis(null_hyp)
        if not null_valid:
            errors.append(f"Null Hypothesis: {null_error}")
        
        return len(errors) == 0, errors


def validate_claims_file(claims: List[Dict]) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Validate all claims in a file
    
    Returns:
        (all_valid, errors_by_claim_id)
    """
    validator = SemanticValidator()
    all_errors = {}
    
    for claim in claims:
        claim_id = claim.get('id', 'unknown')
        is_valid, errors = validator.validate_claim(claim)
        
        if not is_valid:
            all_errors[claim_id] = errors
    
    return len(all_errors) == 0, all_errors
