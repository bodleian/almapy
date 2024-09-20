from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal

from gracy import Gracy, GracyNamespace, graceful
from typing_extensions import assert_never

from almapy._endpoints import AlmaEndpoint

if TYPE_CHECKING:
    from almapy._utils import RESP_TYPE


class AlmaClientConfigSetsNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for set functionality, exposed at AlmaClient.config.sets."""

    async def get_list(
        self,
        content_type: str | None = None,
        set_type: Literal["ITEMIZED", "LOGICAL"] | None = None,
        q: str | None = None,
        limit: int = 10,
        offset: int = 0,
        set_origin: Literal["UI", "UI_CZ"] = "UI",
    ) -> RESP_TYPE:
        params = {
            "content_type": content_type,
            "set_type": set_type,
            "q": q,
            "limit": limit,
            "offset": offset,
            "set_origin": set_origin,
        }
        resp: RESP_TYPE = await self.get(AlmaEndpoint.SETS, params=params)

        return resp

    async def get_set(self, set_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.SET, {"SET_ID": set_id})
        return resp

    async def create(
        self,
        data: RESP_TYPE,
        population: str | None = None,
        job_instance_id: str | None = None,
        from_logical_set: str | None = None,
        combine: str | None = None,
        set1: str | None = None,
        set2: str | None = None,
        nz_set_from_iz_set: str | None = None,
        indication_rule: str | None = None,
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.SETS,
            json=data,
            params={
                "population": population,
                "job_instance_id": job_instance_id,
                "from_logical_set": from_logical_set,
                "combine": combine,
                "set1": set1,
                "set2": set2,
                "nz_set_from_iz_set": nz_set_from_iz_set,
                "indication_rule": indication_rule,
            },
        )
        return resp

    async def get_members(
        self,
        set_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> RESP_TYPE:
        params = {
            "limit": limit,
            "offset": offset,
        }
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.SET_MEMBERS,
            {"SET_ID": set_id},
            params=params,
        )

        return resp

    @graceful(parser={HTTPStatus.NO_CONTENT: lambda r: True, "default": lambda r: False})
    async def delete_set(self, set_id: str) -> bool:
        resp: bool = await self.delete(AlmaEndpoint.SET, {"SET_ID": set_id})
        return resp

    async def manage_members(
        self,
        set_id: str,
        member_id_list: list[str],
        *,
        id_type: str,
        op: Literal["add_members", "delete_members", "replace_members"],
        fail_on_invalid: bool = True,
    ) -> RESP_TYPE:
        params = {
            "id_type": id_type,
            "op": op,
            "fail_on_invalid": fail_on_invalid,
        }
        body = await self.get_set(set_id)
        body["members"] = {"member": [{"id": member_id} for member_id in member_id_list]}
        resp: RESP_TYPE = await self.post(AlmaEndpoint.SET, {"SET_ID": set_id}, body, params=params)
        return resp


class AlmaClientConfigLibrariesNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for library functionality, exposed at AlmaClient.config.sets."""

    async def get_libraries(
        self,
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.LIBRARIES)
        return resp

    async def get_circ_desks(self, library: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.CIRC_DESKS, {"LIBRARY_CODE": library})
        return resp

    async def get_locations(self, library: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.LOCATIONS, {"LIBRARY_CODE": library})
        return resp

    async def get_location(self, library: str, location: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.LOCATION, {"LIBRARY": library, "LOCATION_CODE": location}
        )

        return resp


class AlmaClientConfigLettersNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for letter functionality, exposed at AlmaClient.config.letters."""

    async def get_letters(self) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.LETTERS)
        return resp

    async def get_components(self) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.LETTERS, params={"type": "COMPONENT"})
        return resp

    async def get_letter(self, letter_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.LETTER, {"LETTER_ID": letter_id})
        return resp

    async def update_letter(self, letter_id: str, data: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.put(
            AlmaEndpoint.LETTER,
            {"LETTER_ID": letter_id},
            content=data,
            headers={"Content-Type": "application/xml"},
        )
        return resp


class AlmaClientConfigJobsNS(GracyNamespace[AlmaEndpoint]):
    async def get_jobs(
        self,
        limit: int = 10,
        offset: int = 0,
        *,
        category: str | None = None,
        job_type: Literal["MANUAL", "SCHEDULED", "OTHER"] | None = None,
        profile_id: str | None = None,
    ) -> RESP_TYPE:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if job_type:
            params["job_type"] = job_type
        if profile_id:
            params["profile_id"] = profile_id
        resp: RESP_TYPE = await self.get(AlmaEndpoint.JOBS, params=params)
        return resp

    async def get_job(self, job_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.JOB, {"JOB_ID": job_id})
        return resp

    async def submit_job(
        self, job_id: str, job: dict[str, str | dict[str, str | dict[str, str]]]
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.JOB, {"JOB_ID": job_id}, json=job, params={"op": "run"}
        )
        return resp

    async def get_job_instances(
        self,
        job_id: str,
        limit: int = 10,
        offset: int = 0,
        submit_date_from: str | None = None,
        submit_date_to: str | None = None,
        status: str | None = None,
    ) -> RESP_TYPE:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if submit_date_to:
            params["submit_date_to"] = submit_date_to
        if submit_date_from:
            params["submit_date_from"] = submit_date_from
        if status:
            params["status"] = status
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.JOB_INSTANCES, {"JOB_ID": job_id}, params=params
        )
        return resp

    async def get_job_instance(self, job_id: str, instance_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.JOB_INSTANCE, {"JOB_ID": job_id, "INSTANCE_ID": instance_id}
        )
        return resp

    async def get_job_instance_matches(
        self,
        job_id: str,
        instance_id: str,
        single_or_multi: Literal["single", "multi"],
        limit: int = 10,
        offset: int = 0,
    ) -> RESP_TYPE:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if single_or_multi == "multi":
            params["population"] = "MULTI_MATCHES"
        elif single_or_multi == "single":
            params["population"] = "SINGLE_MATCHES"
        else:
            assert_never(single_or_multi)
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.JOB_INSTANCE_MATCHES,
            {"JOB_ID": job_id, "INSTANCE_ID": instance_id},
            params=params,
        )
        return resp


class AlmaClientConfigCodeTablesNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for code table functionality, exposed at AlmaClient.config.code_tables."""

    async def get_code_tables(self) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.CODE_TABLES)
        return resp

    async def get_code_table(self, table_code: str, *, lang: str = "en") -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.CODE_TABLE, {"TABLE_CODE": table_code}, params={"lang": lang}
        )
        return resp

    async def update_code_table(
        self, table_code: str, data: dict[str, Any], *, lang: str = "en"
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.put(
            AlmaEndpoint.CODE_TABLE,
            {"TABLE_CODE": table_code},
            params={"lang": lang},
            json=data,
        )
        return resp


class AlmaClientConfigNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for config/admin functionality, exposing a number of sub-namespace via attrs.

    - sets
    - libraries
    - letters
    """

    def __init__(self, parent: Gracy[AlmaEndpoint], **kwargs: Any):
        super().__init__(parent, **kwargs)
        self.sets = AlmaClientConfigSetsNS(parent)
        self.libraries = AlmaClientConfigLibrariesNS(parent)
        self.letters = AlmaClientConfigLettersNS(parent)
        self.jobs = AlmaClientConfigJobsNS(parent)
        self.code_tables = AlmaClientConfigCodeTablesNS(parent)
