try:
    import nmap
except ImportError:
    nmap = None  # type: ignore
import xml.etree.ElementTree as ET
import json
import logging
import sys

# Setup logging
logging.basicConfig(filename='nmap_recon.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

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


def run_nmap(target: str) -> dict:
    """Convenience wrapper: run an nmap scan and return results as a dict.

    Returns a dict with key 'result' on success, or 'error' if nmap is not
    installed or the scan fails.
    """
    if nmap is None:
        return {"returncode": 1, "error": "python-nmap not installed — run: pip install python-nmap"}
    try:
        recon = NmapRecon(target)
        recon.run_scan()
        recon.parse_xml_to_json()
        return {"returncode": 0, "result": "scan complete", "target": target}
    except Exception as exc:
        return {"returncode": 1, "error": str(exc)}