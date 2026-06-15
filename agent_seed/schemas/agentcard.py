"""
agent_seed/schemas/agentcard.py

Pydantic models for the AgentCard JSON-LD schema with x402 payment extension.
This is what discovery.matcher returns and what publish_product() validates against.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, HttpUrl, Field, field_validator


class PaymentPolicy(BaseModel):
    """x402 payment extension for AgentCard — not in core A2A spec."""

    currency: str = Field(default="USDC", description="Payment currency")
    network: str = Field(default="base", description="Blockchain network")
    price: str = Field(..., description="Price per task in currency units")
    pay_to: str = Field(
        ..., description="Wallet address receiving x402 payments"
    )
    x402_endpoint: Optional[HttpUrl] = Field(
        default=None, description="Dedicated x402 endpoint if different from serviceEndpoint"
    )
    batching_supported: bool = Field(
        default=False, description="Whether sub-$0.0001 batch payments are supported"
    )
    min_batch_fee: Optional[str] = Field(
        default=None, description="Minimum batch fee if batching is supported"
    )


class TaskType(BaseModel):
    """A capability this agent offers."""

    name: str = Field(..., description="Machine-readable capability name")
    description: str = Field(
        ..., description="Human-readable description"
    )
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for input"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for output"
    )


class CapabilitySet(BaseModel):
    """Collection of task types offered by the agent."""

    task_types: List[TaskType] = Field(
        default_factory=list, description="List of supported task types"
    )


class SecurityPolicy(BaseModel):
    """Security configuration for DID and VC verification."""

    did_document: Optional[Dict[str, Any]] = Field(
        default=None, description="DID document for the agent"
    )
    verification_method: Optional[str] = Field(
        default=None, description="Key ID used for signing artifacts"
    )
    supported_vc_types: List[str] = Field(
        default_factory=lambda: [
            "VerifiableReceipt",
            "QualityScore",
            "DisputeRecord",
        ],
        description="VC types this agent issues and accepts",
    )


class Organization(BaseModel):
    """Provider information."""

    name: str = Field(..., description="Organization or agent name")


class AgentCard(BaseModel):
    """
    A2A AgentCard with x402 payment extension.

    This is the machine-readable descriptor every agent publishes to the DHT.
    Compliant with A2A spec's AgentCard structure, extended with payment and
    security blocks that the agent-seed SDK understands.
    """

    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="What this agent does")
    url: HttpUrl = Field(
        ..., description="Public URL for this agent or its documentation"
    )
    provider: Organization = Field(
        ..., description="Organization or entity behind this agent"
    )
    service_endpoint: HttpUrl = Field(
        ..., description="A2A task endpoint (HTTP+JSON binding)"
    )
    capabilities: CapabilitySet = Field(
        default_factory=CapabilitySet,
        description="Task types this agent supports",
    )
    payment: Optional[PaymentPolicy] = Field(
        default=None,
        description="x402 payment policy — agent-seed extension",
    )
    security: Optional[SecurityPolicy] = Field(
        default=None,
        description="Security and verification policy",
    )
    version: str = Field(
        default="1.0.0", description="AgentCard schema version"
    )
    did: Optional[str] = Field(
        default=None, description="Agent's DID for identity verification"
    )

    @field_validator("version")
    @classmethod
    def version_must_be_semver(cls, v: str) -> str:
        """Validate version string is semver-like."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be semver (e.g., 1.0.0)")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version part '{part}' must be numeric")
        return v

    def model_dump_jsonld(self) -> Dict[str, Any]:
        """
        Export as JSON-LD compatible dict with @context.

        Returns:
            Dict ready for JSON-LD serialization
        """
        data = self.model_dump(mode="json", exclude_none=True)

        # Add JSON-LD context
        jsonld = {
            "@context": {
                "@vocab": "https://a2a-protocol.org/ns#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "payment": "https://x402.org/ns#",
                "security": "https://w3id.org/security#",
                "cred": "https://www.w3.org/2018/credentials#",
            },
            **data,
        }

        return jsonld


# ------------------------------------------------------------------
# Factory functions for common agent types
# ------------------------------------------------------------------

def create_seller_agent_card(
    name: str,
    description: str,
    url: str,
    service_endpoint: str,
    provider_name: str,
    capability_name: str,
    capability_description: str,
    price: str,
    pay_to: str,
    did: Optional[str] = None,
    currency: str = "USDC",
    network: str = "base",
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
) -> AgentCard:
    """
    Factory for a typical seller agent card with one capability and x402 payment.

    Args:
        name: Agent name
        description: What the agent does
        url: Documentation or homepage URL
        service_endpoint: A2A task endpoint
        provider_name: Organization name
        capability_name: Machine-readable capability (e.g., "sentiment-analysis")
        capability_description: Human-readable capability description
        price: Price in currency units
        pay_to: Wallet address for payments
        did: Optional DID for identity
        currency: Payment currency
        network: Blockchain network
        input_schema: JSON Schema for capability input
        output_schema: JSON Schema for capability output

    Returns:
        Configured AgentCard ready for publication
    """
    return AgentCard(
        name=name,
        description=description,
        url=HttpUrl(url),
        provider=Organization(name=provider_name),
        service_endpoint=HttpUrl(service_endpoint),
        capabilities=CapabilitySet(
            task_types=[
                TaskType(
                    name=capability_name,
                    description=capability_description,
                    input_schema=input_schema or {},
                    output_schema=output_schema or {},
                )
            ]
        ),
        payment=PaymentPolicy(
            currency=currency,
            network=network,
            price=price,
            pay_to=pay_to,
        ),
        security=SecurityPolicy() if did else None,
        did=did,
    )


# ------------------------------------------------------------------
# Self-test
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing AgentCard schema...\n")

    # Create a sample seller card using the factory
    card = create_seller_agent_card(
        name="Sentiment Analysis Agent",
        description="Analyzes text sentiment with confidence scores",
        url="https://example-agent.com",
        service_endpoint="https://example-agent.com/a2a",
        provider_name="ML Services Inc.",
        capability_name="sentiment-analysis",
        capability_description="Returns positive/negative/neutral with 0-1 confidence",
        price="0.001",
        pay_to="0x1234567890abcdef",
        did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
    )

    print("✅ AgentCard created successfully")
    print(f"   Name: {card.name}")
    print(f"   Capability: {card.capabilities.task_types[0].name}")
    print(f"   Price: {card.payment.price} {card.payment.currency}")
    print(f"   Pay to: {card.payment.pay_to}")

    # Validate JSON-LD export
    jsonld = card.model_dump_jsonld()
    print(f"\n✅ JSON-LD export: {len(jsonld)} top-level keys")
    print(f"   @context present: {'@context' in jsonld}")

    # Validate the factory output is a valid AgentCard
    validated = AgentCard(**card.model_dump())
    print(f"\n✅ Re-validation passed: {validated.name}")

    print("\n→ AgentCard schema ready. Next: plug it into discovery.matcher")
