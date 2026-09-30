"""
title: SolidEarth RAG
author: INGV RockGPT
version: 0.1.0
description: Exposes the SolidEarth RAG (EarthPrints solid-earth articles indexed in Qdrant behind llm.pp.ingv.it) as a selectable model. Each question is forwarded to POST /rag/query and the sources come back as citations.
"""

# Design notes.
#
# The SolidEarth RAG is not an OpenAI-compatible model: the gateway lists
# only qwen35-122b-a10b-int4 and mistral-medium-3.5-128b under /v1/models,
# and the retrieval step lives in a one-shot JSON endpoint, POST /rag/query.
# So it cannot be wired as an extra "OpenAI connection"; a Pipe function is
# the Open WebUI extension point that lets arbitrary code appear as a model
# in the picker.
#
# The endpoint takes a single "question" and no chat history, so the pipe
# forwards only the latest user message. Follow-up questions therefore lose
# the conversational context; that is a limitation of the endpoint, not of
# this pipe, and is deliberately not worked around here.
#
# Response shape, verified on 2026-09-30 against the live endpoint:
#   {"answer": "...", "sources": ["<file>.pdf", ...], "chunks_used": 3,
#    "user": "rockgpt"}
# "sources" lists the files the chunks came from, deduplicated, with no
# chunk text, page or score. All knowledge about the shape is confined to
# _parse_rag_response(); when no answer is found the pipe prints the raw
# JSON in the chat so a schema change shows up instead of failing silently.
#
# The files in the vector DB are the EarthPrints "solid-earth" articles,
# named "<prefix>_<id>_<title>.pdf" where "<prefix>/<id>" is the EarthPrints
# handle (2122_7887_... -> https://www.earth-prints.org/handle/2122/7887).
# That is what makes a filename-only source clickable: the citation URL is
# rebuilt from the handle through SOURCE_URL_TEMPLATE, no PDF has to be
# served from our side.
#
# Citation rendering in Open WebUI 0.11.3, as read from its source:
#   - the socket layer appends the event payload to message.sources only
#     when data has no "type" key (socket/main.py, get_event_emitter);
#   - Citations.svelte groups sources by metadata[i].source, falling back
#     to source.id, and pairs document[i] with metadata[i] and distances[i];
#   - CitationModal.svelte turns the source name into a hyperlink only if
#     metadata.file_id exists or source.url contains "http"; otherwise the
#     chip is still clickable and opens the modal with the chunk text;
#   - if every distance lies in [-1, 1] the UI shows it as a percentage.
# Hence one event per source file (the endpoint does not expose chunks),
# metadata.source set to the filename, the EarthPrints URL rebuilt from the
# handle, and no distances at all: a made-up score would be shown as a
# relevance percentage.

import asyncio
import json
import os
import re
from typing import Any, Callable, Optional

import aiohttp
from pydantic import BaseModel, Field

# Preview budget for the raw response and for HTTP error bodies pasted in
# the chat. Enough to read the schema, small enough not to flood a message.
RAW_PREVIEW_LIMIT = 4000

# "<prefix>_<id>_" at the start of a source filename, i.e. the EarthPrints
# handle with "/" replaced by "_" (2122_7887_Studio_... -> 2122/7887).
HANDLE_PREFIX = re.compile(r"^(\d+)_(\d+)_")

# Trailing ".pdf", ".txt" and the like: 2-5 alphanumerics after the last dot.
FILE_EXTENSION = re.compile(r"\.[A-Za-z0-9]{2,5}$")


class Pipe:
    class Valves(BaseModel):
        RAG_QUERY_URL: str = Field(
            default="https://llm.pp.ingv.it/rag/query",
            description="Full URL of the gateway RAG endpoint.",
        )
        API_KEY: str = Field(
            default="",
            description=(
                "Bearer token for the gateway. Leave empty to reuse the first "
                "key of the OPENAI_API_KEYS environment variable of the "
                "Open WebUI container, i.e. the same 'rockgpt' token already "
                "configured for the gateway models."
            ),
        )
        COLLECTION: str = Field(
            default="SolidEarth",
            description="Qdrant collection to query.",
        )
        TOP_K: int = Field(
            default=10,
            description="Number of chunks retrieved from the vector DB.",
        )
        MODEL: str = Field(
            default="qwen35-122b-a10b-int4",
            description="Gateway model that writes the answer from the chunks.",
        )
        TEMPERATURE: float = Field(default=0.2)
        MAX_TOKENS: int = Field(default=1024)
        TIMEOUT_SECONDS: int = Field(
            default=300,
            description=(
                "Client timeout for the whole request. Retrieval plus a 122B "
                "model through the gateway is slow, keep this generous."
            ),
        )
        SOURCE_URL_TEMPLATE: str = Field(
            default="https://www.earth-prints.org/handle/{handle}",
            description=(
                "Template that turns a source filename into a clickable "
                "link. Placeholders: {handle} (e.g. 2122/7887, taken from "
                "the <prefix>_<id>_ start of the filename) and {filename}. "
                "Empty disables links: the citation shows the name only."
            ),
        )

    def __init__(self):
        self.valves = self.Valves()

    # --- helpers -----------------------------------------------------------

    def _resolve_api_key(self) -> str:
        """Return the bearer token: the valve if set, else the first entry
        of OPENAI_API_KEYS. Open WebUI itself splits that variable on ';'
        (config.py), so the same separator is honoured here to stay in sync
        with what the gateway connection uses."""
        if self.valves.API_KEY.strip():
            return self.valves.API_KEY.strip()
        env_keys = os.environ.get("OPENAI_API_KEYS", "")
        for key in env_keys.split(";"):
            if key.strip():
                return key.strip()
        return ""

    @staticmethod
    def _last_user_question(messages: list[dict]) -> str:
        """Extract the text of the latest user turn. Content may be a plain
        string or, for multimodal messages, a list of parts of which only
        the "text" ones matter to a text-only RAG endpoint."""
        for message in reversed(messages):
            if message.get("role") != "user":
                continue
            content = message.get("content", "")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                return "\n".join(parts).strip()
        return ""

    @staticmethod
    def _parse_rag_response(data: Any) -> tuple[Optional[str], list[str], Optional[int]]:
        """Reduce the endpoint reply to (answer, source filenames,
        chunks_used). Wire format as observed on 2026-09-30:
            {"answer": "...", "sources": ["<file>.pdf", ...],
             "chunks_used": 3, "user": "rockgpt"}
        "sources" is deduplicated per file (3 chunks gave 1 entry) and
        carries no chunk text, page or score. Returns (None, [], None)
        when no answer is found so the caller can show the raw payload."""
        if not isinstance(data, dict):
            return None, [], None
        answer = data.get("answer")
        if not isinstance(answer, str):
            return None, [], None
        sources = [
            item.strip()
            for item in data.get("sources") or []
            if isinstance(item, str) and item.strip()
        ]
        chunks = data.get("chunks_used")
        if not isinstance(chunks, int) or isinstance(chunks, bool):
            chunks = None
        return answer, sources, chunks

    def _source_url(self, filename: str) -> Optional[str]:
        """Rebuild the EarthPrints link from the filename via the template.
        None when links are disabled or the template needs a handle the
        filename does not carry."""
        template = self.valves.SOURCE_URL_TEMPLATE.strip()
        if not template:
            return None
        match = HANDLE_PREFIX.match(filename)
        handle = f"{match.group(1)}/{match.group(2)}" if match else ""
        if "{handle}" in template and not handle:
            return None
        try:
            return template.format(handle=handle, filename=filename)
        except (KeyError, IndexError, ValueError):
            # A template with a typo must not take the whole answer down.
            return None

    @staticmethod
    def _display_name(filename: str) -> str:
        """Human-readable label for the citation chip: drop the handle
        prefix and the extension, turn underscores into spaces. The raw
        filename stays in metadata.source and in the document text. The
        collection holds .txt files too (OCR output of scanned PDFs), so
        any short extension goes, not just .pdf."""
        name = HANDLE_PREFIX.sub("", filename)
        name = FILE_EXTENSION.sub("", name)
        name = name.replace("_", " ").strip()
        return name or filename

    def _citation_event(self, filename: str) -> dict:
        """Build one citation event per source file in the shape the
        0.11.3 frontend groups and renders (see the design notes above).
        No "type" key inside data, or the socket layer drops it. The
        endpoint gives no chunk text, so the "document" entry carries the
        file identity instead of pretending to be a passage."""
        url = self._source_url(filename)
        source_block: dict = {"name": self._display_name(filename)}
        if url:
            source_block["url"] = url

        lines = [f"File: {filename}"]
        if url:
            lines.append(f"EarthPrints: {url}")
        lines.append(
            "The RAG endpoint returns the source file names only; "
            "the retrieved passage text is not available."
        )
        return {
            "type": "citation",
            "data": {
                "source": source_block,
                "document": ["\n".join(lines)],
                "metadata": [{"source": filename}],
            },
        }

    @staticmethod
    async def _emit(emitter: Optional[Callable], event: dict) -> None:
        # The emitter is absent for background tasks (title, tags, ...).
        if emitter is not None:
            await emitter(event)

    @staticmethod
    async def _status(emitter: Optional[Callable], description: str, done: bool) -> None:
        await Pipe._emit(
            emitter,
            {"type": "status", "data": {"description": description, "done": done}},
        )

    # --- entry point ---------------------------------------------------------

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable] = None,
    ) -> str:
        """Forward the latest user question to /rag/query, emit one
        citation per returned source, and return the answer text. Open
        WebUI wraps the string into a single streaming chunk when the
        client asked for stream=true, so no streaming logic is needed."""
        question = self._last_user_question(body.get("messages", []))
        if not question:
            return "No user question found in the conversation."

        api_key = self._resolve_api_key()
        if not api_key:
            return (
                "SolidEarth RAG: no API key. Set the API_KEY valve or "
                "OPENAI_API_KEYS in the container environment."
            )

        payload = {
            "question": question,
            "collection": self.valves.COLLECTION,
            "top_k": self.valves.TOP_K,
            "model": self.valves.MODEL,
            "temperature": self.valves.TEMPERATURE,
            "max_tokens": self.valves.MAX_TOKENS,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        await self._status(
            __event_emitter__,
            f"Querying the {self.valves.COLLECTION} collection...",
            False,
        )

        timeout = aiohttp.ClientTimeout(total=self.valves.TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.valves.RAG_QUERY_URL, json=payload, headers=headers
                ) as response:
                    status = response.status
                    raw_text = await response.text()
        except asyncio.TimeoutError:
            await self._status(__event_emitter__, "RAG request timed out", True)
            return (
                f"SolidEarth RAG: no reply within {self.valves.TIMEOUT_SECONDS}s."
            )
        except aiohttp.ClientError as exc:
            await self._status(__event_emitter__, "RAG request failed", True)
            return f"SolidEarth RAG: request failed ({exc})."

        if status != 200:
            await self._status(__event_emitter__, f"RAG endpoint HTTP {status}", True)
            return (
                f"SolidEarth RAG: endpoint answered HTTP {status}.\n\n"
                f"```\n{raw_text[:RAW_PREVIEW_LIMIT]}\n```"
            )

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            await self._status(__event_emitter__, "RAG reply is not JSON", True)
            return (
                "SolidEarth RAG: the endpoint did not return JSON.\n\n"
                f"```\n{raw_text[:RAW_PREVIEW_LIMIT]}\n```"
            )

        answer, sources, chunks = self._parse_rag_response(data)
        if answer is None:
            # Unknown schema: surface it verbatim so the parser can be fixed
            # against real data rather than guesses.
            await self._status(__event_emitter__, "Unexpected RAG reply shape", True)
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
            return (
                "SolidEarth RAG: reply received but no `answer` field found. "
                "Raw payload:\n\n"
                f"```json\n{pretty[:RAW_PREVIEW_LIMIT]}\n```"
            )

        for filename in sources:
            await self._emit(__event_emitter__, self._citation_event(filename))

        summary = f"{len(sources)} source(s) from {self.valves.COLLECTION}"
        if chunks is not None:
            summary = f"{chunks} chunk(s), " + summary
        await self._status(__event_emitter__, summary, True)
        return answer
