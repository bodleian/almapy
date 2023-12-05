from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gracy import Gracy, GracyNamespace

from almapy._endpoints import AlmaEndpoint

if TYPE_CHECKING:
    from almapy._utils import RESP_TYPE


class AlmaClientAcqNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for acquisitions functionality."""

    def __init__(self, parent: Gracy[AlmaEndpoint], **kwargs: Any):
        super().__init__(parent, **kwargs)

    async def get_po_line(self, po_line_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.PO_LINE, {"PO_LINE_ID": po_line_id})
        return resp
