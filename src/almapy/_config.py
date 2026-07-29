"""Configuration and administration namespaces.

Reached as ``client.config``, which is a container exposing five sub-namespaces
over Alma's ``/conf`` endpoints:

| Attribute | Covers |
|---|---|
| ``client.config.sets`` | Itemized and logical sets, and their members |
| ``client.config.libraries`` | Libraries, locations, circulation desks, departments |
| ``client.config.letters`` | Notification letter templates and their components |
| ``client.config.jobs`` | Jobs, job instances, and integration profiles |
| ``client.config.code_tables`` | Code tables — the source of valid codes elsewhere |

``client.config.code_tables`` is the one to reach for when another method wants a
code you do not have to hand.
"""

from typing import TYPE_CHECKING, Any, Literal, assert_never, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Body, _ModelT

if TYPE_CHECKING:
    from almapy._base import _AlmaExecutable


class AlmaClientConfigSetsNS(BaseNamespace):
    """Namespace for set functionality, exposed at ``client.config.sets``.

    Alma sets come in two flavours: *itemized* sets hold an explicit list of member
    IDs, while *logical* sets are saved queries evaluated when the set is used.
    Only itemized sets can have their membership edited with
    [`manage_members`][almapy._config.AlmaClientConfigSetsNS.manage_members].
    """

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
        """List the sets defined in the institution.

        Args:
            content_type: Restrict to sets over one kind of record, e.g. ``"BIB_MMS"``,
                ``"ITEM"``, ``"USER"``. Values come from the ``SetContentType`` code
                table.
            set_type: ``"ITEMIZED"`` for explicit member lists, ``"LOGICAL"`` for
                saved queries. Both are returned when omitted.
            q: Search query, in Alma's ``field~value`` form, e.g. ``"name~Annual"``.
            limit: Maximum number of sets to return in this page.
            offset: Index of the first set to return, for paging.
            set_origin: ``"UI"`` for sets created in this institution zone,
                ``"UI_CZ"`` for sets originating in the community zone.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of sets, with ``total_record_count`` giving the full size of the
            result so the caller can page through it.

        Raises:
            APIClientError: If the query or content type is not valid.

        Examples:
            ```python
            page = await client.config.sets.get_list(
                set_type="ITEMIZED", content_type="BIB_MMS", limit=100
            )
            print(page.total_record_count)
            for s in page.set:
                print(s.id, s.name)
            ```
        """
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
        """Retrieve a single set by its ID.

        Returns the set's metadata — name, type, content type, member count — but not
        its members. Use
        [`get_members`][almapy._config.AlmaClientConfigSetsNS.get_members] for those.

        Args:
            set_id: The numeric set identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The set record.

        Raises:
            APIClientError: If no set with that ID exists.

        Examples:
            ```python
            s = await client.config.sets.get_set("1234567890")
            print(s.name, s.number_of_members.value)
            ```
        """
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
        """Create a set.

        Alma builds the new set in one of several ways depending on which optional
        argument is supplied — from a job's results, by combining two existing sets,
        by copying a logical set, and so on. Supply at most one of them; the plain
        form with none creates an empty itemized set from ``data`` alone.

        Args:
            data: The set record to create — at minimum ``name``, ``type`` and
                ``content`` must be present.
            population: Which subset of a job's output to build the set from, e.g.
                ``"MULTI_MATCHES"``. Requires ``job_instance_id``.
            job_instance_id: Build the set from the results of this job instance.
            from_logical_set: ID of a logical set to itemize into the new set.
            combine: Set operation to apply to ``set1`` and ``set2`` — one of
                ``"AND"``, ``"OR"``, ``"NOT"``.
            set1: ID of the first operand set for ``combine``.
            set2: ID of the second operand set for ``combine``.
            nz_set_from_iz_set: ID of an institution-zone set to build the
                corresponding network-zone set from.
            indication_rule: ID of an indication rule to filter members by.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created set record, including its assigned ``id``.

        Raises:
            APIClientError: If the body is incomplete, the referenced sets or job
                instance do not exist, or the combination of arguments is not valid.

        Examples:
            ```python
            new_set = await client.config.sets.create(
                {
                    "name": "Weeding candidates 2026",
                    "type": {"value": "ITEMIZED"},
                    "content": {"value": "ITEM"},
                    "private": {"value": "false"},
                }
            )
            ```
        """
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
        """Retrieve a page of a set's members.

        Args:
            set_id: The numeric set identifier.
            limit: Maximum number of members to return in this page.
            offset: Index of the first member to return, for paging.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of members, with ``total_record_count`` giving the size of the
            whole set.

        Raises:
            APIClientError: If no set with that ID exists.

        Examples:
            Page through a set of any size:

            ```python
            offset, members = 0, []
            while True:
                page = await client.config.sets.get_members("1234567890", offset=offset)
                members.extend(page.member)
                offset += 100
                if offset >= int(page.total_record_count):
                    break
            ```
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        return await self._get(
            AlmaEndpoint.SET_MEMBERS, {"SET_ID": set_id}, model=model, params=params
        )

    async def delete_set(self, set_id: str) -> None:
        """Delete a set.

        Deletes the set itself, not the records it contains.

        Args:
            set_id: The numeric set identifier.

        Returns:
            ``None``. Alma returns an empty body on success.

        Raises:
            APIClientError: If no set with that ID exists, or it is in use by a
                scheduled job.

        Examples:
            ```python
            await client.config.sets.delete_set("1234567890")
            ```
        """
        await self._delete(AlmaEndpoint.SET, {"SET_ID": set_id}, parser="none")

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
        """Add, remove or replace the members of an itemized set.

        Alma requires the whole set record on this call, so this method fetches the
        set first and then posts it back with the member list attached — **it costs
        two API requests**, not one. Only itemized sets can be edited this way;
        logical sets derive their membership from a query.

        Args:
            set_id: The numeric set identifier.
            member_id_list: The record identifiers to act on. These must match the
                set's content type — MMS IDs for a ``BIB_MMS`` set, item PIDs for an
                ``ITEM`` set, and so on.
            id_type: The kind of identifier in ``member_id_list`` when it is not the
                set's default, e.g. ``"BARCODE"`` for an item set.
            op: ``"add_members"`` appends, ``"delete_members"`` removes, and
                ``"replace_members"`` discards the existing membership entirely.
            fail_on_invalid: When True, an unrecognised identifier fails the whole
                call. Set to False to have Alma skip bad IDs and apply the rest.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated set record.

        Raises:
            APIClientError: If the set does not exist, is a logical set, or an
                identifier is invalid and ``fail_on_invalid`` is True.

        Examples:
            ```python
            await client.config.sets.manage_members(
                "1234567890",
                ["99123456789012345", "99123456789012346"],
                op="add_members",
                fail_on_invalid=False,
            )
            ```
        """
        params: dict[str, Any] = {"op": op, "fail_on_invalid": fail_on_invalid}
        if id_type:
            params["id_type"] = id_type
        body = await self.get_set(set_id)
        body["members"] = {"member": [{"id": member_id} for member_id in member_id_list]}
        return await self._post(
            AlmaEndpoint.SET, {"SET_ID": set_id}, model=model, json=body, params=params
        )


class AlmaClientConfigLibrariesNS(BaseNamespace):
    """Namespace for library functionality, exposed at ``client.config.libraries``.

    Reads the institution's physical structure: its libraries, the locations and
    circulation desks within each, and its work departments. Everything here is
    read-only — Alma does not expose library configuration for editing over the API.
    """

    @overload
    async def get_libraries(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_libraries(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_libraries(self, *, model: Any = None) -> Any:
        """List every library in the institution.

        Unpaginated — Alma returns them all in one response.

        Args:
            model: Optional Pydantic model class to validate the response into.

        Returns:
            All libraries, each with its ``code``, ``name`` and ``path``. The codes
            are what the other methods on this namespace expect.

        Examples:
            ```python
            libs = await client.config.libraries.get_libraries()
            for lib in libs.library:
                print(lib.code, lib.name)
            ```
        """
        return await self._get(AlmaEndpoint.LIBRARIES, model=model)

    @overload
    async def get_circ_desks(self, library: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_circ_desks(self, library: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_circ_desks(self, library: str, *, model: Any = None) -> Any:
        """List the circulation desks belonging to a library.

        Circulation desk codes are needed when creating loans and scanning items in.

        Args:
            library: The library code, as returned by
                [`get_libraries`][almapy._config.AlmaClientConfigLibrariesNS.get_libraries].
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The library's circulation desks.

        Raises:
            APIClientError: If no library with that code exists.

        Examples:
            ```python
            desks = await client.config.libraries.get_circ_desks("MAIN")
            for desk in desks.circ_desk:
                print(desk.code, desk.name)
            ```
        """
        return await self._get(AlmaEndpoint.CIRC_DESKS, {"LIBRARY_CODE": library}, model=model)

    @overload
    async def get_locations(self, library: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_locations(self, library: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_locations(self, library: str, *, model: Any = None) -> Any:
        """List the shelving locations within a library.

        Args:
            library: The library code, as returned by
                [`get_libraries`][almapy._config.AlmaClientConfigLibrariesNS.get_libraries].
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The library's locations, each with its ``code`` and ``name``.

        Raises:
            APIClientError: If no library with that code exists.

        Examples:
            ```python
            locs = await client.config.libraries.get_locations("MAIN")
            for loc in locs.location:
                print(loc.code, loc.name)
            ```
        """
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
        """Retrieve a single shelving location.

        Args:
            library: The library code the location belongs to.
            location: The location code.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The location record, including its external name and fulfilment unit.

        Raises:
            APIClientError: If the library or location code does not exist.

        Examples:
            ```python
            loc = await client.config.libraries.get_location("MAIN", "STACKS")
            print(loc.external_name)
            ```
        """
        return await self._get(
            AlmaEndpoint.LOCATION, {"LIBRARY_CODE": library, "LOCATION_CODE": location}, model=model
        )

    @overload
    async def get_departments(
        self,
        department_type: Literal["DIGI", "ALL"] = "ALL",
        view: Literal["brief", "FULL"] = "brief",
        library: str | None = None,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_departments(
        self,
        department_type: Literal["DIGI", "ALL"] = "ALL",
        view: Literal["brief", "FULL"] = "brief",
        library: str | None = None,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_departments(
        self,
        department_type: Literal["DIGI", "ALL"] = "ALL",
        view: Literal["brief", "FULL"] = "brief",
        library: str | None = None,
        *,
        model: Any = None,
    ) -> Any:
        """List the institution's work departments.

        Departments are the work areas material passes through — acquisitions,
        digitisation, binding — and their codes are what
        [`receive_existing_item`][almapy._acq.AlmaClientAcqNS.receive_existing_item]
        and the request-processing endpoints expect.

        Args:
            department_type: ``"ALL"`` for every department, or ``"DIGI"`` to
                restrict to digitisation departments.
            view: ``"brief"`` returns codes and names only; ``"FULL"`` adds each
                department's owners, work stations and served libraries.
            library: Restrict to departments serving this library code.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The matching departments.

        Raises:
            APIClientError: If the library code does not exist.

        Examples:
            ```python
            depts = await client.config.libraries.get_departments(
                department_type="DIGI", view="FULL", library="MAIN"
            )
            ```
        """
        params: dict[str, str] = {"type": department_type, "view": view}
        if library is not None:
            params["library"] = library
        return await self._get(AlmaEndpoint.DEPARTMENTS, {}, params=params, model=model)


class AlmaClientConfigLettersNS(BaseNamespace):
    """Namespace for letter functionality, exposed at ``client.config.letters``.

    Letters are the XSL templates Alma renders notifications from — overdue notices,
    hold shelf slips, and so on. Note that
    [`update_letter`][almapy._config.AlmaClientConfigLettersNS.update_letter] takes
    and returns XML rather than a mapping, since the template body is itself XSL.
    """

    @overload
    async def get_letters(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_letters(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_letters(self, *, model: Any = None) -> Any:
        """List the institution's letter templates.

        Returns letters only. Use
        [`get_components`][almapy._config.AlmaClientConfigLettersNS.get_components]
        for the shared header and footer fragments.

        Args:
            model: Optional Pydantic model class to validate the response into.

        Returns:
            All letter templates, each with its ``code``, ``description`` and
            enabled state.

        Examples:
            ```python
            letters = await client.config.letters.get_letters()
            for letter in letters.letter:
                print(letter.code, letter.enabled)
            ```
        """
        return await self._get(AlmaEndpoint.LETTERS, model=model)

    @overload
    async def get_components(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_components(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_components(self, *, model: Any = None) -> Any:
        """List the shared letter components.

        Components are the fragments — headers, footers, style blocks — that
        individual letters include. Same endpoint as
        [`get_letters`][almapy._config.AlmaClientConfigLettersNS.get_letters],
        filtered to ``type=COMPONENT``.

        Args:
            model: Optional Pydantic model class to validate the response into.

        Returns:
            All letter components.

        Examples:
            ```python
            components = await client.config.letters.get_components()
            ```
        """
        return await self._get(AlmaEndpoint.LETTERS, model=model, params={"type": "COMPONENT"})

    @overload
    async def get_letter(self, letter_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_letter(self, letter_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_letter(self, letter_id: str, *, model: Any = None) -> Any:
        """Retrieve a single letter template, including its XSL body.

        Args:
            letter_id: The letter code, e.g. ``"FulOverdueNotice"``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The letter record, with the template source in its ``translations``.

        Raises:
            APIClientError: If no letter with that code exists.

        Examples:
            ```python
            letter = await client.config.letters.get_letter("FulOverdueNotice")
            ```
        """
        return await self._get(AlmaEndpoint.LETTER, {"LETTER_ID": letter_id}, model=model)

    @overload
    async def update_letter(
        self, letter_id: str, data: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_letter(self, letter_id: str, data: str, *, model: None = ...) -> RESP_TYPE: ...

    async def update_letter(self, letter_id: str, data: str, *, model: Any = None) -> Any:
        """Replace a letter template.

        Unlike the rest of almapy this method sends **XML**: ``data`` is a string,
        posted with ``Content-Type: application/xml``, not a mapping. Fetch the
        current letter with
        [`get_letter`][almapy._config.AlmaClientConfigLettersNS.get_letter] first —
        Alma replaces the whole record, so a partial body drops the rest of it.

        Args:
            letter_id: The letter code, e.g. ``"FulOverdueNotice"``.
            data: The complete letter record as an XML string.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated letter record.

        Raises:
            APIClientError: If no letter with that code exists, or the XML is
                malformed or fails Alma's schema validation.

        Examples:
            ```python
            xml = "<letter><code>FulOverdueNotice</code>...</letter>"
            await client.config.letters.update_letter("FulOverdueNotice", xml)
            ```
        """
        return await self._put(
            AlmaEndpoint.LETTER,
            {"LETTER_ID": letter_id},
            model=model,
            data=data,
            headers={"Content-Type": "application/xml"},
        )


class AlmaClientConfigJobsNS(BaseNamespace):
    """Namespace for job functionality, exposed at ``client.config.jobs``.

    Covers two related areas of Alma configuration:

    - **Jobs** — the definitions Alma can run, the instances (individual runs) of
      each, and the records a run matched. Submitting a job is asynchronous:
      [`submit_job`][almapy._config.AlmaClientConfigJobsNS.submit_job] returns
      immediately with an instance link, and progress is read back with
      [`get_job_instance`][almapy._config.AlmaClientConfigJobsNS.get_job_instance].
    - **Integration profiles** — the configuration for Alma's external system
      integrations, which are the only objects here that can be created and edited.
    """

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
        """List the jobs defined in the institution.

        Args:
            limit: Maximum number of jobs to return in this page.
            offset: Index of the first job to return, for paging.
            category: Restrict to one job category, e.g. ``"IMPORT"``,
                ``"EXPORT"``, ``"REPOSITORY"``.
            job_type: ``"MANUAL"`` for jobs run against a set on demand,
                ``"SCHEDULED"`` for jobs Alma runs on a timetable, ``"OTHER"`` for
                the rest.
            profile_id: Restrict to jobs belonging to this integration or import
                profile.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of jobs, with ``total_record_count`` giving the full result size.

        Raises:
            APIClientError: If the category or profile ID is not valid.

        Examples:
            ```python
            jobs = await client.config.jobs.get_jobs(job_type="MANUAL", limit=100)
            for job in jobs.job:
                print(job.id, job.name)
            ```
        """
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
        """Retrieve a single job definition.

        The response lists the job's parameters, which is how you discover what
        [`submit_job`][almapy._config.AlmaClientConfigJobsNS.submit_job] expects in
        its body for this particular job.

        Args:
            job_id: The job identifier, e.g. ``"M1"`` or a numeric ID.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The job definition, including its parameter list.

        Raises:
            APIClientError: If no job with that ID exists.

        Examples:
            ```python
            job = await client.config.jobs.get_job("M1")
            for param in job.parameter:
                print(param.name.value, param.type.value)
            ```
        """
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
        """Submit a job for execution.

        This is asynchronous: Alma queues the job and returns immediately with a link
        to the new instance. Poll
        [`get_job_instance`][almapy._config.AlmaClientConfigJobsNS.get_job_instance]
        to follow its progress.

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could queue the job twice. See the retry semantics in
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            job_id: The job identifier to run.
            job: The job's parameters. The shape depends entirely on the job; read it
                off [`get_job`][almapy._config.AlmaClientConfigJobsNS.get_job] for the
                job in question. Manual jobs normally take at least a set ID.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A record containing ``additional_info``, whose ``link`` identifies the
            newly created job instance.

        Raises:
            APIClientError: If the job does not exist, a required parameter is
                missing, or the job cannot be run manually.

        Examples:
            ```python
            submitted = await client.config.jobs.submit_job(
                "M1",
                {"parameter": [{"name": {"value": "set_id"}, "value": "1234567890"}]},
            )
            instance_id = submitted.additional_info.link.rsplit("/", 1)[-1]
            ```
        """
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
        """List the runs (instances) of a job.

        Args:
            job_id: The job identifier.
            limit: Maximum number of instances to return in this page.
            offset: Index of the first instance to return, for paging.
            submit_date_from: Earliest submission date to include, as ``YYYY-MM-DD``.
            submit_date_to: Latest submission date to include, as ``YYYY-MM-DD``.
            status: Restrict to one run status, e.g. ``"COMPLETED_SUCCESS"``,
                ``"COMPLETED_FAILED"``, ``"RUNNING"``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of job instances, most recent first.

        Raises:
            APIClientError: If the job does not exist or a date is malformed.

        Examples:
            ```python
            runs = await client.config.jobs.get_job_instances(
                "M1", status="COMPLETED_FAILED", submit_date_from="2026-07-01"
            )
            ```
        """
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
        """Retrieve a single job run, including its status and counters.

        This is what you poll after
        [`submit_job`][almapy._config.AlmaClientConfigJobsNS.submit_job]: the
        ``status`` field reports progress, and ``counter`` carries the per-stage
        record counts once the run finishes.

        Args:
            job_id: The job identifier.
            instance_id: The identifier of the individual run.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The job instance record.

        Raises:
            APIClientError: If the job or instance does not exist.

        Examples:
            ```python
            run = await client.config.jobs.get_job_instance("M1", "9876543210")
            print(run.status.value, run.progress)
            ```
        """
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
        """Retrieve the records a job run matched.

        Applies to import and matching jobs, which classify each incoming record by
        how many existing records it matched.

        Args:
            job_id: The job identifier.
            instance_id: The identifier of the individual run.
            single_or_multi: ``"single"`` returns records that matched exactly one
                existing record, ``"multi"`` those that matched more than one and so
                need manual resolution.
            limit: Maximum number of matches to return in this page.
            offset: Index of the first match to return, for paging.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of matched records.

        Raises:
            APIClientError: If the job or instance does not exist, or the job is not
                one that produces match results.

        Examples:
            ```python
            ambiguous = await client.config.jobs.get_job_instance_matches(
                "M1", "9876543210", "multi", limit=100
            )
            ```
        """
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
        """List the institution's integration profiles.

        Args:
            profile_type: Restrict to one profile type, e.g. ``"SSO"``,
                ``"DISCOVERY"``, ``"OAI"``.
            query: Search query, in Alma's ``field~value`` form.
            limit: Maximum number of profiles to return in this page.
            offset: Index of the first profile to return, for paging.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of integration profiles.

        Raises:
            APIClientError: If the profile type or query is not valid.

        Examples:
            ```python
            profiles = await client.config.jobs.get_integration_profiles(
                profile_type="SSO"
            )
            ```
        """
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
        """Retrieve a single integration profile.

        Args:
            profile_id: The profile identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The integration profile record, including its type-specific settings.

        Raises:
            APIClientError: If no profile with that ID exists.

        Examples:
            ```python
            profile = await client.config.jobs.get_integration_profile("1234567890")
            ```
        """
        return await self._get(
            AlmaEndpoint.INTEGRATION_PROFILE, {"PROFILE_ID": profile_id}, model=model
        )

    @overload
    async def update_integration_profile(
        self, profile_id: str, data: Body, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_integration_profile(
        self, profile_id: str, data: Body, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def update_integration_profile(
        self, profile_id: str, data: Body, *, model: Any = None
    ) -> Any:
        """Replace an integration profile.

        Alma replaces the whole profile, so fetch it with
        [`get_integration_profile`][almapy._config.AlmaClientConfigJobsNS.get_integration_profile]
        and modify that rather than sending a partial body.

        Args:
            profile_id: The profile identifier.
            data: The full, modified profile record. Accepts a mapping or any object
                implementing ``dump``/``model_dump``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated integration profile record.

        Raises:
            APIClientError: If no profile with that ID exists, or the body fails
                Alma's validation for the profile type.

        Examples:
            ```python
            profile = await client.config.jobs.get_integration_profile("1234567890")
            profile.description = "Updated by nightly sync"
            await client.config.jobs.update_integration_profile("1234567890", profile)
            ```
        """
        return await self._put(
            AlmaEndpoint.INTEGRATION_PROFILE, {"PROFILE_ID": profile_id}, model=model, json=data
        )

    @overload
    async def create_integration_profile(self, data: Body, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def create_integration_profile(self, data: Body, *, model: None = ...) -> RESP_TYPE: ...

    async def create_integration_profile(self, data: Body, *, model: Any = None) -> Any:
        """Create an integration profile.

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could create a second profile. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            data: The profile record to create. The required fields depend on the
                profile ``type``. Accepts a mapping or any object implementing
                ``dump``/``model_dump``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created profile record, including its assigned ID.

        Raises:
            APIClientError: If the body is incomplete or fails Alma's validation for
                the profile type.

        Examples:
            ```python
            profile = await client.config.jobs.create_integration_profile(
                {"name": "Nightly patron load", "type": {"value": "USER"}}
            )
            ```
        """
        return await self._post(AlmaEndpoint.INTEGRATION_PROFILES, model=model, json=data)


class AlmaClientConfigCodeTablesNS(BaseNamespace):
    """Namespace for code table functionality, exposed at ``client.config.code_tables``.

    Worth reaching for when another method wants a code you do not have to hand:
    institutions add and disable rows freely, so the live table is the only
    dependable list.
    """

    @overload
    async def get_code_tables(self, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_code_tables(self, *, model: None = ...) -> RESP_TYPE: ...

    async def get_code_tables(self, *, model: Any = None) -> Any:
        """List the names of every code table in the institution.

        Returns table names only, not their rows — use
        [`get_code_table`][almapy._config.AlmaClientConfigCodeTablesNS.get_code_table]
        for the contents of one.

        Args:
            model: Optional Pydantic model class to validate the response into.

        Returns:
            All code table names.

        Examples:
            ```python
            tables = await client.config.code_tables.get_code_tables()
            ```
        """
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
        """Retrieve a code table and its rows.

        Args:
            table_code: The table name, e.g. ``"POLineCancellationReasons"``,
                ``"RequestTypes"``, ``"UserBlockDescriptions"``.
            lang: Two-letter language code for the row descriptions.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The code table, whose ``row`` list carries each ``code``, its
            ``description``, and whether it is ``enabled``. Disabled rows are still
            returned, and Alma rejects them if used.

        Raises:
            APIClientError: If no table with that name exists.

        Examples:
            Discover the cancellation reasons this institution accepts:

            ```python
            table = await client.config.code_tables.get_code_table(
                "POLineCancellationReasons"
            )
            valid = [r.code for r in table.row if r.enabled == "true"]
            ```
        """
        return await self._get(
            AlmaEndpoint.CODE_TABLE, {"TABLE_CODE": table_code}, model=model, params={"lang": lang}
        )

    @overload
    async def update_code_table(
        self, table_code: str, data: Body, *, lang: str = ..., model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_code_table(
        self, table_code: str, data: Body, *, lang: str = ..., model: None = ...
    ) -> RESP_TYPE: ...

    async def update_code_table(
        self, table_code: str, data: Body, *, lang: str = "en", model: Any = None
    ) -> Any:
        """Replace a code table's rows.

        Alma replaces the entire table, so fetch it with
        [`get_code_table`][almapy._config.AlmaClientConfigCodeTablesNS.get_code_table]
        and modify that — sending only the rows you care about deletes every other
        row in the table.

        Args:
            table_code: The table name.
            data: The full, modified code table record. Accepts a mapping or any
                object implementing ``dump``/``model_dump``.
            lang: Two-letter language code the descriptions in ``data`` are written
                in. Must match the language the table was fetched in.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated code table.

        Raises:
            APIClientError: If no table with that name exists, the table is not
                editable, or a row is malformed.

        Examples:
            ```python
            table = await client.config.code_tables.get_code_table("MyLocalTable")
            table.row.append({"code": "NEW", "description": "New reason", "enabled": "true"})
            await client.config.code_tables.update_code_table("MyLocalTable", table)
            ```
        """
        return await self._put(
            AlmaEndpoint.CODE_TABLE,
            {"TABLE_CODE": table_code},
            model=model,
            params={"lang": lang},
            json=data,
        )


class AlmaClientConfigNS(BaseNamespace):
    """Namespace for config/admin functionality, exposed at ``client.config``.

    A container only — it has no methods of its own. The work is done by its five
    sub-namespaces:

    | Attribute | Class |
    |---|---|
    | ``client.config.sets`` | [`AlmaClientConfigSetsNS`][almapy._config.AlmaClientConfigSetsNS] |
    | ``client.config.libraries`` | [`AlmaClientConfigLibrariesNS`][almapy._config.AlmaClientConfigLibrariesNS] |
    | ``client.config.letters`` | [`AlmaClientConfigLettersNS`][almapy._config.AlmaClientConfigLettersNS] |
    | ``client.config.jobs`` | [`AlmaClientConfigJobsNS`][almapy._config.AlmaClientConfigJobsNS] |
    | ``client.config.code_tables`` | [`AlmaClientConfigCodeTablesNS`][almapy._config.AlmaClientConfigCodeTablesNS] |
    """

    def __init__(self, client: "_AlmaExecutable") -> None:
        super().__init__(client)
        self.sets = AlmaClientConfigSetsNS(client)
        self.libraries = AlmaClientConfigLibrariesNS(client)
        self.letters = AlmaClientConfigLettersNS(client)
        self.jobs = AlmaClientConfigJobsNS(client)
        self.code_tables = AlmaClientConfigCodeTablesNS(client)
