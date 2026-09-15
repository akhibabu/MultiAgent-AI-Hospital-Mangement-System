"""Insurance documentation against the encounter's billed code set."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from codeset_validator import CodeSetValidator


class InsuranceDocumentationValidator(CodeSetValidator):
    """
    Compares generated billing documentation against the codes actually billed.

    Diagnosis and procedure codes are both in scope; DRG codes are not, because
    a DRG is assigned by a grouper from the coded record rather than named in
    free text, and the agent produces no field that corresponds to one.

    This is a coding-agreement measure. It says nothing about whether a claim
    would be accepted, which depends on payer rules outside this dataset.
    """

    supported_kinds = frozenset({"BILLING_CODE_SET", "ICD_CODE_SET"})
    gold_item_names = ("diagnosis_code", "procedure_code")
    output_paths = (
        ("diagnosis_codes",),
        ("insurance_documentation", "diagnosis_codes"),
    )
    field_name = "billing_codes"

    def _predicted_values(self, agent_output: Any) -> Tuple[List[str], Optional[str]]:
        """Pool diagnosis and procedure code descriptions from the claim payload."""
        if not isinstance(agent_output, dict):
            return super()._predicted_values(agent_output)

        node = agent_output.get("insurance_documentation")
        payload: Dict[str, Any] = node if isinstance(node, dict) else agent_output

        values: List[str] = []
        used: List[str] = []
        for key in ("diagnosis_codes", "procedure_codes"):
            entries = payload.get(key)
            if isinstance(entries, list) and entries:
                used.append(key)
                values.extend(self._as_name(entry) for entry in entries)

        if not used:
            return super()._predicted_values(agent_output)
        return values, "+".join(used)

    def _as_name(self, item: Any) -> str:
        """Prefer the code's description, since the reference is matched by title."""
        if isinstance(item, dict):
            for key in ("description", "title", "long_title", "name", "condition"):
                if item.get(key):
                    return str(item[key])
            code = item.get("code") or item.get("icd_code")
            version = item.get("icd_version")
            if code:
                from terminology import diagnosis_title, procedure_title

                title = diagnosis_title(str(code), version) or procedure_title(str(code), version)
                if title:
                    return title
                return str(code)
        return super()._as_name(item)
