"""Content-type registry: the *shape* of every authorable content collection.

This is structure, not content. Field specs drive three things from one place:
publish-time validation, the admin form UI (served via /v1/admin/content/types),
and ref pinning when a version is published. The actual questions, weights,
prices, prompts ... are documents in MongoDB.
"""
from dataclasses import asdict, dataclass
from typing import Dict, List, Literal, Optional, Tuple

FieldKind = Literal["text", "textarea", "number", "integer", "bool", "select", "tags", "ref", "refs", "json"]


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: FieldKind
    required: bool = False
    help: str = ""
    options: Tuple[str, ...] = ()  # select
    ref_type: Optional[str] = None  # ref / refs: key of another ContentType
    min: Optional[float] = None  # number / integer
    max: Optional[float] = None
    default: object = None
    # ref / refs: also accept items that exist only as drafts (not pinned). Used where the link is a
    # grant of access resolved later (e.g. a product listing assessments still being authored).
    allow_draft: bool = False

    def to_api(self) -> dict:
        data = asdict(self)
        data["options"] = list(self.options)
        return data


@dataclass(frozen=True)
class ContentType:
    name: str  # also the Mongo collection name
    label: str
    title_field: str  # shown in admin tables
    fields: Tuple[FieldSpec, ...]
    key_help: str = ""

    def field(self, name: str) -> Optional[FieldSpec]:
        return next((f for f in self.fields if f.name == name), None)

    def ref_fields(self) -> List[FieldSpec]:
        return [f for f in self.fields if f.kind in ("ref", "refs")]

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "title_field": self.title_field,
            "key_help": self.key_help,
            "fields": [f.to_api() for f in self.fields],
        }


# MVP (plan v2 Phase 5): five answer types, plus file_upload for the resume (plan v5 Phase 5).
# free_text questions can also accept an uploaded file instead of text (written OR video / document).
QUESTION_TYPES = ("single_choice", "multi_select", "likert", "rank", "free_text", "file_upload")
UPLOAD_KINDS = ("pdf", "docx", "pptx", "mp4", "mov", "webm")
# Types whose answer is picked from `options`.
CHOICE_QUESTION_TYPES = ("single_choice", "multi_select", "likert", "rank")

ASSESSMENT_CATEGORIES = ("Profile", "Potential", "Values", "Capability", "Demonstrated")

_types: Tuple[ContentType, ...] = (
    ContentType(
        name="assessments",
        label="Assessments",
        title_field="name",
        key_help="e.g. capability",
        fields=(
            FieldSpec("name", "Name", "text", required=True),
            FieldSpec("category", "Category", "select", required=True, options=ASSESSMENT_CATEGORIES),
            FieldSpec("purpose", "Purpose / coverage", "textarea", required=True),
            FieldSpec("section_keys", "Sections (in order)", "refs", required=True, ref_type="sections"),
            FieldSpec("time_limit_minutes", "Expected time (minutes, shown to candidates — not enforced)", "integer", min=1),
        ),
    ),
    ContentType(
        name="sections",
        label="Sections",
        title_field="title",
        key_help="e.g. S-STRUCT-01",
        fields=(
            FieldSpec("title", "Title", "text", required=True),
            FieldSpec("instructions", "Instructions", "textarea"),
            FieldSpec("question_keys", "Questions (in order)", "refs", required=True, ref_type="questions"),
            FieldSpec(
                "skip_if",
                "Skip this section if",
                "json",
                default=[],
                help='Skipped when any earlier answer matches. List of {"question_key": "Q1", "answer": "A"}',
            ),
        ),
    ),
    ContentType(
        name="questions",
        label="Questions",
        title_field="prompt",
        key_help="e.g. Q-STRUCT-001",
        fields=(
            FieldSpec("type", "Question type", "select", required=True, options=QUESTION_TYPES),
            FieldSpec("prompt", "Prompt", "textarea", required=True),
            FieldSpec(
                "options",
                "Options",
                "json",
                default=[],
                help='Required for choice / likert / rank. List of {"key": "A", "label": "..."}',
            ),
            FieldSpec(
                "competency_map",
                "Competency map",
                "json",
                default=[],
                help='List of {"competency_key": "problem_structuring", "weight": 1.0}',
            ),
            FieldSpec("value_map", "Values map", "json", default=[], help='List of {"value_key": "achievement", "weight": 1.0}'),
            FieldSpec("scoring_rule", "Scoring rule", "json", default={}, help='e.g. {"method": "rank_points", "points": [4, 3, 2, 1]}'),
            FieldSpec("rubric_key", "Rubric (AI-scored answers)", "ref", ref_type="rubrics"),
            FieldSpec("min_selections", "Min selections (multi-select)", "integer", min=1),
            FieldSpec("max_selections", "Max selections (multi-select)", "integer", min=1),
            FieldSpec("min_words", "Min words (free text)", "integer", min=1),
            FieldSpec("max_length", "Max characters (free text)", "integer", min=1, default=5000),
            FieldSpec(
                "upload_kinds",
                "Accepted file types",
                "tags",
                default=[],
                help="file_upload: required. free_text: optional — lets the candidate upload instead of typing. Any of: pdf, docx, pptx, mp4, mov, webm",
            ),
            FieldSpec("upload_max_mb", "Max file size (MB)", "integer", min=1),
            FieldSpec(
                "upload_role",
                "Special handling",
                "select",
                options=("none", "resume"),
                default="none",
                help="resume = saved as the candidate's CV and read by AI Profile Understanding (Phase 5b)",
            ),
        ),
    ),
    ContentType(
        name="rubrics",
        label="Rubrics",
        title_field="name",
        key_help="e.g. R-CASE-01",
        fields=(
            FieldSpec("name", "Name", "text", required=True),
            FieldSpec("competency_keys", "Competencies", "refs", ref_type="competencies"),
            FieldSpec(
                "dimensions",
                "Dimensions",
                "json",
                required=True,
                default=[],
                help='List of {"key": "structure", "name": "...", "weight": 0.25, "anchors": [{"level": 1, "descriptor": "..."}]}',
            ),
        ),
    ),
    ContentType(
        name="competencies",
        label="Competencies",
        title_field="name",
        key_help="e.g. problem_structuring",
        fields=(
            FieldSpec("name", "Name", "text", required=True),
            FieldSpec("definition", "Definition", "textarea", required=True),
            FieldSpec("tags", "Tags", "tags", default=[]),
        ),
    ),
    ContentType(
        name="values_taxonomy",
        label="Values taxonomy",
        title_field="name",
        key_help="e.g. self_direction, openness_to_change",
        fields=(
            FieldSpec("name", "Name", "text", required=True),
            FieldSpec("kind", "Kind", "select", required=True, options=("basic_value", "higher_order")),
            FieldSpec("definition", "Core motivational meaning", "textarea", required=True),
            FieldSpec("consulting_interpretation", "Consulting interpretation", "textarea"),
            FieldSpec(
                "constituent_value_keys",
                "Constituent values",
                "refs",
                ref_type="values_taxonomy",
                help="Higher-order views only.",
            ),
            FieldSpec(
                "partial_value_keys",
                "Partially overlapping values",
                "refs",
                ref_type="values_taxonomy",
                help="Higher-order views only (e.g. Hedonism).",
            ),
        ),
    ),
    ContentType(
        name="videos",
        label="Videos",
        title_field="title",
        key_help="e.g. explainer",
        fields=(
            FieldSpec("title", "Title", "text", required=True),
            FieldSpec("description", "Description", "textarea"),
            FieldSpec("provider", "Provider", "select", required=True, options=("youtube", "mp4")),
            FieldSpec("url", "URL", "text", required=True),
            FieldSpec("captions_url", "Captions (.vtt) URL", "text"),
            FieldSpec("transcript", "Transcript", "textarea"),
        ),
    ),
    ContentType(
        name="products",
        label="Products",
        title_field="name",
        key_help="e.g. consulting_assessment",
        fields=(
            FieldSpec("name", "Name", "text", required=True),
            FieldSpec("kind", "Kind", "select", required=True, options=("assessment", "bundle", "report_upgrade")),
            FieldSpec("description", "Description", "textarea"),
            # One flat price per product (plan v2 Phase 4) — no regional / coupon pricing.
            FieldSpec("price", "Price", "number", required=True, min=0),
            FieldSpec("currency", "Currency (ISO 4217)", "text", required=True, default="USD"),
            FieldSpec(
                "assessment_keys",
                "Assessments included",
                "refs",
                ref_type="assessments",
                allow_draft=True,
                help="Buying this product unlocks these assessments (drafts allowed — they open once published).",
            ),
            FieldSpec("bundled_product_keys", "Bundled products", "refs", ref_type="products"),
            FieldSpec(
                "requires_product_keys",
                "Can only be bought after one of",
                "refs",
                ref_type="products",
                help="e.g. the Detailed Report upgrade needs an assessment product first.",
            ),
            FieldSpec("sort_order", "Order on the pricing page", "integer", min=0, default=0),
        ),
    ),
    ContentType(
        name="prompts",
        label="AI prompts",
        title_field="name",
        key_help="scoring, report_generator, results_explainer, support_chatbot",
        fields=(
            FieldSpec("name", "Name", "text", required=True),
            FieldSpec("purpose", "Purpose", "textarea", required=True),
            FieldSpec("system_prompt", "System prompt", "textarea", required=True),
            FieldSpec("output_schema", "Output JSON schema", "json", default={}),
            FieldSpec("model_policy", "Model policy", "json", default={}, help='e.g. {"temperature": 0.2}'),
        ),
    ),
    ContentType(
        # Public page copy (plan v2 Phase 3). Served unauthenticated by GET /v1/site/{key} — published versions only.
        name="site_content",
        label="Site content",
        title_field="headline",
        key_help="e.g. landing",
        fields=(
            FieldSpec("headline", "Headline", "text", required=True),
            FieldSpec("subheadline", "Sub-headline", "textarea", required=True),
            FieldSpec("cta_label", "Main button label", "text", required=True, default="Create your account"),
            FieldSpec(
                "video_key",
                "Explainer video",
                "ref",
                ref_type="videos",
                help="Pick a published video, then publish this page. The page keeps that exact video version until you publish the page again.",
            ),
            FieldSpec("video_heading", "Video heading", "text"),
            FieldSpec("video_body", "Video intro", "textarea"),
            FieldSpec("sections_heading", "Narrative heading", "text"),
            FieldSpec("sections", "Narrative blocks", "json", default=[], help='List of {"title": "...", "body": "..."}'),
            FieldSpec("steps_heading", "Journey heading", "text"),
            FieldSpec("steps", "Journey steps", "json", default=[], help='List of {"title": "...", "body": "..."}'),
            FieldSpec("privacy_note", "Privacy summary", "textarea"),
            FieldSpec("closing_heading", "Closing heading", "text"),
            FieldSpec("closing_body", "Closing text", "textarea"),
        ),
    ),
    ContentType(
        # Questions the AI video interview asks (plan v5: AI video interview). Admin-editable / AI-generatable.
        name="interview_questions",
        label="Interview questions",
        title_field="prompt",
        key_help="e.g. IV-01",
        fields=(
            FieldSpec("prompt", "Question the interviewer asks", "textarea", required=True),
            FieldSpec("seconds", "Time to answer (seconds)", "integer", required=True, min=15, max=600, default=90),
            FieldSpec("order", "Order", "integer", min=0, default=0),
        ),
    ),
    ContentType(
        # Public help content for the Phase 10 support chatbot. PUBLIC ONLY — never candidate data.
        name="support_kb",
        label="Support knowledge base",
        title_field="title",
        key_help="e.g. what-is-included, how-long, my-data",
        fields=(
            FieldSpec("title", "Question / title", "text", required=True),
            FieldSpec("body", "Answer", "textarea", required=True),
            FieldSpec("tags", "Tags / keywords", "tags", default=[], help="Extra keywords to help the bot match this entry."),
        ),
    ),
    ContentType(
        name="report_templates",
        label="Report templates",
        title_field="name",
        key_help="e.g. summary, detailed",
        fields=(
            FieldSpec("name", "Name", "text", required=True),
            FieldSpec("report_type", "Report type", "select", required=True, options=("summary", "detailed")),
            FieldSpec("product_key", "Product", "ref", ref_type="products"),
            FieldSpec(
                "sections",
                "Sections",
                "json",
                required=True,
                default=[],
                help='List of {"key": "exec_summary", "title": "...", "source": "scores.readiness"}',
            ),
        ),
    ),
)

CONTENT_TYPES: Dict[str, ContentType] = {t.name: t for t in _types}


def get_type(name: str) -> Optional[ContentType]:
    return CONTENT_TYPES.get(name)
