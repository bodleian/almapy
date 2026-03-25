from typing import TYPE_CHECKING, Any, Literal, assert_never, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, _ModelT

if TYPE_CHECKING:
    from almapy._base import _AlmaExecutable


class AlmaClientConfigSetsNS(BaseNamespace):
    """Namespace for set functionality, exposed at AlmaClient.config.sets."""

    @overload
    async def get_list(
        self,
        content_type: str | None = ...,
        set_type: Literal["ITEMIZED", "LOGICAL"] | None = ...,
        q: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        set_origin: Literal["UI", "UI_CZ"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_list(
        self,
        content_type: str | None = ...,
        set_type: Literal["ITEMIZED", "LOGICAL"] | None = ...,
        q: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        set_origin: Literal["UI", "UI_CZ"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_list(
        self,
        content_type: str | None = None,
        set_type: Literal["ITEMIZED", "LOGICAL"] | None = None,
        q: str | None = None,
        limit: int = 10,
        offset: int = 0,
        set_origin: Literal["UI", "UI_CZ"] = "UI",
        *,
        model: Any = None,
    ) -> Any:
        params: dict[str, Any] = {
            "content_type": content_type,
            "set_type": set_type,
            "q": q,
            "limit": limit,
            "offset": offset,
            "set_origin": set_origin,
        }
        return await self._get(AlmaEndpoint.SETS, model=model, params=params)

    @overload
    async def get_set(self, set_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_set(self, set_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_set(self, set_id: str, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.SET, {"SET_ID": set_id}, model=model)

    @overload
    async def create(
        self,
        data: RESP_TYPE,
        population: str | None = ...,
        job_instance_id: str | None = ...,
        from_logical_set: str | None = ...,
        combine: str | None = ...,
        set1: str | None = ...,
        set2: str | None = ...,
        nz_set_from_iz_set: str | None = ...,
        indication_rule: str | None = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create(
        self,
        data: RESP_TYPE,
        population: str | None = ...,
        job_instance_id: str | None = ...,
        from_logical_set: str | None = ...,
        combine: str | None = ...,
        set1: str | None = ...,
        set2: str | None = ...,
        nz_set_from_iz_set: str | None = ...,
        indication_rule: str | None = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

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
        *,
        model: Any = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if population:
            params["population"] = population
        if job_instance_id:
            params["job_instance_id"] = job_instance_id
        if from_logical_set:
            params["from_logical_set"] = from_logical_set
        if combine:
            params["combine"] = combine
        if set1:
            params["set1"] = set1
        if set2:
            params["set2"] = set2
        if nz_set_from_iz_set:
            params["nz_set_from_iz_set"] = nz_set_from_iz_set
        if indication_rule:
            params["indication_rule"] = indication_rule
        return await self._post(AlmaEndpoint.SETS, model=model, json=data, params=params)

    @overload
    async def get_members(
        self, set_id: str, limit: int = ..., offset: int = ..., *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_members(
        self, set_id: str, limit: int = ..., offset: int = ..., *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_members(
        self, set_id: str, limit: int = 100, offset: int = 0, *, model: Any = None
    ) -> Any:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        return await self._get(
            AlmaEndpoint.SET_MEMBERS, {"SET_ID": set_id}, model=model, params=params
        )

    async def delete_set(self, set_id: str) -> bool:
        await self._delete(AlmaEndpoint.SET, {"SET_ID": set_id}, parser="none")
        return True

    @overload
    async def manage_members(
        self,
        set_id: str,
        member_id_list: list[str],
        *,
        id_type: str | None = ...,
        op: Literal["add_members", "delete_members", "replace_members"],
        fail_on_invalid: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def manage_members(
        self,
        set_id: str,
        member_id_list: list[str],
        *,
        id_type: str | None = ...,
        op: Literal["add_members", "delete_members", "replace_members"],
        fail_on_invalid: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def manage_members(
        self,
        set_id: str,
        member_id_list: list[str],
        *,
        id_type: str | None = None,
        op: Literal["add_members", "delete_members", "replace_members"],
        fail_on_invalid: bool = True,
        model: Any = None,
    ) -> Any:
        params: dict[str, Any] = {"op": op, "fail_on_invalid": fail_on_invalid}
        if id_type:
            params["id_type"] = id_type
        body = await self.get_set(set_id)
        body["members"] = {"member": [{"id": member_id} for member_id in member_id_list]}
        return await self._post(
            AlmaEndpoint.SET, {"SET_ID": set_id}, model=model, json=body, params=params
        )


class AlmaClientConfigLibrariesNS(BaseNamespace):
    """Namespace for library functionality, exposed at AlmaClient.config.sets."""

    @overload
    async def get_libraries(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_libraries(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_libraries(self, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.LIBRARIES, model=model)

    @overload
    async def get_circ_desks(self, library: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_circ_desks(self, library: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_circ_desks(self, library: str, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.CIRC_DESKS, {"LIBRARY_CODE": library}, model=model)

    @overload
    async def get_locations(self, library: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_locations(self, library: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_locations(self, library: str, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.LOCATIONS, {"LIBRARY_CODE": library}, model=model)

    @overload
    async def get_location(
        self, library: str, location: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_location(
        self, library: str, location: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_location(self, library: str, location: str, *, model: Any = None) -> Any:
        return await self._get(
            AlmaEndpoint.LOCATION, {"LIBRARY_CODE": library, "LOCATION_CODE": location}, model=model
        )


class AlmaClientConfigLettersNS(BaseNamespace):
    """Namespace for letter functionality, exposed at AlmaClient.config.letters."""

    @overload
    async def get_letters(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_letters(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_letters(self, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.LETTERS, model=model)

    @overload
    async def get_components(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_components(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_components(self, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.LETTERS, model=model, params={"type": "COMPONENT"})

    @overload
    async def get_letter(self, letter_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_letter(self, letter_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_letter(self, letter_id: str, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.LETTER, {"LETTER_ID": letter_id}, model=model)

    @overload
    async def update_letter(
        self, letter_id: str, data: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_letter(self, letter_id: str, data: str, *, model: None = ...) -> RESP_TYPE: ...

    async def update_letter(self, letter_id: str, data: str, *, model: Any = None) -> Any:
        return await self._put(
            AlmaEndpoint.LETTER,
            {"LETTER_ID": letter_id},
            model=model,
            content=data,
            headers={"Content-Type": "application/xml"},
        )


class AlmaClientConfigJobsNS(BaseNamespace):
    @overload
    async def get_jobs(
        self,
        limit: int = ...,
        offset: int = ...,
        *,
        category: str | None = ...,
        job_type: Literal["MANUAL", "SCHEDULED", "OTHER"] | None = ...,
        profile_id: str | None = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_jobs(
        self,
        limit: int = ...,
        offset: int = ...,
        *,
        category: str | None = ...,
        job_type: Literal["MANUAL", "SCHEDULED", "OTHER"] | None = ...,
        profile_id: str | None = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_jobs(
        self,
        limit: int = 10,
        offset: int = 0,
        *,
        category: str | None = None,
        job_type: Literal["MANUAL", "SCHEDULED", "OTHER"] | None = None,
        profile_id: str | None = None,
        model: Any = None,
    ) -> Any:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if job_type:
            params["job_type"] = job_type
        if profile_id:
            params["profile_id"] = profile_id
        return await self._get(AlmaEndpoint.JOBS, model=model, params=params)

    @overload
    async def get_job(self, job_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_job(self, job_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_job(self, job_id: str, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.JOB, {"JOB_ID": job_id}, model=model)

    @overload
    async def submit_job(
        self,
        job_id: str,
        job: dict[str, str | dict[str, str | dict[str, str]]],
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def submit_job(
        self,
        job_id: str,
        job: dict[str, str | dict[str, str | dict[str, str]]],
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def submit_job(
        self,
        job_id: str,
        job: dict[str, str | dict[str, str | dict[str, str]]],
        *,
        model: Any = None,
    ) -> Any:
        return await self._post(
            AlmaEndpoint.JOB, {"JOB_ID": job_id}, model=model, json=job, params={"op": "run"}
        )

    @overload
    async def get_job_instances(
        self,
        job_id: str,
        limit: int = ...,
        offset: int = ...,
        submit_date_from: str | None = ...,
        submit_date_to: str | None = ...,
        status: str | None = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_job_instances(
        self,
        job_id: str,
        limit: int = ...,
        offset: int = ...,
        submit_date_from: str | None = ...,
        submit_date_to: str | None = ...,
        status: str | None = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_job_instances(
        self,
        job_id: str,
        limit: int = 10,
        offset: int = 0,
        submit_date_from: str | None = None,
        submit_date_to: str | None = None,
        status: str | None = None,
        *,
        model: Any = None,
    ) -> Any:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if submit_date_to:
            params["submit_date_to"] = submit_date_to
        if submit_date_from:
            params["submit_date_from"] = submit_date_from
        if status:
            params["status"] = status
        return await self._get(
            AlmaEndpoint.JOB_INSTANCES, {"JOB_ID": job_id}, model=model, params=params
        )

    @overload
    async def get_job_instance(
        self, job_id: str, instance_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_job_instance(
        self, job_id: str, instance_id: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_job_instance(self, job_id: str, instance_id: str, *, model: Any = None) -> Any:
        return await self._get(
            AlmaEndpoint.JOB_INSTANCE, {"JOB_ID": job_id, "INSTANCE_ID": instance_id}, model=model
        )

    @overload
    async def get_job_instance_matches(
        self,
        job_id: str,
        instance_id: str,
        single_or_multi: Literal["single", "multi"],
        limit: int = ...,
        offset: int = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_job_instance_matches(
        self,
        job_id: str,
        instance_id: str,
        single_or_multi: Literal["single", "multi"],
        limit: int = ...,
        offset: int = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_job_instance_matches(
        self,
        job_id: str,
        instance_id: str,
        single_or_multi: Literal["single", "multi"],
        limit: int = 10,
        offset: int = 0,
        *,
        model: Any = None,
    ) -> Any:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if single_or_multi == "multi":
            params["population"] = "MULTI_MATCHES"
        elif single_or_multi == "single":
            params["population"] = "SINGLE_MATCHES"
        else:
            assert_never(single_or_multi)
        return await self._get(
            AlmaEndpoint.JOB_INSTANCE_MATCHES,
            {"JOB_ID": job_id, "INSTANCE_ID": instance_id},
            model=model,
            params=params,
        )

    @overload
    async def get_integration_profiles(
        self,
        profile_type: str | None = ...,
        query: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_integration_profiles(
        self,
        profile_type: str | None = ...,
        query: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_integration_profiles(
        self,
        profile_type: str | None = None,
        query: str | None = None,
        limit: int = 10,
        offset: int = 0,
        *,
        model: Any = None,
    ) -> Any:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if profile_type:
            params["type"] = profile_type
        if query:
            params["query"] = query
        return await self._get(AlmaEndpoint.INTEGRATION_PROFILES, model=model, params=params)

    @overload
    async def get_integration_profile(
        self, profile_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_integration_profile(self, profile_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_integration_profile(self, profile_id: str, *, model: Any = None) -> Any:
        return await self._get(
            AlmaEndpoint.INTEGRATION_PROFILE, {"PROFILE_ID": profile_id}, model=model
        )

    @overload
    async def update_integration_profile(
        self, profile_id: str, data: dict[str, Any], *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_integration_profile(
        self, profile_id: str, data: dict[str, Any], *, model: None = ...
    ) -> RESP_TYPE: ...

    async def update_integration_profile(
        self, profile_id: str, data: dict[str, Any], *, model: Any = None
    ) -> Any:
        return await self._put(
            AlmaEndpoint.INTEGRATION_PROFILE, {"PROFILE_ID": profile_id}, model=model, json=data
        )

    @overload
    async def create_integration_profile(
        self, data: dict[str, Any], *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def create_integration_profile(
        self, data: dict[str, Any], *, model: None = ...
    ) -> RESP_TYPE: ...

    async def create_integration_profile(self, data: dict[str, Any], *, model: Any = None) -> Any:
        return await self._post(AlmaEndpoint.INTEGRATION_PROFILES, model=model, json=data)


class AlmaClientConfigCodeTablesNS(BaseNamespace):
    """Namespace for code table functionality, exposed at AlmaClient.config.code_tables."""

    @overload
    async def get_code_tables(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_code_tables(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_code_tables(self, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.CODE_TABLES, model=model)

    @overload
    async def get_code_table(
        self, table_code: str, *, lang: str = ..., model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_code_table(
        self, table_code: str, *, lang: str = ..., model: None = ...
    ) -> RESP_TYPE: ...

    async def get_code_table(self, table_code: str, *, lang: str = "en", model: Any = None) -> Any:
        return await self._get(
            AlmaEndpoint.CODE_TABLE, {"TABLE_CODE": table_code}, model=model, params={"lang": lang}
        )

    @overload
    async def update_code_table(
        self, table_code: str, data: dict[str, Any], *, lang: str = ..., model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_code_table(
        self, table_code: str, data: dict[str, Any], *, lang: str = ..., model: None = ...
    ) -> RESP_TYPE: ...

    async def update_code_table(
        self, table_code: str, data: dict[str, Any], *, lang: str = "en", model: Any = None
    ) -> Any:
        return await self._put(
            AlmaEndpoint.CODE_TABLE,
            {"TABLE_CODE": table_code},
            model=model,
            params={"lang": lang},
            json=data,
        )


class AlmaClientConfigNS(BaseNamespace):
    """Namespace for config/admin functionality, exposing a number of sub-namespace via attrs.

    - sets
    - libraries
    - letters
    """

    def __init__(self, client: "_AlmaExecutable") -> None:
        super().__init__(client)
        self.sets = AlmaClientConfigSetsNS(client)
        self.libraries = AlmaClientConfigLibrariesNS(client)
        self.letters = AlmaClientConfigLettersNS(client)
        self.jobs = AlmaClientConfigJobsNS(client)
        self.code_tables = AlmaClientConfigCodeTablesNS(client)
