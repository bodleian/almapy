"""Acquisitions namespace — purchase order lines and receiving.

Reached as ``client.acq``. Covers the Alma ``/acq/po-lines`` endpoints: retrieving
and updating a PO line, receiving an item against one, and cancelling it.
"""

from datetime import date
from typing import Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Body, _ModelT


class AlmaClientAcqNS(BaseNamespace):
    """Namespace for acquisitions functionality.

    Available as ``client.acq``. Every method here returns a ``Box`` by default;
    pass ``model=`` a Pydantic model class to get a validated instance of that
    model instead. See [Responses](../guide/responses.md) for the details.
    """

    @overload
    async def get_po_line(self, po_line_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_po_line(self, po_line_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_po_line(self, po_line_id: str, *, model: Any = None) -> Any:
        """Retrieve a single purchase order line.

        Args:
            po_line_id: The PO line identifier, e.g. ``POL-12345``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The PO line record.

        Raises:
            APIClientError: If the PO line does not exist or is not accessible.

        Examples:
            ```python
            pol = await client.acq.get_po_line("POL-12345")
            print(pol.number, pol.status.desc)
            ```
        """
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
        """Update a purchase order line.

        Alma replaces the whole PO line with the body supplied, so ``updated_po_line``
        should normally be a record fetched with
        [`get_po_line`][almapy._acq.AlmaClientAcqNS.get_po_line] and then modified,
        not a partial object.

        Args:
            po_line_id: The PO line identifier, e.g. ``POL-12345``.
            updated_po_line: The full, modified PO line record. Accepts a mapping or
                any object implementing ``dump``/``model_dump``, so a Pydantic model
                can be passed directly.
            update_inventory: Whether Alma should propagate the change to the
                associated inventory (items and holdings).
            redistribute_funds: Whether Alma should redistribute encumbrances across
                the fund distribution when the price or funds change.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated PO line record as returned by Alma.

        Raises:
            POUpdateFailedError: If Alma rejected the update (Alma code ``401876``).
            APIClientError: If the PO line does not exist or the body is invalid.

        Examples:
            ```python
            pol = await client.acq.get_po_line("POL-12345")
            pol.vendor_note = "Chase before end of quarter"
            updated = await client.acq.update_po_line("POL-12345", pol)
            ```
        """
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
        """Receive an item that already exists against a purchase order line.

        This is the ``op=receive`` operation on a PO line item — it marks physical
        material as arrived. The item must already exist in Alma; this method does
        not create one.

        Args:
            po_line_id: The PO line identifier, e.g. ``POL-12345``.
            item_pid: The process ID of the item being received.
            receive_date: Date of receipt. Defaults to Alma's own default (now) when
                omitted. Serialised as ``YYYY-MM-DDZ``.
            department: Code of the receiving department.
            department_library: Code of the library owning the receiving department.
            updated_item: Optional item record to apply as part of receiving, for
                example to set a barcode or enumeration at the same time. An empty
                body is sent when omitted.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The received item record.

        Raises:
            APIClientError: If the PO line or item does not exist, or the department
                codes are not valid for this institution.

        Examples:
            ```python
            from datetime import date

            item = await client.acq.receive_existing_item(
                "POL-12345",
                "23456789000000541",
                receive_date=date(2026, 7, 29),
                department="ACQ_DEPT",
                department_library="MAIN",
            )
            ```
        """
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
        """Cancel a purchase order line.

        Args:
            po_line_id: The PO line identifier, e.g. ``POL-12345``.
            reason_code: Cancellation reason. Must be a code from the
                ``POLineCancellationReasons`` code table — fetch the valid values
                with ``client.config.code_tables.get_code_table()``.
            comment: Free-text note recorded against the cancellation.
            inform_vendor: Whether Alma should notify the vendor.
            override: Whether to override Alma's cancellation warnings, for example
                when the line has already been partly received.
            bib_handling: What to do with the associated bibliographic record —
                ``"retain"`` leaves it, ``"delete"`` removes it, ``"suppress"``
                hides it from discovery.

        Returns:
            ``None``. Alma returns an empty body for a successful cancellation.

        Raises:
            APIClientError: If the PO line does not exist, the reason code is not
                valid, or Alma refuses the cancellation and ``override`` is False.

        Examples:
            ```python
            await client.acq.cancel_po_line(
                "POL-12345",
                "LIBRARY_CANCELLED",
                comment="Duplicate order",
                inform_vendor=True,
            )
            ```
        """
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
