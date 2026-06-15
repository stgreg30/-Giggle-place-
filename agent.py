```python
"""
agent_seed/agent.py

The AutonomousAgent class — the single entry point developers import.
Every method delegates to a module that may not exist yet.
Type hints enforce the contract before implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# These will exist soon — for now they're forward references for type hints
# from agent_seed.a2a.client import A2AClient
# from agent_seed.discovery.matcher import DiscoveryMatcher
# from agent_seed.payments.x402 import X402Payment
# from agent_seed.trust.did import DIDManager
# from agent_seed.trust.vc import VCIssuer

logger = logging.getLogger(__name__)


class AutonomousAgent:
    """
    An AI agent that can discover, pay, and transact with other agents
    using A2A, x402, and DIDs — all through a single import.
    """

    def __init__(
        self,
        did: str,
        private_key: str,
        registry_url: Optional[str] = None,
        bootstrap_nodes: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize an autonomous agent.

        Args:
            did: The agent's W3C DID (did:key:...)
            private_key: Ed25519 private key for signing and payments
            registry_url: Optional URL for a hosted discovery registry
            bootstrap_nodes: Optional libp2p multiaddrs for DHT discovery
        """
        self.did = did
        self.private_key = private_key
        self.registry_url = registry_url
        self.bootstrap_nodes = bootstrap_nodes or []

        # These will be initialized when modules are built
        self._discovery = None
        self._a2a_client = None
        self._payment = None
        self._vc_issuer = None

        logger.info(f"Agent initialized: {self.did}")

    # ------------------------------------------------------------------
    # Public API — what developers actually call
    # ------------------------------------------------------------------

    def send_task(
        self,
        capability: str,
        input_data: Dict[str, Any],
        max_price: str = "0.001",
        currency: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Find an agent with the given capability, negotiate terms, pay,
        and return a verified result with a VC receipt.

        This is the one-call experience the entire SDK exists to provide.

        Args:
            capability: What you need (e.g., "sentiment-analysis")
            input_data: The data to send to the remote agent
            max_price: Maximum price willing to pay, in currency units
            currency: Currency for payment (default USDC)

        Returns:
            Dict with keys:
                - artifact: The A2A artifact returned by the seller
                - receipt: A Verifiable Credential issued by the buyer
                - transaction: Payment proof from x402

        Raises:
            NotImplementedError: Until each module is built
        """
        # Step 1: Discover
        logger.info(f"Discovering agents for capability: {capability}")
        seller_card = self._discover(capability, max_price, currency)
        logger.info(f"Found seller: {seller_card.get('url', 'unknown')}")

        # Step 2: Send A2A task (will hit 402)
        logger.info("Sending A2A task...")
        task_response = self._send_a2a_task(seller_card, input_data)
        logger.info(f"Task status: {task_response.get('status', 'unknown')}")

        # Step 3: If 402, pay via x402 and resubmit
        if task_response.get("status") == "payment_required":
            logger.info("Payment required — paying via x402")
            payment_proof = self._pay_x402(
                seller_card, task_response["payment"]
            )
            logger.info("Payment sent — resubmitting task")
            task_response = self._resubmit_task(
                seller_card, input_data, payment_proof
            )

        # Step 4: Verify artifact signature
        logger.info("Verifying artifact signature...")
        artifact = self._verify_artifact(
            task_response["artifact"], seller_card
        )

        # Step 5: Issue VC receipt
        logger.info("Issuing VC receipt...")
        receipt = self._issue_receipt(
            seller_card, task_response, payment_proof
            if task_response.get("status") != "completed"
            else None
        )

        return {
            "artifact": artifact,
            "receipt": receipt,
            "transaction": payment_proof
            if "payment_proof" in locals()
            else None,
        }

    def publish_product(
        self,
        name: str,
        description: str,
        price: str,
        capability: str,
        currency: str = "USDC",
        endpoint: str = "",
        pay_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish a product or service to the agent discovery network.

        Args:
            name: Human-readable product name
            description: What the product does
            price: Price in currency units
            capability: Machine-readable capability name for discovery
            currency: Currency (default USDC)
            endpoint: URL where the agent serves A2A tasks
            pay_to: Wallet address for x402 payments

        Returns:
            Dict with publication details including IPFS CID

        Raises:
            NotImplementedError: Until discovery.publish is built
        """
        raise NotImplementedError("discovery.publish not built")

    def find_and_buy(
        self, product_name: str, max_price: str = "0.001"
    ) -> Dict[str, Any]:
        """
        Convenience method: search by human-readable name and buy.

        Args:
            product_name: Name to search for
            max_price: Maximum price to pay

        Returns:
            Same as send_task result dict

        Raises:
            NotImplementedError: Until discovery.search is built
        """
        raise NotImplementedError("discovery.search not built")

    # ------------------------------------------------------------------
    # Internal methods — each delegates to a module that may not exist
    # ------------------------------------------------------------------

    def _discover(
        self, capability: str, max_price: str, currency: str
    ) -> Dict[str, Any]:
        """
        Find an agent offering the given capability within budget.

        Delegates to discovery.matcher.DiscoveryMatcher
        """
        raise NotImplementedError("discovery.matcher.DiscoveryMatcher not built")

    def _send_a2a_task(
        self, seller_card: Dict[str, Any], input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send an A2A task to a seller's service endpoint.

        Delegates to a2a.client.A2AClient
        """
        raise NotImplementedError("a2a.client.A2AClient not built")

    def _pay_x402(
        self, seller_card: Dict[str, Any], payment_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pay the 402 invoice and return proof of payment.

        Delegates to payments.x402.X402Payment
        """
        raise NotImplementedError("payments.x402.X402Payment not built")

    def _resubmit_task(
        self,
        seller_card: Dict[str, Any],
        input_data: Dict[str, Any],
        payment_proof: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resubmit the A2A task with payment proof in headers.

        Delegates to a2a.client.A2AClient
        """
        raise NotImplementedError(
            "a2a.client.A2AClient resubmit not built"
        )

    def _verify_artifact(
        self,
        artifact: Dict[str, Any],
        seller_card: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Verify the artifact's signature against the seller's DID.

        Delegates to trust.did.DIDManager
        """
        raise NotImplementedError("trust.did.DIDManager not built")

    def _issue_receipt(
        self,
        seller_card: Dict[str, Any],
        task_response: Dict[str, Any],
        payment_proof: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Issue a Verifiable Credential as proof of transaction completion.

        Delegates to trust.vc.VCIssuer
        """
        raise NotImplementedError("trust.vc.VCIssuer not built")


# ------------------------------------------------------------------
# Quick self-test when run directly
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing AutonomousAgent initialization...")

    agent = AutonomousAgent(
        did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        private_key="test-key-not-real",
    )

    print(f"✅ Agent initialized with DID: {agent.did}")

    print("\nAttempting send_task() — expected to fail with NotImplementedError:")
    try:
        agent.send_task(
            capability="sentiment-analysis",
            input_data={"text": "Hello world"},
        )
    except NotImplementedError as e:
        print(f"✅ Correctly raised: {e}")
        print(
            "→ This is the todo list. Each error is a module waiting to be built."
        )
```
