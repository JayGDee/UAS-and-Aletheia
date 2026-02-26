"""
==============================================================================
STANDALONE AUTHORIZATION ENGINE v2.1 - PRODUCTION READY
Fixes FAIL case applied_constraints + swarm UnboundLocalError
==============================================================================
"""
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Constraint:
    """Immutable constraint definition"""
    id: str
    action: str
    rules: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            id_data = f"{self.action}:{json.dumps(self.rules, sort_keys=True)}"
            generated_id = hashlib.sha256(id_data.encode('ascii')).hexdigest()[:16]
            object.__setattr__(self, 'id', generated_id)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "rules": self.rules,
            "metadata": self.metadata
        }

@dataclass(frozen=True)
class Proposal:
    """Immutable proposal"""
    action: str
    params: Dict[str, Any]
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "params": self.params,
            "nonce": self.nonce,
            "timestamp": self.timestamp
        }
    
    @property
    def canonical_hash(self) -> str:
        canonical = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=True
        )
        return hashlib.sha256(canonical.encode('ascii')).hexdigest()

@dataclass
class AuthorizationDecision:
    """Result of UAS evaluation"""
    proposal_hash: str
    verdict: str  # "PASS", "FAIL", "REFUSE"
    matched_constraints: List[str]
    reason: str
    timestamp: str
    nonce: str
    new_constraint: Optional[Constraint] = None
    original_proposal: Optional[Dict[str, Any]] = None
    applied_constraints: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        result = {
            "proposal_hash": self.proposal_hash,
            "verdict": self.verdict,
            "matched_constraints": self.matched_constraints,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "nonce": self.nonce
        }
        if self.new_constraint:
            result["new_constraint"] = self.new_constraint.to_dict()
        if self.original_proposal:
            result["original_proposal"] = self.original_proposal
        result["applied_constraints"] = self.applied_constraints
        return result

def validate_value(value: Any) -> bool:
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str):
            if not all(ord(c) < 128 for c in value):
                raise ValueError(f"Non-ASCII string: {value}")
        return True
    raise ValueError(f"Invalid value type: {type(value)}")

def validate_proposal(proposal: Proposal) -> None:
    if not isinstance(proposal.action, str):
        raise ValueError("Action must be string")
    if not all(ord(c) < 128 for c in proposal.action):
        raise ValueError("Action must be ASCII")
    
    for key, value in proposal.params.items():
        if not isinstance(key, str) or not all(ord(c) < 128 for c in key):
            raise ValueError(f"Invalid param key: {key}")
        validate_value(value)

def matches_constraint(
    proposal: Proposal,
    constraint: Constraint,
    allow_extra_params: bool = False
) -> Tuple[bool, Optional[str]]:
    if proposal.action != constraint.action:
        return False, f"Action mismatch: {proposal.action} != {constraint.action}"
    
    param_rules = constraint.rules
    params = proposal.params
    
    for rule_key in param_rules:
        if rule_key not in params:
            return False, f"Missing required parameter: {rule_key}"
    
    for key, value in params.items():
        if key not in param_rules:
            if not allow_extra_params:
                return False, f"Unexpected parameter: {key}"
            continue
        
        rule = param_rules[key]
        rule_type = rule.get("type")
        
        if rule_type == "number":
            if not isinstance(value, (int, float)):
                return False, f"{key}: expected number, got {type(value)}"
            
            min_val = rule.get("min", float('-inf'))
            max_val = rule.get("max", float('inf'))
            if not (min_val <= value <= max_val):
                return False, f"{key}: {value} not in range [{min_val}, {max_val}]"
        
        elif rule_type == "string":
            if not isinstance(value, str):
                return False, f"{key}: expected string, got {type(value)}"
            allowed = rule.get("allowed")
            if allowed is not None and value not in allowed:
                return False, f"{key}: {value} not in allowed values {allowed}"
            pattern = rule.get("pattern")
            if pattern is not None:
                import re
                if not re.match(pattern, value):
                    return False, f"{key}: {value} doesn't match pattern {pattern}"
        
        elif rule_type == "boolean":
            if not isinstance(value, bool):
                return False, f"{key}: expected boolean, got {type(value)}"
        
        else:
            return False, f"{key}: unknown rule type {rule_type}"
    
    return True, None

class HITLInterface:
    def request_approval(self, proposal: Proposal) -> Optional[Constraint]:
        raise NotImplementedError("HITL interface must be implemented")

class StubHITL(HITLInterface):
    def request_approval(self, proposal: Proposal) -> Optional[Constraint]:
        print(f"[HITL STUB] Rejecting proposal: {proposal.action}")
        return None

class UniversalAuthoritySubstrate:
    def __init__(
        self,
        constraints: List[Constraint],
        hitl: HITLInterface,
        allow_extra_params: bool = False,
        enable_replay_protection: bool = True
    ):
        self.constraints = list(constraints)
        self.hitl = hitl
        self.allow_extra_params = allow_extra_params
        self.enable_replay_protection = enable_replay_protection
        self._seen_nonces = set() if enable_replay_protection else None
    
    def add_constraint(self, constraint: Constraint) -> None:
        conflicts = [c for c in self.constraints if c.id == constraint.id]
        if conflicts:
            raise ValueError(f"Constraint ID collision: {constraint.id}")
        self.constraints.append(constraint)
    
    def evaluate(self, proposal: Proposal) -> AuthorizationDecision:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Replay protection
        if self.enable_replay_protection:
            if proposal.nonce in self._seen_nonces:
                return AuthorizationDecision(
                    proposal_hash=proposal.canonical_hash,
                    verdict="REFUSE",
                    matched_constraints=[],
                    reason="Replay attack detected",
                    timestamp=timestamp,
                    nonce=proposal.nonce,
                    original_proposal=proposal.to_dict(),
                    applied_constraints=[]
                )
            self._seen_nonces.add(proposal.nonce)
        
        # Validate proposal
        try:
            validate_proposal(proposal)
        except ValueError as e:
            return AuthorizationDecision(
                proposal_hash="invalid",
                verdict="REFUSE",
                matched_constraints=[],
                reason=f"Invalid proposal: {e}",
                timestamp=timestamp,
                nonce=proposal.nonce,
                original_proposal=proposal.to_dict(),
                applied_constraints=[]
            )
        
        # FIXED: Collect ALL action-relevant constraints + match results
        matches = []
        reasons = []
        evaluated_constraints = []
        
        for constraint in self.constraints:
            if constraint.action == proposal.action:
                evaluated_constraints.append(constraint.to_dict())
                is_match, reason = matches_constraint(proposal, constraint, self.allow_extra_params)
                if is_match:
                    matches.append(constraint)
                elif reason:
                    reasons.append(f"{constraint.id}: {reason}")
        
        proposal_dict = proposal.to_dict()
        
        # FIXED: Use evaluated constraints for ALL paths
        if len(matches) == 1:
            return AuthorizationDecision(
                proposal_hash=proposal.canonical_hash,
                verdict="PASS",
                matched_constraints=[matches[0].id],
                reason=f"Matched constraint: {matches[0].id}",
                timestamp=timestamp,
                nonce=proposal.nonce,
                original_proposal=proposal_dict,
                applied_constraints=evaluated_constraints
            )
        
        elif len(matches) > 1:
            match_ids = [c.id for c in matches]
            return AuthorizationDecision(
                proposal_hash=proposal.canonical_hash,
                verdict="REFUSE",
                matched_constraints=match_ids,
                reason=f"Ambiguous: multiple constraints match {match_ids}",
                timestamp=timestamp,
                nonce=proposal.nonce,
                original_proposal=proposal_dict,
                applied_constraints=evaluated_constraints
            )
        
        else:
            # HITL
            new_constraint = self.hitl.request_approval(proposal)
            if new_constraint is not None:
                self.add_constraint(new_constraint)
                return AuthorizationDecision(
                    proposal_hash=proposal.canonical_hash,
                    verdict="PASS",
                    matched_constraints=[new_constraint.id],
                    reason=f"Approved by HITL: {new_constraint.id}",
                    timestamp=timestamp,
                    nonce=proposal.nonce,
                    new_constraint=new_constraint,
                    original_proposal=proposal_dict,
                    applied_constraints=[new_constraint.to_dict()]
                )
            else:
                failure_reasons = "; ".join(reasons) if reasons else "No matching constraints"
                return AuthorizationDecision(
                    proposal_hash=proposal.canonical_hash,
                    verdict="FAIL",
                    matched_constraints=[],
                    reason=f"Denied: {failure_reasons}",
                    timestamp=timestamp,
                    nonce=proposal.nonce,
                    original_proposal=proposal_dict,
                    applied_constraints=evaluated_constraints  # FIXED: Shows failing constraint
                )

# Test it works
if __name__ == "__main__":
    drone_roe = Constraint(
        id="test_drone",
        action="drone_flight",
        rules={
            "altitude_ft": {"type": "number", "max": 400},
            "speed_kts": {"type": "number", "max": 100}
        }
    )
    
    uas = UniversalAuthoritySubstrate([drone_roe], StubHITL())
    
    # PASS
    proposal_pass = Proposal(action="drone_flight", params={"altitude_ft": 350, "speed_kts": 80})
    print("PASS:", uas.evaluate(proposal_pass).verdict)
    
    # FAIL
    proposal_fail = Proposal(action="drone_flight", params={"altitude_ft": 500, "speed_kts": 80})
    decision_fail = uas.evaluate(proposal_fail)
    print("FAIL:", decision_fail.verdict)
    print("Applied constraints on FAIL:", len(decision_fail.applied_constraints))
    print("Reason:", decision_fail.reason)
