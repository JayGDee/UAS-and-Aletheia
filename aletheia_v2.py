"""
ALETHEIA PROTOCOL V2.0
==============================================================================
UNIVERSAL VERIFICATION ENGINE
Can verify any decision structure - not tied to UAS
==============================================================================
"""

import hashlib
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from datetime import datetime, timezone

# Deterministic decimal arithmetic
getcontext().prec = 28


# ==============================================================================
# CORE DATA STRUCTURES
# ==============================================================================

@dataclass(frozen=True)
class VerificationConstraint:
    """
    Universal constraint format - can be adapted from any policy system
    """
    identifier: str
    constraint_type: str  # "numeric_range", "string_enum", "boolean", "hash_match", etc.
    parameters: Dict[str, Any]
    
    def __post_init__(self):
        # Normalize identifier
        normalized = self.identifier.strip().lower().encode('ascii', 'ignore').decode()
        object.__setattr__(self, 'identifier', normalized)
        
        # Validate parameters are deterministic
        self._validate_parameters(self.parameters)
    
    @staticmethod
    def _validate_parameters(params: Dict[str, Any]) -> None:
        """Ensure parameters are deterministically serializable"""
        for key, value in params.items():
            if not isinstance(key, str):
                raise ValueError(f"Parameter key must be string: {key}")
            if isinstance(value, float):
                raise ValueError(f"Use Decimal instead of float: {key}={value}")
            if isinstance(value, (dict, list)) and not AletheiaProtocol._is_deterministic(value):
                raise ValueError(f"Parameter {key} contains non-deterministic data")
    
    @property
    def canonical_hash(self) -> str:
        """Deterministic hash of constraint"""
        canonical = json.dumps({
            "identifier": self.identifier,
            "type": self.constraint_type,
            "parameters": self._serialize_params(self.parameters)
        }, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical.encode('ascii')).hexdigest()
    
    @staticmethod
    def _serialize_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parameters to canonical form"""
        result = {}
        for key, value in params.items():
            if isinstance(value, Decimal):
                result[key] = str(value.normalize())
            elif isinstance(value, dict):
                result[key] = VerificationConstraint._serialize_params(value)
            elif isinstance(value, list):
                result[key] = [
                    VerificationConstraint._serialize_params({"v": item})["v"]
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_uas_constraint(cls, uas_constraint: Dict[str, Any]) -> 'VerificationConstraint':
        """Convert UAS constraint to Aletheia format"""
        # Extract first rule as primary constraint
        # (In production, you might create multiple VerificationConstraints)
        rules = uas_constraint.get("rules", {})
        if not rules:
            raise ValueError("UAS constraint has no rules")
        
        # Take first rule
        param_name, rule = next(iter(rules.items()))
        rule_type = rule.get("type")
        
        if rule_type == "number":
            return cls(
                identifier=f"{uas_constraint['action']}:{param_name}",
                constraint_type="numeric_range",
                parameters={
                    "min": Decimal(str(rule.get("min", 0))),
                    "max": Decimal(str(rule.get("max", 10**10)))
                }
            )
        elif rule_type == "string":
            return cls(
                identifier=f"{uas_constraint['action']}:{param_name}",
                constraint_type="string_enum",
                parameters={
                    "allowed": rule.get("allowed", [])
                }
            )
        elif rule_type == "boolean":
            return cls(
                identifier=f"{uas_constraint['action']}:{param_name}",
                constraint_type="boolean",
                parameters={}
            )
        else:
            raise ValueError(f"Unknown UAS rule type: {rule_type}")


@dataclass(frozen=True)
class UniversalBinaryObject:
    """
    UBO - Immutable proof of verification
    
    Can verify:
    - UAS authorization decisions
    - Numeric computations
    - Hash-based proofs
    - Any structured decision
    """
    decision_data_hash: str  # Hash of the decision being verified
    decision_structure: str  # Type of decision: "uas_authorization", "numeric_check", etc.
    constraint_hashes: List[str]  # Hashes of constraints applied
    verification_result: Dict[str, Any]  # Structured result
    verdict: str  # "PASS", "FAIL", "REFUSE"
    timestamp: str
    protocol_version: str = "v2.0"
    seal: str = field(default="")
    
    def __post_init__(self):
        if not self.seal:
            seal_data = self._compute_seal_input()
            seal = hashlib.sha256(seal_data.encode('ascii')).hexdigest()
            object.__setattr__(self, 'seal', seal)
    
    def _compute_seal_input(self) -> str:
        """Canonical seal computation"""
        return json.dumps({
            "decision_hash": self.decision_data_hash,
            "structure": self.decision_structure,
            "constraints": sorted(self.constraint_hashes),
            "result": self.verification_result,
            "verdict": self.verdict,
            "timestamp": self.timestamp,
            "version": self.protocol_version
        }, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    
    def verify_seal(self) -> bool:
        """Verify cryptographic seal"""
        expected_seal_input = self._compute_seal_input()
        expected_seal = hashlib.sha256(expected_seal_input.encode('ascii')).hexdigest()
        return self.seal == expected_seal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_data_hash": self.decision_data_hash,
            "decision_structure": self.decision_structure,
            "constraint_hashes": self.constraint_hashes,
            "verification_result": self.verification_result,
            "verdict": self.verdict,
            "timestamp": self.timestamp,
            "protocol_version": self.protocol_version,
            "seal": self.seal,
        }


# ==============================================================================
# ALETHEIA PROTOCOL ENGINE
# ==============================================================================

class AletheiaProtocol:
    """
    Universal verification engine
    
    Can verify:
    1. UAS authorization decisions
    2. Numeric constraint satisfaction
    3. Hash-based proofs
    4. Custom decision structures
    """
    
    VERSION = "v2.0"
    
    @staticmethod
    def _is_deterministic(obj: Any) -> bool:
        """Check if object is deterministically serializable"""
        if isinstance(obj, (str, int, bool, type(None))):
            return True
        if isinstance(obj, Decimal):
            return True
        if isinstance(obj, dict):
            return all(
                isinstance(k, str) and AletheiaProtocol._is_deterministic(v)
                for k, v in obj.items()
            )
        if isinstance(obj, list):
            return all(AletheiaProtocol._is_deterministic(item) for item in obj)
        return False
    
    @classmethod
    def verify_uas_decision(
        cls,
        decision: Dict[str, Any],
        constraints: List[VerificationConstraint]
    ) -> UniversalBinaryObject:
        """
        Verify a UAS authorization decision
        
        Args:
            decision: UAS AuthorizationDecision dict
            constraints: VerificationConstraints that were applied
        """
        # Hash the decision
        decision_json = json.dumps(decision, sort_keys=True, separators=(',', ':'))
        decision_hash = hashlib.sha256(decision_json.encode('ascii')).hexdigest()
        
        # Verify structure
        required_fields = ["verdict", "matched_constraints", "proposal_hash"]
        missing = [f for f in required_fields if f not in decision]
        if missing:
            return cls._create_refusal_ubo(
                decision_hash,
                "uas_authorization",
                constraints,
                f"Missing required fields: {missing}"
            )
        
        # Extract constraint IDs from decision
        matched_ids = set(decision.get("matched_constraints", []))
        constraint_ids = {c.identifier for c in constraints}
        
        # Verify constraint consistency
        if decision["verdict"] == "PASS":
            if not matched_ids.issubset(constraint_ids):
                return cls._create_refusal_ubo(
                    decision_hash,
                    "uas_authorization",
                    constraints,
                    f"Decision references unknown constraints: {matched_ids - constraint_ids}"
                )
            
            verification_result = {
                "decision_verdict": decision["verdict"],
                "constraints_verified": list(matched_ids),
                "proposal_hash": decision["proposal_hash"],
                "verification_status": "constraints_match"
            }
            verdict = "PASS"
        
        elif decision["verdict"] in ("FAIL", "REFUSE"):
            verification_result = {
                "decision_verdict": decision["verdict"],
                "reason": decision.get("reason", "No reason provided"),
                "verification_status": "decision_recorded"
            }
            verdict = decision["verdict"]
        
        else:
            return cls._create_refusal_ubo(
                decision_hash,
                "uas_authorization",
                constraints,
                f"Invalid verdict: {decision['verdict']}"
            )
        
        return UniversalBinaryObject(
            decision_data_hash=decision_hash,
            decision_structure="uas_authorization",
            constraint_hashes=[c.canonical_hash for c in constraints],
            verification_result=verification_result,
            verdict=verdict,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    @classmethod
    def verify_numeric_value(
        cls,
        value: Decimal,
        constraints: List[VerificationConstraint],
        metadata: Optional[Dict[str, Any]] = None
    ) -> UniversalBinaryObject:
        """
        Verify a numeric value against range constraints
        (Original Aletheia use case)
        """
        # Create decision record
        decision_data = {
            "value": str(value.normalize()),
            "metadata": metadata or {}
        }
        decision_json = json.dumps(decision_data, sort_keys=True, separators=(',', ':'))
        decision_hash = hashlib.sha256(decision_json.encode('ascii')).hexdigest()
        
        # Evaluate each constraint
        results = []
        all_passed = True
        
        for constraint in constraints:
            if constraint.constraint_type != "numeric_range":
                return cls._create_refusal_ubo(
                    decision_hash,
                    "numeric_verification",
                    constraints,
                    f"Invalid constraint type for numeric verification: {constraint.constraint_type}"
                )
            
            params = constraint.parameters
            min_val = params.get("min", Decimal('-Infinity'))
            max_val = params.get("max", Decimal('Infinity'))
            
            passed = min_val <= value <= max_val
            all_passed = all_passed and passed
            
            results.append({
                "constraint_id": constraint.identifier,
                "passed": passed,
                "value": str(value.normalize()),
                "range": f"[{min_val}, {max_val}]"
            })
        
        verification_result = {
            "value": str(value.normalize()),
            "constraint_results": results,
            "all_constraints_passed": all_passed
        }
        
        return UniversalBinaryObject(
            decision_data_hash=decision_hash,
            decision_structure="numeric_verification",
            constraint_hashes=[c.canonical_hash for c in constraints],
            verification_result=verification_result,
            verdict="PASS" if all_passed else "FAIL",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    @classmethod
    def verify_hash_proof(
        cls,
        data_hash: str,
        expected_hash: str,
        constraints: List[VerificationConstraint]
    ) -> UniversalBinaryObject:
        """
        Verify a hash-based proof
        (For document verification, signature checking, etc.)
        """
        decision_data = {
            "provided_hash": data_hash,
            "expected_hash": expected_hash
        }
        decision_json = json.dumps(decision_data, sort_keys=True, separators=(',', ':'))
        decision_hash = hashlib.sha256(decision_json.encode('ascii')).hexdigest()
        
        match = data_hash == expected_hash
        
        verification_result = {
            "hash_match": match,
            "provided": data_hash,
            "expected": expected_hash
        }
        
        return UniversalBinaryObject(
            decision_data_hash=decision_hash,
            decision_structure="hash_proof",
            constraint_hashes=[c.canonical_hash for c in constraints],
            verification_result=verification_result,
            verdict="PASS" if match else "FAIL",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    @classmethod
    def _create_refusal_ubo(
        cls,
        decision_hash: str,
        structure: str,
        constraints: List[VerificationConstraint],
        reason: str
    ) -> UniversalBinaryObject:
        """Create a REFUSE UBO for invalid inputs"""
        return UniversalBinaryObject(
            decision_data_hash=decision_hash,
            decision_structure=structure,
            constraint_hashes=[c.canonical_hash for c in constraints],
            verification_result={"refusal_reason": reason},
            verdict="REFUSE",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    @staticmethod
    def reconstruct_ubo(raw: Dict[str, Any]) -> UniversalBinaryObject:
        """
        Reconstruct a UniversalBinaryObject from serialized data
        for OFFLINE verification only.

        This does NOT re-run UAS, constraints, or authorization.
        It only rebuilds immutable evidence so the seal can be verified.
        """
        required_fields = [
            "decision_data_hash",
            "decision_structure",
            "constraint_hashes",
            "verification_result",
            "verdict",
            "timestamp",
            "protocol_version",
            "seal",
        ]

        missing = [f for f in required_fields if f not in raw]
        if missing:
            raise ValueError(f"Invalid UBO data, missing fields: {missing}")

        return UniversalBinaryObject(
            decision_data_hash=raw["decision_data_hash"],
            decision_structure=raw["decision_structure"],
            constraint_hashes=raw["constraint_hashes"],
            verification_result=raw["verification_result"],
            verdict=raw["verdict"],
            timestamp=raw["timestamp"],
            protocol_version=raw.get("protocol_version", AletheiaProtocol.VERSION),
            seal=raw["seal"],
        )


# ==============================================================================
# INTEGRATION HELPERS
# ==============================================================================

def integrate_uas_with_aletheia(uas_decision_dict: Dict[str, Any]) -> UniversalBinaryObject:
    """
    Convenience function to verify UAS decisions with Aletheia
    
    Automatically extracts constraints from UAS decision if present
    """
    # If decision includes constraint definitions, use them
    if "new_constraint" in uas_decision_dict and uas_decision_dict["new_constraint"]:
        uas_constraint = uas_decision_dict["new_constraint"]
        constraint = VerificationConstraint.from_uas_constraint(uas_constraint)
        constraints = [constraint]
    else:
        # Create a minimal constraint for verification
        matched = uas_decision_dict.get("matched_constraints", [])
        constraints = [
            VerificationConstraint(
                identifier=cid,
                constraint_type="uas_reference",
                parameters={"constraint_id": cid}
            )
            for cid in matched
        ]
    
    return AletheiaProtocol.verify_uas_decision(uas_decision_dict, constraints)


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("ALETHEIA PROTOCOL V2.0 - UNIVERSAL VERIFICATION")
    print("=" * 70)
    
    # Example 1: Standalone numeric verification (original use case)
    print("\n📊 Example 1: Numeric Verification (Standalone)")
    print("-" * 70)
    
    constraints_numeric = [
        VerificationConstraint(
            identifier="transaction_limit",
            constraint_type="numeric_range",
            parameters={"min": Decimal("0"), "max": Decimal("10000")}
        )
    ]
    
    ubo1 = AletheiaProtocol.verify_numeric_value(
        value=Decimal("5000"),
        constraints=constraints_numeric,
        metadata={"transaction_id": "tx_12345"}
    )
    
    print(f"Value: 5000")
    print(f"Verdict: {ubo1.verdict}")
    print(f"Seal: {ubo1.seal[:16]}...")
    print(f"Verified: {ubo1.verify_seal()}")
    
    # Example 2: UAS integration
    print("\n🔗 Example 2: UAS Decision Verification")
    print("-" * 70)
    
    uas_decision = {
        "proposal_hash": "abc123def456",
        "verdict": "PASS",
        "matched_constraints": ["finance_small_transfer"],
        "reason": "Matched constraint: finance_small_transfer",
        "timestamp": "2026-01-06T12:00:00Z",
        "nonce": "unique_nonce_789"
    }
    
    constraints_uas = [
        VerificationConstraint(
            identifier="finance_small_transfer",
            constraint_type="uas_reference",
            parameters={"constraint_id": "finance_small_transfer"}
        )
    ]
    
    ubo2 = AletheiaProtocol.verify_uas_decision(uas_decision, constraints_uas)
    
    print(f"UAS Verdict: {uas_decision['verdict']}")
    print(f"Aletheia Verdict: {ubo2.verdict}")
    print(f"Decision Hash: {ubo2.decision_data_hash[:16]}...")
    print(f"Seal: {ubo2.seal[:16]}...")
    print(f"Verified: {ubo2.verify_seal()}")
    
    # Example 3: Hash proof verification
    print("\n🔒 Example 3: Hash Proof Verification")
    print("-" * 70)
    
    document_hash = hashlib.sha256(b"important document").hexdigest()
    
    constraints_hash = [
        VerificationConstraint(
            identifier="document_integrity",
            constraint_type="hash_match",
            parameters={"algorithm": "sha256"}
        )
    ]
    
    ubo3 = AletheiaProtocol.verify_hash_proof(
        data_hash=document_hash,
        expected_hash=document_hash,
        constraints=constraints_hash
    )
    
    print(f"Hash Match: {ubo3.verification_result['hash_match']}")
    print(f"Verdict: {ubo3.verdict}")
    print(f"Verified: {ubo3.verify_seal()}")
    
    print("\n" + "=" * 70)
    print("ALETHEIA V2.0: Universal verification - works standalone or with UAS")
    print("=" * 70)