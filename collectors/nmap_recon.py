import xml.etree.ElementTree as ET
import json
import logging
import sys

try:
    import nmap
    _NMAP_AVAILABLE = True
except ImportError:
    nmap = None  # type: ignore
    _NMAP_AVAILABLE = False

# Setup logging
logging.basicConfig(
    filename='nmap_recon.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
)

logger = logging.getLogger(__name__)


def run_nmap(target: str, arguments: str = "-sV") -> dict:
    """
    Run an nmap scan against *target* and return a structured result dict.

    Returns a dict with at least a ``returncode`` key (0 on success).
    Returns an error dict when nmap is not installed or the scan fails.
    """
    if not _NMAP_AVAILABLE:
        return {
            "returncode": 1,
            "error": "nmap Python library not installed (pip install python-nmap)",
        }

    try:
        nm = nmap.PortScanner()
        nm.scan(target, arguments=arguments)
        hosts = []
        for host in nm.all_hosts():
            hosts.append({
                "ip": host,
                "state": nm[host].state(),
                "protocols": list(nm[host].all_protocols()),
            })
        return {
            "returncode": 0,
            "target": target,
            "hosts": hosts,
            "result": nm.csv(),
        }
    except Exception as exc:
        logger.error("nmap scan failed for %s: %s", target, exc)
        return {"returncode": 1, "error": str(exc)}


class NmapRecon:
    def __init__(self, target):
        self.target = target
        if _NMAP_AVAILABLE:
            self.nm = nmap.PortScanner()
        else:
            self.nm = None

    def run_scan(self):
        if not _NMAP_AVAILABLE:
            logger.error("nmap not available; install python-nmap")
            return
        try:
            logging.info('Starting scan for %s', self.target)
            self.nm.scan(self.target, arguments='-sV -oX nmap_scan.xml')
            logging.info('Scan completed successfully')
        except Exception as e:
            logging.error('Scan failed for %s: %s', self.target, str(e))
            sys.exit(1)

    def parse_xml_to_json(self):
        try:
            tree = ET.parse('nmap_scan.xml')
            root = tree.getroot()
            data = {
                'targets': [],
                'hosts': []
            }

            for host in root.findall('host'):
                ip = host.find('address').get('addr')
                hostname_el = host.find('hostnames/hostname')
                hostname = hostname_el.get('name') if hostname_el is not None else 'N/A'
                services = []
                for service in host.findall('services/service'):
                    services.append({
                        'name': service.get('name'),
                        'port': service.get('port'),
                        'protocol': service.get('protocol')
                    })

                data['hosts'].append({
                    'ip': ip,
                    'hostname': hostname,
                    'services': services
                })

            with open('nmap_recon.json', 'w') as json_file:
                json.dump(data, json_file, indent=4)
                logging.info('Parsed XML to JSON and saved to nmap_recon.json')
        except Exception as e:
            logging.error('Failed to parse XML: %s', str(e))
            sys.exit(1)


if __name__ == '__main__':
    target = 'target_ip_or_hostname'
    nmap_recon = NmapRecon(target)
    nmap_recon.run_scan()
    nmap_recon.parse_xml_to_json()