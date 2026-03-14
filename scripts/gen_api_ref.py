"""Generate data/on24_api_reference.json"""
import json, os

data = {
    "source": "ON24 REST API v2",
    "base_urls": {"na": "https://api.on24.com", "eu": "https://api.eu.on24.com", "qa": "https://apiqa.on24.com"},
    "authentication": {
        "description": "All requests require accessTokenKey and accessTokenSecret headers.",
        "headers": ["accessTokenKey", "accessTokenSecret"]
    },
    "endpoints": []
}
e = data["endpoints"]

def ep(id, cat, name, method, path, desc, params=None, notes="", ct="application/json"):
    e.append({"id":id,"category":cat,"name":name,"method":method,"path":path,"content_type":ct,
              "description":desc,"parameters":params or [],"notes":notes})

def p(name, typ="string", req=False, desc=""):
    return {"name":name,"type":typ,"required":req,"description":desc}

B = "/v2/client/{clientId}"
BE = B + "/event/{eventId}"

# === Client Analytics (15) ===
C = "Client Analytics"
ep("client_events",C,"List Events","GET",B+"/event","List all events with optional date/type filters. Returns paginated event metadata.",
   [p("startDate",desc="YYYY-MM-DD"),p("endDate",desc="YYYY-MM-DD"),p("includeInactive",desc="Y/N"),
    p("contentType",desc="all/webcast/simulive/ondemand/always/virtual/hybrid"),
    p("itemsPerPage","integer",desc="Results per page"),p("pageOffset","integer",desc="Page number")])
ep("client_attendees",C,"Client Attendees","GET",B+"/attendee","List attendees across all events. Returns engagement metrics and session details. Paginated.",
   [p("startDate"),p("endDate"),p("itemsPerPage","integer"),p("pageOffset","integer")])
ep("attendee_by_email",C,"Attendee by Email","GET",B+"/attendee/{email}","Get most recent attendance for an email. Returns engagement score and viewing time.",
   [p("email",req=True,desc="Path parameter")])
ep("attendee_all_events",C,"Attendee All Events","GET",B+"/attendee/{email}/allevents","Get attendance across all events for an email. Paginated.",
   [p("email",req=True,desc="Path parameter"),p("pageOffset","integer"),p("itemsPerPage","integer")])
ep("client_registrants",C,"Client Registrants","GET",B+"/registrant","List registrants across all events. Paginated.",
   [p("startDate"),p("endDate"),p("itemsPerPage","integer"),p("pageOffset","integer")])
ep("registrant_by_email",C,"Registrant by Email","GET",B+"/registrant/{email}","Get registration for an email. Optionally filter by event or partner ref.",
   [p("email",req=True,desc="Path parameter"),p("eventId","integer"),p("partnerref")])
ep("registrant_all_events",C,"Registrant All Events","GET",B+"/registrant/{email}/allevents","Get all registrations across events for an email. Supports sub-account filtering.",
   [p("email",req=True,desc="Path parameter"),p("excludeSubaccounts","boolean"),p("subaccounts",desc="Comma-separated IDs"),p("pageOffset","integer"),p("itemsPerPage","integer")])
ep("survey_library",C,"Client Survey Library","GET",B+"/surveylibrary","Get reusable survey question library. Returns templates with questions and answer options.")
ep("engaged_accounts",C,"Engaged Accounts","GET",B+"/engagedaccount","Top engaged accounts from last 90 days (max 100). Useful for ABM targeting.",notes="90-day lookback, max 100 results.")
ep("client_leads",C,"Client Leads","GET",B+"/lead","List leads across all events. Returns lead scores and engagement levels. Paginated.",
   [p("startDate"),p("endDate"),p("itemsPerPage","integer"),p("pageOffset","integer")])
ep("pep",C,"Prospect Engagement Profile","GET",B+"/lead/{email}","Get PEP score and engagement history for an email across all touchpoints.",
   [p("email",req=True,desc="Path parameter")])
ep("client_presenters",C,"Client Presenters","GET",B+"/presenter","List all presenters across the client account.")
ep("sub_clients",C,"Sub-Clients","GET",B,"List sub-client accounts under this client.",notes="Special path: no trailing segment.")
ep("user_questions",C,"Real-time User Questions","GET",B+"/userquestions","Questions submitted in last 5 minutes across live events. Real-time Q&A monitoring.",
   [p("excludesubaccounts","boolean"),p("emailFilter"),p("startDate"),p("endDate")],notes="Returns last 5 min of data.")
ep("client_users",C,"Users","GET",B+"/users","List platform users for the client account. Returns names, emails, roles.")

# === Event Analytics (16) ===
E = "Event Analytics"
ep("event_attendees",E,"Event Attendees","GET",BE+"/attendee","List attendees for a specific event with engagement data. Paginated.",
   [p("startDate"),p("endDate"),p("itemsPerPage","integer"),p("pageOffset","integer")])
ep("event_viewing_sessions",E,"Attendee Viewing Sessions","GET",BE+"/attendeesession","Get viewing session data for an event. Shows live vs on-demand session breakdowns.",
   [p("sessionType",desc="all/live/simulive/od"),p("pageoffset","integer"),p("itemsPerPage","integer")])
ep("event_cta",E,"Call to Action","GET",BE+"/cta","Get CTA click activity for an event. Shows which CTAs were clicked and by whom.")
ep("event_certifications",E,"Certifications","GET",BE+"/certifications","Get certification completions for an event.")
ep("event_content_activity",E,"Engagement Hub Content Activity","GET",BE+"/contentactivity","Get content interaction data for an Engagement Hub event.")
ep("event_calendar_reminder",E,"Email Calendar Reminder","GET",BE+"/calendarreminder","Get calendar reminder configuration for an event.")
ep("event_email_details",E,"Email Notification Details","GET",BE+"/email","Get email notification configurations for an event. Returns all email templates.")
ep("event_email_stats",E,"Email Statistics","GET",BE+"/emailstatistics","Get email send/open/click statistics for an event.")
ep("event_group_chat",E,"Group Chat Activity","GET",BE+"/groupchat","Get group chat messages and activity for an event.")
ep("event_metadata",E,"Event Metadata and Usage","GET",BE,"Get full event details including title, dates, type, and aggregate engagement stats.",
   [p("eventId","integer",True,"Path parameter")])
ep("event_polls",E,"Polls","GET",BE+"/poll","Get poll questions and responses for an event.")
ep("event_presenter_chat",E,"Presentation Manager Chat Logs","GET",BE+"/presenterchat","Get presenter-to-presenter chat logs from an event.")
ep("event_presenters",E,"Event Presenters","GET",BE+"/presenter","Get presenters assigned to a specific event.")
ep("event_registrants",E,"Event Registrants","GET",BE+"/registrant","List registrants for a specific event. Paginated. Can filter for no-shows.",
   [p("startDate"),p("endDate"),p("itemsPerPage","integer"),p("pageOffset","integer"),p("noshow",desc="Y/N")])
ep("event_resources",E,"Resources Viewed","GET",BE+"/resource","Get resource download/view activity for an event.")
ep("event_surveys",E,"Surveys","GET",BE+"/survey","Get survey questions and responses for an event.")

# === Registration (7) ===
R = "Registration"
ep("register_attendee",R,"REST Registration","POST",BE+"/registrant","Register a person for an event. Requires email, firstname, lastname. Supports custom fields.",
   [p("email",req=True),p("firstname",req=True),p("lastname",req=True),p("company"),p("jobtitle"),
    p("std1"),p("std2"),p("std3"),p("std4"),p("std5"),p("std6"),p("std7"),
    p("honorrequired","boolean",desc="Query param: honor required fields"),
    p("honorvalidation","boolean",desc="Query param: honor field validation")],
   ct="application/x-www-form-urlencoded")
ep("update_event_registrant",R,"Update Registrant (Event Level)","PATCH",BE+"/registrant","Update registrant fields at event level.",
   [p("email",req=True),p("firstname"),p("lastname"),p("company"),p("jobtitle"),
    p("honorrequired","boolean",desc="Query param"),p("honorvalidation","boolean",desc="Query param")],
   ct="application/x-www-form-urlencoded")
ep("update_client_registrant",R,"Update Registrant (Client Level)","PATCH",B+"/registrant/{email}","Update registrant fields across all events at client level.",
   [p("email",desc="New email address"),p("firstname"),p("lastname"),p("company"),p("jobtitle")],
   ct="application/x-www-form-urlencoded")
ep("forget_registrant",R,"Forget Registrant","POST",B+"/forget","GDPR: Nullify all PII for registrant(s). Email becomes {id}-deleted, names become 'deleted'.",
   [p("email",req=True,desc="Comma-separated for multiple"),p("eventid",desc="Optional event scope")],
   notes="GDPR compliance endpoint.",ct="application/x-www-form-urlencoded")
ep("forget_all_event",R,"Forget All (Event Level)","POST",BE+"/forgetall","GDPR: Nullify all PII for all registrants in an event.",
   notes="GDPR. Irreversible.")
ep("forget_all_workspace",R,"Forget All (Workspace Level)","POST",B+"/forgetall","GDPR: Nullify all PII for all registrants across the entire workspace.",
   notes="DESTRUCTIVE. Irreversible. Affects all events.")
ep("remove_registration",R,"Remove Registration","DELETE",BE+"/registrant/{email}","Remove a registrant from an event by email.",
   [p("email",req=True,desc="Path parameter")])

# === Event Management (17) ===
M = "Event Management"
ep("copy_webinar",M,"Copy a Webinar","POST",B+"/event","Copy an existing webinar to create a new event with the same settings.",
   [p("eventsource","integer",True,desc="Query param: source event ID"),p("liveStart",req=True),
    p("liveDuration","integer"),p("title"),p("languageCd"),p("timeZone"),p("campaignCode"),
    p("tagCampaign"),p("customAccountTag"),p("archiveAvailable"),p("testevent"),
    p("hybrid"),p("venue"),p("address"),p("promotionalSummary"),p("countryCd")],
   ct="application/x-www-form-urlencoded")
ep("create_webinar",M,"Create a Webinar","POST",B+"/event","Create a new webinar with full configuration options.",
   [p("title",req=True),p("liveStart",req=True),p("liveDuration","integer",True),
    p("eventType",req=True),p("languageCd",req=True),p("timeZone",req=True),
    p("eventAbstract"),p("campaignCode"),p("countryCd"),p("tagCampaign"),
    p("customAccountTag"),p("archiveAvailable"),p("promotionalSummary"),
    p("testevent"),p("hybrid"),p("venue"),p("address")],
   ct="application/x-www-form-urlencoded")
ep("create_related_content",M,"Create Related Content","POST",BE+"/relatedcontent","Upload related content (file or URL) for an event.",
   [p("matchname",req=True),p("name",req=True),p("type",desc="Resource or URL"),p("file",desc="File upload"),p("url")],
   ct="multipart/form-data")
ep("create_speaker_bio",M,"Create Speaker Bio","POST",BE+"/speakerbio","Create a speaker bio with optional image for an event.",
   [p("metadata",desc="JSON with speaker details"),p("file",desc="Speaker image")],
   ct="multipart/form-data")
ep("create_survey_questions",M,"Create Survey Questions","POST",BE+"/surveyquestions","Create survey questions for an event.",
   [p("metadata",req=True,desc="JSON body with surveyquestions array")])
ep("delete_speaker_bio",M,"Delete Speaker Bio","DELETE",BE+"/speakerbio","Delete all speaker bios for an event.")
ep("delete_vtt_files",M,"Delete VTT Files","DELETE",BE+"/vtt","Delete VTT caption files for an event.")
ep("delete_webinar",M,"Delete Webinar","DELETE",BE,"Delete a webinar entirely.",notes="Irreversible.")
ep("edit_webinar",M,"Edit a Webinar","PUT",BE,"Edit a webinar (full replacement). All required fields must be provided.",
   [p("title",req=True),p("liveStart",req=True),p("liveDuration","integer",True),
    p("eventType",req=True),p("languageCd",req=True),p("campaignCode"),p("countryCd")],
   notes="Full PUT — omitted optional fields reset to defaults.",ct="application/x-www-form-urlencoded")
ep("update_webinar",M,"Update a Webinar","PUT",BE,"Update specific webinar fields (partial update). Only provided fields change.",
   [p("title"),p("liveStart"),p("liveDuration","integer"),p("eventType"),p("languageCd"),
    p("countryCd"),p("timeZone"),p("tagCampaign"),p("campaignCode"),p("archiveAvailable"),
    p("promotionalSummary"),p("customAccountTag"),p("enableRegistration")],
   notes="Partial PUT — only send fields to change.",ct="application/x-www-form-urlencoded")
ep("upload_document",M,"Media Manager Upload Document","POST",B+"/mediamanager/document","Upload a document to Media Manager.",
   [p("file",req=True,desc="Document file"),p("metadata",desc="Optional JSON with id, title")],
   ct="multipart/form-data")
ep("upload_video",M,"Media Manager Upload Video","POST",B+"/mediamanager/uploadvideo","Upload a video to Media Manager.",
   [p("file",req=True,desc="Video file"),p("metadata",desc="Optional JSON with id, title")],
   ct="multipart/form-data")
ep("event_slides_listing",M,"Slide Listing","GET",BE+"/slides","Get the slide listing for an event.")
ep("update_calendar_reminder",M,"Update Email Calendar Reminder","PUT",BE+"/calendarreminder","Update calendar reminder settings for an event.",
   [p("reminder"),p("subject"),p("location"),p("body")],ct="application/x-www-form-urlencoded")
ep("update_email_notification",M,"Update Email Notification","PUT",BE+"/email/{emailId}","Update an email notification template for an event.",
   [p("emailId","integer",True,desc="Path parameter"),p("activated"),p("whentosend"),p("goodafter"),
    p("fromlabel"),p("replyto"),p("subject"),p("body")],ct="application/x-www-form-urlencoded")
ep("upload_slides",M,"Upload Slides","POST",BE+"/slides","Upload PowerPoint slides for an event.",
   [p("file",req=True,desc="PowerPoint file")],ct="multipart/form-data")
ep("update_text_banner",M,"Update Text With Banner Widget","POST",BE+"/textwithbanner","Update the text-with-banner widget for an event.",
   [p("metadata",req=True,desc="JSON string with widget config")],ct="application/x-www-form-urlencoded")

# === Content Listings (3) ===
L = "Content Listings"
ep("ehub_content",L,"Engagement Hub Content Listing","GET",B+"/ehub/{gatewayId}/content","Get content listing for an Engagement Hub.",
   [p("gatewayId","integer",True,desc="Path parameter: Engagement Hub gateway ID")])
ep("media_manager_list",L,"Media Manager Derivative Content","GET",B+"/mediamanager","List Media Manager derivative content items. Paginated.",
   [p("startDate"),p("endDate"),p("pageOffset","integer"),p("itemsPerPage","integer")])
ep("media_manager_detail",L,"Media Manager Content Detail","GET",B+"/mediamanager/{mediaId}","Get a single Media Manager derivative content item.",
   [p("mediaId","integer",True,desc="Path parameter")])

# === Helper Endpoints (13) ===
H = "Helper Endpoints"
ep("custom_account_tags",H,"Custom Account Tags","GET",B+"/customaccounttag","Get custom account tags configured for the client.")
ep("account_managers",H,"Account Managers","GET",B+"/accountmanager","Get account manager contacts for the client.")
ep("event_types",H,"Event Types","GET",B+"/eventtypes","Get available event types (webcast, simulive, etc.).")
ep("language_codes",H,"Language Codes","GET",B+"/languages","Get available language codes for event configuration.")
ep("registration_fields",H,"Registration Fields","GET",BE+"/regfield","Get registration form fields configured for an event.",
   [p("eventId","integer",True,desc="Path parameter")])
ep("replacement_tokens",H,"Replacement Tokens","GET",B+"/tokens","Get available replacement tokens for email templates.",
   [p("context",desc="Optional context filter")])
ep("sales_reps",H,"Sales Rep Contacts","GET",B+"/salesrep","Get sales rep contacts for the client.")
ep("signal_contacts",H,"Signal Contacts","GET",B+"/signalrep","Get signal contacts for the client.")
ep("technical_reps",H,"Technical Rep Contacts","GET",B+"/technicalrep","Get technical rep contacts for the client.")
ep("timezones",H,"Timezones","GET",B+"/timezones","Get available timezone codes for event scheduling.")
ep("event_managers",H,"Event Managers","GET",B+"/eventmanager","Get event manager contacts for the client.")
ep("event_profiles",H,"Event Profiles","GET",B+"/eventprofile","Get event profile templates for the client.")
ep("users_list",H,"Users","GET",B+"/users","List platform users for the client. Same endpoint as Client Analytics > Users.",
   notes="Alias of client_users endpoint.")

out = os.path.join(os.path.dirname(__file__), "..", "data", "on24_api_reference.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print(f"Wrote {len(e)} endpoints to {out}")
