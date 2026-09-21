"""Alma Digital representation namespace.

Reached as ``client.bibs.representations``. Covers the ten Digital
Representations endpoints of the Bibs API: the representations hanging off a
bibliographic record, and the files hanging off each representation.

A representation is Alma Digital's equivalent of a holding: a bib record can
carry several, each with its own usage type (``DERIVATIVE_COPY``,
``PRESERVATION_MASTER`` and so on) and either local files or a link to a remote
repository. Remote representations have no files, so the file methods here apply
only to non-remote ones.

Files are not uploaded through this API. ``create_file`` registers a file that
has already been placed in the institution's S3 upload folder – see
[Alma Digital](https://developers.exlibrisgroup.com/alma/integrations/digital/almadigital/).
"""

from typing import Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Body, _ModelT


class AlmaClientBibRepresentationsNS(BaseNamespace):
    """Namespace for digital representations, exposed at ``client.bibs.representations``.

    Representations and their files live under a bibliographic record, so every
    method here wants an MMS ID. Start with
    [`get_representations`][almapy._representations.AlmaClientBibRepresentationsNS.get_representations]
    to find the representation IDs a record carries.

    The file methods – ``get_files``, ``get_file``, ``create_file``,
    ``update_file``, ``delete_file`` – are supported for non-remote
    representations only. A remote representation points at an external
    repository and has no files in Alma.

    Everything here returns a ``Box`` and accepts ``model=``, except the two
    delete methods, which return ``None``.
    """

    @overload
    async def get_representations(
        self,
        mms_id: str,
        *,
        originating_record_id: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        use_updated_terminology: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_representations(
        self,
        mms_id: str,
        *,
        originating_record_id: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        use_updated_terminology: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_representations(
        self,
        mms_id: str,
        *,
        originating_record_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
        use_updated_terminology: bool = False,
        model: Any = None,
    ) -> Any:
        """List the digital representations on a bibliographic record.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            originating_record_id: Restrict the result to the representation whose
                object has this ID in the remote repository. Only meaningful for
                remote representations.
            limit: Maximum number of representations to return in this page. Note
                the default here is 10, not 100; Alma caps it at 100.
            offset: Index of the first representation to return, for paging.
            use_updated_terminology: Report the usage type of the institution's
                main representation as ``PRIMARY`` rather than the older
                ``DERIVATIVE_COPY``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of representations, with ``total_record_count`` giving the full
            result size.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.

        Examples:
            ```python
            reps = await client.bibs.representations.get_representations(
                "99123456789012345", limit=100
            )
            for rep in reps.representation:
                print(rep.id, rep.label, rep.usage_type.value)
            ```
        """
        params: dict[str, Any] = {
            "originating_record_id": originating_record_id,
            "limit": limit,
            "offset": offset,
            "use_updated_terminology": use_updated_terminology,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._get(
            AlmaEndpoint.REPRESENTATIONS, {"MMS_ID": mms_id}, model=model, params=params
        )

    @overload
    async def get_representation(
        self,
        mms_id: str,
        rep_id: str,
        *,
        use_updated_terminology: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_representation(
        self,
        mms_id: str,
        rep_id: str,
        *,
        use_updated_terminology: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_representation(
        self,
        mms_id: str,
        rep_id: str,
        *,
        use_updated_terminology: bool = False,
        model: Any = None,
    ) -> Any:
        """Retrieve one digital representation.

        Works for both remote and non-remote representations.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            use_updated_terminology: Report the usage type of the institution's
                main representation as ``PRIMARY`` rather than the older
                ``DERIVATIVE_COPY``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The representation record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation does not exist.

        Examples:
            ```python
            rep = await client.bibs.representations.get_representation(
                "99123456789012345", "12345678900001234"
            )
            print(rep.label, rep.library.value)
            ```
        """
        return await self._get(
            AlmaEndpoint.REPRESENTATION,
            {"MMS_ID": mms_id, "REP_ID": rep_id},
            model=model,
            params={"use_updated_terminology": use_updated_terminology},
        )

    @overload
    async def create_representation(
        self,
        mms_id: str,
        representation: Body,
        *,
        generate_label: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_representation(
        self,
        mms_id: str,
        representation: Body,
        *,
        generate_label: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_representation(
        self,
        mms_id: str,
        representation: Body,
        *,
        generate_label: bool = False,
        model: Any = None,
    ) -> Any:
        """Create a digital representation on a bibliographic record.

        Being a POST, this call is **not replayed** if the response is lost in
        transit – a retry could create a duplicate representation. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            mms_id: The MMS ID of the bibliographic record.
            representation: The representation to create. ``library`` and
                ``usage_type`` are mandatory; ``is_remote`` defaults to ``false``.
                Accepts a mapping or any object implementing ``dump``/``model_dump``.
            generate_label: Whether Alma should build the representation's label
                from its entity type and bibliographic fields.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created representation, including its assigned ID.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            BibNotInCollectionError: If the bib record is not assigned to a
                collection, which Alma Digital requires.
            APIClientError: If the library or usage type is not valid for this
                institution.

        Examples:
            ```python
            rep = await client.bibs.representations.create_representation(
                "99123456789012345",
                {
                    "library": {"value": "MAIN"},
                    "usage_type": {"value": "DERIVATIVE_COPY"},
                    "label": "Digitised copy",
                },
            )
            ```
        """
        return await self._post(
            AlmaEndpoint.REPRESENTATIONS,
            {"MMS_ID": mms_id},
            model=model,
            params={"generate_label": generate_label},
            json=representation,
        )

    @overload
    async def update_representation(
        self,
        mms_id: str,
        rep_id: str,
        representation: Body,
        *,
        generate_label: bool = ...,
        handle_bib: Literal["retain", "suppress"] = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def update_representation(
        self,
        mms_id: str,
        rep_id: str,
        representation: Body,
        *,
        generate_label: bool = ...,
        handle_bib: Literal["retain", "suppress"] = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def update_representation(
        self,
        mms_id: str,
        rep_id: str,
        representation: Body,
        *,
        generate_label: bool = False,
        handle_bib: Literal["retain", "suppress"] = "retain",
        model: Any = None,
    ) -> Any:
        """Update a digital representation.

        Alma replaces the whole representation, so fetch it with
        [`get_representation`][almapy._representations.AlmaClientBibRepresentationsNS.get_representation]
        and modify that rather than sending a partial body.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            representation: The full, modified representation. Accepts a mapping or
                any object implementing ``dump``/``model_dump``.
            generate_label: Whether Alma should rebuild the representation's label
                from its entity type and bibliographic fields.
            handle_bib: What to do with the bib record if this update leaves it
                without an active representation – ``"retain"`` or ``"suppress"``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated representation.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation does not exist, or a code in the
                body is not valid for this institution.

        Examples:
            ```python
            rep = await client.bibs.representations.get_representation(
                "99123456789012345", "12345678900001234"
            )
            rep.public_note = "Access restricted to reading room"
            await client.bibs.representations.update_representation(
                "99123456789012345", "12345678900001234", rep
            )
            ```
        """
        # Alma spells the bib-disposition parameter "bibs" here, where the holding
        # and item endpoints spell it "bib". It ignores an unrecognised parameter
        # silently, so the wrong spelling would suppress nothing and report nothing.
        return await self._put(
            AlmaEndpoint.REPRESENTATION,
            {"MMS_ID": mms_id, "REP_ID": rep_id},
            model=model,
            params={"generate_label": generate_label, "bibs": handle_bib},
            json=representation,
        )

    async def delete_representation(
        self,
        mms_id: str,
        rep_id: str,
        *,
        override: bool = False,
        handle_bib: Literal["retain", "suppress", "delete"] = "retain",
    ) -> None:
        """Delete a digital representation.

        Deleting a representation deletes its files with it. ``handle_bib``
        defaults to ``"retain"``, the conservative choice – deleting the bib record
        removes everything else attached to it too.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            override: Delete even when Alma raises warnings. Defaults to ``False``
                so the shortest call cannot silently discard content.
            handle_bib: What to do with the bib record if this was its last
                representation – ``"retain"``, ``"suppress"`` or ``"delete"``.

        Returns:
            ``None``. Alma returns an empty body on success.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation does not exist.

        Examples:
            ```python
            await client.bibs.representations.delete_representation(
                "99123456789012345", "12345678900001234"
            )
            ```
        """
        await self._delete(
            AlmaEndpoint.REPRESENTATION,
            {"MMS_ID": mms_id, "REP_ID": rep_id},
            parser="none",
            params={"override": override, "bibs": handle_bib},
        )

    @overload
    async def get_files(
        self, mms_id: str, rep_id: str, *, expand_url: bool = ..., model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_files(
        self, mms_id: str, rep_id: str, *, expand_url: bool = ..., model: None = ...
    ) -> RESP_TYPE: ...

    async def get_files(
        self, mms_id: str, rep_id: str, *, expand_url: bool = False, model: Any = None
    ) -> Any:
        """List the files on a digital representation.

        Supported for non-remote representations only.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            expand_url: Send ``expand=url``, which makes Alma populate each file's
                ``url`` field with a signed download link. Off by default – the
                links are short-lived and cost Alma work to mint.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The representation's files, with ``total_record_count`` giving the full
            result size.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation does not exist or is remote.

        Examples:
            ```python
            files = await client.bibs.representations.get_files(
                "99123456789012345", "12345678900001234", expand_url=True
            )
            for f in files.representation_file:
                print(f.pid, f.label, f.url)
            ```
        """
        params = {"expand": "url"} if expand_url else {}
        return await self._get(
            AlmaEndpoint.REPRESENTATION_FILES,
            {"MMS_ID": mms_id, "REP_ID": rep_id},
            model=model,
            params=params,
        )

    @overload
    async def get_file(
        self,
        mms_id: str,
        rep_id: str,
        file_id: str,
        *,
        expand_url: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_file(
        self,
        mms_id: str,
        rep_id: str,
        file_id: str,
        *,
        expand_url: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_file(
        self,
        mms_id: str,
        rep_id: str,
        file_id: str,
        *,
        expand_url: bool = False,
        model: Any = None,
    ) -> Any:
        """Retrieve one file from a digital representation.

        Supported for non-remote representations only.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            file_id: The file ID.
            expand_url: Send ``expand=url``, which makes Alma populate the file's
                ``url`` field with a signed download link.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The file record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation or file does not exist.

        Examples:
            ```python
            f = await client.bibs.representations.get_file(
                "99123456789012345", "12345678900001234", "23456789000001234"
            )
            print(f.label, f.path)
            ```
        """
        params = {"expand": "url"} if expand_url else {}
        return await self._get(
            AlmaEndpoint.REPRESENTATION_FILE,
            {"MMS_ID": mms_id, "REP_ID": rep_id, "FILE_ID": file_id},
            model=model,
            params=params,
        )

    @overload
    async def create_file(
        self,
        mms_id: str,
        rep_id: str,
        file: Body,
        *,
        timeout: float | tuple[float, float] | None = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_file(
        self,
        mms_id: str,
        rep_id: str,
        file: Body,
        *,
        timeout: float | tuple[float, float] | None = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_file(
        self,
        mms_id: str,
        rep_id: str,
        file: Body,
        *,
        timeout: float | tuple[float, float] | None = None,
        model: Any = None,
    ) -> Any:
        """Register a file on a digital representation.

        This does **not** upload bytes. The file must already have been placed in
        the institution's S3 upload folder, and ``path`` in the body is its
        location there, starting with the institution code – for example
        ``01UNI_INST/upload/scratch/1234/file.png``. See
        [Alma Digital](https://developers.exlibrisgroup.com/alma/integrations/digital/almadigital/).

        Alma *moves* the file from the upload folder to permanent storage as part
        of this call, so it can take many seconds on a large file. The session's
        read timeout is 90 seconds; pass ``timeout=`` to raise it for this call.

        Being a POST, this call is **not replayed** if the response is lost in
        transit – a retry could register a duplicate file. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            file: The file to register. ``path`` is mandatory. Accepts a mapping or
                any object implementing ``dump``/``model_dump``.
            timeout: Override the transport timeout for this call, in seconds.
                Either a single value or a ``(connect, read)`` pair.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly registered file, including its assigned PID and its final
            storage path.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation does not exist or is remote, or
                the path does not resolve to a file in the upload folder.

        Examples:
            ```python
            f = await client.bibs.representations.create_file(
                "99123456789012345",
                "12345678900001234",
                {"label": "Page 1", "path": "01UNI_INST/upload/scratch/1234/page1.jpg"},
                timeout=120,
            )
            ```
        """
        extra: dict[str, Any] = {} if timeout is None else {"timeout": timeout}
        return await self._post(
            AlmaEndpoint.REPRESENTATION_FILES,
            {"MMS_ID": mms_id, "REP_ID": rep_id},
            model=model,
            json=file,
            **extra,
        )

    @overload
    async def update_file(
        self, mms_id: str, rep_id: str, file_id: str, file: Body, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_file(
        self, mms_id: str, rep_id: str, file_id: str, file: Body, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def update_file(
        self, mms_id: str, rep_id: str, file_id: str, file: Body, *, model: Any = None
    ) -> Any:
        """Update a file on a digital representation.

        Alma replaces the whole file record, so fetch it with
        [`get_file`][almapy._representations.AlmaClientBibRepresentationsNS.get_file]
        and modify that rather than sending a partial body. Only the metadata is
        updatable – to replace the bytes, register a new file and delete this one.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            file_id: The file ID.
            file: The full, modified file record. Accepts a mapping or any object
                implementing ``dump``/``model_dump``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated file record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation or file does not exist.

        Examples:
            ```python
            await client.bibs.representations.update_file(
                "99123456789012345",
                "12345678900001234",
                "23456789000001234",
                {"label": "Title page"},
            )
            ```
        """
        return await self._put(
            AlmaEndpoint.REPRESENTATION_FILE,
            {"MMS_ID": mms_id, "REP_ID": rep_id, "FILE_ID": file_id},
            model=model,
            json=file,
        )

    async def delete_file(
        self,
        mms_id: str,
        rep_id: str,
        file_id: str,
        *,
        handle_representation: Literal["retain", "delete"] = "retain",
        handle_bib: Literal["retain", "suppress", "delete"] = "retain",
    ) -> None:
        """Delete a file from a digital representation.

        Both dispositions default to ``"retain"``, the conservative choice: a
        representation left with no files, and a bib left with no representations,
        stay where they are unless asked otherwise.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            rep_id: The representation ID.
            file_id: The file ID.
            handle_representation: What to do with the representation if this was
                its last file – ``"retain"`` or ``"delete"``.
            handle_bib: What to do with the bib record if the representation is
                deleted and was its last one – ``"retain"``, ``"suppress"`` or
                ``"delete"``. Only reachable when ``handle_representation`` is
                ``"delete"``.

        Returns:
            ``None``. Alma returns an empty body on success.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the representation or file does not exist.

        Examples:
            ```python
            await client.bibs.representations.delete_file(
                "99123456789012345", "12345678900001234", "23456789000001234"
            )
            ```
        """
        await self._delete(
            AlmaEndpoint.REPRESENTATION_FILE,
            {"MMS_ID": mms_id, "REP_ID": rep_id, "FILE_ID": file_id},
            parser="none",
            params={"representations": handle_representation, "bibs": handle_bib},
        )
