"""
NL2DSL Agent - Natural Language to DSL Generation for OTA Updates
"""

from .agent import DSLAgent, AgentResponse
from .knowledge_base import (
    OTAKnowledgeBase,
    OTADeploymentPattern,
    OTAMetadata,
    SchemaField,
    ECUType,
    SafetyClass,
    DeploymentMode
)
from .ota_test_dataset import OTATestDatasetGenerator, OTATestCase
from .ota_metrics_evaluator import OTAMetricsEvaluator, OTATestResult, OTAMetricsReport

__version__ = "1.0.0"
__all__ = [
    "DSLAgent",
    "AgentResponse",
    "OTAKnowledgeBase",
    "OTADeploymentPattern",
    "OTAMetadata",
    "SchemaField",
    "ECUType",
    "SafetyClass",
    "DeploymentMode",
    "OTATestDatasetGenerator",
    "OTATestCase",
    "OTAMetricsEvaluator",
    "OTATestResult",
    "OTAMetricsReport",
]
