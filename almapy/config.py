from typing import Any, Dict, List, Optional, Union

import re

from httpx import AsyncClient

from almapy.client import Client
from almapy.utils import APIError, ArgError


class SubClientConfigSets(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/conf/sets"

    async def get_list(
        self,
        content_type: Optional[str] = None,
        set_type: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        set_origin: str = "UI",
    ):
        params = {
            "content_type": content_type,
            "set_type": set_type,
            "q": q,
            "limit": limit,
            "offset": offset,
            "set_origin": set_origin,
        }
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}", params=params
        )

        return response

    async def get_set(self, set_id: str):
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{set_id}"
        )
        return response

    async def create(
        self,
        data: Dict[str, Any],
        population: Optional[str] = None,
        job_instance_id: Optional[str] = None,
        from_logical_set: Optional[str] = None,
        combine: Optional[str] = None,
        set1: Optional[str] = None,
        set2: Optional[str] = None,
        nz_set_from_iz_set: Optional[str] = None,
        indication_rule: Optional[str] = None,
    ):

        response = await self.__post_req__(
            f"{self.con_params['api_endpoint']}",
            data,
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
        return response

    async def get_members(
        self,
        set_id: str,
        limit: int = 100,
        offset: int = 0,
    ):
        params = {
            "limit": limit,
            "offset": offset,
        }
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{set_id}/members",
            params=params,
        )

        return response

    async def manage_members(
        self,
        set_data: Dict[str, Any],
        member_data: List,
        id_type: Optional[str],
        op: str,
        ignore_delete_errors: bool = False,
    ):

        if op not in ["add_members", "delete_members", "replace_members"]:
            raise ArgError(
                "Manage Set Members 'op' parameter must be one of: 'add_members', 'delete_members', "
                "'replace_members'."
            )

        async def post_catch_missing_ids() -> Union[Dict, List[str]]:
            if ignore_delete_errors:
                try:
                    resp = await self.__post_req__(
                        f"{self.con_params['api_endpoint']}/{set_data['id']}",
                        body,
                        params={"id_type": id_type, "op": op},
                    )
                    return resp
                except APIError as exc:
                    missing_id_str = re.search(
                        r"The following ID\(s\) are not members in the set: \[(.*)]\.",
                        exc.message,
                    )
                    if missing_id_str:
                        missing_ids = missing_id_str.group(1).split(",")
                        return missing_ids
                    else:
                        raise exc
            else:
                resp = await self.__post_req__(
                    f"{self.con_params['api_endpoint']}/{set_data['id']}",
                    body,
                    params={"id_type": id_type, "op": op},
                )
                return resp

        if len(member_data) > 1000:
            raise ArgError("can only manage 1000 set members at once")
            # member_lists = chunks(member_data, 1000)
            # response: Union[Dict, List[str]] = {}
            # for member_list in member_lists:
            #     data = set_data.copy(exclude=excludes)
            #     data.members = {"member": list(member_list)}
            #     body = data.dict()
            #     response = await self.__post_req__(
            #         f"{self.con_params['api_endpoint']}/{set_data.id}",
            #         body,
            #         params={"id_type": id_type, "op": op},
            #     )
            #     # First loop will replace all members, subsequent loops will add remaining members.
            #     if op == "replace_members":
            #         op = "add_members"
        else:
            set_data["members"] = {"member": member_data}
            body = set_data
            response = await post_catch_missing_ids()
        return response

    async def delete(self, set_id: str) -> bool:
        """

        Args:
            set_id: str

        Returns:
            Set

        """

        response = await self.__delete_req__(
            f"{self.con_params['api_endpoint']}/{set_id}"
        )
        return response


class SubClientConfigLibraries(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/conf/libraries"

    async def get_libraries(
        self,
    ):
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}"
        )

        return response

    async def get_circ_desks(
        self,
        library: str
    ):
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{library}/circ-desks/"
        )

        return response


class SubClientConfigLetters(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/conf/letters"

    async def get_letters(self):
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}"
        )
        return response

    async def get_components(self):
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}",
            params={"type": "COMPONENT"}
        )
        return response

    async def get_letter(self, letter_id: str):
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{letter_id}"
        )
        return response

    async def update_letter(self, letter_id: str, data: str):
        response = await self.__put_req__(
            f"{self.con_params['api_endpoint']}/{letter_id}",
            data,
            xml=True
        )
        return response


class SubClientConfig(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, str],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)

        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/conf"

        self.sets = SubClientConfigSets(session, self.con_params, rate_limit)
        self.libraries = SubClientConfigLibraries(session, self.con_params, rate_limit)
        self.letters = SubClientConfigLetters(session, self.con_params, rate_limit)
