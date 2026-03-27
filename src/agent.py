"""OTA-specific agent using three-stage retrieval pipeline."""

import os
import json
from typing import Optional, Dict, List
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv
from .knowledge_base import (
    OTAKnowledgeBase,
    OTADeploymentPattern,
    ECUType,
    SafetyClass,
    DeploymentMode
)

load_dotenv()


@dataclass
class AgentResponse:
    """Response from OTA agent"""
    message: str
    deployment_spec: Optional[Dict] = None
    retrieved_patterns: Optional[List[tuple]] = None  # (pattern, score, breakdown)
    validation_results: Optional[Dict] = None
    is_valid: bool = False


class DSLAgent:
    """Agent for generating OTA deployment specifications"""
    
    def __init__(self, model: str = "gpt-4o-2024-08-06"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.kb = OTAKnowledgeBase()
        self.conversation_history = []
        
        self.system_prompt = """You are an expert system for generating OTA (Over-The-Air) update deployment specifications for automotive ECUs.

Your role:
1. Understand OTA update requirements from user queries
2. Use retrieved OTA patterns that match ECU type, safety class, region, and version
3. Generate COMPLETE and VALID deployment specifications following schema rules EXACTLY
4. Ensure safety-critical requirements are met for all ASIL-rated systems
5. Include rollback procedures and verification steps

CRITICAL REQUIREMENTS:
- ALWAYS generate a complete deployment_spec with ALL required sections
- deployment_spec MUST include: update_package, pre_conditions, installation, post_conditions
- Use the retrieved pattern as a TEMPLATE and adapt it to the user's requirements
- Preserve ALL safety-critical fields from the pattern
- For ASIL-A/B/C/D: Include safety_validation in post_conditions
- For ASIL-B/C/D: Include rollback capability (backup_current, keep_backup_bank, or dual-bank)
- For ASIL-C/D: Require battery_level_min >= 85%
- For ALL updates: Include verify_boot and run_diagnostics in post_conditions

Output Format:
Respond with valid JSON:
{
    "message": "conversational response explaining what was generated",
    "needs_clarification": boolean,
    "clarification_questions": ["questions if needed"],
    "deployment_spec": {
        "update_package": {
            "name": "package_name_vX.Y.Z",
            "size_mb": number,
            "checksum": "sha256:...",
            "signature": "RSA2048:...",
            "compression": "zstd|lzma|bsdiff",
            ... (other fields from pattern)
        },
        "pre_conditions": {
            "battery_level_min": number,
            "vehicle_state": "parked|parked_engine_off",
            "network_available": true,
            ... (other checks based on safety class)
        },
        "installation": {
            "target_partition": "partition_B|bank_1",
            "backup_current": true,
            "verify_integrity": true,
            "reboot_required": true,
            ... (other installation steps)
        },
        "post_conditions": {
            "verify_boot": true,
            "run_diagnostics": true,
            "report_telemetry": true,
            "safety_validation": true (for ASIL),
            ... (other validation steps)
        }
    }
}

VALIDATION RULES:
- NEVER omit required fields from the retrieved pattern
- ALWAYS include safety_validation for ASIL systems
- ALWAYS include backup/rollback capability
- Match the structure of the retrieved pattern EXACTLY
- Adapt values (like version numbers, sizes) to match the user request
- For multi-ECU updates, coordinate installation and verification steps"""
        
        self._initialize_conversation()
    
    def _initialize_conversation(self):
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]
    
    def _build_ota_context(
        self,
        patterns: List[tuple],
        query: str
    ) -> str:
        """Build context from retrieved OTA patterns"""
        if not patterns:
            return ""
        
        context = "\n\n# Retrieved OTA Patterns (Metadata Filtered + Semantically Ranked):\n\n"
        
        for i, (pattern, score, breakdown) in enumerate(patterns, 1):
            context += f"## Pattern {i}: {pattern.name}\n"
            context += f"**Composite Score:** {breakdown['composite']:.3f}\n"
            context += f"- Semantic: {breakdown['semantic']:.3f}\n"
            context += f"- Schema: {breakdown['schema']:.3f}\n"
            context += f"- Recency: {breakdown['recency']:.3f}\n"
            context += f"- Validation: {breakdown['validation']:.3f}\n\n"
            
            context += f"**Metadata:**\n"
            context += f"- Device: {pattern.metadata.device_type.value}\n"
            context += f"- Version: {pattern.metadata.sw_version}\n"
            context += f"- Safety: {pattern.metadata.safety_class.value}\n"
            context += f"- Region: {pattern.metadata.region}\n"
            context += f"- Mode: {pattern.metadata.deployment_mode.value}\n\n"
            
            context += f"**Deployment Spec Template:**\n"
            context += f"```json\n{json.dumps(pattern.deployment_spec, indent=2)}\n```\n\n"
            
            context += f"**Schema Fields (MUST follow):**\n"
            for field in pattern.schema_fields:
                context += f"- {field.name}: {field.field_type}, required={field.required}\n"
                if field.validation_pattern:
                    context += f"  Pattern: {field.validation_pattern}\n"
            
            context += f"\n**Validation Rules:**\n"
            for rule in pattern.validation_rules:
                context += f"- {rule}\n"
            
            context += f"\n**Rollback:** {pattern.rollback_procedure}\n\n"
            context += f"**Best Practices:**\n"
            for bp in pattern.best_practices:
                context += f"- {bp}\n"
            
            context += "\n---\n\n"
        
        return context
    
    def chat(
        self,
        user_message: str,
        device_type: ECUType,
        sw_version: str,
        safety_class: SafetyClass,
        region: str,
        hardware_revision: str,
        deployment_mode: Optional[DeploymentMode] = None,
        required_capabilities: Optional[set] = None
    ) -> AgentResponse:
        """Chat with metadata-filtered retrieval"""
        
        # Three-stage retrieval
        retrieved_patterns = self.kb.retrieve_ota_patterns(
            query=user_message,
            device_type=device_type,
            sw_version=sw_version,
            safety_class=safety_class,
            region=region,
            hardware_revision=hardware_revision,
            deployment_mode=deployment_mode,
            required_capabilities=required_capabilities,
            top_k=2
        )
        
        if not retrieved_patterns:
            return AgentResponse(
                message=f"No compatible OTA patterns found for {device_type.value} with safety class {safety_class.value}",
                retrieved_patterns=[]
            )
        
        # Build context
        ota_context = self._build_ota_context(retrieved_patterns, user_message)
        enhanced_message = ota_context + f"\n\n# User Request:\n{user_message}"
        
        # Add to conversation
        self.conversation_history.append({
            "role": "user",
            "content": enhanced_message
        })
        
        # Get LLM response
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=0.3,  # Lower for deterministic OTA specs
                response_format={"type": "json_object"}
            )
        except Exception as e:
            if "response_format" in str(e):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    temperature=0.3
                )
            else:
                raise e
        
        assistant_message = response.choices[0].message.content
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Parse response
        try:
            response_data = json.loads(assistant_message)
        except json.JSONDecodeError:
            return AgentResponse(
                message="Error parsing response",
                retrieved_patterns=retrieved_patterns
            )
        
        return AgentResponse(
            message=response_data.get("message", ""),
            deployment_spec=response_data.get("deployment_spec"),
            retrieved_patterns=retrieved_patterns,
            is_valid=True if response_data.get("deployment_spec") else False
        )