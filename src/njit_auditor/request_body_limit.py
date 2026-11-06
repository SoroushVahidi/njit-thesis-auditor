"""Bound desktop request buffering before Starlette's body/form consumers."""

from typing import TYPE_CHECKING

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

if TYPE_CHECKING:
    from python_multipart.exceptions import MultipartParseError
    from python_multipart.multipart import parse_options_header
else:
    try:
        from python_multipart.exceptions import MultipartParseError
        from python_multipart.multipart import parse_options_header
    except ModuleNotFoundError:  # Older supported python-multipart releases.
        from multipart.exceptions import MultipartParseError
        from multipart.multipart import parse_options_header

# Bound the aggregate multipart envelope without reducing the PDF payload limit.
# This includes boundaries, part headers, filenames, CSRF and other form fields.
MULTIPART_OVERHEAD_BYTES = 64 * 1024
BODY_TOO_LARGE = (
    "This upload request is too large. Choose one PDF within the displayed file size "
    "limit and try again."
)
INVALID_BODY = "The upload request could not be read. Select your PDF and try again."


class _CSRFMultipartParser(MultiPartParser):
    """Read a token, discarding uploads even when the final boundary is missing."""

    complete = False

    def on_end(self) -> None:
        self.complete = True

    async def token(self) -> str:
        try:
            form = await self.parse()
            if not self.complete:
                raise HTTPException(400, INVALID_BODY)
            return str(form.get("csrf_token", ""))
        except (MultiPartException, MultipartParseError):
            raise HTTPException(400, INVALID_BODY) from None
        finally:
            # FormData.close() only sees completed parts. Starlette tracks every
            # allocated spool here, including an unfinished part absent from the
            # returned form. Close them all on success, parse failure or cancellation.
            for file in self._files_to_close_on_error:
                file.close()


async def read_csrf_token(request: Request) -> str:
    """Parse only after the guarded body read, leaving its cache for the endpoint."""
    content_type, _ = parse_options_header(request.headers.get("content-type"))
    if content_type == b"multipart/form-data":
        return await _CSRFMultipartParser(request.headers, request.stream()).token()
    async with request.form() as form:
        return str(form.get("csrf_token", ""))


class RequestBodyLimitMiddleware:
    """Count original ASGI bytes, without consuming or replaying the stream.

    Checks are lazy: desktop Host/session/Origin rejection can run without reading
    any body. Content-Length is only an early-rejection hint; every actual chunk
    is checked before it reaches Request.body() or a multipart parser. At most
    the budget is passed through, plus the server-owned offending chunk inspected
    here (never appended to the application's body cache).
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        received = 0
        lengths = Headers(scope=scope).getlist("content-length")

        async def limited_receive() -> Message:
            nonlocal received
            if lengths:
                try:
                    if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
                        raise ValueError
                    declared = int(lengths[0])
                except ValueError:
                    raise HTTPException(400, INVALID_BODY) from None
                if declared > self.max_body_bytes:
                    raise HTTPException(413, BODY_TOO_LARGE)
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise HTTPException(413, BODY_TOO_LARGE)
            return message

        await self.app(scope, limited_receive, send)
