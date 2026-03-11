"""Tool definitions for agent system.

Each tool is defined as:
1. A schema dict (for Anthropic API tool_use)
2. An async handler function (for execution)
"""

from app.agents.tools.query_tools import (
    query_events,
    query_attendees,
    query_registrants,
    compute_kpis,
    generate_chart_data,
    run_analytics_query,
)
from app.agents.tools.content_tools import (
    analyze_topic_performance,
    compare_event_performance,
    analyze_scheduling_patterns,
    suggest_topics,
)
from app.agents.tools.admin_tools import (
    create_event,
    update_event,
    add_registrant,
    remove_registrant,
    get_event_summary,
)

# Tool schemas for Anthropic API
DATA_AGENT_TOOLS = [
    {
        "name": "query_events",
        "description": "Search and filter events from the database. Returns event list with metadata and analytics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search term for event title"},
                "event_type": {"type": "string", "description": "Filter by event type (e.g. 'Webcast')"},
                "date_from": {"type": "string", "description": "Start date filter (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date filter (YYYY-MM-DD)"},
                "sort_by": {"type": "string", "enum": ["live_start", "total_attendees", "engagement_score", "title"], "description": "Sort field"},
                "sort_order": {"type": "string", "enum": ["asc", "desc"], "description": "Sort direction"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
        },
    },
    {
        "name": "query_attendees",
        "description": "Query attendees with optional filters. Returns attendee details with engagement metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "Filter by ON24 event ID"},
                "email": {"type": "string", "description": "Search by email address"},
                "company": {"type": "string", "description": "Filter by company name"},
                "min_engagement": {"type": "number", "description": "Minimum engagement score filter"},
                "sort_by": {"type": "string", "enum": ["engagement_score", "live_minutes", "email"], "description": "Sort field"},
                "limit": {"type": "integer", "description": "Max results (default 50)"},
            },
        },
    },
    {
        "name": "query_registrants",
        "description": "Query registrants with optional filters. Returns registration details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "Filter by ON24 event ID"},
                "company": {"type": "string", "description": "Filter by company name"},
                "limit": {"type": "integer", "description": "Max results (default 50)"},
            },
        },
    },
    {
        "name": "compute_kpis",
        "description": "Compute analytics KPIs like total events, avg engagement, conversion rate. Can scope to an event or date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "Scope to a specific event ID"},
                "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            },
        },
    },
    {
        "name": "generate_chart_data",
        "description": "Generate data formatted for chart rendering. Specify chart type, metric, and grouping.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": ["line", "bar", "pie"], "description": "Chart type"},
                "metric": {"type": "string", "enum": ["attendees", "registrants", "engagement", "events"], "description": "Metric to chart"},
                "group_by": {"type": "string", "enum": ["month", "week", "event_type", "company"], "description": "Grouping dimension"},
                "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "limit": {"type": "integer", "description": "Max data points (default 12)"},
            },
            "required": ["chart_type"],
        },
    },
    {
        "name": "run_analytics_query",
        "description": "Run a predefined analytics query. Options: 'top_companies', 'registration_sources', 'no_show_analysis'",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "enum": ["top_companies", "registration_sources", "no_show_analysis"], "description": "Query to run"},
                "event_id": {"type": "integer", "description": "Optional event ID to scope the query"},
            },
            "required": ["description"],
        },
    },
]

# Map tool names to handler functions
TOOL_HANDLERS = {
    "query_events": query_events,
    "query_attendees": query_attendees,
    "query_registrants": query_registrants,
    "compute_kpis": compute_kpis,
    "generate_chart_data": generate_chart_data,
    "run_analytics_query": run_analytics_query,
}

CONTENT_AGENT_TOOLS = [
    {
        "name": "analyze_topic_performance",
        "description": "Analyze which event types/topics drive the highest engagement and attendance rates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_events": {"type": "integer", "description": "Minimum events per type to include (default 3)"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
        },
    },
    {
        "name": "compare_event_performance",
        "description": "Side-by-side performance comparison of specific events by their ON24 event IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of ON24 event IDs to compare"},
            },
            "required": ["event_ids"],
        },
    },
    {
        "name": "analyze_scheduling_patterns",
        "description": "Find the best day of week and time of day for scheduling events based on historical performance.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "suggest_topics",
        "description": "Generate topic/content suggestions based on top-performing past events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "based_on": {"type": "string", "enum": ["engagement", "attendance"], "description": "Metric to base suggestions on"},
                "limit": {"type": "integer", "description": "Number of suggestions (default 5)"},
            },
        },
    },
]

CONTENT_TOOL_HANDLERS = {
    "analyze_topic_performance": analyze_topic_performance,
    "compare_event_performance": compare_event_performance,
    "analyze_scheduling_patterns": analyze_scheduling_patterns,
    "suggest_topics": suggest_topics,
}

# Admin Agent tools — write operations against ON24 API
ADMIN_AGENT_TOOLS = [
    {
        "name": "get_event_summary",
        "description": "Fetch a summary of an ON24 event from the local database (read-only). Use this before destructive operations to show the user what will be affected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "on24_event_id": {"type": "integer", "description": "The ON24 event ID to look up"},
            },
            "required": ["on24_event_id"],
        },
    },
    {
        "name": "create_event",
        "description": "Create a new ON24 webinar/event. Requires confirmation before execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "event_type": {"type": "string", "description": "Event type (e.g. 'Webcast', 'SimLive')"},
                "start_time": {"type": "string", "description": "Start time in ISO 8601 format"},
                "end_time": {"type": "string", "description": "End time in ISO 8601 format"},
                "description": {"type": "string", "description": "Optional event description"},
            },
            "required": ["title", "event_type", "start_time", "end_time"],
        },
    },
    {
        "name": "update_event",
        "description": "Update fields on an existing ON24 event. Requires confirmation before execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "on24_event_id": {"type": "integer", "description": "The ON24 event ID to update"},
                "title": {"type": "string", "description": "New event title"},
                "description": {"type": "string", "description": "New event description"},
                "start_time": {"type": "string", "description": "New start time in ISO 8601 format"},
                "end_time": {"type": "string", "description": "New end time in ISO 8601 format"},
            },
            "required": ["on24_event_id"],
        },
    },
    {
        "name": "add_registrant",
        "description": "Register a person for an ON24 event. Requires confirmation before execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "on24_event_id": {"type": "integer", "description": "The ON24 event ID"},
                "email": {"type": "string", "description": "Registrant email address"},
                "first_name": {"type": "string", "description": "Registrant first name"},
                "last_name": {"type": "string", "description": "Registrant last name"},
                "company": {"type": "string", "description": "Registrant company (optional)"},
                "job_title": {"type": "string", "description": "Registrant job title (optional)"},
            },
            "required": ["on24_event_id", "email", "first_name", "last_name"],
        },
    },
    {
        "name": "remove_registrant",
        "description": "Remove a registrant from an ON24 event. Requires confirmation before execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "on24_event_id": {"type": "integer", "description": "The ON24 event ID"},
                "email": {"type": "string", "description": "Email address of the registrant to remove"},
            },
            "required": ["on24_event_id", "email"],
        },
    },
]

ADMIN_TOOL_HANDLERS = {
    "get_event_summary": get_event_summary,
    "create_event": create_event,
    "update_event": update_event,
    "add_registrant": add_registrant,
    "remove_registrant": remove_registrant,
}
