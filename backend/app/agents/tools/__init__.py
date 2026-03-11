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
