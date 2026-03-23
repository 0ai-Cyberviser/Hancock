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

logger = logging.getLogger(__name__)

# Setup logging
logging.basicConfig(
    filename='nmap_recon.log', level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
)

class NmapRecon:
    def __init__(self, target):
        self.target = target
        self.nm = nmap.PortScanner()

    def run_scan(self):
        try:
            logging.info(f'Starting scan for {self.target}')
            self.nm.scan(self.target, arguments='-sV -oX nmap_scan.xml')
            logging.info('Scan completed successfully')
        except Exception as e:
            logging.error(f'Scan failed for {self.target}: {str(e)}')
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
                hostname = host.find('hostnames/hostname').get('name') if host.find('hostnames/hostname') is not None else 'N/A'
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
            logging.error(f'Failed to parse XML: {str(e)}')
            sys.exit(1)

if __name__ == '__main__':
    target = 'target_ip_or_hostname'
    nmap_recon = NmapRecon(target)
    nmap_recon.run_scan()
    nmap_recon.parse_xml_to_json()


def run_nmap(target: str, arguments: str = "-sV") -> dict:
    """Convenience wrapper: run an Nmap scan and return a result dict.

    Returns a dict with ``returncode`` 0 on success, or an ``error`` key when
    nmap is unavailable or the scan fails.
    """
    if not _NMAP_AVAILABLE:
        logger.warning("nmap Python library not installed; skipping scan of %s", target)
        return {"returncode": 1, "error": "nmap not installed", "target": target}
    try:
        scanner = nmap.PortScanner()
        scanner.scan(target, arguments=arguments)
        hosts = []
        for host in scanner.all_hosts():
            hosts.append({
                "host": host,
                "state": scanner[host].state(),
                "protocols": list(scanner[host].all_protocols()),
            })
        return {"returncode": 0, "result": hosts, "target": target}
    except Exception as exc:
        logger.error("Nmap scan failed for %s: %s", target, exc)
        return {"returncode": 1, "error": str(exc), "target": target}
