"""Create one diagnostic storage ZIP, attempt local retrieval, remove that ZIP only."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from local_api_tools import BASE, HOST, TARGET, LocalAPI, save


def run():
    # export-*/ is git-ignored: it holds private raw data of the own device.
    folder = BASE / "export-archive-retrieval"
    folder.mkdir(exist_ok=False)
    api = LocalAPI()
    filename = None
    summary = {"target": TARGET, "restore_invoked": False, "generated_archive": False,
               "downloaded": False, "cleanup_called": False, "requests": []}

    def fetch(path, download=False):
        with api.session.get(HOST + path, timeout=(5, 15), allow_redirects=False, stream=True) as response:
            record = {"path": path.replace(filename, "<generated_storage.zip>") if filename else path,
                      "status": response.status_code, "content_type": response.headers.get("Content-Type"),
                      "content_length": response.headers.get("Content-Length")}
            summary["requests"].append(record)
            first = response.raw.read(4)
            if response.status_code == 200 and download and first in (b"PK\x03\x04", b"PK\x05\x06"):
                destination = folder / "storage.zip"
                total = len(first)
                with destination.open("xb") as output:
                    output.write(first)
                    while True:
                        chunk = response.raw.read(65536)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > 128 * 1024 * 1024:
                            raise ValueError("Download exceeds bounded size")
                        output.write(chunk)
                summary.update({"downloaded": True, "download_bytes": total,
                                "download_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})

    try:
        # This exact path comes from the original Android client's fallback URL.
        fetch("/root/index.html")
        # Optional ProSyst Web Console endpoints; no login guesses or configuration calls.
        for path in ["/system/console", "/system/console/logs", "/system/console/status"]:
            fetch(path)
        metadata = api.rpc("FIM/getItemsMetadata", [["com.devolo.fi.gw.GatewayManager"], False])
        summary["gateway_manager_metadata_count"] = len(metadata.get("result", {}).get("metadata", []))
        result = api.result("FIM/invokeOperation", ["devolo.DevoloGateway", "generateLogsZip", [3]])
        if not isinstance(result, str) or len(result) > 128 or "/" in result or "\\" in result or not result.endswith("_storage.zip"):
            raise ValueError("Unexpected generated archive identifier")
        filename = result
        summary["generated_archive"] = True
        save(folder / "created-archive.json", {"filename": filename, "created_by_this_probe": True})
        location = api.result("FIM/invokeOperation", ["devolo.DevoloGateway", "getLogsZipLocation", [filename]])
        summary["reported_location"] = location if location == "/tmp/osgi" else "unexpected"
        name = quote(filename, safe="")
        # Inferred, bounded candidates, not claimed to be documented download routes.
        for prefix in ["/tmp/osgi/", "/root/", "/logs/", "/remote/backup/", "/remote/files/", "/remote/filetransfer/", "/dhlp/portal/full/"]:
            try:
                fetch(prefix + name, download=True)
            except Exception as exc:
                summary["requests"].append({"path": prefix + "<generated_storage.zip>", "error_type": type(exc).__name__})
            if summary["downloaded"]:
                break
    except Exception as exc:
        summary["exception_type"] = type(exc).__name__
    finally:
        if filename is not None:
            try:
                cleanup = api.rpc("FIM/invokeOperation", ["devolo.DevoloGateway", "deleteLogsZip", [filename]])
                summary["cleanup_called"] = True
                summary["cleanup_rpc_error"] = cleanup.get("error", {}).get("code")
                after = api.result("FIM/invokeOperation", ["devolo.DevoloGateway", "getLogsZipLocation", [filename]])
                summary["location_after_cleanup"] = after if after is None else "still_returned"
                save(folder / "cleanup-response.json", cleanup)
            except Exception as exc:
                summary["cleanup_error_type"] = type(exc).__name__
        api.close()
        save(BASE / "archive-download-probe-redacted-2026-11-12.json", summary)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run()
