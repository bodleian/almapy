from typing import Any, Dict

from box import Box
from httpx import AsyncClient

from almapy.client import Client


class SubClientAcquisitions(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/acq"

    async def get_po_line(self, po_line_id: str) -> Box:
        return await self.__get_req__(self.con_params["api_endpoint"] + f"/po-lines/{po_line_id}")
