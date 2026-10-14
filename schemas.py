"""Contracts between agents. Valid structure is not medical validation."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=12000)]
Number = Annotated[float, Field(allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class ReferenceRange(Contract):
    low: Number | None
    high: Number | None
    low_inclusive: bool
    high_inclusive: bool

    @model_validator(mode="after")
    def ordered_bounds(self):
        if self.low is None and self.high is None:
            raise ValueError("Use null for a missing reference range")
        if self.low is not None and self.high is not None:
            if self.low > self.high:
                raise ValueError("Reference range is reversed")
            if self.low == self.high and not (self.low_inclusive and self.high_inclusive):
                raise ValueError("Reference range is empty")
        return self


class TestResult(Contract):
    test_name: Text
    value: Number
    unit: Text
    reference_text: Text
    reference_range: ReferenceRange | None
    status: Literal["low", "normal", "high", "unknown"]

    @model_validator(mode="after")
    def consistent_status(self):
        bounds = self.reference_range
        expected = "unknown"
        if bounds:
            expected = "normal"
            if bounds.low is not None and (
                self.value < bounds.low or (self.value == bounds.low and not bounds.low_inclusive)
            ):
                expected = "low"
            if bounds.high is not None and (
                self.value > bounds.high or (self.value == bounds.high and not bounds.high_inclusive)
            ):
                expected = "high"
        if self.status != expected:
            raise ValueError("Status does not match the supplied reference range")
        return self


class Extraction(Contract):
    tests: list[TestResult] = Field(min_length=1, max_length=100)
    warnings: list[Text] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_tests(self):
        names = [test.test_name.casefold() for test in self.tests]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate test names")
        return self


class Panel(Contract):
    panel_name: Text
    tests: list[Text] = Field(min_length=1, max_length=100)
    panel_summary: Text


class Finding(Contract):
    finding: Text
    related_tests: list[Text] = Field(min_length=1, max_length=100)
    rationale: Text


class Analysis(Contract):
    panels: list[Panel] = Field(min_length=1, max_length=100)
    findings: list[Finding] = Field(max_length=100)
    limitations: list[Text] = Field(min_length=1, max_length=20)


class Explanation(Contract):
    quick_summary: Text
    findings_explained: list[Text] = Field(max_length=100)
    within_range: Text
    limitations: Text


DISCLAIMER = (
    "**PORTFOLIO DEMO — FOR INFORMATIONAL PURPOSES ONLY**\n\n"
    "This project uses synthetic reports and AI-generated explanations, which can make mistakes. "
    "It is not a medical tool. Do not use it for diagnosis, treatment, or decisions about seeking care. "
    "Consult a qualified doctor about your own results."
)


class PipelineResult(Contract):
    sample_id: Text
    model: Text
    extraction: Extraction
    analysis: Analysis
    explanation: Explanation
    summary_markdown: str = Field(min_length=1)
