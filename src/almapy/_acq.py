from datetime import date
from typing import Any, Literal

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE


class AlmaClientAcqNS(BaseNamespace):
    """Namespace for acquisitions functionality."""

    async def get_po_line(self, po_line_id: str) -> RESP_TYPE:
        return await self._get(AlmaEndpoint.PO_LINE, {"PO_LINE_ID": po_line_id})

    async def update_po_line(
        self,
        po_line_id: str,
        updated_po_line: dict[str, Any],
        *,
        update_inventory: bool = False,
        redistribute_funds: bool = False,
    ) -> RESP_TYPE:
        return await self._put(
            AlmaEndpoint.PO_LINE,
            {"PO_LINE_ID": po_line_id},
            params={"update_inventory": update_inventory, "redistribute_funds": redistribute_funds},
            json=updated_po_line,
        )

    async def receive_existing_item(
        self,
        po_line_id: str,
        item_pid: str,
        *,
        receive_date: date | None = None,
        department: str | None = None,
        department_library: str | None = None,
        updated_item: dict[str, Any] | None = None,
    ) -> RESP_TYPE:
        if updated_item is None:
            updated_item = {}
        params: dict[str, Any] = {"op": "receive"}
        if receive_date:
            params["receive_date"] = receive_date.strftime("%Y-%m-%dZ")
        if department:
            params["department"] = department
        if department_library:
            params["department_library"] = department_library
        return await self._post(
            AlmaEndpoint.PO_LINE_ITEM,
            {"PO_LINE_ID": po_line_id, "ITEM_PID": item_pid},
            params=params,
            json=updated_item,
        )

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
        params: dict[str, Any] = {
            "reason": reason_code,
            "inform_vendor": inform_vendor,
            "override": override,
            "bib": bib_handling,
        }
        if comment:
            params["comment"] = comment
        await self._delete(
            AlmaEndpoint.PO_LINE, {"PO_LINE_ID": po_line_id}, parser="none", params=params
        )
        return True
