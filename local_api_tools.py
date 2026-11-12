"""Local-only MT2600 snapshot helpers.

Configuration comes from the environment, never from the repository:
  MT2600_HOST     IP address of the central unit (default 10.0.0.107)
  MT2600_USER     local_user (mydevolo user UUID)
  MT2600_PASSKEY  local_passkey (32 hex characters)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

BASE = Path(__file__).resolve().parent
TARGET = os.environ.get("MT2600_HOST", "10.0.0.107")
HOST = "http://" + TARGET


def save(path, value):
    path = Path(path)
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(content)
    return {"file": path.name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


class LocalAPI:
    def __init__(self):
        try:
            user, key = os.environ["MT2600_USER"], os.environ["MT2600_PASSKEY"]
        except KeyError as missing:
            raise ValueError(f"Environment variable {missing} is not set") from None
        self.session = requests.Session()
        self.session.trust_env = False
        self.counter = 0
        response = self.session.get(HOST + "/dhlp/portal/full", auth=(user, key), timeout=15, allow_redirects=False)
        response.raise_for_status()
        link = response.json()["link"]
        parsed = urlsplit(link)
        if parsed.scheme != "http" or parsed.hostname != TARGET or parsed.port not in (None, 80) or not parsed.path.startswith("/dhlp/"):
            raise ValueError("Unexpected session destination")
        self.session.get(link, timeout=15, allow_redirects=False)
        if "JSESSIONID" not in self.session.cookies:
            raise ValueError("No local session cookie")

    def rpc(self, method, params):
        self.counter += 1
        response = self.session.post(
            HOST + "/remote/json-rpc",
            json={"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params},
            timeout=30, allow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("id") != self.counter:
            raise ValueError("RPC response ID mismatch")
        return data

    def result(self, method, params):
        response = self.rpc(method, params)
        if "error" in response:
            raise ValueError(f"RPC failed: {method}, code {response['error'].get('code')}")
        if "result" not in response:
            raise ValueError(f"RPC response has no result: {method}")
        return response["result"]

    def close(self):
        self.session.close()


def item_uid(item):
    return item.get("uid", item.get("UID", item.get("id")))


def snapshot(directory):
    directory = Path(directory)
    if not directory.is_dir() or list(directory.iterdir()):
        raise ValueError("Snapshot destination must be an existing empty private directory")
    api = LocalAPI()
    manifest = {"started_utc": datetime.now(timezone.utc).isoformat(), "target": TARGET,
                "scope": "Readable API configuration snapshot, not a tested restorable firmware/NVM backup",
                "device_writes": False, "files": [], "read_errors": []}

    def record(name, method, params):
        response = api.rpc(method, params)
        manifest["files"].append(save(directory / name, response))
        if "error" in response:
            manifest["read_errors"].append({"method": method, "code": response["error"].get("code")})
        return response.get("result")

    try:
        methods = record("rpc-methods.json", "system.listMethods", [])
        uids = record("functional-item-uids.json", "FIM/getFunctionalItemUIDs", [None])
        if not isinstance(uids, list):
            raise ValueError("Functional item inventory unavailable")
        items = []
        for offset in range(0, len(uids), 40):
            result = record(f"functional-items-{offset // 40:02d}.json", "FIM/getFunctionalItems", [uids[offset:offset + 40], 0])
            if not isinstance(result, dict):
                raise ValueError("Functional item batch unavailable")
            items.extend(result.get("items", []))
        classes = sorted({c for item in items for c in item.get("objectClass", [])})
        metadatas = []
        for offset in range(0, len(classes), 25):
            result = record(f"item-metadata-{offset // 25:02d}.json", "FIM/getItemsMetadata", [classes[offset:offset + 25], True])
            if isinstance(result, dict):
                metadatas.extend(result.get("metadata", []))
        for method in ["HAM/getRules", "HAM/getAllConditions", "HAM/getAllCommands", "HAM/getApplications",
                       "HAM2/getRules", "HAM2/getAllConditions", "HAM2/getAllCommands",
                       "backup/isAutomaticBackupEnabled", "backup/isBackendStorageEnabled"]:
            if method in methods:
                record(method.replace("/", "-") + ".json", method, [])
        returned = {item_uid(x) for x in items}
        manifest.update({"rpc_method_count": len(methods), "requested_item_count": len(uids), "returned_item_count": len(items),
                         "identified_item_count": len(returned - {None}), "missing_item_count": len(set(uids) - returned),
                         "class_count": len(classes), "metadata_count": len(metadatas),
                         "completed_utc": datetime.now(timezone.utc).isoformat()})
        save(directory / "manifest.json", manifest)
        inventory = [{"class": m.get("objectClass"), "operations": [o.get("name") for o in m.get("operations", [])],
                      "properties": [{"name": p.get("name"), "readable": p.get("readable", False), "writable": p.get("writable", False)}
                                     for p in m.get("properties", [])]} for m in metadatas]
        save(BASE / "management-class-inventory-redacted-2026-11-12.json", inventory)
        print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=2))
        print(json.dumps({"snapshot_directory": str(directory), "saved_files": len(manifest["files"])}, indent=2))
    finally:
        api.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_directory", type=Path)
    arguments = parser.parse_args()
    try:
        snapshot(arguments.snapshot_directory)
    except Exception as exc:
        print(json.dumps({"failure_type": type(exc).__name__, "message": str(exc)[:200]}))
        raise SystemExit(1) from None
