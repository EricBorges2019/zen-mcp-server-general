"""
TextAnalyze tool - Step-by-step text document analysis with systematic investigation

This tool provides a structured workflow for comprehensive text document analysis.
It guides the CLI agent through systematic investigation steps with forced pauses between each step
to ensure thorough document examination, content pattern identification, and structural assessment.
The tool supports complex analysis scenarios including content structure review, readability analysis,
thematic assessment, and argumentative evaluation.

Key features:
- Step-by-step document analysis workflow with progress tracking
- Context-aware file embedding for text documents (markdown, txt, etc.)
- Automatic theme and argument tracking with categorization
- Expert analysis integration with external models for collaborative text review
- Support for focused analysis (structure, themes, arguments, style, readability)
- Confidence-based workflow optimization for text-specific insights
"""

import logging
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from systemprompts import TEXT_ANALYZE_PROMPT
from tools.shared.base_models import WorkflowRequest

from .workflow.base import WorkflowTool

logger = logging.getLogger(__name__)

# Tool-specific field descriptions for text analyze workflow
TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS = {
    "step": (
        "What to analyze or look for in this step. In step 1, describe what you want to analyze about the text document(s) and begin forming "
        "an analytical approach after thinking carefully about what needs to be examined. Consider content structure, "
        "thematic elements, argumentative patterns, writing style, and readability. Map out the document structure, "
        "understand the main arguments, and identify areas requiring deeper textual analysis. In later steps, continue "
        "exploring with precision and adapt your understanding as you uncover more insights about the text."
    ),
    "step_number": (
        "The index of the current step in the text analysis sequence, beginning at 1. Each step should build upon or "
        "revise the previous one."
    ),
    "total_steps": (
        "Your current estimate for how many steps will be needed to complete the text analysis. "
        "Adjust as new findings emerge."
    ),
    "next_step_required": (
        "Set to true if you plan to continue the investigation with another step. False means you believe the text analysis is complete and ready for expert validation."
    ),
    "findings": (
        "Summarize everything discovered in this step about the text documents being analyzed. Include analysis of content structure, thematic patterns, "
        "argumentative strategies, writing style, readability factors, audience considerations, and strategic improvement opportunities for the text. "
        "Be specific and avoid vague language—document what you now know about the text and how it affects your assessment. "
        "IMPORTANT: Document both strengths (clear arguments, good structure, effective communication) and areas for improvement "
        "(unclear passages, weak arguments, structural issues, style inconsistencies). In later steps, confirm or update past findings with additional evidence."
    ),
    "relevant_files": (
        "Subset of files_checked (as full absolute paths) that contain text directly relevant to the analysis or contain significant patterns, "
        "themes, or examples worth highlighting. Only list those that are directly tied to important findings, thematic insights, "
        "structural characteristics, or strategic improvement opportunities. This could include main documents, reference materials, "
        "or files demonstrating key textual patterns."
    ),
    "issues_found": (
        "Issues or concerns identified during text analysis, each with severity level (critical, high, medium, low). Include unclear passages, "
        "weak arguments, structural problems, style inconsistencies, readability issues, etc."
    ),
    "analysis_type": (
        "Type of text analysis to perform (structure, themes, arguments, style, readability, general)"
    ),
}


class TextAnalyzeRequest(WorkflowRequest):
    """Request model for Text Analysis workflow tool"""

    step: str = Field(..., description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["step"])
    step_number: int = Field(..., ge=1, description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["step_number"])
    total_steps: int = Field(..., ge=1, description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["total_steps"])
    next_step_required: bool = Field(..., description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["next_step_required"])
    findings: str = Field(..., description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["findings"])

    # Analysis tracking fields
    files_checked: Optional[list[str]] = Field(default_factory=list, description="List all files (as absolute paths, do not clip or shrink file names) examined during the text analysis investigation so far.")
    relevant_files: Optional[list[str]] = Field(default_factory=list, description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["relevant_files"])
    relevant_context: Optional[list[str]] = Field(default_factory=list, description="Themes/arguments identified as central to the text")
    issues_found: Optional[list[dict[str, Any]]] = Field(default_factory=list, description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["issues_found"])

    # Analysis configuration
    analysis_type: Literal["structure", "themes", "arguments", "style", "readability", "general"] = Field(
        default="general", description=TEXT_ANALYZE_WORKFLOW_FIELD_DESCRIPTIONS["analysis_type"]
    )
    output_format: Literal["summary", "detailed", "actionable"] = Field(
        default="detailed", description="How to format the output (summary, detailed, actionable)"
    )

    # Workflow control
    confidence: Literal["exploring", "low", "medium", "high", "very_high", "almost_certain", "certain"] = Field(
        default="exploring",
        description=(
            "Your confidence level in the current text analysis findings: exploring (early investigation), low (some insights but more needed), "
            "medium (solid understanding), high (comprehensive insights), very_high (very comprehensive insights), almost_certain (nearly complete analysis), "
            "certain (100% confidence - complete text analysis ready for expert validation)"
        ),
    )
    backtrack_from_step: Optional[int] = Field(
        default=None,
        ge=1,
        description="If an earlier finding or assessment needs to be revised or discarded, specify the step number from which to start over.",
    )


class TextAnalyzeTool(WorkflowTool):
    """
    Text document analysis tool for comprehensive content understanding using WorkflowTool architecture.

    Provides step-by-step analysis workflow for text documents including structure, themes,
    arguments, style, and readability assessment.
    """

    def __init__(self):
        super().__init__()
        self.initial_request = None
        self.analysis_config = {}

    def get_name(self) -> str:
        return "textanalyze"

    def get_description(self) -> str:
        return (
            "TEXT ANALYSIS WORKFLOW - Step-by-step text document analysis with systematic investigation. "
            "This tool guides you through a systematic investigation process where you:\n\n"
            "1. Start with step 1: describe your text analysis investigation plan\n"
            "2. STOP and investigate document structure, themes, and content patterns\n"
            "3. Report findings in step 2 with concrete evidence from actual text analysis\n"
            "4. Continue investigating between each step\n"
            "5. Track findings, relevant files, and insights throughout\n"
            "6. Update assessments as understanding evolves\n"
            "7. Once investigation is complete, receive expert validation\n\n"
            "IMPORTANT: This tool enforces investigation between steps:\n"
            "- After each call, you MUST investigate before calling again\n"
            "- Each step must include NEW evidence from text examination\n"
            "- No recursive calls without actual investigation work\n"
            "- The tool will specify which step number to use next\n"
            "- Follow the required_actions list for investigation guidance\n\n"
            "Perfect for: text structure analysis, thematic assessment, argument evaluation, "
            "style analysis, readability review, content understanding."
        )

    def get_system_prompt(self) -> str:
        return TEXT_ANALYZE_PROMPT

    def get_request_model(self):
        return TextAnalyzeRequest

    @property
    def model_category(self) -> "ToolModelCategory":
        """Text analysis works well with reasoning and analytical models"""
        return "reasoning"

    def should_embed_files_as_context(self, request: TextAnalyzeRequest) -> bool:
        """
        Determine if files should be embedded as context for text analysis.

        For text analysis, we want to embed files when:
        - It's step 1 and we're setting up the analysis
        - We have specific files to analyze in relevant_files
        - Analysis type requires full content review
        """
        if request.step_number == 1:
            return True

        # Embed if we have specific relevant files for this step
        if request.relevant_files:
            return True

        # For detailed analysis types, usually want full content
        if request.analysis_type in ["structure", "themes", "arguments"]:
            return True

        return False

    def get_required_actions(self, request: TextAnalyzeRequest) -> list[str]:
        """Generate step-specific investigation actions for text analysis."""
        actions = []

        if request.step_number == 1:
            actions.extend([
                "Use Read tool to examine the text document(s) specified in relevant_files",
                "Understand the document structure and main content areas",
                "Identify key themes, arguments, and organizational patterns",
                "Map out the text structure and content flow"
            ])
        else:
            actions.extend([
                "Continue investigating specific aspects identified in previous steps",
                "Use Read tool to examine additional sections or related documents",
                "Gather concrete evidence to support your analysis",
                "Build on previous findings with new insights"
            ])

        return actions

    def should_call_expert_analysis(self, request: TextAnalyzeRequest) -> bool:
        """Determine if expert analysis should be called based on confidence level."""
        return request.confidence != "certain"

    def prepare_expert_analysis_context(self, request: TextAnalyzeRequest) -> str:
        """Prepare context for expert analysis of text analysis findings."""
        context_parts = [
            f"TEXT ANALYSIS REQUEST - {request.analysis_type.upper()}",
            f"Analysis confidence: {request.confidence}",
            f"Step {request.step_number} of {request.total_steps}",
            "",
            "ANALYSIS FINDINGS:",
            request.findings,
        ]

        if request.issues_found:
            context_parts.extend([
                "",
                "ISSUES IDENTIFIED:",
                *[f"- {issue}" for issue in request.issues_found],
            ])

        if request.relevant_context:
            context_parts.extend([
                "",
                "KEY THEMES/ARGUMENTS:",
                *[f"- {context}" for context in request.relevant_context],
            ])

        return "\n".join(context_parts)

    def prepare_prompt(self, request: TextAnalyzeRequest) -> str:
        """Prepare the analysis prompt."""
        # This method is called by the base tool but we handle prompting in the workflow
        return request.step
