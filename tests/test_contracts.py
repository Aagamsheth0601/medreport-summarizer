import copy
import pytest
from pydantic import ValidationError
from schemas import Extraction, TestResult as Result


def result_data():
    return dict(test_name="Example", value=200, unit="mg/dL", reference_text="< 200",
                reference_range=dict(low=None, high=200, low_inclusive=True, high_inclusive=False),
                status="high")


@pytest.mark.parametrize("inclusive,value,status", [
    (False, 200, "high"), (True, 200, "normal"), (False, 199, "normal"),
])
def test_upper_boundary(inclusive, value, status):
    data = result_data()
    data["reference_range"]["high_inclusive"] = inclusive
    data.update(value=value, status=status)
    assert Result.model_validate(data).status == status


@pytest.mark.parametrize("value", ["200", True, float("nan"), float("inf")])
def test_reject_invalid_numbers(value):
    data = result_data()
    data["value"] = value
    with pytest.raises(ValidationError):
        Result.model_validate(data)


def test_reject_inconsistent_status():
    data = result_data()
    data["status"] = "normal"
    with pytest.raises(ValidationError):
        Result.model_validate(data)


def test_reject_duplicate_names():
    data = result_data()
    duplicate = copy.deepcopy(data)
    duplicate["test_name"] = "EXAMPLE"
    with pytest.raises(ValidationError):
        Extraction.model_validate(dict(tests=[data, duplicate], warnings=[]))


def test_missing_range_is_unknown():
    data = result_data()
    data.update(reference_range=None, reference_text="not supplied", status="unknown")
    assert Result.model_validate(data).status == "unknown"


@pytest.mark.parametrize("inclusive,status", [(False, "low"), (True, "normal")])
def test_lower_boundary(inclusive, status):
    data = result_data()
    data.update(value=40, status=status, reference_text="> 40")
    data["reference_range"] = dict(low=40, high=None, low_inclusive=inclusive, high_inclusive=True)
    assert Result.model_validate(data).status == status


def test_reversed_range_is_invalid():
    data = result_data()
    data["reference_range"].update(low=201, high=200)
    with pytest.raises(ValidationError):
        Result.model_validate(data)


def test_reject_missing_and_extra_fields():
    with pytest.raises(ValidationError):
        Extraction.model_validate({"tests": [], "unexpected": True})
