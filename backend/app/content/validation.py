"""Publish-time validation: required fields, types, and no orphan references.

Drafts may be incomplete; `validate()` is what stands between a draft and an
immutable published version. Every reference must point at a *published*
version, and the versions it resolved to are recorded (`used`) so publish can
pin them.
"""
import re

from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from app import database
from app.content.registry import CHOICE_QUESTION_TYPES, UPLOAD_KINDS, ContentType, FieldSpec, get_type

Error = Dict[str, str]


def _err(field: str, message: str) -> Error:
    return {"field": field, "message": message}


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class RefLookup:
    """Latest published version of every key, per content type, for one tenant."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._cache: Dict[str, Dict[str, dict]] = {}
        # (type, key) -> version, for every reference that resolved.
        self.used: Dict[Tuple[str, str], int] = {}

    async def published(self, type_name: str) -> Dict[str, dict]:
        if type_name not in self._cache:
            pipeline = [
                {"$match": {"tenant_id": self.tenant_id, "status": "published"}},
                {"$sort": {"key": 1, "version": -1}},
                {"$group": {"_id": "$key", "doc": {"$first": "$$ROOT"}}},
            ]
            docs = await database.collection(type_name).aggregate(pipeline).to_list(None)
            self._cache[type_name] = {d["_id"]: d["doc"] for d in docs}
        return self._cache[type_name]

    async def resolve(self, type_name: str, key: Any) -> Optional[dict]:
        if not isinstance(key, str):
            return None
        doc = (await self.published(type_name)).get(key)
        if doc:
            self.used[(type_name, key)] = doc["version"]
        return doc

    async def exists(self, type_name: str, key: Any) -> bool:
        """Any version (draft or published) of this key exists."""
        if not isinstance(key, str):
            return False
        return await database.collection(type_name).find_one({"tenant_id": self.tenant_id, "key": key}, projection={"_id": 1}) is not None

    def pinned(self) -> Dict[str, Dict[str, int]]:
        pins: Dict[str, Dict[str, int]] = {}
        for (type_name, key), version in sorted(self.used.items()):
            pins.setdefault(type_name, {})[key] = version
        return pins


async def _check_ref(errors: List[Error], lookup: RefLookup, field: str, ref_type: str, key: Any, self_ref: Optional[str]) -> Optional[dict]:
    if not isinstance(key, str) or not key:
        errors.append(_err(field, "must be a content key"))
        return None
    if key == self_ref:
        errors.append(_err(field, f"cannot reference itself ({key})"))
        return None
    doc = await lookup.resolve(ref_type, key)
    if doc is None:
        label = get_type(ref_type).label if get_type(ref_type) else ref_type
        errors.append(_err(field, f"'{key}' is not a published item in {label}"))
    return doc


async def _check_field(errors: List[Error], spec: FieldSpec, value: Any, lookup: RefLookup, ctype: ContentType, key: str) -> None:
    name = spec.name
    self_ref = key if spec.ref_type == ctype.name else None
    if spec.kind in ("text", "textarea"):
        if not isinstance(value, str):
            errors.append(_err(name, "must be text"))
    elif spec.kind in ("number", "integer"):
        if not _is_number(value) or (spec.kind == "integer" and not isinstance(value, int)):
            errors.append(_err(name, f"must be {'a whole number' if spec.kind == 'integer' else 'a number'}"))
            return
        if spec.min is not None and value < spec.min:
            errors.append(_err(name, f"must be ≥ {spec.min:g}"))
        if spec.max is not None and value > spec.max:
            errors.append(_err(name, f"must be ≤ {spec.max:g}"))
    elif spec.kind == "bool":
        if not isinstance(value, bool):
            errors.append(_err(name, "must be true or false"))
    elif spec.kind == "select":
        if value not in spec.options:
            errors.append(_err(name, f"must be one of: {', '.join(spec.options)}"))
    elif spec.kind == "tags":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(_err(name, "must be a list of text values"))
    elif spec.kind == "ref":
        await _check_ref(errors, lookup, name, spec.ref_type, value, self_ref)
    elif spec.kind == "refs":
        if not isinstance(value, list):
            errors.append(_err(name, "must be a list of content keys"))
            return
        if len(set(map(str, value))) != len(value):
            errors.append(_err(name, "contains duplicates"))
        for item in value:
            if spec.allow_draft:
                if item == self_ref:
                    errors.append(_err(name, f"cannot reference itself ({item})"))
                elif not await lookup.exists(spec.ref_type, item):
                    errors.append(_err(name, f"'{item}' does not exist in {get_type(spec.ref_type).label}"))
            else:
                await _check_ref(errors, lookup, name, spec.ref_type, item, self_ref)
    # "json" fields are shape-checked by the per-type validators below.


# --- per-type rules ---------------------------------------------------------------------------

def _list_of_objects(errors: List[Error], field: str, value: Any, required_keys: Tuple[str, ...]) -> List[dict]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        errors.append(_err(field, "must be a list of objects"))
        return []
    for i, item in enumerate(value):
        for k in required_keys:
            if _is_empty(item.get(k)):
                errors.append(_err(field, f"item {i + 1} is missing '{k}'"))
    return value


def _unique_keys(errors: List[Error], field: str, items: List[dict], attr: str = "key") -> None:
    keys = [i.get(attr) for i in items if i.get(attr) is not None]
    if len(set(map(str, keys))) != len(keys):
        errors.append(_err(field, f"has duplicate '{attr}' values"))


async def _questions(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    qtype = data.get("type")
    options = _list_of_objects(errors, "options", data.get("options"), ("key", "label"))
    _unique_keys(errors, "options", options)
    if qtype in CHOICE_QUESTION_TYPES and len(options) < 2:
        errors.append(_err("options", f"'{qtype}' questions need at least 2 options"))

    for i, item in enumerate(_list_of_objects(errors, "competency_map", data.get("competency_map"), ("competency_key", "weight"))):
        if item.get("competency_key"):
            await _check_ref(errors, lookup, "competency_map", "competencies", item["competency_key"], None)
        if "weight" in item and (not _is_number(item["weight"]) or item["weight"] <= 0):
            errors.append(_err("competency_map", f"item {i + 1} weight must be a positive number"))

    for i, item in enumerate(_list_of_objects(errors, "value_map", data.get("value_map"), ("value_key", "weight"))):
        if item.get("value_key"):
            value = await _check_ref(errors, lookup, "value_map", "values_taxonomy", item["value_key"], None)
            if value and value["data"].get("kind") != "basic_value":
                errors.append(_err("value_map", f"'{item['value_key']}' is a higher-order view; map items to basic values"))
        if "weight" in item and (not _is_number(item["weight"]) or item["weight"] <= 0):
            errors.append(_err("value_map", f"item {i + 1} weight must be a positive number"))

    if data.get("scoring_rule") is not None and not isinstance(data["scoring_rule"], dict):
        errors.append(_err("scoring_rule", "must be an object"))

    lo, hi = data.get("min_selections"), data.get("max_selections")
    if (lo or hi) and qtype != "multi_select":
        errors.append(_err("min_selections", "selection limits only apply to multi_select questions"))
    if _is_number(lo) and _is_number(hi) and lo > hi:
        errors.append(_err("max_selections", "must be ≥ min selections"))
    if _is_number(hi) and options and hi > len(options):
        errors.append(_err("max_selections", f"can't exceed the number of options ({len(options)})"))
    if qtype in ("free_text", "file_upload") and options:
        errors.append(_err("options", f"{qtype} questions don't have options"))
    kinds = data.get("upload_kinds") or []
    bad_kinds = [k for k in kinds if k not in UPLOAD_KINDS] if isinstance(kinds, list) else []
    if bad_kinds:
        errors.append(_err("upload_kinds", f"unknown file type(s): {', '.join(map(str, bad_kinds))} — use {', '.join(UPLOAD_KINDS)}"))
    if qtype == "file_upload" and not kinds:
        errors.append(_err("upload_kinds", "is required for file_upload questions"))
    if kinds and qtype not in ("free_text", "file_upload"):
        errors.append(_err("upload_kinds", "only free_text and file_upload questions accept files"))
    if data.get("upload_role") == "resume" and qtype != "file_upload":
        errors.append(_err("upload_role", "the resume role needs a file_upload question"))
    if (data.get("min_words") or data.get("max_length")) and qtype not in (None, "free_text"):
        if data.get("min_words"):
            errors.append(_err("min_words", "only applies to free_text questions"))


async def _sections(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    """skip_if: "if answer = X, skip this section" (plan v2 Phase 5) — no orphan question refs."""
    own_questions = set(data.get("question_keys") or [])
    for item in _list_of_objects(errors, "skip_if", data.get("skip_if"), ("question_key", "answer")):
        q_key = item.get("question_key")
        if not q_key:
            continue
        if q_key in own_questions:
            errors.append(_err("skip_if", f"'{q_key}' is in this section — skip rules must depend on an earlier section"))
            continue
        question = await _check_ref(errors, lookup, "skip_if", "questions", q_key, None)
        option_keys = {str(o.get("key")) for o in (question or {}).get("data", {}).get("options") or [] if isinstance(o, dict)}
        if question and option_keys and str(item.get("answer")) not in option_keys:
            errors.append(_err("skip_if", f"answer '{item.get('answer')}' is not an option of '{q_key}'"))


async def _rubrics(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    dims = _list_of_objects(errors, "dimensions", data.get("dimensions"), ("key", "name"))
    _unique_keys(errors, "dimensions", dims)
    for dim in dims:
        if "weight" in dim and (not _is_number(dim["weight"]) or dim["weight"] < 0):
            errors.append(_err("dimensions", f"'{dim.get('key')}' weight must be a non-negative number"))
        anchors = _list_of_objects(errors, "dimensions", dim.get("anchors"), ("level", "descriptor"))
        _unique_keys(errors, "dimensions", anchors, "level")


async def _values_taxonomy(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    constituents = data.get("constituent_value_keys") or []
    partials = data.get("partial_value_keys") or []
    if data.get("kind") == "higher_order":
        if not constituents:
            errors.append(_err("constituent_value_keys", "is required for a higher-order view"))
        for field, keys in (("constituent_value_keys", constituents), ("partial_value_keys", partials)):
            for k in keys if isinstance(keys, list) else []:
                doc = await lookup.resolve("values_taxonomy", k)
                if doc and doc["data"].get("kind") != "basic_value":
                    errors.append(_err(field, f"'{k}' must be a basic value"))
    elif constituents or partials:
        errors.append(_err("constituent_value_keys", "only higher-order views have constituent values"))


async def _products(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    currency = data.get("currency")
    if isinstance(currency, str) and currency and not re.fullmatch(r"[A-Z]{3}", currency):
        errors.append(_err("currency", "must be a 3-letter ISO code like USD"))
    if data.get("kind") == "bundle" and not data.get("bundled_product_keys"):
        errors.append(_err("bundled_product_keys", "is required for a bundle"))
    if data.get("kind") in ("assessment", "bundle") and not (data.get("assessment_keys") or data.get("bundled_product_keys")):
        errors.append(_err("assessment_keys", "an assessment product must include at least one assessment"))


async def _prompts(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    for field in ("output_schema", "model_policy"):
        if data.get(field) is not None and not isinstance(data[field], dict):
            errors.append(_err(field, "must be an object"))


async def _report_templates(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    sections = _list_of_objects(errors, "sections", data.get("sections"), ("key", "title"))
    _unique_keys(errors, "sections", sections)


async def _site_content(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    for field in ("sections", "steps"):
        _list_of_objects(errors, field, data.get(field), ("title", "body"))


async def _videos(errors: List[Error], data: dict, lookup: RefLookup, key: str) -> None:
    for field in ("url", "captions_url"):
        value = data.get(field)
        if isinstance(value, str) and value and not re.match(r"^https://\S+$", value):
            errors.append(_err(field, "must be a full https:// link"))
    if data.get("provider") == "youtube" and isinstance(data.get("url"), str) and data["url"] and not youtube_id(data["url"]):
        errors.append(_err("url", "is not a recognisable YouTube link (watch, youtu.be, shorts or embed URL)"))


def youtube_id(url: str) -> Optional[str]:
    match = re.search(r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


TypeRule = Callable[[List[Error], dict, RefLookup, str], Awaitable[None]]
TYPE_RULES: Dict[str, TypeRule] = {
    "questions": _questions,
    "sections": _sections,
    "rubrics": _rubrics,
    "values_taxonomy": _values_taxonomy,
    "products": _products,
    "prompts": _prompts,
    "site_content": _site_content,
    "videos": _videos,
    "report_templates": _report_templates,
}


async def validate(ctype: ContentType, key: str, data: Any, lookup: RefLookup) -> List[Error]:
    if not isinstance(data, dict):
        return [_err("data", "must be an object")]
    errors: List[Error] = []
    known = {f.name for f in ctype.fields}
    for name in sorted(set(data) - known):
        errors.append(_err(name, "is not a field of this content type"))
    for spec in ctype.fields:
        value = data.get(spec.name)
        if _is_empty(value):
            if spec.required:
                errors.append(_err(spec.name, "is required"))
            continue
        await _check_field(errors, spec, value, lookup, ctype, key)
    rule = TYPE_RULES.get(ctype.name)
    if rule:
        await rule(errors, data, lookup, key)
    return errors
