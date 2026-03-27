import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .paths import default_config_path, default_session_path

SHARE_URL_RE = re.compile(
    r"https?://mypikpak\.com/s/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)?",
    re.IGNORECASE,
)
INVALID_FOLDER_CHARS_RE = re.compile(r'[\\/:*?"<>|\r\n]+')
DEFAULT_CONFIG_PATH = default_config_path()
DEFAULT_SESSION_FILE = default_session_path()


@dataclass(frozen=True)
class ShareLink:
    url: str
    share_id: str
    nested_id: str | None = None


@dataclass(frozen=True)
class ShareEntry:
    link: ShareLink
    label: str


@dataclass(frozen=True)
class ImportItemResult:
    url: str
    ok: bool
    name: str
    error: str | None = None


@dataclass(frozen=True)
class AppConfig:
    username: str = ""
    password: str = ""
    folder_path: str = ""
    session_file: str = str(DEFAULT_SESSION_FILE)


@dataclass(frozen=True)
class FolderOption:
    id: str | None
    path: str
    name: str


def sanitize_folder_name(name: str) -> str:
    value = INVALID_FOLDER_CHARS_RE.sub(" ", name).strip().strip(".")
    return re.sub(r"\s+", " ", value) or "未命名链接"


def parse_share_link(url: str) -> ShareLink:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] != "s":
        raise ValueError(f"Invalid PikPak share link: {url}")

    share_id = path_parts[1]
    nested_id = path_parts[2] if len(path_parts) >= 3 else None
    return ShareLink(url=url, share_id=share_id, nested_id=nested_id)


def guess_label_from_neighbors(lines: list[str], index: int) -> str:
    for offset in range(1, 4):
        pos = index + offset
        if pos >= len(lines):
            break
        candidate = lines[pos].strip()
        if not candidate:
            continue
        if SHARE_URL_RE.search(candidate):
            continue
        if candidate.lower().startswith("pikpak drive"):
            continue
        return sanitize_folder_name(candidate)
    return ""


def extract_share_entries(text: str) -> list[ShareEntry]:
    lines = text.splitlines()
    seen: set[str] = set()
    results: list[ShareEntry] = []

    for index, raw_line in enumerate(lines):
        matches = list(SHARE_URL_RE.finditer(raw_line))
        if not matches:
            continue
        for match in matches:
            url = match.group(0).rstrip(".,;:!?)]}>\"'")
            if url in seen:
                continue
            seen.add(url)
            trailing = raw_line[match.end() :].strip(" -:：")
            label = sanitize_folder_name(trailing) if trailing else ""
            if not label:
                label = guess_label_from_neighbors(lines, index)
            if not label:
                label = parse_share_link(url).share_id
            results.append(ShareEntry(link=parse_share_link(url), label=label))

    return results


def extract_share_links(text: str) -> list[ShareLink]:
    return [entry.link for entry in extract_share_entries(text)]


def load_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.text_file:
        return Path(args.text_file).read_text(encoding="utf-8")
    return sys.stdin.read()


def load_app_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        return AppConfig()

    data = json.loads(path.read_text(encoding="utf-8"))
    return AppConfig(
        username=str(data.get("username", "")),
        password=str(data.get("password", "")),
        folder_path=str(data.get("folder_path", "")),
        session_file=str(data.get("session_file", str(DEFAULT_SESSION_FILE))),
    )


def save_app_config(config: AppConfig, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "username": config.username,
                "password": config.password,
                "folder_path": config.folder_path,
                "session_file": config.session_file,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_session(session_file: Path) -> dict[str, Any] | None:
    if not session_file.exists():
        return None
    return json.loads(session_file.read_text(encoding="utf-8"))


def save_session(session_file: Path, client: Any) -> None:
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(
        json.dumps(client.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def create_client(
    *,
    session_file: str,
    username: str | None = None,
    password: str | None = None,
) -> Any:
    try:
        from pikpakapi import PikPakApi
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency pikpakapi. Run: python -m pip install -r requirements.txt"
        ) from exc

    session_path = Path(session_file)
    session_data = load_session(session_path)
    username = username or os.getenv("PIKPAK_USERNAME")
    password = password or os.getenv("PIKPAK_PASSWORD")

    if session_data:
        client = PikPakApi.from_dict(session_data)
        if username:
            client.username = username
        if password:
            client.password = password
        try:
            await client.refresh_access_token()
            save_session(session_path, client)
            return client
        except Exception:
            if not username or not password:
                raise SystemExit("Saved session expired and no username/password was provided.")

    if not username or not password:
        raise SystemExit("Username and password are required on first login.")

    client = PikPakApi(username=username, password=password)
    await client.login()
    await client.refresh_access_token()
    save_session(session_path, client)
    return client


def is_folder_item(item: dict[str, Any]) -> bool:
    kind = str(item.get("kind", "")).lower()
    if "folder" in kind:
        return True
    mime_type = str(item.get("mime_type", "")).lower()
    return "folder" in mime_type


async def list_all_items(
    client: Any,
    parent_id: str | None = None,
    additional_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        result = await client.file_list(
            parent_id=parent_id,
            next_page_token=page_token,
            additional_filters=additional_filters,
        )
        items.extend(result.get("files", []))
        page_token = result.get("next_page_token")
        if not page_token:
            return items


async def list_current_items(client: Any, parent_id: str | None) -> list[dict[str, Any]]:
    return await list_all_items(
        client,
        parent_id=parent_id,
        additional_filters={"trashed": {"eq": False}},
    )


async def list_child_folders(
    client: Any,
    parent_id: str | None,
    parent_path: str,
) -> list[FolderOption]:
    items = await list_all_items(
        client,
        parent_id=parent_id,
        additional_filters={"trashed": {"eq": False}},
    )
    folders = [item for item in items if is_folder_item(item)]
    folders.sort(key=lambda item: str(item.get("name", "")).lower())

    results: list[FolderOption] = []
    for item in folders:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        path = f"{parent_path.rstrip('/')}/{name}" if parent_path != "/" else f"/{name}"
        results.append(FolderOption(id=item.get("id"), path=path, name=name))
    return results


async def ensure_folder_path(client: Any, folder_path: str | None) -> str | None:
    if not folder_path or folder_path == "/":
        return None
    ids = await client.path_to_id(folder_path, create=True)
    return ids[-1]["id"] if ids else None


async def create_child_folder(client: Any, parent_id: str | None, folder_name: str) -> tuple[str, str]:
    existing_children = await list_child_folders(
        client=client,
        parent_id=parent_id,
        parent_path="/",
    )
    for child in existing_children:
        if child.name == folder_name and child.id:
            return child.id, child.name

    response = await client.create_folder(name=folder_name, parent_id=parent_id)
    file_data = response.get("file", {})
    folder_id = file_data.get("id")
    actual_name = file_data.get("name") or folder_name
    if not folder_id:
        raise RuntimeError(f"Failed to create folder: {folder_name}")
    return folder_id, actual_name


def extract_shared_file_ids(share_info: dict[str, Any], link: ShareLink) -> list[str]:
    if link.nested_id:
        return [link.nested_id]
    files = share_info.get("files", [])
    file_ids = [item["id"] for item in files if item.get("id")]
    if not file_ids:
        raise RuntimeError(f"No file ids found for share link: {link.url}")
    return file_ids


async def get_file_by_id(client: Any, file_id: str) -> dict[str, Any]:
    return await client._request_get(f"https://{client.PIKPAK_API_HOST}/drive/v1/files/{file_id}")


async def wait_for_new_items_in_parent(
    client: Any,
    *,
    parent_id: str | None,
    known_ids: set[str],
    expected_names: set[str],
    expected_count: int,
    timeout_seconds: int = 20,
    interval_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    end_time = asyncio.get_running_loop().time() + timeout_seconds
    best_match: list[dict[str, Any]] = []

    while asyncio.get_running_loop().time() < end_time:
        items = await list_current_items(client, parent_id=parent_id)
        new_items = [
            item
            for item in items
            if item.get("id") not in known_ids and item.get("name") in expected_names
        ]
        if new_items:
            best_match = new_items
        if len(new_items) >= expected_count:
            return new_items
        await asyncio.sleep(interval_seconds)

    if best_match:
        return best_match
    raise RuntimeError("Timed out waiting for restored items to appear in target directory.")


async def wait_for_file_ready(
    client: Any,
    file_id: str,
    *,
    timeout_seconds: int = 20,
    interval_seconds: float = 1.0,
) -> dict[str, Any]:
    end_time = asyncio.get_running_loop().time() + timeout_seconds
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < end_time:
        try:
            item = await get_file_by_id(client, file_id)
            phase = str(item.get("phase", "")).upper()
            if not phase or phase == "PHASE_TYPE_COMPLETE":
                return item
        except Exception as exc:
            last_error = exc
        await asyncio.sleep(interval_seconds)

    if last_error:
        raise RuntimeError(f"Timed out waiting for restored item: {last_error}") from last_error
    raise RuntimeError("Timed out waiting for restored item to become available.")


async def move_files_to_parent(client: Any, ids: list[str], parent_id: str | None) -> None:
    if not ids:
        return
    if parent_id is None:
        return
    await client.file_batch_move(ids=ids, to_parent_id=parent_id)


async def rename_file_if_needed(client: Any, file_id: str, current_name: str, desired_name: str) -> str:
    if not desired_name or desired_name == current_name:
        return current_name
    await client.file_rename(id=file_id, new_file_name=desired_name)
    return desired_name


async def restore_one_share(
    client: Any,
    entry: ShareEntry,
    parent_folder_id: str | None,
    known_parent_ids: set[str],
    stage_callback=None,
) -> tuple[str, set[str]]:
    if stage_callback:
        stage_callback("读取分享信息")
    share_info = await client.get_share_info(entry.link.url)
    if isinstance(share_info, ValueError):
        raise share_info

    share_status = str(share_info.get("share_status", "")).upper()
    if share_status and share_status != "OK":
        share_status_text = str(share_info.get("share_status_text", "")).strip()
        raise RuntimeError(share_status_text or f"Share status is {share_status}.")

    top_level_items = share_info.get("files", [])
    if not top_level_items:
        raise RuntimeError("分享链接里没有可转存的顶层文件。")

    pass_code_token = share_info.get("pass_code_token", "")
    file_ids = extract_shared_file_ids(share_info, entry.link)
    desired_name = sanitize_folder_name(entry.label)
    expected_names = {
        str(item.get("name", "")).strip()
        for item in top_level_items
        if str(item.get("name", "")).strip()
    }
    existing_parent_items = await list_current_items(client, parent_folder_id)
    existing_by_name = {
        str(item.get("name", "")).strip(): item
        for item in existing_parent_items
        if str(item.get("name", "")).strip()
    }

    single_top_folder = len(top_level_items) == 1 and is_folder_item(top_level_items[0])
    single_top_item = len(top_level_items) == 1
    top_level_name = str(top_level_items[0].get("name", "")).strip() if single_top_item else ""

    if single_top_folder and top_level_name and top_level_name in existing_by_name:
        existing_item = existing_by_name[top_level_name]
        if desired_name != top_level_name:
            if stage_callback:
                stage_callback("重命名已存在文件夹")
            await rename_file_if_needed(
                client,
                str(existing_item["id"]),
                top_level_name,
                desired_name,
            )
        return desired_name, known_parent_ids

    if stage_callback:
        stage_callback("向 PikPak 请求转存")
    await client.restore(
        share_id=entry.link.share_id,
        pass_code_token=pass_code_token,
        file_ids=file_ids,
    )

    if single_top_folder:
        if stage_callback:
            stage_callback("等待新文件夹出现在目标目录")
        new_items = await wait_for_new_items_in_parent(
            client,
            parent_id=parent_folder_id,
            known_ids=known_parent_ids,
            expected_names=expected_names,
            expected_count=1,
        )
        new_item = new_items[0]
        if stage_callback:
            stage_callback("重命名文件夹")
        final_name = await rename_file_if_needed(
            client,
            str(new_item["id"]),
            str(new_item.get("name", "")).strip() or desired_name,
            desired_name,
        )
        updated_parent_ids = known_parent_ids | {str(new_item["id"])}
        return final_name, updated_parent_ids

    if stage_callback:
        stage_callback("创建目标子文件夹")
    child_folder_id, child_folder_name = await create_child_folder(
        client=client,
        parent_id=parent_folder_id,
        folder_name=desired_name,
    )

    if single_top_item:
        if stage_callback:
            stage_callback("等待新文件出现在目标目录")
        new_items = await wait_for_new_items_in_parent(
            client,
            parent_id=parent_folder_id,
            known_ids=known_parent_ids,
            expected_names=expected_names,
            expected_count=1,
        )
        restored_file_id = str(new_items[0]["id"])
        await wait_for_file_ready(client, restored_file_id)
        if stage_callback:
            stage_callback("移动新文件到目标子文件夹")
        await client.file_batch_move(ids=[restored_file_id], to_parent_id=child_folder_id)
        updated_parent_ids = known_parent_ids | {restored_file_id}
        return child_folder_name, updated_parent_ids

    if stage_callback:
        stage_callback("等待转存结果出现在目标目录")
    new_items = await wait_for_new_items_in_parent(
        client,
        parent_id=parent_folder_id,
        known_ids=known_parent_ids,
        expected_names=expected_names,
        expected_count=len(expected_names),
    )
    new_ids = [str(item["id"]) for item in new_items if item.get("id")]
    if stage_callback:
        stage_callback("移动新文件到目标子文件夹")
    await client.file_batch_move(ids=new_ids, to_parent_id=child_folder_id)
    updated_parent_ids = known_parent_ids | set(new_ids)
    return child_folder_name, updated_parent_ids


async def validate_account(
    *,
    username: str | None,
    password: str | None,
    session_file: str,
) -> dict[str, Any]:
    client = await create_client(
        session_file=session_file,
        username=username,
        password=password,
    )
    quota = await client.get_quota_info()
    folders = await list_child_folders(client, parent_id=None, parent_path="/")
    return {
        "quota": quota if isinstance(quota, dict) else {},
        "current_path": "/",
        "current_id": None,
        "folders": [{"id": item.id, "path": item.path, "name": item.name} for item in folders],
    }


async def browse_folder(
    *,
    username: str | None,
    password: str | None,
    session_file: str,
    parent_id: str | None,
    parent_path: str,
) -> dict[str, Any]:
    client = await create_client(
        session_file=session_file,
        username=username,
        password=password,
    )
    folders = await list_child_folders(client, parent_id=parent_id, parent_path=parent_path)
    return {
        "current_path": parent_path,
        "current_id": parent_id,
        "folders": [{"id": item.id, "path": item.path, "name": item.name} for item in folders],
    }


async def import_text(
    *,
    text: str,
    username: str | None = None,
    password: str | None = None,
    folder_path: str | None = None,
    session_file: str = ".pikpak_session.json",
    progress_callback=None,
) -> tuple[list[ShareEntry], list[ImportItemResult]]:
    entries = extract_share_entries(text)
    if not entries:
        return [], []

    client = await create_client(
        session_file=session_file,
        username=username,
        password=password,
    )
    parent_folder_id = await ensure_folder_path(client, folder_path)
    known_parent_ids = {
        item["id"] for item in await list_current_items(client, parent_folder_id) if item.get("id")
    }

    results: list[ImportItemResult] = []
    stages_per_entry = 6
    total = len(entries) * stages_per_entry
    for index, entry in enumerate(entries, start=1):
        stage_base = (index - 1) * stages_per_entry
        current_stage = 0

        def emit_stage(stage_text: str) -> None:
            nonlocal current_stage
            current_stage = min(current_stage + 1, stages_per_entry - 1)
            if progress_callback:
                progress_callback(
                    stage_base + current_stage,
                    total,
                    f"{index}/{len(entries)} {entry.label}: {stage_text}",
                )

        emit_stage("准备开始")
        try:
            final_name, known_parent_ids = await restore_one_share(
                client=client,
                entry=entry,
                parent_folder_id=parent_folder_id,
                known_parent_ids=known_parent_ids,
                stage_callback=emit_stage,
            )
            results.append(ImportItemResult(url=entry.link.url, ok=True, name=final_name))
        except Exception as exc:
            results.append(
                ImportItemResult(url=entry.link.url, ok=False, name=entry.label, error=str(exc))
            )
        if progress_callback:
            progress_callback(stage_base + stages_per_entry, total, f"{index}/{len(entries)} {entry.label}: 已完成")

    return entries, results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract PikPak share links from text and restore them to your drive."
    )
    parser.add_argument("--text", help="Text that contains PikPak share links.")
    parser.add_argument("--text-file", help="Read source text from a file.")
    parser.add_argument("--username", help="PikPak username/email/phone.")
    parser.add_argument("--password", help="PikPak password.")
    parser.add_argument(
        "--session-file",
        default=str(DEFAULT_SESSION_FILE),
        help="Local session cache file. Default: ./.codex/pikpak/session.json",
    )
    parser.add_argument(
        "--folder-path",
        default="",
        help="Target parent folder path in PikPak, for example /收藏/待整理",
    )
    parser.add_argument(
        "--print-links-only",
        action="store_true",
        help="Only extract and print links without logging in.",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    text = load_text(args)
    entries = extract_share_entries(text)
    if not entries:
        print("No PikPak share links found.", file=sys.stderr)
        return 1

    if args.print_links_only:
        for entry in entries:
            print(f"{entry.label} <- {entry.link.url}")
        return 0

    _, results = await import_text(
        text=text,
        username=args.username,
        password=args.password,
        folder_path=args.folder_path,
        session_file=args.session_file,
    )

    success_count = 0
    for index, result in enumerate(results, start=1):
        if result.ok:
            success_count += 1
            print(f"[{index}/{len(results)}] Imported into folder: {result.name} <- {result.url}")
        else:
            print(f"[{index}/{len(results)}] Failed: {result.url} | {result.error}", file=sys.stderr)

    print(f"Done. Success {success_count} / {len(results)}")
    return 0 if success_count else 2


def cli_main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    return asyncio.run(async_main(args))
