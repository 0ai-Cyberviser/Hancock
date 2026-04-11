"""
Fuzz target for XML parsing (collectors/nmap_recon.py via defusedxml).

Feeds arbitrary XML data through defusedxml.ElementTree to exercise the
parsing and element-access paths used by the nmap result parser.
"""
import atheris
import io
import sys

import defusedxml.ElementTree as ET


def TestOneInput(data: bytes) -> None:
    """Fuzz defusedxml parsing with arbitrary byte data."""
    try:
        tree = ET.parse(io.BytesIO(data))
    except Exception:
        # Any parse failure is expected with random input
        return

    root = tree.getroot()

    # Walk the tree the same way nmap_recon.parse_xml_to_json does
    try:
        for host in root.findall("host"):
            addr = host.find("address")
            if addr is not None:
                addr.get("addr")
                addr.get("addrtype")
            hostnames = host.find("hostnames/hostname")
            if hostnames is not None:
                hostnames.get("name")
            # Match actual nmap_recon.py: ports/port -> service child
            for port in host.findall("ports/port"):
                port.get("portid")
                port.get("protocol")
                service_el = port.find("service")
                if service_el is not None:
                    service_el.get("name")
    except (AttributeError, TypeError, ValueError):
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
