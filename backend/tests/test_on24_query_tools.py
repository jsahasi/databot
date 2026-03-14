"""Tests for on24_query_tools.py — all query functions with mocked asyncpg pool.

Mocking strategy:
- Patch get_pool() to return a mock pool with acquire() context manager
- Patch get_tenant_client_ids() to return a fixed hierarchy [10710, 22355]
- Mock conn.fetch / conn.fetchrow to return asyncpg-like Record dicts
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

MODULE = "app.agents.tools.on24_query_tools"


# ---------- Helpers ----------

class FakeRecord(dict):
    """Dict subclass that supports both dict[key] and attribute access like asyncpg.Record."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


def make_records(rows: list[dict]) -> list[FakeRecord]:
    return [FakeRecord(r) for r in rows]


def make_record(row: dict) -> FakeRecord:
    return FakeRecord(row)


class _FakeAcquire:
    """Mimics asyncpg pool.acquire() which returns a sync object usable as async ctx mgr."""
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool with acquire() context manager."""
    conn = AsyncMock()
    pool = MagicMock()  # MagicMock so acquire() is a sync call returning ctx mgr
    pool.acquire.return_value = _FakeAcquire(conn)
    return pool, conn


@pytest.fixture
def patch_db(mock_pool):
    """Patch get_pool and get_tenant_client_ids for all query tool tests."""
    pool, conn = mock_pool
    with patch(f"{MODULE}.get_pool", AsyncMock(return_value=pool)), \
         patch(f"{MODULE}.get_tenant_client_ids", AsyncMock(return_value=[10710, 22355])):
        yield conn


# ---------- _serialize ----------

class TestSerialize:
    def test_decimal_to_float(self):
        from app.agents.tools.on24_query_tools import _serialize
        assert _serialize(Decimal("3.14")) == 3.14

    def test_datetime_to_isoformat(self):
        from app.agents.tools.on24_query_tools import _serialize
        dt = datetime(2026, 3, 14, 10, 30)
        assert _serialize(dt) == "2026-03-14T10:30:00"

    def test_date_to_isoformat(self):
        from app.agents.tools.on24_query_tools import _serialize
        d = date(2026, 3, 14)
        assert _serialize(d) == "2026-03-14"

    def test_nested_dict(self):
        from app.agents.tools.on24_query_tools import _serialize
        result = _serialize({"val": Decimal("1.5"), "nested": {"d": date(2026, 1, 1)}})
        assert result == {"val": 1.5, "nested": {"d": "2026-01-01"}}

    def test_list_of_dicts(self):
        from app.agents.tools.on24_query_tools import _serialize
        result = _serialize([{"v": Decimal("2")}, {"v": Decimal("3")}])
        assert result == [{"v": 2.0}, {"v": 3.0}]

    def test_plain_values_passthrough(self):
        from app.agents.tools.on24_query_tools import _serialize
        assert _serialize("hello") == "hello"
        assert _serialize(42) == 42
        assert _serialize(None) is None


# ---------- _clamp_months ----------

class TestClampMonths:
    def test_normal_range(self):
        from app.agents.tools.on24_query_tools import _clamp_months
        assert _clamp_months(6) == 6

    def test_below_minimum(self):
        from app.agents.tools.on24_query_tools import _clamp_months
        assert _clamp_months(0) == 1
        assert _clamp_months(-5) == 1

    def test_above_maximum(self):
        from app.agents.tools.on24_query_tools import _clamp_months
        assert _clamp_months(30) == 24

    def test_boundary_values(self):
        from app.agents.tools.on24_query_tools import _clamp_months
        assert _clamp_months(1) == 1
        assert _clamp_months(24) == 24


# ---------- query_events ----------

class TestQueryEvents:
    @pytest.mark.asyncio
    async def test_returns_serialized_rows(self, patch_db):
        from app.agents.tools.on24_query_tools import query_events
        patch_db.fetch.return_value = make_records([
            {"event_id": 100, "description": "Webinar A", "event_type": "webcast",
             "goodafter": datetime(2026, 3, 1), "goodtill": datetime(2026, 3, 2),
             "is_active": "Y", "create_timestamp": datetime(2026, 2, 1),
             "last_modified": datetime(2026, 2, 15)},
        ])
        result = await query_events(limit=10)
        assert len(result) == 1
        assert result[0]["event_id"] == 100
        assert result[0]["goodafter"] == "2026-03-01T00:00:00"

    @pytest.mark.asyncio
    async def test_empty_result(self, patch_db):
        from app.agents.tools.on24_query_tools import query_events
        patch_db.fetch.return_value = []
        result = await query_events()
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_parameters(self, patch_db):
        from app.agents.tools.on24_query_tools import query_events
        patch_db.fetch.return_value = []
        await query_events(limit=5, offset=10, event_type="webcast", search="demo", past_only=True)
        args = patch_db.fetch.call_args
        # Verify params: client_ids, event_type, is_active, search, past_only, limit, offset
        positional = args[0]
        assert positional[1] == [10710, 22355]  # client_ids
        assert positional[2] == "webcast"  # event_type
        assert positional[4] == "demo"  # search
        assert positional[5] is True  # past_only


# ---------- get_event_detail ----------

class TestGetEventDetail:
    @pytest.mark.asyncio
    async def test_returns_event(self, patch_db):
        from app.agents.tools.on24_query_tools import get_event_detail
        patch_db.fetchrow.return_value = make_record(
            {"event_id": 200, "description": "Big Event", "goodafter": datetime(2026, 3, 10)}
        )
        result = await get_event_detail(200)
        assert result["event_id"] == 200
        assert result["goodafter"] == "2026-03-10T00:00:00"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, patch_db):
        from app.agents.tools.on24_query_tools import get_event_detail
        patch_db.fetchrow.return_value = None
        result = await get_event_detail(999)
        assert result is None


# ---------- query_attendees ----------

class TestQueryAttendees:
    @pytest.mark.asyncio
    async def test_returns_attendees(self, patch_db):
        from app.agents.tools.on24_query_tools import query_attendees
        patch_db.fetch.return_value = make_records([
            {"event_user_id": 1, "engagement_score": Decimal("85.5"),
             "live_minutes": Decimal("30"), "archive_minutes": Decimal("10"),
             "answered_polls": "Y", "asked_questions": "N", "resources_downloaded": 2},
        ])
        result = await query_attendees(event_id=100)
        assert len(result) == 1
        assert result[0]["engagement_score"] == 85.5
        assert result[0]["live_minutes"] == 30.0


# ---------- compute_event_kpis ----------

class TestComputeEventKpis:
    @pytest.mark.asyncio
    async def test_returns_kpis(self, patch_db):
        from app.agents.tools.on24_query_tools import compute_event_kpis
        # First call: KPI query; Second call: AI content check
        patch_db.fetchrow.side_effect = [
            make_record({
                "total_registrants": 100, "total_attendees": 60,
                "avg_engagement": Decimal("72.345"), "avg_live_minutes": Decimal("25.1"),
                "conversion_rate": Decimal("60.0"),
            }),
            make_record({"cnt": 3}),
        ]
        result = await compute_event_kpis(100)
        assert result["event_id"] == 100
        assert result["total_registrants"] == 100
        assert result["avg_engagement"] == 72.34  # round(72.345, 2) = 72.34 (banker's rounding)
        assert result["ai_content"]["count"] == 3

    @pytest.mark.asyncio
    async def test_returns_zeros_when_no_data(self, patch_db):
        from app.agents.tools.on24_query_tools import compute_event_kpis
        patch_db.fetchrow.return_value = None
        result = await compute_event_kpis(999)
        assert result["total_registrants"] == 0
        assert result["total_attendees"] == 0
        assert result["avg_engagement"] is None

    @pytest.mark.asyncio
    async def test_no_ai_content_key_when_zero(self, patch_db):
        from app.agents.tools.on24_query_tools import compute_event_kpis
        patch_db.fetchrow.side_effect = [
            make_record({
                "total_registrants": 50, "total_attendees": 30,
                "avg_engagement": Decimal("60"), "avg_live_minutes": Decimal("20"),
                "conversion_rate": Decimal("60"),
            }),
            make_record({"cnt": 0}),
        ]
        result = await compute_event_kpis(100)
        assert "ai_content" not in result


# ---------- compute_client_kpis ----------

class TestComputeClientKpis:
    @pytest.mark.asyncio
    async def test_returns_client_kpis(self, patch_db):
        from app.agents.tools.on24_query_tools import compute_client_kpis
        patch_db.fetchrow.return_value = make_record({
            "total_events": 15, "total_registrants": 1200,
            "total_attendees": 800, "avg_engagement": Decimal("65.789"),
        })
        result = await compute_client_kpis(months=3)
        assert result["total_events"] == 15
        assert result["avg_engagement"] == 65.79

    @pytest.mark.asyncio
    async def test_clamps_months(self, patch_db):
        from app.agents.tools.on24_query_tools import compute_client_kpis
        patch_db.fetchrow.return_value = make_record({
            "total_events": 0, "total_registrants": 0,
            "total_attendees": 0, "avg_engagement": None,
        })
        result = await compute_client_kpis(months=100)
        # Should clamp to 24 — verify it ran without error
        assert result["total_events"] == 0

    @pytest.mark.asyncio
    async def test_returns_defaults_when_none(self, patch_db):
        from app.agents.tools.on24_query_tools import compute_client_kpis
        patch_db.fetchrow.return_value = None
        result = await compute_client_kpis()
        assert result == {"total_events": 0, "total_registrants": 0, "total_attendees": 0, "avg_engagement": None}


# ---------- query_polls ----------

class TestQueryPolls:
    @pytest.mark.asyncio
    async def test_multiple_choice_grouped(self, patch_db):
        from app.agents.tools.on24_query_tools import query_polls
        # mc_sql returns, then text_sql returns
        patch_db.fetch.side_effect = [
            make_records([
                {"poll_id": 1, "question_id": 10, "question_text": "Favorite color?",
                 "question_type_cd": "singleoption", "answer_cd": "A",
                 "answer_text": "Red", "response_count": 25},
                {"poll_id": 1, "question_id": 10, "question_text": "Favorite color?",
                 "question_type_cd": "singleoption", "answer_cd": "B",
                 "answer_text": "Blue", "response_count": 15},
            ]),
            [],  # no open-text questions
        ]
        result = await query_polls(event_id=100)
        assert len(result) == 1
        assert result[0]["question_text"] == "Favorite color?"
        assert len(result[0]["answers"]) == 2
        assert result[0]["answers"][0]["response_count"] == 25

    @pytest.mark.asyncio
    async def test_open_text_questions(self, patch_db):
        from app.agents.tools.on24_query_tools import query_polls
        patch_db.fetch.side_effect = [
            [],  # no MC
            make_records([
                {"question_id": 20, "question_text": "Feedback?",
                 "question_type_cd": "singletext", "response_count": 10,
                 "sample_answers": ["Great!", "Loved it", "More demos"]},
            ]),
        ]
        result = await query_polls(event_id=100)
        assert len(result) == 1
        assert result[0]["sample_answers"] == ["Great!", "Loved it", "More demos"]
        assert "answers" not in result[0]


# ---------- query_questions ----------

class TestQueryQuestions:
    @pytest.mark.asyncio
    async def test_returns_questions(self, patch_db):
        from app.agents.tools.on24_query_tools import query_questions
        patch_db.fetch.return_value = make_records([
            {"question_id": 1, "question_text": "How does this work?",
             "first_name": "Jane", "last_name": "Doe", "company": "Acme",
             "create_timestamp": datetime(2026, 3, 10, 14, 30),
             "answered_status": "answered", "question_subtype_cd": "userquestion",
             "answer_text": "It works like this."},
        ])
        result = await query_questions(event_id=100)
        assert len(result) == 1
        assert result[0]["question_text"] == "How does this work?"
        assert result[0]["answer_text"] == "It works like this."

    @pytest.mark.asyncio
    async def test_limit_clamped(self, patch_db):
        from app.agents.tools.on24_query_tools import query_questions
        patch_db.fetch.return_value = []
        await query_questions(event_id=100, limit=500)
        # limit should be clamped to 200
        args = patch_db.fetch.call_args[0]
        assert args[3] == 200  # $3 = limit param


# ---------- query_top_events_by_polls ----------

class TestQueryTopEventsByPolls:
    @pytest.mark.asyncio
    async def test_returns_ranked_events(self, patch_db):
        from app.agents.tools.on24_query_tools import query_top_events_by_polls
        patch_db.fetch.return_value = make_records([
            {"event_id": 1, "description": "Event A", "goodafter": datetime(2026, 3, 1),
             "poll_count": 5, "respondent_count": 120},
            {"event_id": 2, "description": "Event B", "goodafter": datetime(2026, 2, 15),
             "poll_count": 3, "respondent_count": 80},
        ])
        result = await query_top_events_by_polls(limit=5, months=6)
        assert len(result) == 2
        assert result[0]["respondent_count"] == 120


# ---------- query_poll_overview ----------

class TestQueryPollOverview:
    @pytest.mark.asyncio
    async def test_returns_overview(self, patch_db):
        from app.agents.tools.on24_query_tools import query_poll_overview
        patch_db.fetch.return_value = make_records([
            {"event_id": 1, "description": "Event A", "goodafter": datetime(2026, 3, 1),
             "poll_count": 5, "respondent_count": 100},
        ])
        result = await query_poll_overview(months=3)
        assert len(result) == 1
        assert result[0]["poll_count"] == 5


# ---------- query_top_events ----------

class TestQueryTopEvents:
    @pytest.mark.asyncio
    async def test_sort_by_attendees(self, patch_db):
        from app.agents.tools.on24_query_tools import query_top_events
        patch_db.fetch.return_value = make_records([
            {"event_id": 1, "description": "Big Event", "event_type": "webcast",
             "goodafter": datetime(2026, 3, 1), "is_active": "Y",
             "total_attendees": 500, "total_registrants": 800,
             "avg_engagement": Decimal("75.123")},
        ])
        result = await query_top_events(sort_by="attendees")
        assert result[0]["avg_engagement"] == 75.12
        assert result[0]["total_attendees"] == 500

    @pytest.mark.asyncio
    async def test_sort_by_engagement(self, patch_db):
        from app.agents.tools.on24_query_tools import query_top_events
        patch_db.fetch.return_value = make_records([
            {"event_id": 1, "description": "Engaged Event", "event_type": "webcast",
             "goodafter": datetime(2026, 3, 1), "is_active": "Y",
             "total_attendees": 100, "total_registrants": 200,
             "avg_engagement": Decimal("90.0")},
        ])
        result = await query_top_events(sort_by="engagement")
        assert result[0]["avg_engagement"] == 90.0

    @pytest.mark.asyncio
    async def test_invalid_sort_falls_back(self, patch_db):
        from app.agents.tools.on24_query_tools import query_top_events
        patch_db.fetch.return_value = []
        # "invalid" sort_by should fall back to total_attendees without error
        result = await query_top_events(sort_by="invalid")
        assert result == []


# ---------- query_attendance_trends ----------

class TestQueryAttendanceTrends:
    @pytest.mark.asyncio
    async def test_returns_monthly_trends(self, patch_db):
        from app.agents.tools.on24_query_tools import query_attendance_trends
        patch_db.fetch.return_value = make_records([
            {"period": datetime(2026, 1, 1), "event_count": 5,
             "total_registrants": 500, "total_attendees": 300,
             "avg_engagement": Decimal("68.5")},
            {"period": datetime(2026, 2, 1), "event_count": 3,
             "total_registrants": 300, "total_attendees": 180,
             "avg_engagement": Decimal("72.3")},
        ])
        result = await query_attendance_trends(months=12)
        assert len(result) == 2
        assert result[0]["period"] == "2026-01-01T00:00:00"
        assert result[1]["avg_engagement"] == 72.3


# ---------- query_audience_companies ----------

class TestQueryAudienceCompanies:
    @pytest.mark.asyncio
    async def test_cross_event_mode(self, patch_db):
        from app.agents.tools.on24_query_tools import query_audience_companies
        patch_db.fetch.return_value = make_records([
            {"company": "Acme Corp", "events_attended": 3,
             "total_registrants": 25, "total_attendees": 18,
             "avg_engagement": Decimal("70.5")},
        ])
        result = await query_audience_companies(limit=10, months=3)
        assert result[0]["company"] == "Acme Corp"
        assert result[0]["avg_engagement"] == 70.5

    @pytest.mark.asyncio
    async def test_single_event_mode(self, patch_db):
        from app.agents.tools.on24_query_tools import query_audience_companies
        patch_db.fetch.return_value = make_records([
            {"company": "Globex", "total_registrants": 10,
             "total_attendees": 8, "avg_engagement": Decimal("55.0")},
        ])
        result = await query_audience_companies(event_id=100)
        assert result[0]["company"] == "Globex"

    @pytest.mark.asyncio
    async def test_exclude_filter(self, patch_db):
        from app.agents.tools.on24_query_tools import query_audience_companies
        patch_db.fetch.return_value = []
        await query_audience_companies(exclude=["internal", "test"])
        # Should have called with exclude params appended
        call_args = patch_db.fetch.call_args
        positional = call_args[0]
        # Last two positional args should be the exclude strings
        assert "internal" in positional
        assert "test" in positional


# ---------- query_audience_sources ----------

class TestQueryAudienceSources:
    @pytest.mark.asyncio
    async def test_with_event_id(self, patch_db):
        from app.agents.tools.on24_query_tools import query_audience_sources
        patch_db.fetch.return_value = make_records([
            {"source": "linkedin", "registrant_count": 50, "attendee_count": 30},
            {"source": "email", "registrant_count": 40, "attendee_count": 25},
        ])
        result = await query_audience_sources(event_id=100)
        assert len(result) == 2
        assert result[0]["source"] == "linkedin"

    @pytest.mark.asyncio
    async def test_without_event_id(self, patch_db):
        from app.agents.tools.on24_query_tools import query_audience_sources
        patch_db.fetch.return_value = make_records([
            {"source": "organic", "registrant_count": 100, "attendee_count": 60},
        ])
        result = await query_audience_sources()
        assert result[0]["source"] == "organic"


# ---------- query_events_by_tag ----------

class TestQueryEventsByTag:
    @pytest.mark.asyncio
    async def test_list_all_tags(self, patch_db):
        from app.agents.tools.on24_query_tools import query_events_by_tag
        patch_db.fetch.return_value = make_records([
            {"tag": "Webinars", "tag_type": "campaign", "event_count": 10,
             "avg_engagement": Decimal("65.0"), "total_registrants": 500,
             "total_attendees": 300},
        ])
        result = await query_events_by_tag(tag=None)
        assert result[0]["tag"] == "Webinars"

    @pytest.mark.asyncio
    async def test_filter_by_tag(self, patch_db):
        from app.agents.tools.on24_query_tools import query_events_by_tag
        patch_db.fetch.return_value = make_records([
            {"event_id": 1, "description": "Demo Event", "goodafter": datetime(2026, 3, 1),
             "event_type": "webcast", "tag_name": "Demo", "tag_type": "campaign",
             "registrant_count": 50, "attendee_count": 30,
             "avg_engagement": Decimal("70.0")},
        ])
        result = await query_events_by_tag(tag="Demo")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_aggregate_mode(self, patch_db):
        from app.agents.tools.on24_query_tools import query_events_by_tag
        patch_db.fetch.return_value = make_records([
            {"tag": "EMEA", "tag_type": "campaign", "event_count": 5,
             "total_registrants": 250, "total_attendees": 150,
             "avg_engagement": Decimal("68.0"), "avg_conversion_rate": Decimal("60.0")},
        ])
        result = await query_events_by_tag(tag="EMEA", aggregate=True)
        assert result[0]["event_count"] == 5


# ---------- query_resources ----------

class TestQueryResources:
    @pytest.mark.asyncio
    async def test_returns_resources(self, patch_db):
        from app.agents.tools.on24_query_tools import query_resources
        patch_db.fetch.return_value = make_records([
            {"resource_name": "Whitepaper.pdf", "downloader_count": 45, "total_hits": 78},
            {"resource_name": "Slides.pptx", "downloader_count": 30, "total_hits": 42},
        ])
        result = await query_resources(event_id=100)
        assert len(result) == 2
        assert result[0]["resource_name"] == "Whitepaper.pdf"
        assert result[0]["downloader_count"] == 45

    @pytest.mark.asyncio
    async def test_limit_clamped(self, patch_db):
        from app.agents.tools.on24_query_tools import query_resources
        patch_db.fetch.return_value = []
        await query_resources(event_id=100, limit=200)
        args = patch_db.fetch.call_args[0]
        assert args[3] == 100  # clamped to max 100


# ---------- query_ai_content ----------

class TestQueryAiContent:
    @pytest.mark.asyncio
    async def test_returns_content(self, patch_db):
        from app.agents.tools.on24_query_tools import query_ai_content
        patch_db.fetch.return_value = make_records([
            {"content_type": "BLOG", "title": "AI Insights",
             "content": "<p>Great article</p>", "event_id": 100,
             "event_title": "Big Webinar", "created_at": datetime(2026, 3, 10)},
        ])
        result = await query_ai_content(content_type="BLOG", limit=3)
        assert len(result) == 1
        assert result[0]["content_type"] == "BLOG"
        assert result[0]["created_at"] == "2026-03-10T00:00:00"

    @pytest.mark.asyncio
    async def test_skips_empty_content_type(self, patch_db):
        from app.agents.tools.on24_query_tools import query_ai_content
        patch_db.fetch.return_value = make_records([
            {"content_type": "", "title": "Empty", "content": "x",
             "event_id": 1, "event_title": "E", "created_at": datetime(2026, 1, 1)},
            {"content_type": "FAQ", "title": "Real", "content": "y",
             "event_id": 2, "event_title": "F", "created_at": datetime(2026, 1, 2)},
        ])
        result = await query_ai_content()
        assert len(result) == 1
        assert result[0]["content_type"] == "FAQ"

    @pytest.mark.asyncio
    async def test_truncates_long_content(self, patch_db):
        from app.agents.tools.on24_query_tools import query_ai_content
        long_content = "x" * 10000
        patch_db.fetch.return_value = make_records([
            {"content_type": "BLOG", "title": "Long", "content": long_content,
             "event_id": 1, "event_title": "E", "created_at": datetime(2026, 1, 1)},
        ])
        result = await query_ai_content()
        assert len(result[0]["content"]) == 8000

    @pytest.mark.asyncio
    async def test_limit_clamped_to_10(self, patch_db):
        from app.agents.tools.on24_query_tools import query_ai_content
        patch_db.fetch.return_value = []
        await query_ai_content(limit=50)
        args = patch_db.fetch.call_args[0]
        # limit param should be clamped to 10
        assert args[2] == 10

    @pytest.mark.asyncio
    async def test_handles_none_created_at(self, patch_db):
        from app.agents.tools.on24_query_tools import query_ai_content
        patch_db.fetch.return_value = make_records([
            {"content_type": "FAQ", "title": "No Date", "content": "content",
             "event_id": 1, "event_title": "E", "created_at": None},
        ])
        result = await query_ai_content()
        assert result[0]["created_at"] is None
