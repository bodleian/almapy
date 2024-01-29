from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal

from gracy import Gracy, GracyNamespace, graceful

from almapy._endpoints import AlmaEndpoint

if TYPE_CHECKING:
    from datetime import date

    from almapy._utils import RESP_TYPE


class AlmaClientAcqNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for acquisitions functionality."""

    def __init__(self, parent: Gracy[AlmaEndpoint], **kwargs: Any):
        super().__init__(parent, **kwargs)

    async def get_po_line(self, po_line_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.PO_LINE, {"PO_LINE_ID": po_line_id})
        return resp

    async def receive_existing_item(
        self,
        po_line_id: str,
        item_pid: str,
        *,
        receive_date: date | None = None,
        department: str | None = None,
        department_library: str | None = None,
        updated_item=None,
    ) -> RESP_TYPE:
        if updated_item is None:
            updated_item = {}
        params = {
            "op": "receive",
        }
        if receive_date:
            params["receive_date"] = receive_date.strftime("%Y-%m-%dZ")
        if department:
            params["department"] = department
        if department_library:
            params["department_library"] = department_library
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.PO_LINE_ITEM,
            {"PO_LINE_ID": po_line_id, "ITEM_PID": item_pid},
            params=params,
            json=updated_item,
        )
        return resp

    @graceful(parser={HTTPStatus.NO_CONTENT: lambda r: True, "default": lambda r: False})
    async def cancel_po_line(
        self,
        po_line_id: str,
        reason_code: str,
        *,
        comment: str | None = None,
        inform_vendor: bool = False,
        override: bool = False,
        bib_handling: Literal["retain", "delete", "suppress"] = "retain",
    ) -> bool:
        params = {
            "reason": reason_code,
            "inform_vendor": inform_vendor,
            "override": override,
            "bib": bib_handling,
        }
        if comment:
            params["comment"] = comment
        resp: bool = self.delete(AlmaEndpoint.PO_LINE, {"PO_LINE_ID": po_line_id}, params=params)
        return resp
