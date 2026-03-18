import logging
from typing import Any

import httpx

from app.config import settings
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class ON24APIError(Exception):
    """Raised when ON24 API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"ON24 API error {status_code}: {message}")


class ON24Client:
    """Async client for ON24 REST API v2."""

    def __init__(
        self,
        client_id: str | None = None,
        access_token_key: str | None = None,
        access_token_secret: str | None = None,
        base_url: str | None = None,
    ):
        self.client_id = client_id or settings.on24_client_id
        self.base_url = (base_url or settings.on24_base_url).rstrip("/")
        self._headers = {
            "accessTokenKey": access_token_key or settings.on24_access_token_key,
            "accessTokenSecret": access_token_secret or settings.on24_access_token_secret,
            "Accept": "application/json",
        }
        self._rate_limiter = RateLimiter()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=30.0,
            )
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _build_path(self, endpoint: str) -> str:
        """Build full API path with client ID."""
        return f"/v2/client/{self.client_id}/{endpoint.lstrip('/')}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        raw_path: bool = False,
    ) -> dict[str, Any]:
        """Make a rate-limited request to ON24 API.

        Args:
            method: HTTP method
            endpoint: API endpoint (appended to client path unless raw_path=True)
            params: Query parameters
            json_body: JSON request body
            form_data: Form-urlencoded request body (mutually exclusive with json_body)
            files: Multipart file uploads (mutually exclusive with json_body)
            raw_path: If True, endpoint is used as the full path (no _build_path)
        """
        path = endpoint if raw_path else self._build_path(endpoint)
        category = self._rate_limiter.get_category_for_endpoint(path)
        await self._rate_limiter.acquire(category)

        client = await self._get_client()
        logger.debug(f"ON24 {method} {path} params={params}")

        # Build request kwargs — json, form data, and files are mutually exclusive
        kwargs: dict[str, Any] = {"params": params}
        if files is not None:
            # multipart/form-data: httpx sets Content-Type with boundary automatically
            kwargs["files"] = files
            if form_data:
                kwargs["data"] = form_data
        elif form_data is not None:
            # application/x-www-form-urlencoded
            kwargs["data"] = form_data
        elif json_body is not None:
            kwargs["json"] = json_body

        response = await client.request(method, path, **kwargs)

        if response.status_code == 401:
            raise ON24APIError(401, "Invalid or deactivated API credentials")
        if response.status_code == 403:
            raise ON24APIError(403, "Permission denied or rate limit exceeded")
        if response.status_code == 404:
            raise ON24APIError(404, f"Resource not found: {path}")
        if response.status_code >= 400:
            raise ON24APIError(response.status_code, response.text)

        return response.json()

    async def _form_request(
        self,
        method: str,
        endpoint: str,
        form_data: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a rate-limited form-urlencoded request."""
        return await self._request(method, endpoint, params=params, form_data=form_data)

    async def _multipart_request(
        self,
        method: str,
        endpoint: str,
        form_data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a rate-limited multipart/form-data request."""
        return await self._request(method, endpoint, params=params, form_data=form_data, files=files)

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", endpoint, params=params, json_body=json_body)

    async def put(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PUT", endpoint, params=params, json_body=json_body)

    async def patch(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PATCH", endpoint, params=params, json_body=json_body)

    async def delete(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("DELETE", endpoint, params=params)

    # ── Client-Level Analytics ──

    async def list_events(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        include_inactive: bool = False,
        content_type: str = "all",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List events for the client."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
            "contentType": content_type,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if include_inactive:
            params["includeInactive"] = "Y"
        return await self.get("event", params=params)

    async def get_event(self, event_id: int) -> dict[str, Any]:
        """Get event metadata and usage summary."""
        return await self.get(f"event/{event_id}")

    async def list_client_attendees(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List attendees across all events."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get("attendee", params=params)

    async def list_client_registrants(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List registrants across all events."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get("registrant", params=params)

    async def get_registrant_by_email(
        self,
        email: str,
        event_id: int | None = None,
        partnerref: str | None = None,
    ) -> dict[str, Any]:
        """Get registrant by email address."""
        params: dict[str, Any] = {}
        if event_id is not None:
            params["eventId"] = event_id
        if partnerref is not None:
            params["partnerref"] = partnerref
        return await self.get(f"registrant/{email}", params=params or None)

    async def get_registrant_all_events(
        self,
        email: str,
        exclude_subaccounts: bool = False,
        subaccounts: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """Get all registrations across events for an email."""
        params: dict[str, Any] = {
            "pageOffset": page_offset,
            "itemsPerPage": items_per_page,
        }
        if exclude_subaccounts:
            params["excludeSubaccounts"] = "true"
        if subaccounts is not None:
            params["subaccounts"] = subaccounts
        return await self.get(f"registrant/{email}/allevents", params=params)

    async def list_sub_clients(self) -> dict[str, Any]:
        """List sub-clients for the current client."""
        path = f"/v2/client/{self.client_id}"
        return await self._request("GET", path, raw_path=True)

    async def get_realtime_user_questions(
        self,
        exclude_subaccounts: bool = False,
        email_filter: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get real-time user questions (last 5 minutes)."""
        params: dict[str, Any] = {}
        if exclude_subaccounts:
            params["excludesubaccounts"] = "true"
        if email_filter is not None:
            params["emailFilter"] = email_filter
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        return await self.get("userquestions", params=params or None)

    async def get_attendee_by_email(self, email: str) -> dict[str, Any]:
        """Get most recent attendance for an email."""
        return await self.get(f"attendee/{email}")

    async def get_attendee_all_events(self, email: str, page_offset: int = 0, items_per_page: int = 100) -> dict[str, Any]:
        """Get all attendance across events for an email."""
        return await self.get(
            f"attendee/{email}/allevents",
            params={"pageOffset": page_offset, "itemsPerPage": items_per_page},
        )

    async def list_client_leads(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 50,
    ) -> dict[str, Any]:
        """List leads for the client."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get("lead", params=params)

    async def get_pep(self, email: str) -> dict[str, Any]:
        """Get Prospect Engagement Profile for an email."""
        return await self.get(f"lead/{email}")

    async def get_engaged_accounts(self) -> dict[str, Any]:
        """Get top engaged accounts (last 90 days, max 100)."""
        return await self.get("engagedaccount")

    async def list_client_presenters(self) -> dict[str, Any]:
        """List presenters for the client."""
        return await self.get("presenter")

    async def get_survey_library(self) -> dict[str, Any]:
        """Get client survey library."""
        return await self.get("surveylibrary")

    async def list_users(self) -> dict[str, Any]:
        """List users for the client."""
        return await self.get("users")

    # ── Event-Level Analytics ──

    async def list_event_attendees(
        self,
        event_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List attendees for a specific event."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get(f"event/{event_id}/attendee", params=params)

    async def list_event_registrants(
        self,
        event_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
        noshow: bool = False,
    ) -> dict[str, Any]:
        """List registrants for a specific event."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if noshow:
            params["noshow"] = "Y"
        return await self.get(f"event/{event_id}/registrant", params=params)

    async def get_event_viewing_sessions(
        self,
        event_id: int,
        session_type: str = "all",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """Get attendee viewing sessions for an event."""
        return await self.get(
            f"event/{event_id}/attendeesession",
            params={
                "sessionType": session_type,
                "pageoffset": page_offset,
                "itemsPerPage": items_per_page,
            },
        )

    async def get_event_polls(self, event_id: int) -> dict[str, Any]:
        """Get polls for an event."""
        return await self.get(f"event/{event_id}/poll")

    async def get_event_surveys(self, event_id: int) -> dict[str, Any]:
        """Get surveys for an event."""
        return await self.get(f"event/{event_id}/survey")

    async def get_event_resources(self, event_id: int) -> dict[str, Any]:
        """Get resources viewed for an event."""
        return await self.get(f"event/{event_id}/resource")

    async def get_event_ctas(self, event_id: int) -> dict[str, Any]:
        """Get CTA activity for an event."""
        return await self.get(f"event/{event_id}/cta")

    async def get_event_group_chat(self, event_id: int) -> dict[str, Any]:
        """Get group chat activity for an event."""
        return await self.get(f"event/{event_id}/groupchat")

    async def get_event_email_stats(self, event_id: int) -> dict[str, Any]:
        """Get email statistics for an event."""
        return await self.get(f"event/{event_id}/emailstatistics")

    async def get_event_certifications(self, event_id: int) -> dict[str, Any]:
        """Get certifications for an event."""
        return await self.get(f"event/{event_id}/certifications")

    async def get_event_content_activity(self, event_id: int) -> dict[str, Any]:
        """Get Engagement Hub content activity for an event."""
        return await self.get(f"event/{event_id}/contentactivity")

    async def get_event_presenters(self, event_id: int) -> dict[str, Any]:
        """Get presenters for an event."""
        return await self.get(f"event/{event_id}/presenter")

    async def get_event_calendar_reminder(self, event_id: int) -> dict[str, Any]:
        """Get email calendar reminder for an event."""
        return await self.get(f"event/{event_id}/calendarreminder")

    async def get_event_email(self, event_id: int) -> dict[str, Any]:
        """Get email notification details for an event."""
        return await self.get(f"event/{event_id}/email")

    async def get_event_presenter_chat(self, event_id: int) -> dict[str, Any]:
        """Get presenter chat logs for an event."""
        return await self.get(f"event/{event_id}/presenterchat")

    async def get_event_slides(self, event_id: int) -> dict[str, Any]:
        """Get slide listing for an event."""
        return await self.get(f"event/{event_id}/slides")

    # ── Registration ──

    async def update_event_registrant(
        self,
        event_id: int,
        email: str,
        firstname: str | None = None,
        lastname: str | None = None,
        company: str | None = None,
        jobtitle: str | None = None,
        jobfunction: str | None = None,
        honor_required: bool = False,
        honor_validation: bool = False,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Update a registrant at the event level (form-urlencoded PATCH)."""
        form: dict[str, Any] = {"email": email}
        if firstname is not None:
            form["firstname"] = firstname
        if lastname is not None:
            form["lastname"] = lastname
        if company is not None:
            form["company"] = company
        if jobtitle is not None:
            form["jobtitle"] = jobtitle
        if jobfunction is not None:
            form["jobfunction"] = jobfunction
        form.update(extra_fields)

        params: dict[str, Any] = {}
        if honor_required:
            params["honorrequired"] = "true"
        if honor_validation:
            params["honorvalidation"] = "true"

        return await self._form_request(
            "PATCH",
            f"event/{event_id}/registrant",
            form_data=form,
            params=params or None,
        )

    async def update_client_registrant(
        self,
        email: str,
        firstname: str | None = None,
        lastname: str | None = None,
        new_email: str | None = None,
        company: str | None = None,
        jobtitle: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Update a registrant at the client level (form-urlencoded PATCH)."""
        form: dict[str, Any] = {}
        if firstname is not None:
            form["firstname"] = firstname
        if lastname is not None:
            form["lastname"] = lastname
        if new_email is not None:
            form["email"] = new_email
        if company is not None:
            form["company"] = company
        if jobtitle is not None:
            form["jobtitle"] = jobtitle
        form.update(extra_fields)
        return await self._form_request("PATCH", f"registrant/{email}", form_data=form)

    async def forget_registrant(
        self,
        email: str,
        event_id: int | None = None,
    ) -> dict[str, Any]:
        """Forget a registrant (GDPR). Email can be comma-separated for multiple."""
        form: dict[str, Any] = {"email": email}
        if event_id is not None:
            form["eventid"] = str(event_id)
        return await self._form_request("POST", "forget", form_data=form)

    async def forget_all_event_registrants(self, event_id: int) -> dict[str, Any]:
        """Forget all registrants in an event (GDPR)."""
        return await self.post(f"event/{event_id}/forgetall")

    async def forget_all_workspace_registrants(self) -> dict[str, Any]:
        """Forget all registrants in the workspace (GDPR). DESTRUCTIVE."""
        return await self.post("forgetall")

    # ── Write Operations ──

    async def create_event(
        self,
        title: str,
        event_type: str,
        start_time: str,
        end_time: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new ON24 event."""
        body: dict[str, Any] = {
            "eventType": event_type,
            "title": title,
            "startTime": start_time,
            "endTime": end_time,
        }
        if description is not None:
            body["description"] = description
        return await self.post("event", json_body=body)

    async def update_event(
        self,
        event_id: int,
        title: str | None = None,
        description: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing ON24 event."""
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        return await self.patch(f"event/{event_id}", json_body=body)

    async def register_attendee(
        self,
        event_id: int,
        email: str,
        first_name: str,
        last_name: str,
        company: str | None = None,
        job_title: str | None = None,
    ) -> dict[str, Any]:
        """Register a person for an ON24 event."""
        body: dict[str, Any] = {
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
        }
        if company is not None:
            body["company"] = company
        if job_title is not None:
            body["jobTitle"] = job_title
        return await self.post(f"event/{event_id}/registrant", json_body=body)

    async def remove_registration(
        self,
        event_id: int,
        email: str,
    ) -> dict[str, Any]:
        """Remove a registrant from an ON24 event by email."""
        return await self.delete(f"event/{event_id}/registrant/{email}")

    # ── Event Management ──

    async def copy_webinar(
        self,
        source_event_id: int,
        live_start: str,
        live_duration: int | None = None,
        title: str | None = None,
        language_cd: str | None = None,
        time_zone: str | None = None,
        campaign_code: str | None = None,
        tag_campaign: str | None = None,
        custom_account_tag: str | None = None,
        archive_available: str | None = None,
        testevent: str | None = None,
        hybrid: str | None = None,
        venue: str | None = None,
        address: str | None = None,
        promotional_summary: str | None = None,
        country_cd: str | None = None,
    ) -> dict[str, Any]:
        """Copy a webinar from an existing event."""
        form: dict[str, Any] = {"liveStart": live_start}
        if live_duration is not None:
            form["liveDuration"] = str(live_duration)
        if title is not None:
            form["title"] = title
        if language_cd is not None:
            form["languageCd"] = language_cd
        if time_zone is not None:
            form["timeZone"] = time_zone
        if campaign_code is not None:
            form["campaignCode"] = campaign_code
        if tag_campaign is not None:
            form["tagCampaign"] = tag_campaign
        if custom_account_tag is not None:
            form["customAccountTag"] = custom_account_tag
        if archive_available is not None:
            form["archiveAvailable"] = archive_available
        if testevent is not None:
            form["testevent"] = testevent
        if hybrid is not None:
            form["hybrid"] = hybrid
        if venue is not None:
            form["venue"] = venue
        if address is not None:
            form["address"] = address
        if promotional_summary is not None:
            form["promotionalSummary"] = promotional_summary
        if country_cd is not None:
            form["countryCd"] = country_cd
        return await self._form_request("POST", "event", form_data=form, params={"eventsource": source_event_id})

    async def create_webinar(
        self,
        title: str,
        live_start: str,
        live_duration: int,
        event_type: str,
        language_cd: str,
        time_zone: str,
        event_abstract: str | None = None,
        campaign_code: str | None = None,
        country_cd: str | None = None,
        tag_campaign: str | None = None,
        custom_account_tag: str | None = None,
        archive_available: str | None = None,
        promotional_summary: str | None = None,
        testevent: str | None = None,
        hybrid: str | None = None,
        venue: str | None = None,
        address: str | None = None,
    ) -> dict[str, Any]:
        """Create a webinar with full form-urlencoded parameters."""
        form: dict[str, Any] = {
            "title": title,
            "liveStart": live_start,
            "liveDuration": str(live_duration),
            "eventType": event_type,
            "languageCd": language_cd,
            "timeZone": time_zone,
        }
        if event_abstract is not None:
            form["eventAbstract"] = event_abstract
        if campaign_code is not None:
            form["campaignCode"] = campaign_code
        if country_cd is not None:
            form["countryCd"] = country_cd
        if tag_campaign is not None:
            form["tagCampaign"] = tag_campaign
        if custom_account_tag is not None:
            form["customAccountTag"] = custom_account_tag
        if archive_available is not None:
            form["archiveAvailable"] = archive_available
        if promotional_summary is not None:
            form["promotionalSummary"] = promotional_summary
        if testevent is not None:
            form["testevent"] = testevent
        if hybrid is not None:
            form["hybrid"] = hybrid
        if venue is not None:
            form["venue"] = venue
        if address is not None:
            form["address"] = address
        return await self._form_request("POST", "event", form_data=form)

    async def upload_related_content(
        self,
        event_id: int,
        matchname: str,
        name: str,
        content_type: str,
        file: tuple | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Upload related content for an event (multipart/form-data).

        Args:
            event_id: Event ID
            matchname: Match name for the content
            name: Display name
            content_type: 'Resource' or 'URL'
            file: Tuple of (filename, file_bytes, content_type) for file uploads
            url: URL string for URL-type content
        """
        form: dict[str, Any] = {
            "matchname": matchname,
            "name": name,
            "type": content_type,
        }
        if url is not None:
            form["url"] = url
        files = {"file": file} if file is not None else None
        return await self._multipart_request(
            "POST",
            f"event/{event_id}/relatedcontent",
            form_data=form,
            files=files,
        )

    async def create_speaker_bio(
        self,
        event_id: int,
        metadata: dict[str, Any],
        file: tuple | None = None,
    ) -> dict[str, Any]:
        """Create a speaker bio for an event (multipart/form-data).

        Args:
            event_id: Event ID
            metadata: JSON metadata for the speaker bio
            file: Optional tuple of (filename, file_bytes, content_type) for speaker image
        """
        import json

        form: dict[str, Any] = {"metadata": json.dumps(metadata)}
        files = {"file": file} if file is not None else None
        return await self._multipart_request(
            "POST",
            f"event/{event_id}/speakerbio",
            form_data=form,
            files=files,
        )

    async def create_survey_questions(
        self,
        event_id: int,
        survey_questions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create survey questions for an event."""
        body: dict[str, Any] = {"metadata": {"surveyquestions": survey_questions}}
        return await self.post(f"event/{event_id}/surveyquestions", json_body=body)

    async def delete_speaker_bios(self, event_id: int) -> dict[str, Any]:
        """Delete all speaker bios for an event."""
        return await self.delete(f"event/{event_id}/speakerbio")

    async def delete_vtt_files(self, event_id: int) -> dict[str, Any]:
        """Delete VTT files for an event."""
        return await self.delete(f"event/{event_id}/vtt")

    async def delete_webinar(self, event_id: int) -> dict[str, Any]:
        """Delete a webinar."""
        return await self.delete(f"event/{event_id}")

    async def edit_webinar(
        self,
        event_id: int,
        title: str,
        live_start: str,
        live_duration: int,
        event_type: str,
        language_cd: str,
        campaign_code: str | None = None,
        country_cd: str | None = None,
    ) -> dict[str, Any]:
        """Edit a webinar (full PUT, all required fields must be provided)."""
        form: dict[str, Any] = {
            "title": title,
            "liveStart": live_start,
            "liveDuration": str(live_duration),
            "eventType": event_type,
            "languageCd": language_cd,
        }
        if campaign_code is not None:
            form["campaignCode"] = campaign_code
        if country_cd is not None:
            form["countryCd"] = country_cd
        return await self._form_request("PUT", f"event/{event_id}", form_data=form)

    async def update_webinar(
        self,
        event_id: int,
        title: str | None = None,
        live_start: str | None = None,
        live_duration: int | None = None,
        event_type: str | None = None,
        language_cd: str | None = None,
        country_cd: str | None = None,
        time_zone: str | None = None,
        tag_campaign: str | None = None,
        campaign_code: str | None = None,
        archive_available: str | None = None,
        promotional_summary: str | None = None,
        custom_account_tag: str | None = None,
        enable_registration: str | None = None,
    ) -> dict[str, Any]:
        """Update a webinar (partial PUT, all fields optional)."""
        form: dict[str, Any] = {}
        if title is not None:
            form["title"] = title
        if live_start is not None:
            form["liveStart"] = live_start
        if live_duration is not None:
            form["liveDuration"] = str(live_duration)
        if event_type is not None:
            form["eventType"] = event_type
        if language_cd is not None:
            form["languageCd"] = language_cd
        if country_cd is not None:
            form["countryCd"] = country_cd
        if time_zone is not None:
            form["timeZone"] = time_zone
        if tag_campaign is not None:
            form["tagCampaign"] = tag_campaign
        if campaign_code is not None:
            form["campaignCode"] = campaign_code
        if archive_available is not None:
            form["archiveAvailable"] = archive_available
        if promotional_summary is not None:
            form["promotionalSummary"] = promotional_summary
        if custom_account_tag is not None:
            form["customAccountTag"] = custom_account_tag
        if enable_registration is not None:
            form["enableRegistration"] = enable_registration
        return await self._form_request("PUT", f"event/{event_id}", form_data=form)

    async def upload_document(
        self,
        file: tuple,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload a document to Media Manager.

        Args:
            file: Tuple of (filename, file_bytes, content_type)
            metadata: Optional JSON metadata with id, title
        """
        import json

        form = {"metadata": json.dumps(metadata)} if metadata else None
        return await self._multipart_request(
            "POST",
            "mediamanager/document",
            form_data=form,
            files={"file": file},
        )

    async def upload_video(
        self,
        file: tuple,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload a video to Media Manager.

        Args:
            file: Tuple of (filename, file_bytes, content_type)
            metadata: Optional JSON metadata with id, title
        """
        import json

        form = {"metadata": json.dumps(metadata)} if metadata else None
        return await self._multipart_request(
            "POST",
            "mediamanager/uploadvideo",
            form_data=form,
            files={"file": file},
        )

    async def upload_slides(
        self,
        event_id: int,
        file: tuple,
    ) -> dict[str, Any]:
        """Upload slides (PowerPoint) for an event.

        Args:
            event_id: Event ID
            file: Tuple of (filename, file_bytes, content_type)
        """
        return await self._multipart_request(
            "POST",
            f"event/{event_id}/slides",
            files={"file": file},
        )

    async def update_calendar_reminder(
        self,
        event_id: int,
        reminder: str | None = None,
        subject: str | None = None,
        location: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Update calendar reminder for an event."""
        form: dict[str, Any] = {}
        if reminder is not None:
            form["reminder"] = reminder
        if subject is not None:
            form["subject"] = subject
        if location is not None:
            form["location"] = location
        if body is not None:
            form["body"] = body
        return await self._form_request("PUT", f"event/{event_id}/calendarreminder", form_data=form)

    async def update_email_notification(
        self,
        event_id: int,
        email_id: int,
        activated: str | None = None,
        whentosend: str | None = None,
        goodafter: str | None = None,
        fromlabel: str | None = None,
        replyto: str | None = None,
        subject: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Update an email notification for an event."""
        form: dict[str, Any] = {}
        if activated is not None:
            form["activated"] = activated
        if whentosend is not None:
            form["whentosend"] = whentosend
        if goodafter is not None:
            form["goodafter"] = goodafter
        if fromlabel is not None:
            form["fromlabel"] = fromlabel
        if replyto is not None:
            form["replyto"] = replyto
        if subject is not None:
            form["subject"] = subject
        if body is not None:
            form["body"] = body
        return await self._form_request("PUT", f"event/{event_id}/email/{email_id}", form_data=form)

    async def update_text_with_banner(
        self,
        event_id: int,
        metadata: str,
    ) -> dict[str, Any]:
        """Update text with banner widget for an event.

        Args:
            event_id: Event ID
            metadata: JSON string containing widget configuration
        """
        return await self._form_request(
            "POST",
            f"event/{event_id}/textwithbanner",
            form_data={"metadata": metadata},
        )

    # ── Content Listings ──

    async def get_ehub_content(self, gateway_id: int) -> dict[str, Any]:
        """Get Engagement Hub content listing."""
        return await self.get(f"ehub/{gateway_id}/content")

    async def list_media_manager_content(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List Media Manager derivative content."""
        params: dict[str, Any] = {
            "pageOffset": page_offset,
            "itemsPerPage": items_per_page,
        }
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        return await self.get("mediamanager", params=params)

    async def get_media_manager_content(self, media_id: int) -> dict[str, Any]:
        """Get a single Media Manager derivative content item."""
        return await self.get(f"mediamanager/{media_id}")

    # ── Helper Endpoints ──

    async def get_custom_account_tags(self) -> dict[str, Any]:
        """Get custom account tags."""
        return await self.get("customaccounttag")

    async def get_account_managers(self) -> dict[str, Any]:
        """Get account managers."""
        return await self.get("accountmanager")

    async def get_event_managers(self) -> dict[str, Any]:
        """Get event managers."""
        return await self.get("eventmanager")

    async def get_event_profiles(self) -> dict[str, Any]:
        """Get event profiles."""
        return await self.get("eventprofile")

    async def get_event_types(self) -> dict[str, Any]:
        """Get event types."""
        return await self.get("eventtypes")

    async def get_languages(self) -> dict[str, Any]:
        """Get available language codes."""
        return await self.get("languages")

    async def get_registration_fields(self, event_id: int) -> dict[str, Any]:
        """Get registration fields for an event."""
        return await self.get(f"event/{event_id}/regfield")

    async def get_replacement_tokens(self, context: str | None = None) -> dict[str, Any]:
        """Get replacement tokens."""
        params = {"context": context} if context else None
        return await self.get("tokens", params=params)

    async def get_sales_reps(self) -> dict[str, Any]:
        """Get sales rep contacts."""
        return await self.get("salesrep")

    async def get_signal_contacts(self) -> dict[str, Any]:
        """Get signal contacts."""
        return await self.get("signalrep")

    async def get_technical_reps(self) -> dict[str, Any]:
        """Get technical rep contacts."""
        return await self.get("technicalrep")

    async def get_timezones(self) -> dict[str, Any]:
        """Get available timezone codes."""
        return await self.get("timezones")

    # ── Pagination Helper ──

    async def paginate(
        self,
        endpoint: str,
        items_key: str = "items",
        items_per_page: int = 100,
        max_pages: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Auto-paginate through all pages of a paginated endpoint.

        Args:
            endpoint: API endpoint path
            items_key: Key in response containing the items list
            items_per_page: Number of items per page
            max_pages: Maximum number of pages to fetch (None = all)
            params: Additional query parameters

        Returns:
            Combined list of all items across pages
        """
        all_items: list[dict[str, Any]] = []
        page_offset = 0
        page_count = 0

        while True:
            request_params = dict(params or {})
            request_params["itemsPerPage"] = items_per_page
            request_params["pageOffset"] = page_offset

            data = await self.get(endpoint, params=request_params)

            # ON24 uses various keys for the items list
            items = data.get(items_key, [])
            if not items:
                # Try common alternative keys
                for key in ["events", "attendees", "registrants", "leads"]:
                    items = data.get(key, [])
                    if items:
                        break

            all_items.extend(items)
            page_count += 1

            logger.debug(f"Paginate {endpoint}: page {page_offset}, got {len(items)} items, total so far: {len(all_items)}")

            # Stop conditions
            if len(items) < items_per_page:
                break
            if max_pages and page_count >= max_pages:
                break

            page_offset += 1

        return all_items
