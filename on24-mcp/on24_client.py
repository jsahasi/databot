import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class ON24APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"ON24 API error {status_code}: {message}")


class ON24Client:
    def __init__(self, client_id: str, token_key: str, token_secret: str, base_url: str):
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "accessTokenKey": token_key,
            "accessTokenSecret": token_secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _path(self, endpoint: str) -> str:
        return f"/v2/client/{self.client_id}/{endpoint.lstrip('/')}"

    async def _request(self, method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.request(method, self._path(endpoint), json=json_body)
        if resp.status_code == 401:
            raise ON24APIError(401, "Invalid credentials")
        if resp.status_code == 403:
            raise ON24APIError(403, "Permission denied")
        if resp.status_code == 404:
            raise ON24APIError(404, f"Not found: {endpoint}")
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def create_event(self, title: str, event_type: str, start_time: str, end_time: str, description: str | None = None) -> dict:
        body: dict = {"eventType": event_type, "title": title, "startTime": start_time, "endTime": end_time}
        if description:
            body["description"] = description
        return await self._request("POST", "event", body)

    async def update_event(self, event_id: int, title: str | None = None, description: str | None = None, start_time: str | None = None, end_time: str | None = None) -> dict:
        body = {k: v for k, v in {"title": title, "description": description, "startTime": start_time, "endTime": end_time}.items() if v is not None}
        return await self._request("PATCH", f"event/{event_id}", body)

    async def register_attendee(self, event_id: int, email: str, first_name: str, last_name: str, company: str | None = None, job_title: str | None = None) -> dict:
        body: dict = {"email": email, "firstName": first_name, "lastName": last_name}
        if company:
            body["company"] = company
        if job_title:
            body["jobTitle"] = job_title
        return await self._request("POST", f"event/{event_id}/registrant", body)

    async def remove_registration(self, event_id: int, email: str) -> dict:
        return await self._request("DELETE", f"event/{event_id}/registrant/{email}")

    # ── Additional Write Operations ──

    async def copy_webinar(self, source_event_id: int, live_start: str, **kwargs: Any) -> dict:
        form: dict = {"liveStart": live_start}
        for k, v in kwargs.items():
            if v is not None:
                form[k] = str(v) if isinstance(v, int) else v
        return await self._form_request("POST", "event", form, params={"eventsource": source_event_id})

    async def create_webinar(self, title: str, live_start: str, live_duration: int,
                             event_type: str, language_cd: str, time_zone: str, **kwargs: Any) -> dict:
        form: dict = {"title": title, "liveStart": live_start, "liveDuration": str(live_duration),
                      "eventType": event_type, "languageCd": language_cd, "timeZone": time_zone}
        for k, v in kwargs.items():
            if v is not None:
                form[k] = str(v) if isinstance(v, int) else v
        return await self._form_request("POST", "event", form)

    async def edit_webinar(self, event_id: int, title: str, live_start: str, live_duration: int,
                           event_type: str, language_cd: str, **kwargs: Any) -> dict:
        form: dict = {"title": title, "liveStart": live_start, "liveDuration": str(live_duration),
                      "eventType": event_type, "languageCd": language_cd}
        for k, v in kwargs.items():
            if v is not None:
                form[k] = str(v) if isinstance(v, int) else v
        return await self._form_request("PUT", f"event/{event_id}", form)

    async def update_webinar(self, event_id: int, **kwargs: Any) -> dict:
        form: dict = {}
        for k, v in kwargs.items():
            if v is not None:
                form[k] = str(v) if isinstance(v, int) else v
        return await self._form_request("PUT", f"event/{event_id}", form)

    async def delete_webinar(self, event_id: int) -> dict:
        return await self._delete(f"event/{event_id}")

    async def update_event_registrant(self, event_id: int, email: str, **kwargs: Any) -> dict:
        form: dict = {"email": email}
        for k, v in kwargs.items():
            if v is not None:
                form[k] = v
        return await self._form_request("PATCH", f"event/{event_id}/registrant", form)

    async def update_client_registrant(self, email: str, **kwargs: Any) -> dict:
        form: dict = {}
        for k, v in kwargs.items():
            if v is not None:
                form[k] = v
        return await self._form_request("PATCH", f"registrant/{email}", form)

    async def forget_registrant(self, email: str, event_id: int | None = None) -> dict:
        form: dict = {"email": email}
        if event_id is not None:
            form["eventid"] = str(event_id)
        return await self._form_request("POST", "forget", form)

    async def forget_all_event_registrants(self, event_id: int) -> dict:
        return await self._form_request("POST", f"event/{event_id}/forgetall", {})

    async def forget_all_workspace_registrants(self) -> dict:
        return await self._form_request("POST", "forgetall", {})

    async def create_survey_questions(self, event_id: int, survey_questions: list) -> dict:
        return await self._request("POST", f"event/{event_id}/surveyquestions",
                                   {"metadata": {"surveyquestions": survey_questions}})

    async def delete_speaker_bios(self, event_id: int) -> dict:
        return await self._delete(f"event/{event_id}/speakerbio")

    async def delete_vtt_files(self, event_id: int) -> dict:
        return await self._delete(f"event/{event_id}/vtt")

    async def update_calendar_reminder(self, event_id: int, **kwargs: Any) -> dict:
        form: dict = {k: v for k, v in kwargs.items() if v is not None}
        return await self._form_request("PUT", f"event/{event_id}/calendarreminder", form)

    async def update_email_notification(self, event_id: int, email_id: int, **kwargs: Any) -> dict:
        form: dict = {k: v for k, v in kwargs.items() if v is not None}
        return await self._form_request("PUT", f"event/{event_id}/email/{email_id}", form)

    async def update_text_with_banner(self, event_id: int, metadata: str) -> dict:
        return await self._form_request("POST", f"event/{event_id}/textwithbanner", {"metadata": metadata})

    async def upload_document(self, file: tuple, metadata: dict | None = None) -> dict:
        import json as _json
        form = {"metadata": _json.dumps(metadata)} if metadata else None
        return await self._multipart_request("POST", "mediamanager/document", form, {"file": file})

    async def upload_video(self, file: tuple, metadata: dict | None = None) -> dict:
        import json as _json
        form = {"metadata": _json.dumps(metadata)} if metadata else None
        return await self._multipart_request("POST", "mediamanager/uploadvideo", form, {"file": file})

    async def upload_slides(self, event_id: int, file: tuple) -> dict:
        return await self._multipart_request("POST", f"event/{event_id}/slides", files={"file": file})

    async def upload_related_content(self, event_id: int, matchname: str, name: str,
                                     content_type: str, file: tuple | None = None, url: str | None = None) -> dict:
        form: dict = {"matchname": matchname, "name": name, "type": content_type}
        if url:
            form["url"] = url
        files = {"file": file} if file else None
        return await self._multipart_request("POST", f"event/{event_id}/relatedcontent", form, files)

    async def create_speaker_bio(self, event_id: int, metadata: dict, file: tuple | None = None) -> dict:
        import json as _json
        form: dict = {"metadata": _json.dumps(metadata)}
        files = {"file": file} if file else None
        return await self._multipart_request("POST", f"event/{event_id}/speakerbio", form, files)

    # ── Read Operations ──

    async def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.get(self._path(endpoint), params=params)
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def _form_request(self, method: str, endpoint: str, form_data: dict,
                            params: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.request(method, self._path(endpoint), data=form_data, params=params)
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def _multipart_request(self, method: str, endpoint: str,
                                 form_data: dict | None = None, files: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.request(method, self._path(endpoint), data=form_data, files=files)
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def _delete(self, endpoint: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.delete(self._path(endpoint))
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def list_events(self, start_date: str | None = None, end_date: str | None = None,
                          items_per_page: int = 100, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("event", params)

    async def get_event(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}")

    async def list_event_attendees(self, event_id: int, items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get(f"event/{event_id}/attendee", {"itemsPerPage": items_per_page, "pageOffset": page_offset})

    async def list_event_registrants(self, event_id: int, items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get(f"event/{event_id}/registrant", {"itemsPerPage": items_per_page, "pageOffset": page_offset})

    async def list_client_attendees(self, start_date: str | None = None, end_date: str | None = None,
                                    items_per_page: int = 100, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("attendee", params)

    async def list_client_registrants(self, start_date: str | None = None, end_date: str | None = None,
                                      items_per_page: int = 100, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("registrant", params)

    async def list_client_leads(self, start_date: str | None = None, end_date: str | None = None,
                                items_per_page: int = 50, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("lead", params)

    async def get_event_polls(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/poll")

    async def get_event_surveys(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/survey")

    async def get_event_resources(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/resource")

    async def get_event_types(self) -> dict:
        return await self._get("eventtypes")

    async def get_timezones(self) -> dict:
        return await self._get("timezones")

    async def get_attendee_by_email(self, email: str) -> dict:
        return await self._get(f"attendee/{email}")

    async def get_attendee_all_events(self, email: str, items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get(f"attendee/{email}/allevents", {"pageOffset": page_offset, "itemsPerPage": items_per_page})

    async def get_registrant_by_email(self, email: str, event_id: int | None = None) -> dict:
        params: dict = {}
        if event_id is not None:
            params["eventId"] = event_id
        return await self._get(f"registrant/{email}", params or None)

    async def get_registrant_all_events(self, email: str, items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get(f"registrant/{email}/allevents", {"pageOffset": page_offset, "itemsPerPage": items_per_page})

    async def get_survey_library(self) -> dict:
        return await self._get("surveylibrary")

    async def get_engaged_accounts(self) -> dict:
        return await self._get("engagedaccount")

    async def get_pep(self, email: str) -> dict:
        return await self._get(f"lead/{email}")

    async def list_client_presenters(self) -> dict:
        return await self._get("presenter")

    async def list_sub_clients(self) -> dict:
        """Special path: /v2/client/{clientId} with no trailing segment."""
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.get(f"/v2/client/{self.client_id}")
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def get_realtime_user_questions(self) -> dict:
        return await self._get("userquestions")

    async def list_users(self) -> dict:
        return await self._get("users")

    async def get_event_viewing_sessions(self, event_id: int, session_type: str = "all",
                                         items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get(f"event/{event_id}/attendeesession",
                               {"sessionType": session_type, "pageoffset": page_offset, "itemsPerPage": items_per_page})

    async def get_event_ctas(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/cta")

    async def get_event_group_chat(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/groupchat")

    async def get_event_email_stats(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/emailstatistics")

    async def get_event_certifications(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/certifications")

    async def get_event_content_activity(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/contentactivity")

    async def get_event_presenters(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/presenter")

    async def get_event_calendar_reminder(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/calendarreminder")

    async def get_event_email(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/email")

    async def get_event_presenter_chat(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/presenterchat")

    async def get_event_slides(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/slides")

    async def get_ehub_content(self, gateway_id: int) -> dict:
        return await self._get(f"ehub/{gateway_id}/content")

    async def list_media_manager_content(self, items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get("mediamanager", {"pageOffset": page_offset, "itemsPerPage": items_per_page})

    async def get_media_manager_content(self, media_id: int) -> dict:
        return await self._get(f"mediamanager/{media_id}")

    async def get_custom_account_tags(self) -> dict:
        return await self._get("customaccounttag")

    async def get_account_managers(self) -> dict:
        return await self._get("accountmanager")

    async def get_event_managers(self) -> dict:
        return await self._get("eventmanager")

    async def get_event_profiles(self) -> dict:
        return await self._get("eventprofile")

    async def get_languages(self) -> dict:
        return await self._get("languages")

    async def get_registration_fields(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/regfield")

    async def get_replacement_tokens(self, context: str | None = None) -> dict:
        params = {"context": context} if context else None
        return await self._get("tokens", params)

    async def get_sales_reps(self) -> dict:
        return await self._get("salesrep")

    async def get_signal_contacts(self) -> dict:
        return await self._get("signalrep")

    async def get_technical_reps(self) -> dict:
        return await self._get("technicalrep")
