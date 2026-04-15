#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
OSINT Geolocation Intelligence Collector
CyberViser | collectors/osint_geolocation.py

Multi-source IP/domain geolocation with threat intelligence enrichment,
infrastructure mapping, clustering, and predictive location analytics.

Environment variables:
    IPINFO_TOKEN    — ipinfo.io API token (optional fallback)
    ABUSEIPDB_KEY   — AbuseIPDB API key for threat enrichment (optional)
    VT_API_KEY      — VirusTotal API key for threat enrichment (optional)
    HANCOCK_ALLOW_INSECURE_GEOIP — set to 1/true/yes to allow plaintext
        ip-api.com fallback requests when HTTPS sources fail
"""
from __future__ import annotations

import logging
import math
import os
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ── Known bulletproof / frequently-abused ASNs ────────────────────────────────
BULLETPROOF_ASNS: set[str] = {
    "AS44477",   # Stark Industries / PE Freehost
    "AS202425",  # IP Volume / Ecatel
    "AS9009",    # M247 Europe
    "AS16276",   # OVH SAS
    "AS20473",   # Choopa / Vultr
    "AS14061",   # DigitalOcean
    "AS63023",   # GTHost
    "AS49505",   # Selectel
    "AS197695",  # Reg.ru Hosting
    "AS59642",   # Tribeka Web Advisors / Frantech Solutions
    "AS53667",   # FranTech Solutions / BuyVM
    "AS24940",   # Hetzner Online
    "AS51167",   # Contabo
    "AS136907",  # Huawei Cloud
    "AS45102",   # Alibaba Cloud
    "AS37963",   # Alibaba (China)
    "AS4134",    # China Telecom
    "AS4837",    # China Unicom
    "AS3462",    # Chunghwa Telecom (TW)
    "AS8076",    # Microsoft (abused hosting)
}

# Country cyber-risk index (higher = higher risk, scale 0-100)
COUNTRY_RISK_INDEX: dict[str, int] = {
    "CN": 80, "RU": 85, "KP": 95, "IR": 85, "NG": 70,
    "UA": 60, "RO": 65, "BR": 55, "IN": 45, "US": 30,
    "DE": 25, "GB": 25, "FR": 25, "NL": 40, "LU": 35,
    "HK": 65, "SG": 30, "VN": 60, "PK": 70, "BD": 65,
}

_DEFAULT_RISK = 40  # baseline for unlisted countries


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class GeoLocationResult:
    """Structured geolocation result for a single IP address."""
    ip: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asn: Optional[str] = None
    timezone: Optional[str] = None
    is_proxy: bool = False
    is_vpn: bool = False
    is_tor: bool = False
    is_datacenter: bool = False
    threat_score: int = 0       # 0-100
    confidence: float = 0.0     # 0.0-1.0
    source: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ThreatInfrastructure:
    """Tracks threat infrastructure across time with geolocation context."""
    indicator: str
    indicator_type: str = "ip"          # ip | domain | url
    geo_results: list[GeoLocationResult] = field(default_factory=list)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    associated_campaigns: list[str] = field(default_factory=list)
    associated_threat_actors: list[str] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


# ── GeoIPLookup ───────────────────────────────────────────────────────────────

class GeoIPLookup:
    """Multi-source IP geolocation with threat intelligence enrichment."""

    # Secure HTTPS sources are used by default. The plaintext ip-api.com free
    # tier remains available only as an explicit opt-in fallback.
    _IPINFO_URL = "https://ipinfo.io/{ip}/json"
    _IPAPICO_URL = "https://ipapi.co/{ip}/json/"
    _IPAPI_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,city,lat,lon,isp,org,as,timezone,proxy,hosting"
    _ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
    _VT_URL = "https://www.virustotal.com/api/v3/ip_addresses/{ip}"

    # Rate limiting: track request timestamps for ip-api.com free tier
    _req_times: list[float] = []
    _RATE_LIMIT = 45   # requests per minute
    _RATE_WINDOW = 60  # seconds

    def _throttle(self) -> None:
        """Enforce rate limiting for free-tier APIs (45 req/min)."""
        now = time.time()
        self._req_times = [t for t in self._req_times if now - t < self._RATE_WINDOW]
        if len(self._req_times) >= self._RATE_LIMIT:
            sleep_time = self._RATE_WINDOW - (now - self._req_times[0]) + 0.1
            logger.warning("[osint-geo] Rate limit reached; sleeping %.1fs", sleep_time)
            time.sleep(max(sleep_time, 0))
        self._req_times.append(time.time())

    def lookup_ip(self, ip: str) -> GeoLocationResult:
        """Look up geolocation for a single IP using multi-source fallback chain.

        Primary: ipinfo.io (HTTPS, IPINFO_TOKEN optional)
        Fallback 1: ipapi.co (HTTPS)
        Fallback 2: ip-api.com (HTTP only, opt-in via env var)
        """
        result = self._lookup_ipinfo(ip)
        if result and result.latitude is not None:
            return result

        result = self._lookup_ipapico(ip)
        if result and result.latitude is not None:
            return result

        if self._allow_insecure_ipapi():
            result = self._lookup_ipapi(ip)
            if result and result.latitude is not None:
                return result
        else:
            logger.debug(
                "[osint-geo] Skipping insecure ip-api.com fallback for %s",
                ip,
            )

        # Return a stub if all sources fail
        logger.warning("[osint-geo] All geolocation sources failed for %s", ip)
        return GeoLocationResult(ip=ip, confidence=0.0, source="none")

    @staticmethod
    def _allow_insecure_ipapi() -> bool:
        """Return True when plaintext ip-api.com fallback is explicitly enabled."""
        value = os.getenv("HANCOCK_ALLOW_INSECURE_GEOIP", "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _lookup_ipapi(self, ip: str) -> Optional[GeoLocationResult]:
        """Query ip-api.com (primary free source)."""
        self._throttle()
        try:
            url = self._IPAPI_URL.format(ip=ip)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                logger.debug("[osint-geo] ip-api.com returned non-success for %s: %s", ip, data.get("message"))
                return None
            asn = data.get("as", "")
            asn_number = asn.split(" ")[0] if asn else None
            return GeoLocationResult(
                ip=ip,
                latitude=data.get("lat"),
                longitude=data.get("lon"),
                city=data.get("city"),
                region=data.get("region"),
                country=data.get("country"),
                country_code=data.get("countryCode"),
                isp=data.get("isp"),
                org=data.get("org"),
                asn=asn_number,
                timezone=data.get("timezone"),
                is_proxy=data.get("proxy", False),
                is_datacenter=data.get("hosting", False),
                confidence=0.85,
                source="ip-api.com",
            )
        except Exception as exc:
            logger.warning("[osint-geo] ip-api.com error for %s: %s", ip, exc)
            return None

    def _lookup_ipinfo(self, ip: str) -> Optional[GeoLocationResult]:
        """Query ipinfo.io (requires IPINFO_TOKEN env var for best results)."""
        token = os.getenv("IPINFO_TOKEN")
        try:
            url = self._IPINFO_URL.format(ip=ip)
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                return None
            loc = data.get("loc", "")
            lat, lon = (None, None)
            if loc and "," in loc:
                try:
                    lat, lon = float(loc.split(",")[0]), float(loc.split(",")[1])
                except ValueError:
                    pass
            return GeoLocationResult(
                ip=ip,
                latitude=lat,
                longitude=lon,
                city=data.get("city"),
                region=data.get("region"),
                country=data.get("country_name") or data.get("country"),
                country_code=data.get("country"),
                isp=data.get("org"),
                org=data.get("org"),
                asn=data.get("org", "").split(" ")[0] if data.get("org") else None,
                timezone=data.get("timezone"),
                confidence=0.80,
                source="ipinfo.io",
            )
        except Exception as exc:
            logger.warning("[osint-geo] ipinfo.io error for %s: %s", ip, exc)
            return None

    def _lookup_ipapico(self, ip: str) -> Optional[GeoLocationResult]:
        """Query ipapi.co (free fallback, no key required)."""
        try:
            url = self._IPAPICO_URL.format(ip=ip)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return None
            return GeoLocationResult(
                ip=ip,
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                city=data.get("city"),
                region=data.get("region"),
                country=data.get("country_name"),
                country_code=data.get("country_code"),
                isp=data.get("org"),
                org=data.get("org"),
                asn=data.get("asn"),
                timezone=data.get("timezone"),
                confidence=0.75,
                source="ipapi.co",
            )
        except Exception as exc:
            logger.warning("[osint-geo] ipapi.co error for %s: %s", ip, exc)
            return None

    def lookup_domain(self, domain: str) -> list[GeoLocationResult]:
        """Resolve a domain to IP(s) and geolocate each."""
        results: list[GeoLocationResult] = []
        try:
            ips = list({info[4][0] for info in socket.getaddrinfo(domain, None)})
        except Exception as exc:
            logger.warning("[osint-geo] DNS resolution failed for %s: %s", domain, exc)
            return results
        for ip in ips:
            geo = self.lookup_ip(ip)
            results.append(geo)
        return results

    def bulk_lookup(self, indicators: list[str]) -> list[GeoLocationResult]:
        """Geolocate a list of IPs/domains with rate limiting."""
        results: list[GeoLocationResult] = []
        for indicator in indicators:
            try:
                # Detect whether indicator is an IP or domain
                socket.inet_aton(indicator)
                results.append(self.lookup_ip(indicator))
            except OSError:
                # Not a plain IPv4 — treat as domain
                results.extend(self.lookup_domain(indicator))
        return results

    def enrich_with_threat_intel(self, result: GeoLocationResult) -> GeoLocationResult:
        """Enrich a GeoLocationResult with threat intelligence from AbuseIPDB and VirusTotal.

        Requires ABUSEIPDB_KEY and/or VT_API_KEY environment variables.
        Gracefully degrades if keys are missing or requests fail.
        """
        abuseipdb_key = os.getenv("ABUSEIPDB_KEY")
        vt_key = os.getenv("VT_API_KEY")

        score_components: list[int] = []

        if abuseipdb_key:
            try:
                resp = requests.get(
                    self._ABUSEIPDB_URL,
                    headers={"Key": abuseipdb_key, "Accept": "application/json"},
                    params={"ipAddress": result.ip, "maxAgeInDays": "90"},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})
                abuse_score = int(data.get("abuseConfidenceScore", 0))
                score_components.append(abuse_score)
                if data.get("isPublic") is False:
                    result.is_vpn = True
                if data.get("usageType", "").lower() in ("tor exit node",):
                    result.is_tor = True
            except Exception as exc:
                logger.warning("[osint-geo] AbuseIPDB enrichment failed for %s: %s", result.ip, exc)
        else:
            logger.debug("[osint-geo] ABUSEIPDB_KEY not set; skipping AbuseIPDB enrichment")

        if vt_key:
            try:
                resp = requests.get(
                    self._VT_URL.format(ip=result.ip),
                    headers={"x-apikey": vt_key},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                malicious = int(stats.get("malicious", 0))
                suspicious = int(stats.get("suspicious", 0))
                total = sum(stats.values()) or 1
                vt_score = int(((malicious + suspicious) / total) * 100)
                score_components.append(vt_score)
            except Exception as exc:
                logger.warning("[osint-geo] VirusTotal enrichment failed for %s: %s", result.ip, exc)
        else:
            logger.debug("[osint-geo] VT_API_KEY not set; skipping VirusTotal enrichment")

        if score_components:
            result.threat_score = min(100, int(sum(score_components) / len(score_components)))

        return result


# ── InfrastructureMapper ──────────────────────────────────────────────────────

class InfrastructureMapper:
    """Maps and clusters geographically distributed threat infrastructure."""

    def __init__(self):
        self._geo = GeoIPLookup()

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return distance in km between two lat/lon points (Haversine formula)."""
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def map_infrastructure(self, indicators: list[str]) -> dict:
        """Geolocate all indicators and group by ASN, country, and ISP."""
        results = self._geo.bulk_lookup(indicators)
        by_asn: dict[str, list[str]] = {}
        by_country: dict[str, list[str]] = {}
        by_isp: dict[str, list[str]] = {}
        for r in results:
            asn = r.asn or "unknown"
            country = r.country_code or "unknown"
            isp = r.isp or "unknown"
            by_asn.setdefault(asn, []).append(r.ip)
            by_country.setdefault(country, []).append(r.ip)
            by_isp.setdefault(isp, []).append(r.ip)
        return {
            "total": len(results),
            "results": [vars(r) for r in results],
            "by_asn": by_asn,
            "by_country": by_country,
            "by_isp": by_isp,
        }

    def find_clusters(self, results: list[GeoLocationResult], radius_km: float = 50.0) -> list[dict]:
        """Group IPs into geographic clusters within radius_km using Haversine distance."""
        valid = [r for r in results if r.latitude is not None and r.longitude is not None]
        assigned: list[Optional[int]] = [None] * len(valid)
        cluster_id = 0
        for i, r in enumerate(valid):
            if assigned[i] is not None:
                continue
            assigned[i] = cluster_id
            for j in range(i + 1, len(valid)):
                if assigned[j] is not None:
                    continue
                dist = self._haversine(r.latitude, r.longitude, valid[j].latitude, valid[j].longitude)
                if dist <= radius_km:
                    assigned[j] = cluster_id
            cluster_id += 1

        clusters: dict[int, list[GeoLocationResult]] = {}
        for idx, cid in enumerate(assigned):
            if cid is not None:
                clusters.setdefault(cid, []).append(valid[idx])

        output = []
        for cid, members in clusters.items():
            lats = [m.latitude for m in members]
            lons = [m.longitude for m in members]
            output.append({
                "cluster_id": cid,
                "count": len(members),
                "centroid_lat": sum(lats) / len(lats),
                "centroid_lon": sum(lons) / len(lons),
                "ips": [m.ip for m in members],
                "countries": list({m.country_code for m in members if m.country_code}),
            })
        return output

    def generate_heatmap_data(self, results: list[GeoLocationResult]) -> list[dict]:
        """Return lat/lon/weight tuples suitable for heatmap visualization."""
        heatmap = []
        for r in results:
            if r.latitude is not None and r.longitude is not None:
                weight = max(1, r.threat_score) / 100.0
                heatmap.append({"lat": r.latitude, "lon": r.longitude, "weight": weight, "ip": r.ip})
        return heatmap

    def timeline_analysis(self, infra: list[ThreatInfrastructure]) -> dict:
        """Temporal analysis — when did infrastructure first/last appear."""
        timeline: list[dict] = []
        for ti in infra:
            entry: dict = {
                "indicator": ti.indicator,
                "indicator_type": ti.indicator_type,
                "first_seen": ti.first_seen,
                "last_seen": ti.last_seen,
                "campaigns": ti.associated_campaigns,
                "threat_actors": ti.associated_threat_actors,
                "active_days": None,
            }
            if ti.first_seen and ti.last_seen:
                try:
                    from datetime import datetime
                    fmt = "%Y-%m-%dT%H:%M:%S"
                    fs = datetime.fromisoformat(ti.first_seen.replace("Z", "+00:00"))
                    ls = datetime.fromisoformat(ti.last_seen.replace("Z", "+00:00"))
                    entry["active_days"] = (ls - fs).days
                except Exception:
                    pass
            timeline.append(entry)

        # Aggregate by campaign
        campaigns: dict[str, list[str]] = {}
        for ti in infra:
            for c in ti.associated_campaigns:
                campaigns.setdefault(c, []).append(ti.indicator)

        return {
            "timeline": sorted(timeline, key=lambda x: x.get("first_seen") or "", reverse=True),
            "total_indicators": len(infra),
            "campaigns": campaigns,
        }


# ── PredictiveLocationAnalyzer ────────────────────────────────────────────────

class PredictiveLocationAnalyzer:
    """Predictive analytics for future threat infrastructure locations."""

    def analyze_patterns(self, historical_data: list[ThreatInfrastructure]) -> dict:
        """Identify geographic patterns from historical ThreatInfrastructure data."""
        country_freq: dict[str, int] = {}
        asn_freq: dict[str, int] = {}
        isp_freq: dict[str, int] = {}
        proxy_count = 0
        vpn_count = 0
        tor_count = 0
        datacenter_count = 0
        total_results = 0

        for ti in historical_data:
            for geo in ti.geo_results:
                total_results += 1
                cc = geo.country_code or "unknown"
                asn = geo.asn or "unknown"
                isp = geo.isp or "unknown"
                country_freq[cc] = country_freq.get(cc, 0) + 1
                asn_freq[asn] = asn_freq.get(asn, 0) + 1
                isp_freq[isp] = isp_freq.get(isp, 0) + 1
                if geo.is_proxy:
                    proxy_count += 1
                if geo.is_vpn:
                    vpn_count += 1
                if geo.is_tor:
                    tor_count += 1
                if geo.is_datacenter:
                    datacenter_count += 1

        def _top(freq: dict, n: int = 5) -> list[dict]:
            return [{"value": k, "count": v} for k, v in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:n]]

        return {
            "total_indicators": len(historical_data),
            "total_geo_results": total_results,
            "top_countries": _top(country_freq),
            "top_asns": _top(asn_freq),
            "top_isps": _top(isp_freq),
            "anonymization_rate": {
                "proxy": (proxy_count / total_results) if total_results else 0,
                "vpn": (vpn_count / total_results) if total_results else 0,
                "tor": (tor_count / total_results) if total_results else 0,
                "datacenter": (datacenter_count / total_results) if total_results else 0,
            },
        }

    def predict_next_locations(
        self,
        historical_data: list[ThreatInfrastructure],
        top_n: int = 5,
    ) -> list[dict]:
        """Predict likely future infrastructure locations based on historical patterns.

        Scoring factors:
          - Historical country/ASN/ISP preferences
          - Known bulletproof hosting providers (ASN list)
          - Country cyber-risk index
          - Proxy/VPN/Tor usage patterns
          - Geographic proximity to previous infrastructure
        """
        patterns = self.analyze_patterns(historical_data)
        top_countries = {e["value"]: e["count"] for e in patterns["top_countries"]}
        top_asns = {e["value"]: e["count"] for e in patterns["top_asns"]}

        # Build candidate set from top countries and known bulletproof ASNs
        candidates: dict[str, float] = {}
        total_geos = max(patterns["total_geo_results"], 1)

        for cc, cnt in top_countries.items():
            base_score = (cnt / total_geos) * 50  # up to 50 pts from frequency
            risk = COUNTRY_RISK_INDEX.get(cc, _DEFAULT_RISK)
            risk_bonus = risk * 0.3  # up to ~28.5 pts from country risk
            candidates[cc] = base_score + risk_bonus

        # Boost candidates that match bulletproof ASNs
        for asn, cnt in top_asns.items():
            if asn in BULLETPROOF_ASNS:
                # Find countries associated with this ASN from historical data
                for ti in historical_data:
                    for geo in ti.geo_results:
                        if geo.asn == asn and geo.country_code:
                            candidates[geo.country_code] = candidates.get(geo.country_code, 0) + 10

        # Sort and return top_n
        ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_n]
        predictions = []
        for rank, (cc, score) in enumerate(ranked, start=1):
            predictions.append({
                "rank": rank,
                "country_code": cc,
                "predicted_score": round(min(100.0, score), 2),
                "confidence": round(min(1.0, score / 100), 2),
                "is_bulletproof_asn_associated": any(
                    geo.country_code == cc and geo.asn in BULLETPROOF_ASNS
                    for ti in historical_data
                    for geo in ti.geo_results
                ),
            })
        return predictions

    def calculate_risk_score(self, geo: GeoLocationResult) -> float:
        """Calculate a 0-100 risk score for a single GeoLocationResult.

        Factors:
          - Known bulletproof hosting ASN (+30)
          - Country cyber-risk index (scaled to 0-25)
          - Proxy flag (+10)
          - VPN flag (+10)
          - Tor exit node (+20)
          - Datacenter hosting (+5)
          - Pre-existing threat_score (weight 30%)
        """
        score = 0.0

        # ASN risk
        if geo.asn and geo.asn in BULLETPROOF_ASNS:
            score += 30

        # Country risk
        cc = geo.country_code or ""
        country_risk = COUNTRY_RISK_INDEX.get(cc, _DEFAULT_RISK)
        score += country_risk * 0.25  # scale to 0-25

        # Anonymization flags
        if geo.is_proxy:
            score += 10
        if geo.is_vpn:
            score += 10
        if geo.is_tor:
            score += 20
        if geo.is_datacenter:
            score += 5

        # Blend in existing threat_score (from enrichment)
        score += geo.threat_score * 0.3

        return round(min(100.0, score), 2)

    def generate_forecast_report(self, historical_data: list[ThreatInfrastructure]) -> dict:
        """Generate a comprehensive forecast report with predictions and recommendations."""
        patterns = self.analyze_patterns(historical_data)
        predictions = self.predict_next_locations(historical_data)

        # Risk scores for all geo results in historical data
        all_geo: list[GeoLocationResult] = [geo for ti in historical_data for geo in ti.geo_results]
        risk_scores = [self.calculate_risk_score(g) for g in all_geo]
        avg_risk = (sum(risk_scores) / len(risk_scores)) if risk_scores else 0.0

        monitoring_actions = []
        if predictions:
            top_cc = predictions[0]["country_code"]
            monitoring_actions.append(f"Prioritise monitoring of IP ranges in {top_cc}")
        for e in patterns.get("top_asns", []):
            if e["value"] in BULLETPROOF_ASNS:
                monitoring_actions.append(f"Block/alert on ASN {e['value']} (known bulletproof host)")

        if patterns["anonymization_rate"].get("tor", 0) > 0.2:
            monitoring_actions.append("Deploy Tor exit node blocking / alerting rules")
        if patterns["anonymization_rate"].get("vpn", 0) > 0.3:
            monitoring_actions.append("Review VPN provider blocklists and apply geofencing")

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_historical_indicators": len(historical_data),
                "average_risk_score": round(avg_risk, 2),
                "high_risk_count": sum(1 for s in risk_scores if s >= 70),
            },
            "patterns": patterns,
            "predicted_locations": predictions,
            "recommended_monitoring": monitoring_actions,
        }


# ── Module-level convenience functions ───────────────────────────────────────

_default_geo = GeoIPLookup()
_default_mapper = InfrastructureMapper()
_default_analyzer = PredictiveLocationAnalyzer()


def lookup_ip(ip: str) -> GeoLocationResult:
    """Look up geolocation for a single IP address."""
    return _default_geo.lookup_ip(ip)


def lookup_domain(domain: str) -> list[GeoLocationResult]:
    """Resolve a domain and geolocate all resulting IPs."""
    return _default_geo.lookup_domain(domain)


def predict_locations(historical_data: list) -> list[dict]:
    """Predict future threat infrastructure locations from historical data."""
    return _default_analyzer.predict_next_locations(historical_data)


def map_threat_infrastructure(indicators: list[str]) -> dict:
    """Map and cluster threat infrastructure for a list of IP/domain indicators."""
    return _default_mapper.map_infrastructure(indicators)
