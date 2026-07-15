"""Code RAG service backed by tree-sitter and a separate Chroma collection."""

from __future__ import annotations

import logging

import hashlib
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "aurasaas_codebase"

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
}

IMPORT_NODE_TYPES = {
    "python": {"import_statement", "import_from_statement"},
    "javascript": {"import_statement"},
    "java": {"import_declaration", "package_declaration"},
}

CLASS_NODE_TYPES = {
    "python": {"class_definition"},
    "javascript": {"class_declaration", "class"},
    "java": {"class_declaration", "interface_declaration", "enum_declaration"},
}

FUNCTION_NODE_TYPES = {
    "python": {"function_definition"},
    "javascript": {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "arrow_function",
        "function",
        "function_expression",
        "generator_function",
    },
    "java": {"method_declaration", "constructor_declaration"},
}


def is_supported_code_file(filename: str | Path) -> bool:
    """Return true when this service can parse the file extension."""

    return Path(filename).suffix.lower() in LANGUAGE_BY_SUFFIX


def _load_parser(language_name: str):
    """Create a tree-sitter parser without importing optional deps at module load."""

    from tree_sitter import Language, Parser

    if language_name == "python":
        import tree_sitter_python as grammar
    elif language_name == "javascript":
        import tree_sitter_javascript as grammar
    elif language_name == "java":
        import tree_sitter_java as grammar
    else:
        raise ValueError(f"Unsupported language: {language_name}")

    try:
        language = Language(grammar.language())
    except TypeError:
        language = Language(grammar.language(), language_name)
    parser = Parser()
    if hasattr(parser, "set_language"):
        parser.set_language(language)
    else:
        parser.language = language
    return parser


def _node_text(source: bytes, node: Any) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _find_first_child_text(source: bytes, node: Any, child_types: set[str]) -> str:
    stack = list(node.children)
    while stack:
        child = stack.pop(0)
        if child.type in child_types:
            return _node_text(source, child).strip()
        stack.extend(child.children)
    return ""


def _extract_name(source: bytes, node: Any, parent: Any | None = None) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _node_text(source, name_node).strip()

    if parent is not None:
        parent_name_node = parent.child_by_field_name("name")
        if parent_name_node is not None:
            return _node_text(source, parent_name_node).strip()

    identifier = _find_first_child_text(source, node, {"identifier", "property_identifier", "type_identifier"})
    if identifier:
        return identifier

    text = _node_text(source, node).strip()
    match = re.search(r"\b(?:class|def|function|interface|enum)\s+([A-Za-z_$][\w$]*)", text)
    return match.group(1) if match else "anonymous"


def _extract_signature(source: bytes, node: Any) -> str:
    text = _node_text(source, node).strip()
    first_line = text.splitlines()[0].strip() if text else ""
    if node.type in {"class_definition", "function_definition"}:
        return first_line.rstrip(":")
    brace_pos = text.find("{")
    if brace_pos >= 0:
        return " ".join(text[:brace_pos].strip().split())
    return first_line


def _collect_imports(source: bytes, root: Any, language_name: str) -> str:
    imports = []
    for child in root.children:
        if child.type in IMPORT_NODE_TYPES.get(language_name, set()):
            imports.append(_node_text(source, child).strip())
    return "\n".join(imports)


def _iter_ast_chunks(source: bytes, root: Any, language_name: str, file_name: str) -> list[dict]:
    chunks: list[dict] = []
    class_stack: list[str] = []
    import_context = _collect_imports(source, root, language_name)

    def visit(node: Any, parent: Any | None = None) -> None:
        is_class = node.type in CLASS_NODE_TYPES[language_name]
        is_function = node.type in FUNCTION_NODE_TYPES[language_name]
        parent_class = class_stack[-1] if class_stack else ""

        if is_class:
            class_name = _extract_name(source, node, parent)
            chunks.append(_build_chunk(source, node, language_name, file_name, "class", class_name, parent_class, import_context))
            class_stack.append(class_name)
            for child in node.children:
                visit(child, node)
            class_stack.pop()
            return

        if is_function:
            function_name = _extract_name(source, node, parent)
            chunks.append(_build_chunk(source, node, language_name, file_name, "function", function_name, parent_class, import_context))
            return

        for child in node.children:
            visit(child, node)

    visit(root)
    return chunks


def _build_chunk(
    source: bytes,
    node: Any,
    language_name: str,
    file_name: str,
    symbol_type: str,
    symbol_name: str,
    parent_class: str,
    import_context: str,
) -> dict:
    code = _node_text(source, node).strip()
    signature = _extract_signature(source, node)
    content_parts = [
        f"file: {file_name}",
        f"language: {language_name}",
        f"type: {symbol_type}",
        f"symbol: {symbol_name}",
    ]
    if parent_class:
        content_parts.append(f"parent_class: {parent_class}")
    if import_context:
        content_parts.extend(["imports:", import_context])
    content_parts.extend(["code:", code])

    return {
        "content": "\n".join(content_parts),
        "metadata": {
            "file_name": file_name,
            "language": language_name,
            "symbol_type": symbol_type,
            "symbol_name": symbol_name,
            "parent_class": parent_class,
            "signature": signature,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        },
    }


def parse_code_chunks(file_path: Path, original_name: str | None = None) -> list[dict]:
    """Parse a code file into AST-based class/function chunks."""

    suffix = file_path.suffix.lower()
    language_name = LANGUAGE_BY_SUFFIX.get(suffix)
    if not language_name:
        raise ValueError(f"Unsupported code extension: {suffix}")

    settings = get_settings()
    source_text = file_path.read_text(encoding=settings.text_encoding, errors="ignore")
    source = source_text.encode(settings.text_encoding)
    parser = _load_parser(language_name)
    tree = parser.parse(source)
    file_name = original_name or file_path.name
    chunks = _iter_ast_chunks(source, tree.root_node, language_name, file_name)

    if chunks:
        return chunks

    content = source_text.strip()
    return [{
        "content": f"file: {file_name}\nlanguage: {language_name}\ntype: module\ncode:\n{content}",
        "metadata": {
            "file_name": file_name,
            "language": language_name,
            "symbol_type": "module",
            "symbol_name": Path(file_name).stem,
            "parent_class": "",
            "signature": "",
            "start_line": 1,
            "end_line": max(1, content.count("\n") + 1),
        },
    }]

def _embedding_function():
    from chromadb.utils import embedding_functions

    settings = get_settings()
    cache_dir = Path(settings.code_embedding_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.code_embedding_model,
        cache_folder=str(cache_dir),
    )


def _get_collection():
    import chromadb

    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_dir)
    return client.get_or_create_collection(
        COLLECTION_NAME,
        embedding_function=_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )

def _delete_existing_file_chunks(collection, file_name: str) -> None:
    """Remove old chunks for the same uploaded filename before overwriting."""

    try:
        collection.delete(where={"file_name": file_name})
    except (ValueError, KeyError) as exc:
        logger.debug("No existing code chunks to delete for file_name=%s: %s", file_name, exc)
    except Exception as exc:
        if exc.__class__.__module__.startswith("chromadb"):
            logger.debug("Ignoring Chroma delete miss for file_name=%s: %s", file_name, exc)
            return
        raise


def _dedupe_results(results: list[dict]) -> list[dict]:
    """Drop repeated chunks from older duplicate uploads."""

    seen: set[tuple] = set()
    unique: list[dict] = []
    for item in results:
        metadata = item.get("metadata") or {}
        key = (
            metadata.get("file_name"),
            metadata.get("symbol_type"),
            metadata.get("symbol_name"),
            metadata.get("parent_class"),
            metadata.get("start_line"),
            metadata.get("end_line"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique

def ingest_code_file(file_path: Path, original_name: str | None = None) -> dict:
    """Index one code file into the isolated codebase collection with overwrite semantics."""

    file_name = original_name or file_path.name
    chunks = parse_code_chunks(file_path, original_name=file_name)
    collection = _get_collection()
    _delete_existing_file_chunks(collection, file_name)
    source_id = hashlib.sha1(file_name.encode("utf-8")).hexdigest()[:12]

    ids = []
    documents = []
    metadatas = []
    for idx, chunk in enumerate(chunks):
        metadata = dict(chunk["metadata"])
        metadata["file_name"] = file_name
        metadata["source_path"] = str(file_path)
        ids.append(f"{source_id}-{idx}")
        documents.append(chunk["content"])
        metadatas.append(metadata)

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    logger.info("Code RAG ingested file_name=%s chunks=%d collection=%s", file_name, len(chunks), COLLECTION_NAME)
    return {
        "success": True,
        "backend": "chromadb",
        "collection": COLLECTION_NAME,
        "file": file_name,
        "chunks": len(chunks),
        "embedding_model": get_settings().code_embedding_model,
    }

def query_codebase(query: str, top_k: int = 6, where: dict | None = None) -> list[dict]:
    """Retrieve AST chunks from the isolated codebase collection."""

    collection = _get_collection()
    query_kwargs = {"query_texts": [query], "n_results": min(max(top_k * 3, top_k), 50)}
    if where:
        query_kwargs["where"] = where

    result = collection.query(**query_kwargs)
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    results = [
        {
            "content": doc,
            "score": float(1 / (1 + distance)) if distance is not None else 0.0,
            "metadata": meta,
        }
        for doc, meta, distance in zip(docs, metas, distances)
    ]
    sorted_results = sorted(results, key=lambda item: item["score"], reverse=True)
    return _dedupe_results(sorted_results)[:top_k]