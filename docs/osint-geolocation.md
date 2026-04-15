# OSINT Geolocation Intelligence Module

**CyberViser | Hancock**

## Overview

The `collectors/osint_geolocation.py` module provides multi-source IP/domain geolocation, threat infrastructure mapping, geographic clustering, and predictive location analytics for threat actor infrastructure.

### Architecture

```
osint_geolocation.py
├── GeoLocationResult       — Structured result dataclass for a single IP
├── ThreatInfrastructure    — Tracks threat infra across time with geo context
├── GeoIPLookup             — Multi-source IP/domain geolocation
│   ├── lookup_ip()         — Primary lookup with fallback chain
│   ├── lookup_domain()     — DNS resolve → geo lookup
│   ├── bulk_lookup()       — Batch processing with rate limiting
│   └── enrich_with_threat_intel() — AbuseIPDB + VirusTotal enrichment
├── InfrastructureMapper    — Geographic clustering and analysis
│   ├── map_infrastructure() — Group indicators by ASN/country/ISP
│   ├── find_clusters()     — Haversine-based geographic clustering
│   ├── generate_heatmap_data() — lat/lon/weight for visualization
│   └── timeline_analysis() — Temporal infrastructure analysis
├── PredictiveLocationAnalyzer — Predictive analytics
│   ├── analyze_patterns()  — Identify geographic/ASN patterns
│   ├── predict_next_locations() — Forecast future infrastructure locations
│   ├── calculate_risk_score()   — Score 0-100 for a single geo result
│   └── generate_forecast_report() — Full report with recommendations
└── Convenience functions   — lookup_ip, lookup_domain, predict_locations,
                              map_threat_infrastructure
```

### Data Sources

| Source | API Key Required | Rate Limit | Notes |
|---|---|---|---|
| ipinfo.io | Optional (`IPINFO_TOKEN`) | 50k req/month free | Primary HTTPS source |
| ipapi.co | No | 1000 req/day | Secondary HTTPS fallback |
| ip-api.com | No | 45 req/min | Plaintext fallback, disabled by default |
| AbuseIPDB | Yes (`ABUSEIPDB_KEY`) | 1000 req/day free | Threat enrichment |
| VirusTotal | Yes (`VT_API_KEY`) | 500 req/day free | Threat enrichment |

---

## Installation and Configuration

### Dependencies

Install Python requirements (includes `maxminddb` for optional local database support):

```bash
pip install -r requirements.txt
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `IPINFO_TOKEN` | No | ipinfo.io API token for improved accuracy and higher rate limits |
| `HANCOCK_ALLOW_INSECURE_GEOIP` | No | Enable plaintext `ip-api.com` fallback (`1`, `true`, `yes`) |
| `ABUSEIPDB_KEY` | No | AbuseIPDB API key for threat intelligence enrichment |
| `VT_API_KEY` | No | VirusTotal API key for malware/threat enrichment |

Set environment variables via `.env` file or shell export:

```bash
export IPINFO_TOKEN="your_ipinfo_token"
export HANCOCK_ALLOW_INSECURE_GEOIP="false"
export ABUSEIPDB_KEY="your_abuseipdb_key"
export VT_API_KEY="your_virustotal_api_key"
```

The module **gracefully degrades** when API keys are missing — geolocation still works via free sources, and threat enrichment is simply skipped with a warning log.

---

## API Endpoints

### POST /v1/geolocate

Geolocate one or more IP addresses or domains.

**Request:**
```json
{
  "indicators": ["1.2.3.4", "example.com"]
}
```

**Response:**
```json
{
  "indicators": ["1.2.3.4", "example.com"],
  "results": [
    {
      "ip": "1.2.3.4",
      "latitude": 51.5074,
      "longitude": -0.1278,
      "city": "London",
      "region": "England",
      "country": "United Kingdom",
      "country_code": "GB",
      "isp": "Example ISP",
      "org": "Example Org",
      "asn": "AS12345",
      "timezone": "Europe/London",
      "is_proxy": false,
      "is_vpn": false,
      "is_tor": false,
      "is_datacenter": false,
      "threat_score": 0,
      "confidence": 0.85,
      "source": "ip-api.com",
      "timestamp": "2025-06-01T12:00:00+00:00"
    }
  ],
  "count": 1
}
```

**Error responses:**
- `400 Bad Request` — `indicators` field missing or empty
- `500 Internal Server Error` — Unexpected error during geolocation

---

### POST /v1/predict-locations

Predict future threat infrastructure locations based on historical data.

**Request:**
```json
{
  "historical_data": [
    {
      "indicator": "1.2.3.4",
      "indicator_type": "ip",
      "geo_results": [
        {
          "ip": "1.2.3.4",
          "country_code": "RU",
          "asn": "AS44477",
          "latitude": 55.75,
          "longitude": 37.62,
          "threat_score": 85,
          "confidence": 0.85,
          "source": "ip-api.com"
        }
      ],
      "first_seen": "2025-01-01T00:00:00Z",
      "last_seen": "2025-03-01T00:00:00Z",
      "associated_campaigns": ["apt-campaign-x"],
      "associated_threat_actors": ["Threat Group Y"],
      "mitre_techniques": ["T1583.003", "T1090.003"],
      "tags": ["bulletproof", "c2"]
    }
  ]
}
```

**Response:**
```json
{
  "predictions": [
    {
      "rank": 1,
      "country_code": "RU",
      "predicted_score": 96.25,
      "confidence": 0.96,
      "is_bulletproof_asn_associated": true
    },
    {
      "rank": 2,
      "country_code": "CN",
      "predicted_score": 80.0,
      "confidence": 0.80,
      "is_bulletproof_asn_associated": false
    }
  ],
  "count": 2
}
```

**Error responses:**
- `400 Bad Request` — `historical_data` field missing or empty

---

### POST /v1/map-infrastructure

Map and cluster threat infrastructure indicators geographically.

**Request:**
```json
{
  "indicators": ["1.2.3.4", "5.6.7.8", "malicious.example.com"]
}
```

**Response:**
```json
{
  "total": 3,
  "results": [...],
  "by_asn": {
    "AS44477": ["1.2.3.4"],
    "AS9009": ["5.6.7.8"]
  },
  "by_country": {
    "RU": ["1.2.3.4"],
    "NL": ["5.6.7.8"],
    "DE": ["9.9.9.9"]
  },
  "by_isp": {
    "M247 Europe SRL": ["5.6.7.8"]
  }
}
```

**Error responses:**
- `400 Bad Request` — `indicators` field missing or empty

---

## Class and Function Reference

### `GeoLocationResult`

Structured result for a single IP address geolocation.

| Field | Type | Description |
|---|---|---|
| `ip` | `str` | Target IP address |
| `latitude` | `float \| None` | Latitude |
| `longitude` | `float \| None` | Longitude |
| `city` | `str \| None` | City name |
| `region` | `str \| None` | Region/state |
| `country` | `str \| None` | Full country name |
| `country_code` | `str \| None` | ISO 3166-1 alpha-2 code |
| `isp` | `str \| None` | Internet Service Provider |
| `org` | `str \| None` | Organisation |
| `asn` | `str \| None` | Autonomous System Number (e.g. `AS12345`) |
| `timezone` | `str \| None` | IANA timezone name |
| `is_proxy` | `bool` | Known proxy IP |
| `is_vpn` | `bool` | Known VPN exit |
| `is_tor` | `bool` | Tor exit node |
| `is_datacenter` | `bool` | Hosted in datacenter |
| `threat_score` | `int` | 0–100 threat score (from enrichment) |
| `confidence` | `float` | 0.0–1.0 confidence in result accuracy |
| `source` | `str \| None` | API source that provided the data |
| `timestamp` | `str \| None` | ISO 8601 timestamp of lookup |

### `ThreatInfrastructure`

Tracks a single threat indicator across time.

| Field | Type | Description |
|---|---|---|
| `indicator` | `str` | IP address, domain, or URL |
| `indicator_type` | `str` | `ip`, `domain`, or `url` |
| `geo_results` | `list[GeoLocationResult]` | Associated geolocation results |
| `first_seen` | `str \| None` | ISO 8601 first-seen timestamp |
| `last_seen` | `str \| None` | ISO 8601 last-seen timestamp |
| `associated_campaigns` | `list[str]` | Campaign names |
| `associated_threat_actors` | `list[str]` | Threat actor names |
| `mitre_techniques` | `list[str]` | MITRE ATT&CK technique IDs |
| `tags` | `list[str]` | Free-form tags |

### `GeoIPLookup`

Multi-source IP geolocation engine.

```python
geo = GeoIPLookup()
result = geo.lookup_ip("8.8.8.8")
results = geo.lookup_domain("evil.example.com")
all_results = geo.bulk_lookup(["1.2.3.4", "evil.example.com"])
enriched = geo.enrich_with_threat_intel(result)
```

### `InfrastructureMapper`

Geographic clustering and infrastructure analysis.

```python
mapper = InfrastructureMapper()
mapping = mapper.map_infrastructure(["1.2.3.4", "5.6.7.8"])
clusters = mapper.find_clusters(geo_results, radius_km=50.0)
heatmap = mapper.generate_heatmap_data(geo_results)
timeline = mapper.timeline_analysis(threat_infra_list)
```

### `PredictiveLocationAnalyzer`

Predictive analytics for future threat infrastructure.

```python
analyzer = PredictiveLocationAnalyzer()
patterns = analyzer.analyze_patterns(historical_data)
predictions = analyzer.predict_next_locations(historical_data, top_n=5)
risk = analyzer.calculate_risk_score(geo_result)
report = analyzer.generate_forecast_report(historical_data)
```

---

## Usage Examples

### CLI — Quick IP Lookup

```python
from collectors.osint_geolocation import lookup_ip

result = lookup_ip("1.2.3.4")
print(f"City: {result.city}, Country: {result.country_code}, ASN: {result.asn}")
```

### CLI — Domain Geolocation

```python
from collectors.osint_geolocation import lookup_domain

results = lookup_domain("malicious-c2.example.com")
for r in results:
    print(f"{r.ip} → {r.city}, {r.country_code} (ASN: {r.asn})")
```

### CLI — Infrastructure Mapping

```python
from collectors.osint_geolocation import map_threat_infrastructure

indicators = ["1.2.3.4", "5.6.7.8", "malicious.example.com"]
mapping = map_threat_infrastructure(indicators)
print(f"Countries: {list(mapping['by_country'].keys())}")
print(f"ASNs: {list(mapping['by_asn'].keys())}")
```

### CLI — Predictive Analysis

```python
from collectors.osint_geolocation import (
    GeoLocationResult, ThreatInfrastructure, predict_locations
)

# Build historical data from your threat intel database
historical = [
    ThreatInfrastructure(
        indicator="1.2.3.4",
        indicator_type="ip",
        geo_results=[
            GeoLocationResult(
                ip="1.2.3.4",
                country_code="RU",
                asn="AS44477",
                latitude=55.75,
                longitude=37.62,
                confidence=0.85,
                source="ip-api.com",
            )
        ],
        first_seen="2025-01-01T00:00:00Z",
        last_seen="2025-03-01T00:00:00Z",
        associated_campaigns=["campaign-alpha"],
    )
]

predictions = predict_locations(historical)
for p in predictions:
    print(f"Rank {p['rank']}: {p['country_code']} (score={p['predicted_score']})")
```

### Pipeline Integration

The pipeline function `run_osint_geolocation()` is integrated into `run_full_assessment()`:

```python
from hancock_pipeline import run_osint_geolocation

result = run_osint_geolocation("1.2.3.4")
print(result["geo_results"])
print(result["infrastructure_map"])
```

---

## Rate Limiting Considerations

- **ip-api.com** (free tier): 45 requests per minute. The `GeoIPLookup` class automatically throttles requests and will sleep when the limit is approached.
- **ipinfo.io** (free tier): 50,000 requests per month. Use `IPINFO_TOKEN` to authenticate.
- **ipapi.co** (free tier): 1,000 requests per day. Used as final fallback only.
- **AbuseIPDB** (free tier): 1,000 requests per day. Used only for threat enrichment.
- **VirusTotal** (free tier): 500 requests per day. Used only for threat enrichment.

For high-volume assessments, consider:
1. Caching geolocation results locally (e.g., using `maxminddb` with a downloaded GeoLite2 database)
2. Using paid API tiers
3. Implementing a local Redis/SQLite cache layer around `GeoIPLookup`

---

## Known Bulletproof Hosting ASNs

The module maintains a list of commonly-abused Autonomous Systems used in risk scoring:

| ASN | Provider | Notes |
|---|---|---|
| AS44477 | Stark Industries / PE Freehost | Frequently abused by APT actors |
| AS202425 | IP Volume / Ecatel | Bulletproof hosting |
| AS9009 | M247 Europe | Abused VPS provider |
| AS16276 | OVH SAS | Large provider, frequently abused |
| AS20473 | Choopa / Vultr | Abused VPS provider |
| AS53667 | FranTech / BuyVM | Bulletproof provider |
| AS59642 | Frantech Solutions | Bulletproof provider |
| AS4134 | China Telecom | APT infrastructure |
| AS4837 | China Unicom | APT infrastructure |

The full list is available in `BULLETPROOF_ASNS` in the module.
