from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal

from gracy import Gracy, GracyNamespace, graceful

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
            data=data,
            headers={"Content-Type": "application/xml"},
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
