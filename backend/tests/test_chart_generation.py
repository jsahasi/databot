"""Tests for generate_chart_data function in on24_query_tools.py.

Covers all chart types, pie chart format, stacked group_mode,
empty data handling, and auto-detection of y_keys.
"""

import pytest

from app.agents.tools.on24_query_tools import generate_chart_data


# ---------- Fixtures ----------

SAMPLE_DATA = [
    {"month": "Jan", "registrants": 100, "attendees": 60, "engagement": 3.2},
    {"month": "Feb", "registrants": 120, "attendees": 80, "engagement": 4.1},
    {"month": "Mar", "registrants": 90, "attendees": 50, "engagement": 2.8},
]

SINGLE_ROW = [{"name": "Acme", "value": 42}]

PIE_DATA = [
    {"source": "LinkedIn", "count": 200},
    {"source": "Email", "count": 150},
    {"source": "Organic", "count": 80},
]


# ---------- Empty data ----------

@pytest.mark.asyncio
async def test_empty_data_returns_empty_dict():
    result = await generate_chart_data(data=[], chart_type="bar", x_key="month")
    assert result == {}


# ---------- Pie chart format ----------

@pytest.mark.asyncio
async def test_pie_chart_produces_name_value_pairs():
    result = await generate_chart_data(
        data=PIE_DATA, chart_type="pie", x_key="source", y_keys=["count"], title="Sources"
    )
    assert result["type"] == "pie"
    assert result["title"] == "Sources"
    for item in result["data"]:
        assert "name" in item
        assert "value" in item
        assert set(item.keys()) == {"name", "value"}


@pytest.mark.asyncio
async def test_pie_chart_uses_first_y_key_only():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="pie", x_key="month", y_keys=["registrants", "attendees"]
    )
    # Pie should only use the first y_key (registrants), not attendees
    assert result["type"] == "pie"
    assert result["data"][0]["value"] == 100  # first row registrants


@pytest.mark.asyncio
async def test_pie_chart_skips_none_values():
    data = [
        {"source": "A", "count": 10},
        {"source": "B", "count": None},
        {"source": "C", "count": 5},
    ]
    result = await generate_chart_data(data=data, chart_type="pie", x_key="source", y_keys=["count"])
    # B should be filtered out because value is None
    assert len(result["data"]) == 2
    names = [item["name"] for item in result["data"]]
    assert "B" not in names


# ---------- All 10 chart types produce correct output ----------

VALID_CHART_TYPES = ["bar", "line", "radar", "funnel", "gauge", "treemap", "scatter", "heatmap", "waterfall"]


@pytest.mark.asyncio
@pytest.mark.parametrize("chart_type", VALID_CHART_TYPES)
async def test_non_pie_chart_types_produce_correct_format(chart_type):
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type=chart_type, x_key="month",
        y_keys=["registrants", "attendees"], title=f"Test {chart_type}"
    )
    assert result["type"] == chart_type
    assert result["title"] == f"Test {chart_type}"
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 3
    # Each row has x_key + y_keys
    row = result["data"][0]
    assert "month" in row
    assert "registrants" in row
    assert "attendees" in row


@pytest.mark.asyncio
async def test_invalid_chart_type_falls_back_to_bar():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="invalid_type", x_key="month", y_keys=["registrants"]
    )
    assert result["type"] == "bar"


# ---------- group_mode ----------

@pytest.mark.asyncio
async def test_stacked_group_mode_passed_through():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month",
        y_keys=["registrants"], group_mode="stacked"
    )
    assert result["groupMode"] == "stacked"


@pytest.mark.asyncio
async def test_grouped_group_mode_passed_through():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month",
        y_keys=["registrants"], group_mode="grouped"
    )
    assert result["groupMode"] == "grouped"


@pytest.mark.asyncio
async def test_empty_group_mode_not_in_result():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month", y_keys=["registrants"]
    )
    assert "groupMode" not in result


@pytest.mark.asyncio
async def test_invalid_group_mode_not_in_result():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month",
        y_keys=["registrants"], group_mode="bad_mode"
    )
    assert "groupMode" not in result


# ---------- y_label ----------

@pytest.mark.asyncio
async def test_y_label_included_when_provided():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month",
        y_keys=["registrants"], y_label="Count"
    )
    assert result["yLabel"] == "Count"


@pytest.mark.asyncio
async def test_y_label_excluded_when_empty():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month", y_keys=["registrants"]
    )
    assert "yLabel" not in result


# ---------- Auto-detection ----------

@pytest.mark.asyncio
async def test_auto_detect_y_keys_when_not_provided():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month"
    )
    # Should auto-detect registrants, attendees, engagement as numeric fields
    row = result["data"][0]
    assert "registrants" in row
    assert "attendees" in row
    assert "engagement" in row


@pytest.mark.asyncio
async def test_auto_detect_x_key_when_not_provided():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key=""
    )
    # Should use first key ("month") as x_key
    assert result["data"][0].get("month") is not None


@pytest.mark.asyncio
async def test_auto_detect_excludes_x_key_from_y_keys():
    data = [{"label": "A", "score": 10, "count": 5}]
    result = await generate_chart_data(data=data, chart_type="bar", x_key="label")
    row = result["data"][0]
    # y_keys should be score and count, not label
    assert "score" in row
    assert "count" in row
    assert row["label"] == "A"


@pytest.mark.asyncio
async def test_auto_detect_ignores_non_numeric_fields():
    data = [{"name": "Event", "status": "active", "count": 10}]
    result = await generate_chart_data(data=data, chart_type="bar", x_key="name")
    row = result["data"][0]
    # "status" is a string, should not be in y_keys
    assert "status" not in row
    assert "count" in row


# ---------- Title passthrough ----------

@pytest.mark.asyncio
async def test_title_passthrough():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="line", x_key="month",
        y_keys=["registrants"], title="Monthly Registrations"
    )
    assert result["title"] == "Monthly Registrations"


@pytest.mark.asyncio
async def test_empty_title():
    result = await generate_chart_data(
        data=SAMPLE_DATA, chart_type="bar", x_key="month", y_keys=["registrants"]
    )
    assert result["title"] == ""
