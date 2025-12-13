"""
Oracle Attack Tests for Callback Security
Tests for timing attacks and side-channel vulnerabilities
"""
import pytest
import time
from src.utils.callback_security import CallbackVerifier


class TestOracleAttacks:
    """Test suite for cryptographic oracle attacks"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.secret = "test_secret_key_for_oracle_testing"
        self.verifier = CallbackVerifier(primary_secret=self.secret)
        self.valid_payload = {"event": "test", "data": "value"}
        self.timestamp = str(int(time.time()))
    
    def test_zero_signature_timing(self):
        """Test that zero signature fails with consistent timing"""
        timings = []
        
        for _ in range(10):
            start = time.perf_counter()
            try:
                self.verifier.verify(
                    payload=self.valid_payload,
                    signature='0' * 64,
                    timestamp=self.timestamp
                )
            except Exception:
                pass
            end = time.perf_counter()
            timings.append((end - start) * 1000)  # Convert to ms
        
        # Check timing consistency (±5ms threshold)
        avg_timing = sum(timings) / len(timings)
        max_deviation = max(abs(t - avg_timing) for t in timings)
        
        assert max_deviation < 5.0, f"Timing attack vulnerability: deviation {max_deviation}ms > 5ms"
    
    def test_none_signature_timing(self):
        """Test that None signature fails with consistent timing"""
        timings = []
        
        for _ in range(10):
            start = time.perf_counter()
            try:
                self.verifier.verify(
                    payload=self.valid_payload,
                    signature=None,
                    timestamp=self.timestamp
                )
            except Exception:
                pass
            end = time.perf_counter()
            timings.append((end - start) * 1000)
        
        avg_timing = sum(timings) / len(timings)
        max_deviation = max(abs(t - avg_timing) for t in timings)
        
        assert max_deviation < 5.0, f"Timing attack vulnerability: deviation {max_deviation}ms > 5ms"
    
    def test_missing_headers_timing(self):
        """Test that missing headers fail with consistent timing"""
        timings = []
        
        for _ in range(10):
            start = time.perf_counter()
            try:
                self.verifier.verify(
                    payload=self.valid_payload,
                    signature='',
                    timestamp=''
                )
            except Exception:
                pass
            end = time.perf_counter()
            timings.append((end - start) * 1000)
        
        avg_timing = sum(timings) / len(timings)
        max_deviation = max(abs(t - avg_timing) for t in timings)
        
        assert max_deviation < 5.0, f"Timing attack vulnerability: deviation {max_deviation}ms > 5ms"
    
    def test_all_invalid_cases_uniform_timing(self):
        """Test that all invalid cases have uniform timing"""
        test_cases = [
            ('0' * 64, self.timestamp),
            (None, self.timestamp),
            ('', ''),
            ('invalid_sig', self.timestamp),
            ('a' * 64, '0'),
        ]
        
        all_timings = []
        
        for signature, timestamp in test_cases:
            case_timings = []
            for _ in range(5):
                start = time.perf_counter()
                try:
                    self.verifier.verify(
                        payload=self.valid_payload,
                        signature=signature,
                        timestamp=timestamp
                    )
                except Exception:
                    pass
                end = time.perf_counter()
                case_timings.append((end - start) * 1000)
            all_timings.append(sum(case_timings) / len(case_timings))
        
        # All invalid cases should have similar average timing
        overall_avg = sum(all_timings) / len(all_timings)
        max_case_deviation = max(abs(t - overall_avg) for t in all_timings)
        
        assert max_case_deviation < 10.0, f"Oracle attack vulnerability: case deviation {max_case_deviation}ms > 10ms"
    
    def test_error_messages_uniform(self):
        """Test that all invalid inputs produce identical error types"""
        test_cases = [
            ('0' * 64, self.timestamp),
            ('invalid', self.timestamp),
            ('', self.timestamp),
        ]
        
        error_types = []
        
        for signature, timestamp in test_cases:
            try:
                self.verifier.verify(
                    payload=self.valid_payload,
                    signature=signature,
                    timestamp=timestamp
                )
            except Exception as e:
                error_types.append(type(e).__name__)
        
        # All should raise the same exception type
        assert len(set(error_types)) == 1, f"Information leak: different error types {set(error_types)}"
