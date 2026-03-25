from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.logging import request_id_var
from app.core.security import decode_token
from app.db import session as db_session
from app.models.request_audit import RequestAudit

log = logging.getLogger(__name__)

Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[..., Awaitable[None]]

def _headers_scope_to_dict(raw: list[tuple[bytes, bytes]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k_b, v_b in raw:
        key = k_b.decode("latin-1")
        val = v_b.decode("latin-1", errors="replace")
        out[key] = val
    return out


def _headers_asgi_list_to_dict(raw: list[tuple[bytes, bytes]]) -> dict[str, str]:
    return _headers_scope_to_dict(raw)


def _has_header(headers: list[tuple[bytes, bytes]], name: bytes) -> bool:
    return any(k.lower() == name.lower() for k, _ in headers)


def _append_request_id_header(message: dict[str, Any], request_id_str: str) -> dict[str, Any]:
    if message["type"] != "http.response.start":
        return message
    headers = list(message.get("headers", []))
    rid_b = request_id_str.encode("latin-1")
    if not _has_header(headers, b"x-request-id"):
        headers.append((b"x-request-id", rid_b))
    return {**message, "headers": headers}


def _parse_request_id_from_scope(scope: dict[str, Any]) -> UUID:
    for k_b, v_b in scope.get("headers", []):
        if k_b.lower() == b"x-request-id":
            try:
                return UUID(v_b.decode("latin-1").strip())
            except ValueError:
                break
    return uuid4()


def _optional_user_id_from_scope(scope: dict[str, Any]) -> UUID | None:
    token: str | None = None
    for k_b, v_b in scope.get("headers", []):
        if k_b.lower() == b"authorization":
            raw = v_b.decode("latin-1").strip()
            if raw.lower().startswith("bearer "):
                token = raw[7:].strip()
            break
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return UUID(str(payload["sub"]))
    except Exception:
        return None


def _path_excluded(path: str, prefixes: list[str]) -> bool:
    for p in prefixes:
        if not p:
            continue
        if path == p or path.startswith(f"{p}/"):
            return True
    return False


class AuditMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        path = scope.get("path", "") or ""
        excluded_prefixes = settings.audit_excluded_path_prefixes()
        excluded = _path_excluded(path, excluded_prefixes)

        request_uuid = _parse_request_id_from_scope(scope)
        request_id_str = str(request_uuid)
        token = request_id_var.set(request_id_str)
        started = time.perf_counter()

        user_id = _optional_user_id_from_scope(scope)

        async def send_with_rid(message: dict[str, Any]) -> None:
            message = _append_request_id_header(message, request_id_str)
            await send(message)

        try:
            if excluded:
                await self.app(scope, receive, send_with_rid)
                return

            max_body = settings.AUDIT_MAX_BODY_BYTES
            body_buf = await self._read_request_body(receive)
            sent = False

            async def replay_receive() -> dict[str, Any]:
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": body_buf, "more_body": False}
                return {"type": "http.disconnect"}

            method = scope.get("method", "")
            qs = scope.get("query_string", b"").decode("latin-1", errors="replace") or None
            req_headers = _headers_scope_to_dict(list(scope.get("headers", [])))

            req_body_text: str | None = None
            if body_buf:
                truncated = body_buf[:max_body]
                req_body_text = truncated.decode("utf-8", errors="replace")
                if len(body_buf) > max_body:
                    req_body_text += "\n... [truncated]"

            status_code: int | None = None
            resp_headers_dict: dict[str, str] | None = None
            resp_chunks: list[bytes] = []
            total_resp = 0

            async def capture_send(message: dict[str, Any]) -> None:
                message = _append_request_id_header(message, request_id_str)
                nonlocal status_code, resp_headers_dict, total_resp
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    resp_headers_dict = _headers_asgi_list_to_dict(list(message.get("headers", [])))
                elif message["type"] == "http.response.body":
                    chunk = message.get("body") or b""
                    new_total = total_resp + len(chunk)
                    if new_total <= max_body:
                        resp_chunks.append(chunk)
                    elif total_resp < max_body:
                        rest = max_body - total_resp
                        resp_chunks.append(chunk[:rest])
                    total_resp = new_total
                await send(message)

            await self.app(scope, replay_receive, capture_send)

            duration_ms = (time.perf_counter() - started) * 1000.0
            resp_body_text: str | None = None
            if resp_chunks:
                raw = b"".join(resp_chunks)
                resp_body_text = raw.decode("utf-8", errors="replace")
                if total_resp > max_body:
                    resp_body_text += "\n... [truncated]"

            await self._persist_audit(
                request_uuid=request_uuid,
                method=method,
                path=path,
                query_string=qs,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_headers=req_headers,
                response_headers=resp_headers_dict,
                request_body=req_body_text,
                response_body=resp_body_text,
            )
        finally:
            request_id_var.reset(token)

    @staticmethod
    async def _read_request_body(receive: Receive) -> bytes:
        chunks: list[bytes] = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
            if message["type"] == "http.request":
                chunks.append(message.get("body") or b"")
                if not message.get("more_body", False):
                    break
        return b"".join(chunks)

    @staticmethod
    async def _persist_audit(
        *,
        request_uuid: UUID,
        method: str,
        path: str,
        query_string: str | None,
        status_code: int | None,
        duration_ms: float,
        user_id: UUID | None,
        request_headers: dict[str, str],
        response_headers: dict[str, str] | None,
        request_body: str | None,
        response_body: str | None,
    ) -> None:
        row = RequestAudit(
            request_id=request_uuid,
            method=method,
            path=path[:2048],
            query_string=query_string,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            request_headers=request_headers or None,
            response_headers=response_headers or None,
            request_body=request_body,
            response_body=response_body,
        )
        try:
            async with db_session.AsyncSessionLocal() as session:
                session.add(row)
                await session.commit()
        except Exception:
            log.exception("request audit persist failed request_id=%s", request_uuid)
