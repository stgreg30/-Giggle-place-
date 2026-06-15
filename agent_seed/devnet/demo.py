"""
agent_seed/devnet/demo.py

Developer sandbox — runs a full agent-to-agent transaction locally
with fake services. Zero external dependencies beyond the SDK itself.
Run with: python -m agent_seed.devnet.demo
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Optional


# ------------------------------------------------------------------
# Fake service layer — replaces real modules until they're built
# ------------------------------------------------------------------

class FakeDiscovery:
    """In-memory discovery that returns a hardcoded seller card."""

    @staticmethod
    def find(capability: str, max_price: str, currency: str) -> Dict[str, Any]:
        return {
            "name": "Sentiment Analysis Agent (devnet)",
            "url": "https://devnet.local/agent",
            "service_endpoint": "http://localhost:8001/a2a",
            "capabilities": {
                "task_types": [
                    {
                        "name": "sentiment-analysis",
                        "description": "Returns positive/negative/neutral with confidence",
                    }
                ]
            },
            "payment": {
                "currency": currency,
                "network": "base",
                "price": "0.001",
                "pay_to": "0xDevNetSeller",
            },
            "did": "did:key:z6MkSellerDevNet",
        }


class FakeX402:
    """Fake payment processor — immediately 'pays' and returns proof."""

    @staticmethod
    def pay(payment_request: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tx_hash": f"0x{uuid.uuid4().hex[:16]}",
            "amount": payment_request.get("amount", "0.001"),
            "currency": payment_request.get("currency", "USDC"),
            "from": "0xDevNetBuyer",
            "to": payment_request.get("pay_to", "0xDevNetSeller"),
            "timestamp": int(time.time()),
        }


class FakeA2A:
    """Fake A2A task server — runs locally, returns sentiment result."""

    @staticmethod
    def send_task(
        endpoint: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        # First call: simulate 402
        return {
            "status": "payment_required",
            "task_id": f"task-{uuid.uuid4().hex[:8]}",
            "payment": {
                "amount": "0.001",
                "currency": "USDC",
                "pay_to": "0xDevNetSeller",
            },
        }

    @staticmethod
    def resubmit(
        endpoint: str,
        input_data: Dict[str, Any],
        payment_proof: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Second call: return completed task with artifact
        text = input_data.get("text", "")
        sentiment = "positive" if "hello" in text.lower() else "neutral"
        return {
            "status": "completed",
            "task_id": f"task-{uuid.uuid4().hex[:8]}",
            "artifact": {
                "content": f"{sentiment} (confidence: 0.95)",
                "signature": "fake-signature-for-devnet",
                "content_type": "text/plain",
            },
        }


class FakeDID:
    """Fake identity verification — trusts everything in devnet."""

    @staticmethod
    def verify_artifact(
        artifact: Dict[str, Any], seller_did: str
    ) -> Dict[str, Any]:
        return {"verified": True, "signer": seller_did, **artifact}


class FakeVC:
    """Fake VC issuer — generates a mock credential."""

    @staticmethod
    def issue_receipt(
        buyer_did: str,
        seller_did: str,
        task_id: str,
        payment_proof: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "vc_id": f"urn:vc:devnet:{uuid.uuid4().hex[:12]}",
            "type": "VerifiableReceipt",
            "issuer": buyer_did,
            "subject": seller_did,
            "claim": {
                "task_id": task_id,
                "payment": payment_proof,
                "timestamp": int(time.time()),
            },
        }


# ------------------------------------------------------------------
# Simulated AutonomousAgent — same API, fake internals
# ------------------------------------------------------------------

class DevNetAgent:
    """
    A simulated agent that uses fake services to demonstrate the full flow.
    This has the exact same public API as AutonomousAgent but works offline.
    """

    def __init__(self, did: str, role: str = "buyer") -> None:
        self.did = did
        self.role = role
        self.discovery = FakeDiscovery()
        self.x402 = FakeX402()
        self.a2a = FakeA2A()
        self.trust_did = FakeDID()
        self.vc = FakeVC()

    def send_task(
        self,
        capability: str,
        input_data: Dict[str, Any],
        max_price: str = "0.001",
        currency: str = "USDC",
    ) -> Dict[str, Any]:
        """Full transaction flow with fake services."""
        print(f"\n{'='*60}")
        print(f"AGENT: {self.did[:30]}...")
        print(f"TASK: find '{capability}', max price {max_price} {currency}")
        print(f"{'='*60}")

        # Step 1: Discover
        print("\n[1/5] Discovering seller...")
        seller = self.discovery.find(capability, max_price, currency)
        print(f"      Found: {seller['name']}")

        # Step 2: Send A2A task
        print("\n[2/5] Sending A2A task...")
        response = self.a2a.send_task(seller["service_endpoint"], input_data)
        print(f"      Status: {response['status']}")
        print(f"      Task ID: {response['task_id']}")

        # Step 3: Pay if required
        payment_proof = None
        if response.get("status") == "payment_required":
            print("\n[3/5] Payment required — paying via x402...")
            payment_proof = self.x402.pay(response["payment"])
            print(f"      TX hash: {payment_proof['tx_hash']}")
            print(f"      Amount: {payment_proof['amount']} {payment_proof['currency']}")

            print("      Resubmitting task with payment proof...")
            response = self.a2a.resubmit(
                seller["service_endpoint"], input_data, payment_proof
            )
            print(f"      Status: {response['status']}")

        # Step 4: Verify artifact
        print("\n[4/5] Verifying artifact...")
        artifact = self.trust_did.verify_artifact(
            response["artifact"], seller["did"]
        )
        print(f"      Verified: {artifact['verified']}")

        # Step 5: Issue VC
        print("\n[5/5] Issuing VC receipt...")
        receipt = self.vc.issue_receipt(
            self.did,
            seller["did"],
            response["task_id"],
            payment_proof,
        )
        print(f"      VC ID: {receipt['vc_id']}")

        return {
            "artifact": artifact,
            "receipt": receipt,
            "transaction": payment_proof,
        }


# ------------------------------------------------------------------
# Main demo
# ------------------------------------------------------------------

def run_devnet_demo():
    """Run a complete buyer-seller transaction in devnet mode."""
    print("\n" + "=" * 60)
    print("  AGENT-SEED DEVNET")
    print("  Full A2A + x402 + VC flow — offline, fake services")
    print("=" * 60)

    # Create identities
    buyer_did = "did:key:z6MkBuyerDevNet12345"
    seller_did = "did:key:z6MkSellerDevNet67890"

    print(f"\n Buyer DID : {buyer_did}")
    print(f" Seller DID: {seller_did}")

    # Initialize buyer agent
    buyer = DevNetAgent(did=buyer_did, role="buyer")

    # Run the transaction
    result = buyer.send_task(
        capability="sentiment-analysis",
        input_data={"text": "Hello world! This is amazing."},
        max_price="0.001",
    )

    # Display results
    print("\n" + "=" * 60)
    print("  TRANSACTION COMPLETE")
    print("=" * 60)
    print(f"\n Result: {result['artifact']['content']}")
    print(f" Receipt: {result['receipt']['vc_id']}")
    if result["transaction"]:
        print(f" Payment: {result['transaction']['tx_hash']}")
    print(f"\n✅ Full flow completed successfully!")
    print("   This is the experience developers get with real services.")
    print("   Every NotImplementedError in agent.py maps to a module")
    print("   that, when built, replaces one of these fakes.")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_devnet_demo()
