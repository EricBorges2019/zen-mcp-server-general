"""
TextRefactor tool - Step-by-step text restructuring and improvement with systematic investigation

This tool provides a structured workflow for comprehensive text document refactoring and reorganization.
It guides the CLI agent through systematic investigation steps with forced pauses between each step
to ensure thorough document examination, structure assessment, and improvement identification.
The tool supports complex refactoring scenarios including content reorganization, clarity enhancement,
argument strengthening, and style consistency improvements.

Key features:
- Step-by-step document refactoring workflow with progress tracking  
- Context-aware file embedding for text documents (markdown, txt, etc.)
- Automatic improvement opportunity tracking with categorization
- Expert analysis integration with external models for collaborative text restructuring
- Support for focused refactoring (organization, clarity, arguments, style, flow)
- Confidence-based workflow optimization for comprehensive text improvements
"""

import logging
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from systemprompts import TEXT_REFACTOR_PROMPT
from tools.shared.base_models import WorkflowRequest

from .workflow.base import WorkflowTool

logger = logging.getLogger(__name__)

# Tool-specific field descriptions for text refactor workflow
TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS = {
    "step": (
        "Describe what you're currently investigating for text refactoring by thinking deeply about the document structure, flow, and improvement opportunities. "
        "In step 1, clearly state your refactoring investigation plan and begin forming a systematic approach after thinking carefully about what needs to be improved. "
        "CRITICAL: Remember to thoroughly examine content organization, clarity issues, argument flow, readability concerns, and structural patterns. "
        "Consider not only obvious issues and reorganization needs but also opportunities for better organization, ways to improve clarity and flow, "
        "areas where arguments could be strengthened, and methods to enhance overall coherence while maintaining the author's voice and intent. "
        "Map out the document structure, understand the content flow, and identify areas requiring refactoring."
    ),
    "step_number": (
        "The index of the current step in the text refactoring investigation sequence, beginning at 1. Each step should build upon or "
        "revise the previous one."
    ),
    "total_steps": (
        "Your current estimate for how many steps will be needed to complete the text refactoring investigation. "
        "Adjust as new opportunities emerge."
    ),
    "next_step_required": (
        "Set to true if you plan to continue the investigation with another step. False means you believe the text refactoring analysis is complete and ready for expert validation."
    ),
    "findings": (
        "Summarize everything discovered in this step about refactoring opportunities in the text. Include analysis of organization issues, "
        "clarity problems, flow disruptions, argument weaknesses, structural patterns, and improvement possibilities. Be specific and avoid vague language—document what you now know about the text and how it could be improved. "
        "IMPORTANT: Document both positive aspects (strong sections, clear arguments, good organization) and improvement opportunities "
        "(confusing sections, weak flow, organizational problems, clarity issues). In later steps, confirm or update past findings with additional evidence."
    ),
    "relevant_files": (
        "Subset of files_checked (as full absolute paths) that contain text requiring refactoring or are directly relevant to the refactoring opportunities identified. "
        "Only list those that are directly tied to specific refactoring opportunities, organizational issues, clarity problems, or improvement areas."
    ),
    "issues_found": (
        "List of refactoring opportunities identified during the investigation. Each opportunity should be a dictionary with 'severity' (critical, high, medium, low), "
        "'type' (organization, clarity, arguments, style, flow), and 'description' fields. Include organizational issues, clarity problems, "
        "argument weaknesses, flow disruptions, style inconsistencies, etc."
    ),
    "refactor_type": (
        "Type of refactoring analysis to perform (organization, clarity, arguments, style, flow)"
    ),
}


class TextRefactorRequest(WorkflowRequest):
    """Request model for Text Refactor workflow tool"""

    step: str = Field(..., description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["step"])
    step_number: int = Field(..., ge=1, description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["step_number"])
    total_steps: int = Field(..., ge=1, description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["total_steps"])
    next_step_required: bool = Field(..., description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["next_step_required"])
    findings: str = Field(..., description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["findings"])

    # Refactoring tracking fields
    files_checked: Optional[list[str]] = Field(default_factory=list, description="List all files (as absolute paths, do not clip or shrink file names) examined during the text refactoring investigation so far.")
    relevant_files: Optional[list[str]] = Field(default_factory=list, description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["relevant_files"])
    relevant_context: Optional[list[str]] = Field(default_factory=list, description="Key sections/themes identified as central to the refactoring")
    issues_found: Optional[list[dict[str, Any]]] = Field(default_factory=list, description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["issues_found"])

    # Refactoring configuration
    refactor_type: Literal["organization", "clarity", "arguments", "style", "flow"] = Field(
        default="organization", description=TEXT_REFACTOR_WORKFLOW_FIELD_DESCRIPTIONS["refactor_type"]
    )
    focus_areas: Optional[list[str]] = Field(
        default_factory=list, description="Specific areas to focus on (e.g., 'introduction', 'conclusion', 'main arguments', 'transitions')"
    )
    style_guide_examples: Optional[list[str]] = Field(
        default_factory=list,
        description="Optional existing text files to use as style/pattern reference (must be FULL absolute paths to real files / folders - DO NOT SHORTEN). These files represent the target writing style and patterns for the document.",
    )

    # Workflow control
    confidence: Literal["exploring", "incomplete", "partial", "complete"] = Field(
        default="incomplete",
        description=(
            "Indicate your current confidence in the text refactoring analysis completeness. Use: 'exploring' (starting analysis), "
            "'incomplete' (just started or significant work remaining), 'partial' (some refactoring opportunities identified but more analysis needed), "
            "'complete' (comprehensive refactoring analysis finished with all major opportunities identified and the CLI agent can handle 100% confidently without help). "
            "Use 'complete' ONLY when you have fully analyzed all text, identified all significant refactoring opportunities, and can provide comprehensive recommendations without expert assistance."
        ),
    )
    backtrack_from_step: Optional[int] = Field(
        default=None,
        ge=1,
        description="If an earlier finding or assessment needs to be revised or discarded, specify the step number from which to start over.",
    )


class TextRefactorTool(WorkflowTool):
    """
    Text document refactoring tool for comprehensive improvement analysis using WorkflowTool architecture.

    Provides step-by-step refactoring workflow for text documents including organization,
    clarity, argument strength, style, and flow improvements.
    """

    def __init__(self):
        super().__init__()
        self.initial_request = None
        self.refactor_config = {}

    def get_name(self) -> str:
        return "textrefactor"

    def get_description(self) -> str:
        return (
            "TEXT REFACTORING WORKFLOW - Step-by-step text document refactoring with systematic investigation. "
            "This tool guides you through a systematic investigation process where you:\n\n"
            "1. Start with step 1: describe your text refactoring investigation plan\n"
            "2. STOP and investigate document structure and improvement opportunities\n"
            "3. Report findings in step 2 with concrete evidence from actual analysis\n"
            "4. Continue investigating between each step\n"
            "5. Track findings, relevant files, and refactoring opportunities throughout\n"
            "6. Update assessments as understanding evolves\n"
            "7. Once investigation is complete, receive expert validation\n\n"
            "Perfect for: text organization improvement, clarity enhancement, argument strengthening, "
            "style consistency, flow optimization."
        )

    def get_system_prompt(self) -> str:
        return TEXT_REFACTOR_PROMPT

    def get_request_model(self):
        return TextRefactorRequest

    @property
    def model_category(self) -> "ToolModelCategory":
        """Text refactoring works well with reasoning and creative models"""
        return "reasoning"

    def should_embed_files_as_context(self, request: TextRefactorRequest) -> bool:
        """
        Determine if files should be embedded as context for text refactoring.

        For text refactoring, we want to embed files when:
        - It's step 1 and we're setting up the refactoring analysis
        - We have specific files to refactor in relevant_files
        - Refactor type requires full content examination
        - We have style guide examples to reference
        """
        if request.step_number == 1:
            return True

        # Embed if we have specific relevant files for this step
        if request.relevant_files:
            return True

        # Embed style guide examples when available
        if request.style_guide_examples:
            return True

        # For comprehensive refactor types, usually want full content
        if request.refactor_type in ["organization", "clarity", "arguments"]:
            return True

        return False

    def get_required_actions(self, request: TextRefactorRequest) -> list[str]:
        """Generate step-specific investigation actions for text refactoring."""
        actions = []

        if request.step_number == 1:
            actions.extend([
                "Use Read tool to examine the text document(s) specified in relevant_files",
                "Analyze document organization and structure patterns",
                "Identify areas needing refactoring and improvement",
                "Map out potential reorganization strategies"
            ])
        else:
            actions.extend([
                "Continue investigating specific refactoring opportunities identified in previous steps",
                "Use Read tool to examine problematic sections or style examples",
                "Gather concrete evidence for refactoring recommendations",
                "Build comprehensive improvement strategy"
            ])

        return actions

    def should_call_expert_analysis(self, request: TextRefactorRequest) -> bool:
        """Determine if expert analysis should be called based on confidence level."""
        return request.confidence != "complete"

    def prepare_expert_analysis_context(self, request: TextRefactorRequest) -> str:
        """Prepare context for expert analysis of text refactoring findings."""
        context_parts = [
            f"TEXT REFACTORING REQUEST - {request.refactor_type.upper()}",
            f"Refactoring confidence: {request.confidence}",
            f"Step {request.step_number} of {request.total_steps}",
            "",
            "REFACTORING FINDINGS:",
            request.findings,
        ]

        if request.issues_found:
            context_parts.extend([
                "",
                "REFACTORING OPPORTUNITIES:",
                *[f"- {issue}" for issue in request.issues_found],
            ])

        if request.focus_areas:
            context_parts.extend([
                "",
                "FOCUS AREAS:",
                *[f"- {area}" for area in request.focus_areas],
            ])

        return "\n".join(context_parts)

    def prepare_prompt(self, request: TextRefactorRequest) -> str:
        """Prepare the refactoring prompt."""
        return request.step
