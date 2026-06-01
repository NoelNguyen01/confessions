import ast
import json
import logging
import re

logger = logging.getLogger(__name__)


def _extract_json_block(text: str) -> str | None:
    start = next((i for i, c in enumerate(text) if c in "{["), None)
    if start is None:
        return None

    opener, closer = ("{", "}") if text[start] == "{" else ("[", "]")
    depth = 0
    for i, c in enumerate(text[start:], start):
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
        if depth == 0:
            return text[start : i + 1]
    return None


def extract_json(raw_text: str) -> dict | list | None:
    if not raw_text:
        return None

    match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
    raw_text = match.group(1) if match else raw_text

    block = _extract_json_block(raw_text)
    if not block:
        logger.warning("extract_json: không tìm thấy JSON block")
        return None

    try:
        return json.loads(block)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(block)
    except (ValueError, SyntaxError) as e:
        logger.warning(f"extract_json failed: {e} | Input: {block[:200]}")
        return None
