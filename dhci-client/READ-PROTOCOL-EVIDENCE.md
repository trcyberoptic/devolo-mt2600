# DHCI read protocol from devolo NetScanner

Statically extracted on 2026-11-12. No downloaded application was executed and no device was contacted. JPEXS 26.4.0 was used only as a decompiler.

## Archive provenance

- APK archive page: https://apkpure.net/devolo-netscanner/air.de.devolo.netscanner/download/1.1.171
- Exact download entry: https://d.apkpure.net/b/APK/air.de.devolo.netscanner?versionCode=1001171
- Downloaded size: 17,600,183 bytes.
- APK SHA-256: ff5cdde288c9e862a89cd390251a180b46a7e9d30455ff6b0bff7718391af48c
- Embedded signer certificate subject: CN=devolo AG,OU=EN,O=devolo AG,C=DE
- Embedded signer certificate SHA-1: 6cebd4390ba4c2e20d81c160f671f856f72aa95d, matching the archive page. This is archive consistency evidence, not an independent manufacturer signature trust check.
- Original APK member: assets/devoloNetScanner.swf; compressed SWF expanded statically.

## Read request

`GET http://IP:22879/?version=1&target=System&key=status`

Content-Type set by client: `application/x-www-form-urlencoded`.
No `type`, `value`, request body, or credential is added in the examined query controller.

Evidence under `decompiled/scripts/network/dHCI/`:

- `messages/Query/dHCIQueryMessage.as:12`: GET method.
- `messages/Query/SystemStatus.as:9`: exact query string.
- `dHCIBaseMessage.as:15`: content type.
- `dHCIMessageController.as:84-88`: copies method, constructs URL with `?` plus query string, sends.
- `persistence/PLCData.as:454-456`: base URL `http://` + IP + `:` + advertised DHCI port.

This documents an actual client read path, not support or authorization behavior of a specific MT2600 firmware. System status output can include identifying data; suppress private fields. Do not substitute HomePlug/Local: its parser accesses the network membership key NMK.

## Additional verified official artifact

Manufacturer page: https://www.devolo.co.uk/en/software-downloads/cockpit

Direct Linux Cockpit download linked there: https://www.devolo.de/media/0a/fd/c7/1762522595/devolo-cockpit-v5-2-0-185-linux.zip?ts=1762522595

Downloaded size: 37,369,021 bytes. ZIP/run/tar/deb contents extracted statically. Current `devolonetsvc` contains a DHCI setter string, but the exact read evidence above comes from NetScanner.
