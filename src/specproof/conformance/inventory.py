"""C1: AST inventory of the API endpoints a client calls. Reads code; never imports it."""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from specproof.verify.structure import norm_path

API_PATH = re.compile(r"^/?api/v\d+/")
HTTP_VERBS = ("get", "post", "put", "patch", "delete")
METHODS = frozenset(v.upper() for v in HTTP_VERBS)
_SKIP_DIRS = frozenset({"tests", "test", ".git", ".venv", "venv", "__pycache__", "build"})


@dataclass(frozen=True)
class EndpointRef:
    """One client call site (or path constant) for an API endpoint."""

    path_norm: str
    method: str
    file: str
    line: int
    dynamic: bool
    snippet: str


@dataclass(frozen=True)
class _Helper:
    position: int
    default: str | None


def _py_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.py") if not _SKIP_DIRS.intersection(p.relative_to(root).parts)
    )


def _is_api(value: object) -> bool:
    return isinstance(value, str) and bool(API_PATH.match(value))


def _constants(trees: dict[str, ast.Module]) -> dict[str, tuple[str, str, int]]:
    """Module-level NAME = "/api/..." assignments: name -> (path, file, line)."""
    found: dict[str, tuple[str, str, int]] = {}
    for rel, tree in sorted(trees.items()):
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and _is_api(node.value.value)
            ):
                found.setdefault(node.targets[0].id, (str(node.value.value), rel, node.lineno))
    return found


def _helpers(trees: dict[str, ast.Module]) -> dict[str, _Helper]:
    """Functions with a `method` parameter: its position (after self) and str default."""
    helpers: dict[str, _Helper] = {}
    for tree in trees.values():
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            names = [a.arg for a in node.args.args]
            if "method" not in names:
                continue
            offset = 1 if names and names[0] in ("self", "cls") else 0
            index = names.index("method")
            defaults = node.args.defaults
            first_default = len(names) - len(defaults)
            default = None
            if index >= first_default:
                value = defaults[index - first_default]
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    default = value.value.upper()
            helpers[node.name] = _Helper(index - offset, default)
    return helpers


def _func_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return call.func.id if isinstance(call.func, ast.Name) else ""


def _method(call: ast.Call, helpers: dict[str, _Helper]) -> str:
    name = _func_name(call)
    if name in HTTP_VERBS and isinstance(call.func, ast.Attribute):
        return name.upper()
    helper = helpers.get(name)
    if helper is not None:
        for kw in call.keywords:
            if kw.arg == "method" and isinstance(kw.value, ast.Constant):
                return str(kw.value.value).upper()
        if helper.position < len(call.args):
            arg = call.args[helper.position]
            if isinstance(arg, ast.Constant) and str(arg.value).upper() in METHODS:
                return str(arg.value).upper()
        if helper.default is not None:
            return helper.default
    for arg in call.args:
        if (
            isinstance(arg, ast.Constant)
            and isinstance(arg.value, str)
            and arg.value.upper() in METHODS
        ):
            return arg.value.upper()
    return "UNKNOWN"


def _is_http_call(call: ast.Call, helpers: dict[str, _Helper]) -> bool:
    name = _func_name(call)
    return name in helpers or (
        isinstance(call.func, ast.Attribute) and name in (*HTTP_VERBS, "request")
    )


Consts = dict[str, tuple[str, str, int]]
_API_SEARCH = re.compile(r"/?api/v\d+/")
_GLUED = re.compile(r"[^/]\{\}|\{\}[^/]")


def _render(node: ast.JoinedStr, consts: Consts) -> tuple[str, bool] | None:
    """Render an f-string with {} for unknown placeholders; cut any host prefix before the
    API path. Dynamic when a placeholder is glued to text (e.g. `static{path}`)."""
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(str(value.value))
        elif isinstance(value, ast.FormattedValue):
            inner = value.value
            if isinstance(inner, ast.Name) and inner.id in consts:
                parts.append(consts[inner.id][0])
            else:
                parts.append("{}")
    text = "".join(parts)
    match = _API_SEARCH.search(text)
    if match is None:
        return None
    path = text[match.start() :]
    return path, bool(_GLUED.search(path))


def _path_in(
    node: ast.AST, consts: Consts, local: dict[str, tuple[str, bool]]
) -> tuple[str, bool] | None:
    """The API path an expression refers to (literal, f-string, constant or local variable)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and _is_api(sub.value):
            return str(sub.value), False
        if isinstance(sub, ast.JoinedStr):
            rendered = _render(sub, consts)
            if rendered is not None:
                return rendered
        if isinstance(sub, ast.Name) and sub.id in consts:
            return consts[sub.id][0], False
        if isinstance(sub, ast.Name) and sub.id in local:
            return local[sub.id]
    return None


def _is_dynamic_expr(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and _func_name(sub) == "join":
            return True
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Add):
            return True
    return False


def _locals_by_call(tree: ast.Module, consts: Consts) -> dict[int, dict[str, tuple[str, bool]]]:
    """For each call node id, the path-valued local variables of its enclosing function."""
    scopes: dict[int, dict[str, tuple[str, bool]]] = {}
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        local: dict[str, tuple[str, bool]] = {}
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                found = _path_in(node.value, consts, {})
                if found is not None:
                    local[node.targets[0].id] = found
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                scopes[id(node)] = local
    return scopes


def _snippet(lines: list[str], lineno: int) -> str:
    return lines[lineno - 1].strip()[:160] if 0 < lineno <= len(lines) else ""


def _call_ref(
    call: ast.Call, consts: Consts, local: dict[str, tuple[str, bool]]
) -> tuple[str, bool] | None:
    """(raw path, dynamic) for an HTTP call; ("", True) for a path built at runtime."""
    for arg in [*call.args, *(kw.value for kw in call.keywords)]:
        found = _path_in(arg, consts, local)
        if found is not None:
            return found
        if _is_dynamic_expr(arg) and not isinstance(arg, ast.Constant):
            return "", True
    return None


def scan_endpoints(pkg_dir: Path) -> list[EndpointRef]:
    """Every endpoint call site in the package, sorted; test directories are skipped."""
    sources = {
        p.relative_to(pkg_dir).as_posix(): p.read_text(encoding="utf-8") for p in _py_files(pkg_dir)
    }
    trees = {rel: ast.parse(text) for rel, text in sources.items()}
    consts = _constants(trees)
    helpers = _helpers(trees)
    refs: set[EndpointRef] = set()
    used_paths: set[str] = set()
    for rel, tree in sorted(trees.items()):
        lines = sources[rel].splitlines()
        scopes = _locals_by_call(tree, consts)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_http_call(node, helpers):
                found = _call_ref(node, consts, scopes.get(id(node), {}))
                if found is None:
                    continue
                path, dynamic = found
                method = _method(node, helpers)
                used_paths.add(path)
                refs.add(
                    EndpointRef(
                        norm_path(path) if path else "",
                        method,
                        rel,
                        node.lineno,
                        dynamic,
                        _snippet(lines, node.lineno),
                    )
                )
    for name, (path, rel, line) in sorted(consts.items()):
        if not any(p == path or p.startswith(path + "{}") for p in used_paths):
            usage = _first_usage(trees, name) or (rel, line)
            refs.add(
                EndpointRef(
                    norm_path(path),
                    "UNKNOWN",
                    usage[0],
                    usage[1],
                    False,
                    _snippet(sources[usage[0]].splitlines(), usage[1]),
                )
            )
    return sorted(refs, key=lambda r: (r.file, r.line, r.path_norm, r.method))


def _first_usage(trees: dict[str, ast.Module], name: str) -> tuple[str, int] | None:
    """First place (outside its definition) where a path constant is used."""
    for rel, tree in sorted(trees.items()):
        hits = sorted(
            n.lineno
            for n in ast.walk(tree)
            if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)
        )
        if hits:
            return rel, hits[0]
    return None
