"""
UAS + Aletheia Multi-Domain Governance Demo v2.0
Demonstrates Universal Authority Substrate + Aletheia Protocol
across multiple agentic domains with real enforcement and verifiable evidence.

Produces timestamped JSON files for decisions and UBOs.
Compatible with audit_dashboard_generator.py
"""

import json
from datetime import datetime, timezone

# =============================================================================
# REAL SYSTEM IMPORTS – AUTHORITATIVE IMPLEMENTATIONS
# =============================================================================

from uas_v2 import (
    Constraint,
    Proposal,
    UniversalAuthoritySubstrate,
    StubHITL,
)

from aletheia_v2_standalone import (
    VerificationConstraint,
    AletheiaProtocol,
)

# =============================================================================
# DEMO UTILITIES (PRESENTATION ONLY – NO LOGIC)
# =============================================================================

def banner(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")

def pause():
    input("Press ENTER to continue...\n")

def persist_json(obj, filename, description):
    with open(filename, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"✅ {description} written to disk")
    print(f"   File: {filename}\n")


# =============================================================================
# MAIN DEMO – MULTI-DOMAIN WALKTHROUGH
# =============================================================================

def main():

    banner("UAS + ALETHEIA MULTI-DOMAIN GOVERNANCE DEMO")
    print("This demo uses REAL production code to show universal boundary enforcement")
    print("and cryptographic verification across different agent types.\n")
    print("UAS module:", UniversalAuthoritySubstrate.__module__)
    print("Aletheia module:", AletheiaProtocol.__module__)
    pause()

    # Create shared UAS instance (constraints added per scenario)
    uas = UniversalAuthoritySubstrate(
        constraints=[],
        hitl=StubHITL(),
        enable_replay_protection=True,
        allow_extra_params=True,
    )

    # -------------------------------------------------------------------------
    banner("SCENARIO 1: Autonomous Robotics / Drone Operation")

    print("Enforces physical safety boundaries (altitude, speed).\n")

    robotics_roe = Constraint(
        id="robotics_safe_operation",
        action="perform_movement",
        rules={
            "altitude_m": {"type": "number", "min": 0, "max": 120},
            "speed_mps": {"type": "number", "min": 0, "max": 15},
        },
        metadata={"domain": "robotics", "purpose": "physical_safety"}
    )

    uas.add_constraint(robotics_roe)
    print("✅ Robotics safety rules loaded.\n")

    alt = float(input("Proposed altitude (meters): "))
    spd = float(input("Proposed speed (m/s): "))

    prop_robot = Proposal(
        action="perform_movement",
        params={"altitude_m": alt, "speed_mps": spd}
    )

    dec_robot = uas.evaluate(prop_robot)
    print(f"Verdict: {dec_robot.verdict}")
    print(f"Reason:  {dec_robot.reason}")
    print(f"Proposal Hash: {dec_robot.proposal_hash[:16]}...")

    ts = dec_robot.timestamp.replace(':', '-').replace('.', '-')
    persist_json(dec_robot.to_dict(), f"uas_decision_robotics_{ts}.json", "UAS Decision – Robotics")

    pause()

    # -------------------------------------------------------------------------
    banner("SCENARIO 2: Financial Trading Agent")

    print("Prevents excessive risk and unauthorized assets.\n")

    trading_roe = Constraint(
        id="trading_risk_control",
        action="execute_trade",
        rules={
            "amount_usd": {"type": "number", "max": 50000},
            "asset": {"type": "string", "enum": ["BTC", "ETH", "USD", "AAPL"]},
            "leverage": {"type": "number", "max": 5.0}
        },
        metadata={"domain": "finance", "purpose": "risk_management"}
    )

    uas.add_constraint(trading_roe)
    print("✅ Trading risk rules loaded.\n")

    amt = float(input("Trade amount (USD): "))
    asset = input("Asset (BTC/ETH/USD/AAPL): ")
    lev = float(input("Leverage factor: "))

    prop_trade = Proposal(
        action="execute_trade",
        params={"amount_usd": amt, "asset": asset, "leverage": lev}
    )

    dec_trade = uas.evaluate(prop_trade)
    print(f"Verdict: {dec_trade.verdict}")
    print(f"Reason:  {dec_trade.reason}")
    print(f"Proposal Hash: {dec_trade.proposal_hash[:16]}...")

    ts = dec_trade.timestamp.replace(':', '-').replace('.', '-')
    persist_json(dec_trade.to_dict(), f"uas_decision_trading_{ts}.json", "UAS Decision – Trading")

    pause()

    # -------------------------------------------------------------------------
    banner("SCENARIO 3: Healthcare Recommendation Agent")

    print("Enforces dosage and patient safety rules.\n")

    health_roe = Constraint(
        id="medical_dosage_safety",
        action="recommend_treatment",
        rules={
            "dosage_mg": {"type": "number", "max": 1000},
            "patient_age": {"type": "number", "min": 18},
            "contraindication": {"type": "boolean", "value": False}
        },
        metadata={"domain": "healthcare", "purpose": "patient_safety"}
    )

    uas.add_constraint(health_roe)
    print("✅ Medical safety rules loaded.\n")

    dose = float(input("Proposed dosage (mg): "))
    age = int(input("Patient age: "))
    contra = input("Any contraindication? (yes/no): ").lower() == "yes"

    prop_health = Proposal(
        action="recommend_treatment",
        params={"dosage_mg": dose, "patient_age": age, "contraindication": contra}
    )

    dec_health = uas.evaluate(prop_health)
    print(f"Verdict: {dec_health.verdict}")
    print(f"Reason:  {dec_health.reason}")
    print(f"Proposal Hash: {dec_health.proposal_hash[:16]}...")

    ts = dec_health.timestamp.replace(':', '-').replace('.', '-')
    persist_json(dec_health.to_dict(), f"uas_decision_healthcare_{ts}.json", "UAS Decision – Healthcare")

    pause()

    # -------------------------------------------------------------------------
    banner("SCENARIO 4: Web Research / Content Agent")

    print("Prevents sensitive queries and excessive scope.\n")

    web_roe = Constraint(
        id="web_agent_content_safety",
        action="publish_research",
        rules={
            "query_length": {"type": "number", "max": 300},
            "sensitive_topic": {"type": "boolean", "value": False},
            "max_sources": {"type": "number", "max": 30}
        },
        metadata={"domain": "information", "purpose": "compliance"}
    )

    uas.add_constraint(web_roe)
    print("✅ Web agent rules loaded.\n")

    qlen = int(input("Query length (characters): "))
    sens = input("Contains sensitive topic? (yes/no): ").lower() == "yes"
    srcs = int(input("Number of sources requested: "))

    prop_web = Proposal(
        action="publish_research",
        params={"query_length": qlen, "sensitive_topic": sens, "max_sources": srcs}
    )

    dec_web = uas.evaluate(prop_web)
    print(f"Verdict: {dec_web.verdict}")
    print(f"Reason:  {dec_web.reason}")
    print(f"Proposal Hash: {dec_web.proposal_hash[:16]}...")

    ts = dec_web.timestamp.replace(':', '-').replace('.', '-')
    persist_json(dec_web.to_dict(), f"uas_decision_webagent_{ts}.json", "UAS Decision – Web Agent")

    pause()

    # -------------------------------------------------------------------------
    banner("PHASE: Generate Cryptographic Evidence (Aletheia UBOs)")

    print("Creating verifiable proofs for selected decisions...\n")

    decisions = [dec_robot, dec_trade, dec_health, dec_web]
    constraint_ids = ["robotics_safe_operation", "trading_risk_control", "medical_dosage_safety", "web_agent_content_safety"]
    
    # Map constraint IDs to match the UAS filename domains
    domain_map = {
        "robotics_safe_operation": "robotics",
        "trading_risk_control": "trading",
        "medical_dosage_safety": "healthcare",  # Changed from "medical" to "healthcare"
        "web_agent_content_safety": "webagent"
    }

    ubos = []
    for dec, cid in zip(decisions, constraint_ids):
        vc = VerificationConstraint(
            identifier=cid,
            constraint_type="uas_reference",
            parameters={"constraint_id": cid}
        )
        ubo = AletheiaProtocol.verify_uas_decision(dec.to_dict(), [vc])
        ubos.append(ubo)

        ts_str = ubo.timestamp.replace(':', '-').replace('.', '-')
        domain = domain_map[cid]  # Use mapped domain name
        filename = f"aletheia_ubo_{domain}_{ts_str}.json"
        persist_json(ubo.to_dict(), filename, f"UBO – {domain.title()}")

        print(f"  {domain.title()} UBO seal verified: {ubo.verify_seal()}")

    print("\nAll cryptographic proofs generated and saved.\n")
    print("NOTE: UBOs provide machine-verifiable evidence of boundary enforcement.")
    pause()

    # -------------------------------------------------------------------------
    banner("DEMO COMPLETE")

    print("Generated files include:")
    print("  • UAS decisions: uas_decision_[domain]_[timestamp].json")
    print("  • Aletheia UBOs:   aletheia_ubo_[domain]_[timestamp].json")
    print("\nRun 'python audit_dashboard_generator.py' to view interactive audit view.\n")
    print("This demonstrates universal, augmentative governance with provable accountability.")

if __name__ == "__main__":
    main()