"""Exporte l'arborescence du code en TOON compact pour son analyse par une IA."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Any

from toon_format import encode

IGNORED_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "book2plate.egg-info",
    "data",
    "node_modules",
}


def _format_type(annotation: ast.expr) -> str:
    """Réduit une annotation Python à une notation de type courte."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        left = _format_type(annotation.left)
        right = _format_type(annotation.right)
        if left == "None":
            return f"{right}?"
        if right == "None":
            return f"{left}?"
        return f"{left}|{right}"
    if isinstance(annotation, ast.Subscript):
        container = ast.unparse(annotation.value).split(".")[-1]
        arguments = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
        types = [_format_type(argument) for argument in arguments]
        if container in {"Optional"}:
            return f"{types[0]}?"
        if container == "Union":
            return "|".join(types)
        if container in {"list", "List", "Sequence", "Iterable", "set", "Set"}:
            return f"{types[0]}[]"
        if container in {"tuple", "Tuple"}:
            if len(types) == 2 and isinstance(arguments[1], ast.Constant) and arguments[1].value is Ellipsis:
                return f"{types[0]}[]"
            return f"({','.join(types)})"
        if container in {"dict", "Dict", "Mapping"}:
            return f"{{{','.join(types)}}}"
        return f"{container}[{','.join(types)}]"
    return ast.unparse(annotation)


def _format_parameter(argument: ast.arg, default: ast.expr | None = None) -> str:
    """Formate un paramètre sans espaces inutiles, en abrégeant type et défaut."""
    parameter = argument.arg
    optional_default = isinstance(default, ast.Constant) and default.value is None
    type_name = _format_type(argument.annotation) if argument.annotation is not None else ""
    if type_name.endswith("?") or optional_default:
        parameter += "?"
        type_name = type_name.removesuffix("?")
    if type_name:
        parameter += f":{type_name}"
    if default is not None and not optional_default:
        value = ast.unparse(default)
        if isinstance(default, ast.Constant) and isinstance(default.value, float) and default.value.is_integer():
            value = str(int(default.value))
        parameter += f"={value}"
    return parameter


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Produit une signature compacte, sans le nom de fonction ni self/cls."""
    arguments = node.args
    positional = arguments.posonlyargs + arguments.args
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(arguments.defaults))
    defaults.extend(arguments.defaults)
    parameters: list[str] = []

    for index, (argument, default) in enumerate(zip(positional, defaults)):
        if argument.arg not in {"self", "cls"}:
            parameters.append(_format_parameter(argument, default))
        if arguments.posonlyargs and index == len(arguments.posonlyargs) - 1:
            parameters.append("/")

    if arguments.vararg is not None:
        parameters.append(f"*{_format_parameter(arguments.vararg)}")
    elif arguments.kwonlyargs:
        parameters.append("*")

    for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults):
        parameters.append(_format_parameter(argument, default))

    if arguments.kwarg is not None:
        parameters.append(f"**{_format_parameter(arguments.kwarg)}")

    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    signature = f"{prefix}({','.join(parameters)})"
    if node.returns is not None:
        return_type = _format_type(node.returns)
        signature += f"->{('void' if return_type == 'None' else return_type)}"
    return signature


def _describe_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    """Décrit une fonction, sa signature, sa docstring et ses déclarations imbriquées."""
    nested = _describe_declarations(node.body)
    return {
        "name": node.name,
        "signature": _format_signature(node),
        "docstring": ast.get_docstring(node),
        "classes": nested["classes"],
        "functions": nested["functions"],
    }


def _describe_class(node: ast.ClassDef) -> dict[str, Any]:
    """Décrit une classe et les méthodes ou classes qu'elle contient."""
    nested = _describe_declarations(node.body)
    return {
        "name": node.name,
        "docstring": ast.get_docstring(node),
        "classes": nested["classes"],
        "functions": nested["functions"],
    }


def _describe_declarations(nodes: list[ast.stmt]) -> dict[str, list[dict[str, Any]]]:
    """Rassemble les fonctions et classes déclarées dans un même bloc Python."""
    classes = []
    functions = []
    for node in nodes:
        if isinstance(node, ast.ClassDef):
            classes.append(_describe_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_describe_function(node))
    return {"classes": classes, "functions": functions}


def _describe_file(path: Path, root: Path) -> dict[str, Any]:
    """Décrit un fichier et analyse ses déclarations s'il s'agit de Python."""
    description: dict[str, Any] = {
        "type": "file",
        "name": path.name,
        "path": path.relative_to(root).as_posix(),
    }
    if path.suffix == ".py":
        try:
            module = ast.parse(path.read_text(encoding="utf-8"))
            description["docstring"] = ast.get_docstring(module)
            description.update(_describe_declarations(module.body))
        except (OSError, SyntaxError, UnicodeDecodeError) as error:
            description["parse_error"] = str(error)
    return description


def _describe_directory(path: Path, root: Path) -> dict[str, Any]:
    """Construit récursivement l'arborescence en ignorant les données et caches."""
    children = []
    for child in sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if child.is_dir():
            if child.name in IGNORED_DIRECTORIES:
                continue
            children.append(_describe_directory(child, root))
        else:
            if child.name == ".env" or child.name.startswith(".env."):
                continue
            children.append(_describe_file(child, root))
    return {
        "type": "directory",
        "name": path.name,
        "path": "." if path == root else path.relative_to(root).as_posix(),
        "children": children,
    }


def _collect_declarations(
    classes: list[dict[str, Any]],
    functions: list[dict[str, Any]],
    file_id: int,
    structure: dict[str, Any],
    parent_class_id: int | None = None,
) -> None:
    """Aplatit les déclarations en tables TOON avec des colonnes uniformes."""
    for class_info in classes:
        class_id = len(structure["classes"])
        class_entry: dict[str, Any] = {
            "id": class_id,
            "file_id": file_id,
            "name": class_info["name"],
            "docstring": class_info["docstring"],
        }
        if parent_class_id is not None:
            class_entry["parent_class_id"] = parent_class_id
        structure["classes"].append(class_entry)
        _collect_declarations(
            class_info["classes"],
            class_info["functions"],
            file_id,
            structure,
            class_id,
        )

    for function_info in functions:
        if parent_class_id is None:
            function_entry = {
                "file_id": file_id,
                "name": function_info["name"],
                "signature": function_info["signature"],
                "docstring": function_info["docstring"],
            }
            structure["functions"].append(function_entry)
        else:
            method_entry = {
                "class_id": parent_class_id,
                "name": function_info["name"],
                "signature": function_info["signature"],
                "docstring": function_info["docstring"],
            }
            structure["methods"].append(method_entry)
        _collect_declarations(
            function_info["classes"],
            function_info["functions"],
            file_id,
            structure,
            parent_class_id,
        )


def _flatten_directory(
    directory: dict[str, Any],
    structure: dict[str, Any],
    file_tree: dict[str, Any],
) -> None:
    """Construit l'arbre des dossiers et associe un identifiant à chaque fichier."""
    for item in directory["children"]:
        if item["type"] == "directory":
            child_tree: dict[str, Any] = {}
            file_tree[item["name"]] = child_tree
            _flatten_directory(item, structure, child_tree)
            continue

        file_path = item["path"]
        file_id = len(structure["files"])
        structure["files"].append(file_path)
        file_tree[item["name"]] = file_id
        if item["docstring"] is not None:
            structure["modules"].append({"file_id": file_id, "docstring": item["docstring"]})
        if "parse_error" in item:
            structure["errors"].append({"file_id": file_id, "error": item["parse_error"]})
        _collect_declarations(item["classes"], item["functions"], file_id, structure)


def build_code_structure(source_root: Path) -> dict[str, Any]:
    """Retourne une structure TOON compacte avec les fichiers et symboles documentés."""
    tree = _describe_directory(source_root, source_root)
    structure: dict[str, Any] = {
        "root": source_root.name,
        "file_tree": {},
        "files": [],
        "modules": [],
        "classes": [],
        "functions": [],
        "methods": [],
        "errors": [],
    }
    _flatten_directory(tree, structure, structure["file_tree"])
    structure.pop("files")
    return {key: value for key, value in structure.items() if value}


def main(argv: list[str] | None = None) -> int:
    """Génère la structure TOON dans scripts/results/ depuis src/book2plate."""
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=project_root, help="Racine du projet contenant src/book2plate.")
    arguments = parser.parse_args(argv)

    project_root = arguments.root.resolve()
    source_root = project_root / "src" / "book2plate"
    if not source_root.is_dir():
        parser.error(f"Le dossier source est introuvable : {source_root}")
    output_path = project_root / "scripts" / "results" / "code_structure.toon"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    structure = build_code_structure(source_root)
    output_path.write_text(encode(structure) + "\n", encoding="utf-8")
    print(f"Structure exportée : {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
