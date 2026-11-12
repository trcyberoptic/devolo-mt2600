# Static DHCI read-protocol evidence

Analyzed 2026-11-12. No vendor binaries were executed and no device requests were made by this analysis.

## Artifact provenance

- Primary research source: https://github.com/intellisec/devolo/blob/master/dvl_builder/dvl_keys.py
- Analyzed artifact: dLAN 550 WiFi v1.2.0, not MT2600 firmware.
- Original official URL currently returns 404.
- Retrieved vendor firmware mirror: https://fichiers.touslesdrivers.com/57033/firmware-dLAN_550_WiFi-v1-2-0.dvl
- MD5: 7094d3271bf20d2abf3fc9fa3d36118c, exactly matching the primary research source.
- SHA256: b4ffbfd8987880af87ff17466c9fb27725dce888c993be8a83c767a964c1cd3b

Reviewed source parser shows DVL chunks start after an eight-byte magic. Each chunk has a big-endian size, four-byte type, payload, then CRC. The FLSY payload is unencrypted SquashFS. Selected files were extracted with local 7-Zip. The extracted sysmgrd is big-endian MIPS ELF and was disassembled statically using Capstone.

## Read syntax corroboration

SysMgrDHCIManagement::processGetData starts at VA 0x4398ec and is 4120 bytes in sysmgrd. Its disassembly is saved in processGetData.asm.

Recognized GET fields:

- version, string at file offset 0x562b4; must parse as integer 1.
- Optional format, offset 0x58334; accepted json/xml strings at 0x58398/0x583a8.
- target, offset 0x57e54.
- key, offset 0x585c8.

The parser is order-sensitive: version, optional format, target, key. Unknown fields transition to error. The type field belongs to processPutData and is not recognized by the GET parser. Therefore a GET without a body with query string version=1&target=System&key=status matches this parser. Including type=sync in a GET fails. Absence of value from a setter request is not the basis for this finding.

The GET path is separate from executeMultiSet/processPutData. The model file provides explicit access permissions:

- extracted/etc/devolo/model.mdl line 321 declares System.status with access read, flags virtual, incomplete, unexpected and dhciaccess.
- Line 291 declares System.FirmwareVersion with type String, access read, flags virtual, deprecated and dhciaccess.

Status-region binary strings contain product/vendor, IP, hostname, serial number, firmware date, internal version, SVN revision and management dHCI port 22879. A Linux/kernel field was not confirmed. This supports the specific read request; it does not establish identical behavior for every firmware version or arbitrary GET key.

## Bounded follow-up: hardware details and Telnet state

The dLAN550 model contains no DHCI-accessible OS, kernel, CPU, architecture or memory key. Its explicitly read-only System keys with the dhciaccess flag are DeviceType (line 281), FirmwareVersion (line 291) and status (line 321).

System.Telnetd at line 325 is an explicitly read-only integer from zero to one, but it lacks dhciaccess and is absent from the legacy DHCI key list in sysmgrd. Thus this artifact does not establish a supported DHCI getter for its current value. System.Baptization.Telnetd at line 271 has default read/write access and also lacks dhciaccess; it was excluded from candidate queries. No Telnet setting was queried or changed by this analysis.

The legacy DHCI list at sysmgrd file offset 0x58578 includes System.FirmwareVersion. The corresponding supported read request is GET with query version=1&target=System&key=FirmwareVersion, without type or format fields.

Parent-agent live verification on MT2600, reported after this static work:

- GET status returned HTTP 200 and identified Home Control with firmware date 2021-06-29, dvl-version v1.2.14_2021-06-29_0001, java-version version-15.8.1.80.4, osgi-version R1.0_DHC_MS8_B91_1 and zwave-version ZW4.54.0_SDK6.51.10_FEEP3.
- GET FirmwareVersion returned HTTP 200 with result 8.91.1_2021-06-29. This supplies a concise product firmware version; it does not add OS, kernel, CPU or memory information.

These two MT2600 outcomes were supplied by the parent agent, not observed directly by this static-analysis agent. The extracted dLAN550 model remains a separate product artifact.
