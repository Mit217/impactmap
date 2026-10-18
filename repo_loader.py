import ast
import io
import zipfile

import requests

SKIP_DIRS = {"venv", ".venv", "node_modules", "tests", "test", "docs",
             "build", "dist", "site-packages", "__pycache__", "examples"}
MAX_FILES = 300
MAX_ZIP_MB = 50


def parse_repo_url(url):
    """'https://github.com/owner/repo' -> ('owner', 'repo')"""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("github.com/")[-1].split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError("Please enter a URL like https://github.com/owner/repo")
    return parts[0], parts[1]


def download_repo(owner, repo):
    """Download the default branch of a public repo as a zip file."""
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/zipball", timeout=60
    )
    if r.status_code == 404:
        raise ValueError("Repo not found (is it public?)")
    r.raise_for_status()
    if len(r.content) > MAX_ZIP_MB * 1024 * 1024:
        raise ValueError(f"Repo is larger than {MAX_ZIP_MB} MB, too big for this demo")
    return zipfile.ZipFile(io.BytesIO(r.content))


def read_python_files(zf):
    """Return {path_in_repo: source_code} for the repo's .py files."""
    files = {}
    for info in zf.infolist():
        if info.is_dir() or not info.filename.endswith(".py"):
            continue
        path = info.filename.split("/", 1)[1]  # drop GitHub's top-level folder
        if any(part in SKIP_DIRS for part in path.split("/")):
            continue
        files[path] = zf.read(info).decode("utf-8", errors="ignore")
        if len(files) >= MAX_FILES:
            break
    # Handle "src/" layouts so module names come out right
    src = {p[4:]: c for p, c in files.items() if p.startswith("src/")}
    if src and len(src) >= len(files) / 2:
        files = src
    return files


def path_to_module(path):
    """'pkg/sub/mod.py' -> 'pkg.sub.mod', 'pkg/__init__.py' -> 'pkg'"""
    parts = path[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def resolve_to_module(name, modules):
    """Find the longest prefix of `name` that is a module in this repo."""
    while name:
        if name in modules:
            return name
        name = name.rpartition(".")[0]
    return None


def resolve_relative(node, current, is_package):
    """Turn 'from .x import y' into an absolute module name."""
    package = current.split(".") if current else []
    if not is_package:
        package = package[:-1]
    up = node.level - 1
    if up > len(package):
        return None
    if up:
        package = package[:-up]
    if node.module:
        package = package + node.module.split(".")
    return ".".join(package)


def build_dependencies(files):
    """Return (modules, deps) where deps is a set of (importer, imported)."""
    modules = {path_to_module(p): p for p in files if path_to_module(p)}
    deps = set()

    for path, code in files.items():
        me = path_to_module(path)
        if not me:
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        is_package = path.endswith("__init__.py")

        for node in ast.walk(tree):
            candidates = []
            if isinstance(node, ast.Import):
                candidates = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = resolve_relative(node, me, is_package)
                    if base is None:
                        continue
                else:
                    base = node.module or ""
                if base:
                    candidates.append(base)
                for a in node.names:
                    candidates.append(f"{base}.{a.name}" if base else a.name)

            for c in candidates:
                target = resolve_to_module(c, modules)
                if target and target != me:
                    deps.add((me, target))

    return modules, deps


if __name__ == "__main__":
    url = input("GitHub repo URL: ")
    owner, repo = parse_repo_url(url)
    files = read_python_files(download_repo(owner, repo))
    modules, deps = build_dependencies(files)

    print(f"\n{len(modules)} modules, {len(deps)} dependencies")
    for a, b in sorted(deps)[:20]:
        print(f"  {a}  -->  {b}")