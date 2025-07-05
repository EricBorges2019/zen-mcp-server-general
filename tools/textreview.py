"""
TextReview tool - Step-by-step text document review with systematic investigation

This tool provides a structured workflow for comprehensive text document review and critique.
It guides the CLI agent through systematic investigation steps with forced pauses between each step
to ensure thorough document examination, quality assessment, and improvement identification.
The tool supports complex review scenarios including content accuracy, argument strength,
clarity assessment, and style evaluation.

Key features:
- Step-by-step document review workflow with progress tracking
- Context-aware file embedding for text documents (markdown, txt, etc.)
- Automatic issue and improvement tracking with categorization
- Expert analysis integration with external models for collaborative text review
- Support for focused review (content, structure, clarity, arguments, style)
- Confidence-based workflow optimization for comprehensive feedback
"""

import logging
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from systemprompts import TEXT_REVIEW_PROMPT
from tools.shared.base_models import WorkflowRequest

from .workflow.base import WorkflowTool

logger = logging.getLogger(__name__)

# Tool-specific field descriptions for text review workflow
TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS = {
    "step": (
        "Describe what you're currently investigating for text review by thinking deeply about the document content, structure, and effectiveness. "
        "In step 1, clearly state your review plan and begin forming a systematic approach after thinking carefully about what needs to be evaluated. "
        "You must begin by passing the file path for the initial text you are about to review in relevant_files. "
        "CRITICAL: Remember to thoroughly examine content quality, argument strength, clarity, readability, and structural coherence. "
        "Consider not only obvious issues and weaknesses but also opportunities for improvement, ways to strengthen arguments, "
        "areas where clarity could be enhanced, and methods to improve overall effectiveness while maintaining the author's voice and intent. "
        "Map out the document structure, understand the main arguments, and identify areas requiring deeper analysis."
    ),
    "step_number": (
        "The index of the current step in the text review sequence, beginning at 1. Each step should build upon or "
        "revise the previous one."
    ),
    "total_steps": (
        "Your current estimate for how many steps will be needed to complete the text review. "
        "Adjust as new findings emerge."
    ),
    "next_step_required": (
        "Set to true if you plan to continue the investigation with another step. False means you believe the text review analysis is complete and ready for expert validation."
    ),
    "findings": (
        "Summarize everything discovered in this step about the text being reviewed. Include analysis of content quality, argument strength, "
        "clarity issues, structural coherence, readability factors, and audience appropriateness. Be specific and avoid vague language—document what you now know about the text and how it affects your assessment. "
        "IMPORTANT: Document both positive findings (strong arguments, clear writing, effective structure) and areas for improvement "
        "(weak passages, unclear arguments, structural issues, style problems). In later steps, confirm or update past findings with additional evidence."
    ),
    "relevant_files": (
        "For when this is the first step, please pass absolute file paths of relevant text to review (do not clip file paths). "
        "When used for the final step, this contains a subset of files_checked (as full absolute paths) that contain text directly relevant to the review "
        "or contain significant issues, patterns, or examples worth highlighting. Only list those that are directly tied to important findings, "
        "content concerns, structural issues, or improvement opportunities."
    ),
    "issues_found": (
        "List of text issues identified during the investigation. Each issue should be a dictionary with 'severity' (critical, high, medium, low) and 'description' fields. "
        "Include unclear passages, weak arguments, structural problems, style inconsistencies, factual concerns, readability issues, etc."
    ),
    "review_type": (
        "Type of review to perform (comprehensive, content, structure, clarity, style)"
    ),
    "standards": (
        "Writing standards or style guide to enforce during the review"
    ),
}


class TextReviewRequest(WorkflowRequest):
    """Request model for Text Review workflow tool"""

    step: str = Field(..., description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["step"])
    step_number: int = Field(..., ge=1, description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["step_number"])
    total_steps: int = Field(..., ge=1, description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["total_steps"])
    next_step_required: bool = Field(..., description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["next_step_required"])
    findings: str = Field(..., description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["findings"])

    # Review tracking fields
    files_checked: Optional[list[str]] = Field(default_factory=list, description="List all files (as absolute paths, do not clip or shrink file names) examined during the text review investigation so far.")
    relevant_files: Optional[list[str]] = Field(default_factory=list, description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["relevant_files"])
    relevant_context: Optional[list[str]] = Field(default_factory=list, description="Key themes/sections identified as central to the review")
    issues_found: Optional[list[dict[str, Any]]] = Field(default_factory=list, description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["issues_found"])

    # Review configuration
    review_type: Literal["comprehensive", "content", "structure", "clarity", "style"] = Field(
        default="comprehensive", description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["review_type"]
    )
    severity_filter: Literal["critical", "high", "medium", "low", "all"] = Field(
        default="all", description="Minimum severity level to report on the issues found"
    )
    standards: Optional[str] = Field(default=None, description=TEXT_REVIEW_WORKFLOW_FIELD_DESCRIPTIONS["standards"])

    # Workflow control
    confidence: Literal["exploring", "low", "medium", "high", "very_high", "almost_certain", "certain"] = Field(
        default="exploring",
        description=(
            "Indicate your current confidence in the text review assessment. Use: 'exploring' (starting analysis), 'low' (early investigation), "
            "'medium' (some evidence gathered), 'high' (strong evidence), 'very_high' (very strong evidence), 'almost_certain' (nearly complete review), "
            "'certain' (100% confidence - text review is thoroughly complete and all significant issues are identified with no need for external model validation). "
            "Do NOT use 'certain' unless the text review is comprehensively complete, use 'very_high' or 'almost_certain' instead if not 100% sure."
        ),
    )
    backtrack_from_step: Optional[int] = Field(
        default=None,
        ge=1,
        description="If an earlier finding or assessment needs to be revised or discarded, specify the step number from which to start over.",
    )


class TextReviewTool(WorkflowTool):
    """
    Text document review tool for comprehensive quality assessment using WorkflowTool architecture.

    Provides step-by-step review workflow for text documents including content quality,
    argument strength, clarity, structure, and style evaluation.
    """

    def __init__(self):
        super().__init__()
        self.initial_request = None
        self.review_config = {}

    def get_name(self) -> str:
        return "textreview"

    def get_description(self) -> str:
        return (
            "TEXT REVIEW WORKFLOW - Step-by-step text document review with systematic investigation. "
            "This tool guides you through a systematic investigation process where you:\n\n"
            "1. Start with step 1: describe your text review investigation plan\n"
            "2. STOP and investigate document quality, arguments, and structure\n"
            "3. Report findings in step 2 with concrete evidence from actual review\n"
            "4. Continue investigating between each step\n"
            "5. Track findings, relevant files, and issues throughout\n"
            "6. Update assessments as understanding evolves\n"
            "7. Once investigation is complete, receive expert validation\n\n"
            "Perfect for: text quality assessment, argument analysis, structural review, "
            "style evaluation, improvement identification."
        )

    def get_system_prompt(self) -> str:
        return TEXT_REVIEW_PROMPT

    def get_request_model(self):
        return TextReviewRequest

    @property
    def model_category(self) -> "ToolModelCategory":
        """Text review works well with reasoning and analytical models"""
        return "reasoning"

    def should_embed_files_as_context(self, request: TextReviewRequest) -> bool:
        """
        Determine if files should be embedded as context for text review.

        For text review, we want to embed files when:
        - It's step 1 and we're setting up the review
        - We have specific files to review in relevant_files
        - Review type requires full content examination
        """
        if request.step_number == 1:
            return True

        # Embed if we have specific relevant files for this step
        if request.relevant_files:
            return True

        # For comprehensive review types, usually want full content
        if request.review_type in ["comprehensive", "content", "structure"]:
            return True

        return False

    def get_required_actions(self, request: TextReviewRequest) -> list[str]:
        """Generate step-specific investigation actions for text review."""
        actions = []

        if request.step_number == 1:
            actions.extend([
                "Use Read tool to examine the text document(s) specified in relevant_files",
                "Assess overall document quality and structure",
                "Identify potential issues and improvement opportunities",
                "Evaluate argument strength and clarity"
            ])
        else:
            actions.extend([
                "Continue investigating specific quality aspects identified in previous steps",
                "Use Read tool to examine problem areas or related sections",
                "Gather concrete evidence for review assessments",
                "Build comprehensive quality evaluation"
            ])

        return actions

    def should_call_expert_analysis(self, request: TextReviewRequest) -> bool:
        """Determine if expert analysis should be called based on confidence level."""
        return request.confidence != "certain"

    def prepare_expert_analysis_context(self, request: TextReviewRequest) -> str:
        """Prepare context for expert analysis of text review findings."""
        context_parts = [
            f"TEXT REVIEW REQUEST - {request.review_type.upper()}",
            f"Review confidence: {request.confidence}",
            f"Step {request.step_number} of {request.total_steps}",
            "",
            "REVIEW FINDINGS:",
            request.findings,
        ]

        if request.issues_found:
            context_parts.extend([
                "",
                "ISSUES IDENTIFIED:",
                *[f"- {issue}" for issue in request.issues_found],
            ])

        return "\n".join(context_parts)

    def prepare_prompt(self, request: TextReviewRequest) -> str:
        """Prepare the review prompt."""
        return request.step
