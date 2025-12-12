"""
Callback Security: HMAC Signature Generation and Verification

This module provides utilities for securing webhook callbacks between
Echo Substrate v4 and Art of Proof using HMAC-SHA256 signatures.
"""

import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional, Tuple


class CallbackSigner:
    """
    Generates HMAC-SHA256 signatures for outgoing webhook callbacks.
    
    Used by Echo Substrate to sign callbacks sent to Art of Proof.
    """
    
    def __init__(self, primary_secret: str, secondary_secret: Optional[str] = None):
        """
        Initialize the signer with one or two secrets.
        
        Args:
            primary_secret: The current active secret for signing
            secondary_secret: Optional fallback secret (for rollback scenarios)
        """
        self.primary_secret = primary_secret.encode('utf-8')
        self.secondary_secret = secondary_secret.encode('utf-8') if secondary_secret else None
    
    def sign_payload(self, payload: Dict[str, Any]) -> Tuple[str, str, str]:
        """
        Sign a callback payload with the primary secret.
        
        Args:
            payload: The JSON-serializable callback payload
            
        Returns:
            A tuple of (signature, timestamp, json_payload)
        """
        # Generate timestamp (Unix epoch in seconds)
        timestamp = str(int(time.time()))
        
        # Serialize payload to JSON (deterministic ordering)
        json_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # Create the signed string: timestamp.payload
        signed_string = f"{timestamp}.{json_payload}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.primary_secret,
            signed_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp, json_payload


class CallbackVerifier:
    """
    Verifies HMAC-SHA256 signatures for incoming webhook callbacks.
    
    Used by Art of Proof to verify callbacks from Echo Substrate.
    """
    
    def __init__(self, primary_secret: str, secondary_secret: Optional[str] = None):
        """
        Initialize the verifier with one or two secrets.
        
        Args:
            primary_secret: The current active secret
            secondary_secret: Optional deprecated secret (for grace period)
        """
        self.primary_secret = primary_secret.encode('utf-8')
        self.secondary_secret = secondary_secret.encode('utf-8') if secondary_secret else None
    
    def verify_signature(
        self,
        payload: str,
        signature: str,
        timestamp: str,
        max_age_seconds: int = 300
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify a callback signature.
        
        Args:
            payload: The raw JSON payload string
            signature: The signature from X-Substrate-Signature header
            timestamp: The timestamp from X-Substrate-Timestamp header
            max_age_seconds: Maximum age of the callback (default: 5 minutes)
            
        Returns:
            A tuple of (is_valid, error_message)
        """
        # Step 1: Check timestamp freshness (prevent replay attacks)
        try:
            callback_time = int(timestamp)
        except ValueError:
            return False, "Invalid timestamp format"
        
        current_time = int(time.time())
        age = current_time - callback_time
        
        if age > max_age_seconds:
            return False, f"Callback too old ({age}s > {max_age_seconds}s)"
        
        if age < -60:  # Allow 60s clock skew
            return False, "Callback timestamp is in the future"
        
        # Step 2: Reconstruct the signed string
        signed_string = f"{timestamp}.{payload}"
        
        # Step 3: Try to verify with primary secret
        expected_signature_primary = hmac.new(
            self.primary_secret,
            signed_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(signature, expected_signature_primary):
            return True, None
        
        # Step 4: If primary fails, try secondary (if available)
        if self.secondary_secret:
            expected_signature_secondary = hmac.new(
                self.secondary_secret,
                signed_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(signature, expected_signature_secondary):
                return True, None
        
        # Step 5: All verifications failed
        return False, "Signature verification failed"


# Example Usage
if __name__ == "__main__":
    # --- Echo Substrate Side (Sending) ---
    print("=== Echo Substrate: Signing Callback ===")
    
    signer = CallbackSigner(primary_secret="production_secret_v2")
    
    callback_payload = {
        "substrate_case_id": "abc123",
        "original_case_id": "xyz789",
        "status": "completed",
        "message": "Case processing complete",
        "package_url": "https://api.substrate.com/v1/cases/abc123/package",
        "completed_at": "2025-12-12T12:00:00Z"
    }
    
    signature, timestamp, json_payload = signer.sign_payload(callback_payload)
    
    print(f"Signature: {signature}")
    print(f"Timestamp: {timestamp}")
    print(f"Payload: {json_payload}")
    
    # --- Art of Proof Side (Receiving) ---
    print("\n=== Art of Proof: Verifying Callback ===")
    
    # During rotation, Art of Proof accepts both old and new secrets
    verifier = CallbackVerifier(
        primary_secret="production_secret_v2",
        secondary_secret="production_secret_v1"  # Old secret, still valid during grace period
    )
    
    is_valid, error = verifier.verify_signature(
        payload=json_payload,
        signature=signature,
        timestamp=timestamp
    )
    
    if is_valid:
        print("✅ Signature verified successfully!")
    else:
        print(f"❌ Signature verification failed: {error}")
    
    # --- Test with Invalid Signature ---
    print("\n=== Testing Invalid Signature ===")
    
    is_valid, error = verifier.verify_signature(
        payload=json_payload,
        signature="invalid_signature_12345",
        timestamp=timestamp
    )
    
    if is_valid:
        print("✅ Signature verified successfully!")
    else:
        print(f"❌ Signature verification failed: {error}")
    
    # --- Test with Old Timestamp (Replay Attack) ---
    print("\n=== Testing Replay Attack ===")
    
    old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
    
    is_valid, error = verifier.verify_signature(
        payload=json_payload,
        signature=signature,
        timestamp=old_timestamp
    )
    
    if is_valid:
        print("✅ Signature verified successfully!")
    else:
        print(f"❌ Signature verification failed: {error}")
