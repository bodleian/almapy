from datetime import date
from typing import Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Body, _ModelT


class AlmaClientAcqNS(BaseNamespace):
    """Namespace for acquisitions functionality."""

    @overload
    async def get_po_line(self, po_line_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_po_line(self, po_line_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_po_line(self, po_line_id: str, *, model: Any = None) -> Any:
        return await self._get(AlmaEndpoint.PO_LINE, {"PO_LINE_ID": po_line_id}, model=model)

    @overload
    async def update_po_line(
        self,
        po_line_id: str,
        updated_po_line: Body,
        *,
        update_inventory: bool = ...,
        redistribute_funds: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def update_po_line(
        self,
        po_line_id: str,
        updated_po_line: Body,
        *,
        update_inventory: bool = ...,
        redistribute_funds: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def update_po_line(
        self,
        po_line_id: str,
        updated_po_line: Body,
        *,
        update_inventory: bool = False,
        redistribute_funds: bool = False,
        model: Any = None,
    ) -> Any:
        return await self._put(
            AlmaEndpoint.PO_LINE,
            {"PO_LINE_ID": po_line_id},
            model=model,
            params={"update_inventory": update_inventory, "redistribute_funds": redistribute_funds},
            json=updated_po_line,
        )

    @overload
    async def receive_existing_item(
        self,
        po_line_id: str,
        item_pid: str,
        *,
        receive_date: date | None = ...,
        department: str | None = ...,
        department_library: str | None = ...,
        updated_item: Body | None = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def receive_existing_item(
        self,
        po_line_id: str,
        item_pid: str,
        *,
        receive_date: date | None = ...,
        department: str | None = ...,
        department_library: str | None = ...,
        updated_item: Body | None = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def receive_existing_item(
        self,
        po_line_id: str,
        item_pid: str,
        *,
        receive_date: date | None = None,
        department: str | None = None,
        department_library: str | None = None,
        updated_item: Body | None = None,
        model: Any = None,
    ) -> Any:
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
            model=model,
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
    ) -> None:
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
