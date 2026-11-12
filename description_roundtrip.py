"""User-authorized description test, with journal and verified restoration."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from uuid import uuid4

from local_api_tools import BASE, LocalAPI, item_uid, save


def run(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        assert hashlib.sha256((folder / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]
    journal = folder / "description-write-journal.json"
    if journal.exists():
        raise ValueError("An audit already exists; inspect before rerunning")
    items = []
    for path in sorted(folder.glob("functional-items-*.json")):
        items.extend(json.loads(path.read_text(encoding="utf-8"))["result"]["items"])
    chosen = next(x for x in items if "com.devolo.fi.widget.DeviceWidget" in x["objectClass"] and x["properties"].get("status") == 1)
    uid = item_uid(chosen)
    api = LocalAPI()
    original = api.result("FIM/getProperty", [uid, "description"])
    assert original == chosen["properties"].get("description")
    assert original is None or isinstance(original, str)
    marker = "Lokaler Verwaltungstest " + uuid4().hex[:10]
    state = {"uid": uid, "property": "description", "original": original, "temporary": marker,
             "write_attempted": False, "changed_value_verified": False, "restore_verified": False}
    report = {"device_name": chosen["properties"].get("itemName"), "property": "description",
              "original_type": type(original).__name__, "baseline_write_accepted": False,
              "temporary_value_verified": False, "restore_verified": False, "fresh_session_restore_verified": False}
    save(journal, state)
    try:
        # Prove the API accepts the original value (including null) before changing it.
        response = api.rpc("FIM/setProperty", [uid, "description", original])
        state["baseline_write_response"] = response
        save(journal, state)
        if "error" in response:
            report["baseline_error_code"] = response["error"].get("code")
            return report
        assert api.result("FIM/getProperty", [uid, "description"]) == original
        report["baseline_write_accepted"] = True
        state["write_attempted"] = True
        save(journal, state)
        state["temporary_write_response"] = api.rpc("FIM/setProperty", [uid, "description", marker])
        observed = api.result("FIM/getProperty", [uid, "description"])
        state["changed_value_verified"] = observed == marker
        report["temporary_value_verified"] = observed == marker
        save(journal, state)
    finally:
        if state["write_attempted"]:
            for attempt in range(3):
                try:
                    if api is None:
                        api = LocalAPI()
                    current = api.result("FIM/getProperty", [uid, "description"])
                    if current == marker:
                        state["restore_response"] = api.rpc("FIM/setProperty", [uid, "description", original])
                    elif current != original:
                        report["concurrent_change_detected"] = True
                        break
                    state["restore_verified"] = api.result("FIM/getProperty", [uid, "description"]) == original
                    if state["restore_verified"]:
                        break
                except Exception as exc:
                    state["restore_retry_error_type"] = type(exc).__name__
                    if api is not None:
                        api.close()
                    api = None
                    if attempt < 2:
                        time.sleep(0.3)
        else:
            state["restore_verified"] = api.result("FIM/getProperty", [uid, "description"]) == original
        report["restore_verified"] = state["restore_verified"]
        save(journal, state)
        if api is not None:
            api.close()
        if report["restore_verified"]:
            fresh = None
            try:
                fresh = LocalAPI()
                report["fresh_session_restore_verified"] = fresh.result("FIM/getProperty", [uid, "description"]) == original
            except Exception as exc:
                report["fresh_session_error_type"] = type(exc).__name__
            finally:
                if fresh is not None:
                    fresh.close()
        save(BASE / "description-write-test-redacted-2026-11-12.json", report)
        print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_directory", type=Path)
    args = parser.parse_args()
    try:
        outcome = run(args.snapshot_directory)
        if not outcome["restore_verified"] or not outcome["fresh_session_restore_verified"]:
            raise SystemExit(2)
        if not outcome["temporary_value_verified"]:
            raise SystemExit(3)
    except Exception as exc:
        print(json.dumps({"failure_type": type(exc).__name__, "inspect_journal": True}))
        raise SystemExit(1) from None
