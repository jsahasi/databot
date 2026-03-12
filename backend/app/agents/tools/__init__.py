"""Tool definitions for agent system.

Each tool is defined as:
1. A schema dict (for Anthropic API tool_use)
2. An async handler function (for execution)
"""

from app.agents.tools.on24_query_tools import (
    query_events,
    get_event_detail,
    query_attendees,
    compute_event_kpis,
    compute_client_kpis,
    query_polls,
    query_questions,
    query_top_events,
    query_top_events_by_polls,
    query_poll_overview,
    query_attendance_trends,
    query_audience_companies,
    query_audience_sources,
    query_resources,
    generate_chart_data,
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
        "name": "list_events",
        "description": (
            "List and search events for the current client. "
            "Use past_only=true when the user asks for their 'last' or 'most recent' event "
            "to exclude future-dated events. Returns event_id, description (title), goodafter (date), type, status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search term matched against event name (case-insensitive)"},
                "event_type": {"type": "string", "description": "Filter by event type (e.g. 'Webcast', 'SimLive')"},
                "is_active": {"type": "string", "enum": ["Y", "N"], "description": "Filter by active status"},
                "limit": {"type": "integer", "description": "Max results to return (default 20)"},
                "offset": {"type": "integer", "description": "Pagination offset (default 0)"},
                "past_only": {"type": "boolean", "description": "If true, only return events with a date in the past (goodafter <= now). Use for 'last event' queries."},
            },
        },
    },
    {
        "name": "get_event_detail",
        "description": (
            "Fetch full details for a single ON24 event by its event_id. "
            "Automatically verifies the event belongs to the current client."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "ON24 event ID to look up"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_attendees",
        "description": (
            "Retrieve attendees for a specific ON24 event, including engagement scores, "
            "live minutes, archive minutes, company, and job title. "
            "Automatically verifies the event belongs to the current client."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "ON24 event ID"},
                "limit": {"type": "integer", "description": "Max results (default 100)"},
                "offset": {"type": "integer", "description": "Pagination offset (default 0)"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_event_kpis",
        "description": (
            "Compute KPIs for a single ON24 event: total registrants, total attendees, "
            "average engagement score, average live minutes, and conversion rate. "
            "Automatically verifies the event belongs to the current client."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "ON24 event ID"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_client_kpis",
        "description": (
            "Compute platform-wide KPIs across all events for the current client: "
            "total events, total registrants, total attendees, and average engagement score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_polls",
        "description": (
            "Retrieve poll questions and answer distributions for a specific ON24 event. "
            "Returns each poll question with its answer options and response counts. "
            "Automatically verifies the event belongs to the current client."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "ON24 event ID"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_questions",
        "description": (
            "Retrieve Q&A questions asked by attendees during a specific ON24 event. "
            "Returns question text, asker name/company, timestamp, answered status, and answer text if answered. "
            "Use for 'what questions were asked', 'Q&A', 'audience questions'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "ON24 event ID"},
                "limit": {"type": "integer", "description": "Max questions to return (default 50)"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_top_events",
        "description": (
            "Retrieve the top-performing events for the current client, ranked by attendees, "
            "engagement score, or registrants."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of top events to return (default 10)"},
                "sort_by": {
                    "type": "string",
                    "enum": ["attendees", "engagement", "registrants"],
                    "description": "Metric to rank events by (default: attendees)",
                },
            },
        },
    },
    {
        "name": "get_top_events_by_polls",
        "description": (
            "Return the top events ranked by number of poll questions asked. "
            "Use when the user asks which events had the most polls, or wants to find poll-heavy events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of top events to return (default 10)"},
            },
        },
    },
    {
        "name": "get_poll_overview",
        "description": (
            "Cross-event poll summary: lists recent events that ran polls, with poll question count "
            "and total attendee responses per event. Use for 'poll overview', 'poll results overview', "
            "'how are polls performing', or any request for a summary of poll activity across events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "months": {"type": "integer", "description": "How many past months to include (default 6)"},
            },
        },
    },
    {
        "name": "get_attendance_trends",
        "description": (
            "Return monthly attendance and registration trend data for the current client "
            "over the past N months. Useful for time-series charts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "months": {"type": "integer", "description": "Number of past months to include (default 12)"},
            },
        },
    },
    {
        "name": "get_audience_companies",
        "description": (
            "Return the top companies attending the current client's events, ranked by total attendance. "
            "Includes event count, registrant count, attendee count, and average engagement per company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of top companies to return (default 20)"},
            },
        },
    },
    {
        "name": "get_audience_sources",
        "description": (
            "Return audience traffic sources (partnerref) showing where registrants came from — "
            "campaign links, source sites, or UTM-style tags embedded in the registration URL. "
            "Returns registrant and attendee count per source. "
            "ONLY call this if the user asks about traffic sources, referral sources, campaigns, or where registrants came from. "
            "If the result is empty, do NOT show a chart — respond with 'None found.' instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "Scope to a single event (omit for all events)"},
                "limit": {"type": "integer", "description": "Max sources to return (default 20)"},
            },
        },
    },
    {
        "name": "get_resources",
        "description": (
            "Retrieve resource download/hit activity for a specific ON24 event. "
            "Returns resource names, types, and hit timestamps. "
            "Automatically verifies the event belongs to the current client."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "ON24 event ID"},
                "limit": {"type": "integer", "description": "Max results (default 50)"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "generate_chart_data",
        "description": (
            "Format data from a previous tool call into a chart for the frontend. "
            "Call this after get_attendance_trends, get_top_events, get_top_events_by_polls, "
            "get_poll_overview, or get_audience_companies whenever a chart is appropriate. "
            "Pass the full data array returned by the previous tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "The data array from the previous tool call",
                    "items": {"type": "object"},
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie"],
                    "description": "Chart type: 'line' for time series, 'bar' for comparisons, 'pie' for part-of-whole distributions",
                },
                "x_key": {
                    "type": "string",
                    "description": "Field to use as x-axis label (e.g. 'period', 'description')",
                },
                "y_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Metric fields to plot (omit to auto-detect all numeric fields)",
                },
                "title": {"type": "string", "description": "Chart title"},
                "y_label": {"type": "string", "description": "Optional y-axis label"},
            },
            "required": ["data", "chart_type", "x_key"],
        },
    },
]

# Map tool names to handler functions
TOOL_HANDLERS = {
    "list_events": query_events,
    "get_event_detail": get_event_detail,
    "get_attendees": query_attendees,
    "get_event_kpis": compute_event_kpis,
    "get_client_kpis": compute_client_kpis,
    "get_polls": query_polls,
    "get_questions": query_questions,
    "get_top_events": query_top_events,
    "get_top_events_by_polls": query_top_events_by_polls,
    "get_poll_overview": query_poll_overview,
    "get_attendance_trends": query_attendance_trends,
    "get_audience_companies": query_audience_companies,
    "get_audience_sources": query_audience_sources,
    "get_resources": query_resources,
    "generate_chart_data": generate_chart_data,
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
