"""
Tests for collectors/osint_geolocation.py
All external API calls are mocked using unittest.mock.patch.

Run: pytest tests/test_osint_geolocation.py -v
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.osint_geolocation import (
    BULLETPROOF_ASNS,
    GeoIPLookup,
    GeoLocationResult,
    InfrastructureMapper,
    PredictiveLocationAnalyzer,
    ThreatInfrastructure,
    lookup_domain,
    lookup_ip,
    map_threat_infrastructure,
    predict_locations,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_geo(
    ip="1.2.3.4",
    lat=51.5,
    lon=-0.1,
    city="London",
    region="England",
    country="United Kingdom",
    country_code="GB",
    isp="Test ISP",
    org="Test Org",
    asn="AS12345",
    timezone="Europe/London",
    is_proxy=False,
    is_vpn=False,
    is_tor=False,
    is_datacenter=False,
    threat_score=0,
    confidence=0.85,
    source="ip-api.com",
) -> GeoLocationResult:
    return GeoLocationResult(
        ip=ip,
        latitude=lat,
        longitude=lon,
        city=city,
        region=region,
        country=country,
        country_code=country_code,
        isp=isp,
        org=org,
        asn=asn,
        timezone=timezone,
        is_proxy=is_proxy,
        is_vpn=is_vpn,
        is_tor=is_tor,
        is_datacenter=is_datacenter,
        threat_score=threat_score,
        confidence=confidence,
        source=source,
    )


def _make_ipapi_response(ip="1.2.3.4"):
    """Return a mock ip-api.com successful response body."""
    return {
        "status": "success",
        "country": "United Kingdom",
        "countryCode": "GB",
        "region": "England",
        "city": "London",
        "lat": 51.5,
        "lon": -0.1,
        "isp": "Test ISP",
        "org": "Test Org",
        "as": "AS12345 Test AS",
        "timezone": "Europe/London",
        "proxy": False,
        "hosting": False,
    }


def _make_ipinfo_response(ip="1.2.3.4"):
    """Return a mock ipinfo.io successful response body."""
    return {
        "ip": ip,
        "city": "New York",
        "region": "New York",
        "country": "US",
        "loc": "40.7128,-74.0060",
        "org": "AS15169 Google",
        "timezone": "America/New_York",
    }


def _make_ipapico_response(ip="1.2.3.4"):
    """Return a mock ipapi.co successful response body."""
    return {
        "ip": ip,
        "city": "Amsterdam",
        "region": "North Holland",
        "country_name": "Netherlands",
        "country_code": "NL",
        "latitude": 52.3676,
        "longitude": 4.9041,
        "org": "AS9009 M247 Europe",
        "asn": "AS9009",
        "timezone": "Europe/Amsterdam",
    }


# ── GeoLocationResult dataclass ───────────────────────────────────────────────

class TestGeoLocationResult:
    def test_defaults(self):
        r = GeoLocationResult(ip="10.0.0.1")
        assert r.ip == "10.0.0.1"
        assert r.latitude is None
        assert r.threat_score == 0
        assert r.confidence == 0.0
        assert r.is_proxy is False
        assert r.is_tor is False
        assert r.timestamp is not None  # auto-populated

    def test_timestamp_auto_set(self):
        r = GeoLocationResult(ip="1.1.1.1")
        # Should be a valid ISO 8601 string
        datetime.fromisoformat(r.timestamp)

    def test_explicit_timestamp_preserved(self):
        ts = "2025-01-01T00:00:00+00:00"
        r = GeoLocationResult(ip="1.1.1.1", timestamp=ts)
        assert r.timestamp == ts


# ── ThreatInfrastructure dataclass ───────────────────────────────────────────

class TestThreatInfrastructure:
    def test_defaults(self):
        ti = ThreatInfrastructure(indicator="1.2.3.4")
        assert ti.indicator == "1.2.3.4"
        assert ti.indicator_type == "ip"
        assert ti.geo_results == []
        assert ti.associated_campaigns == []
        assert ti.tags == []

    def test_with_geo_results(self):
        geo = _make_geo()
        ti = ThreatInfrastructure(indicator="1.2.3.4", geo_results=[geo])
        assert len(ti.geo_results) == 1
        assert ti.geo_results[0].ip == "1.2.3.4"


# ── GeoIPLookup.lookup_ip ─────────────────────────────────────────────────────

class TestGeoIPLookupLookupIp:
    @patch("collectors.osint_geolocation.requests.get")
    def test_lookup_ip_success_from_ipinfo(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        result = geo.lookup_ip("1.2.3.4")

        assert result.ip == "1.2.3.4"
        assert result.city == "New York"
        assert result.country_code == "US"
        assert result.latitude == 40.7128
        assert result.longitude == -74.0060
        assert result.source == "ipinfo.io"
        assert result.confidence == 0.80

    @patch("collectors.osint_geolocation.requests.get")
    def test_lookup_ip_fallback_to_ipapico_when_ipinfo_fails(self, mock_get):
        ipinfo_resp = MagicMock()
        ipinfo_resp.json.return_value = {"error": True, "reason": "no data"}
        ipinfo_resp.raise_for_status = MagicMock()

        ipapico_resp = MagicMock()
        ipapico_resp.json.return_value = _make_ipapico_response()
        ipapico_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [ipinfo_resp, ipapico_resp]

        geo = GeoIPLookup()
        result = geo.lookup_ip("1.2.3.4")

        assert result.city == "Amsterdam"
        assert result.source == "ipapi.co"

    @patch("collectors.osint_geolocation.requests.get")
    def test_lookup_ip_all_sources_fail_returns_stub(self, mock_get):
        mock_get.side_effect = Exception("network error")

        geo = GeoIPLookup()
        result = geo.lookup_ip("1.2.3.4")

        assert result.ip == "1.2.3.4"
        assert result.latitude is None
        assert result.source == "none"
        assert result.confidence == 0.0

    @patch.dict(os.environ, {"HANCOCK_ALLOW_INSECURE_GEOIP": "true"})
    @patch("collectors.osint_geolocation.requests.get")
    def test_lookup_ip_uses_insecure_ipapi_only_when_opted_in(self, mock_get):
        ipinfo_resp = MagicMock()
        ipinfo_resp.json.return_value = {"error": True, "reason": "no data"}
        ipinfo_resp.raise_for_status = MagicMock()

        ipapico_resp = MagicMock()
        ipapico_resp.json.return_value = {"error": True}
        ipapico_resp.raise_for_status = MagicMock()

        ipapi_resp = MagicMock()
        ipapi_resp.json.return_value = _make_ipapi_response()
        ipapi_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [ipinfo_resp, ipapico_resp, ipapi_resp]

        geo = GeoIPLookup()
        result = geo.lookup_ip("1.2.3.4")

        assert result.source == "ip-api.com"
        assert result.country_code == "GB"

    @patch("collectors.osint_geolocation.requests.get")
    def test_lookup_ip_asn_parsed_from_org_field(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        result = geo.lookup_ip("1.2.3.4")
        assert result.asn == "AS15169"

    @patch("collectors.osint_geolocation.requests.get")
    def test_lookup_ip_proxy_flag_preserved(self, mock_get):
        resp_data = _make_ipapi_response()
        resp_data["proxy"] = True
        mock_resp = MagicMock()
        mock_resp.json.return_value = resp_data
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        result = geo._lookup_ipapi("1.2.3.4")
        assert result.is_proxy is True


# ── GeoIPLookup.lookup_domain ─────────────────────────────────────────────────

class TestGeoIPLookupLookupDomain:
    @patch("collectors.osint_geolocation.requests.get")
    @patch("collectors.osint_geolocation.socket.getaddrinfo")
    def test_lookup_domain_resolves_and_geolocates(self, mock_dns, mock_get):
        mock_dns.return_value = [
            (None, None, None, None, ("1.2.3.4", 0)),
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        results = geo.lookup_domain("example.com")

        assert len(results) == 1
        assert results[0].ip == "1.2.3.4"

    @patch("collectors.osint_geolocation.socket.getaddrinfo")
    def test_lookup_domain_dns_failure_returns_empty(self, mock_dns):
        mock_dns.side_effect = OSError("DNS resolution failed")

        geo = GeoIPLookup()
        results = geo.lookup_domain("nonexistent.invalid")
        assert results == []

    @patch("collectors.osint_geolocation.requests.get")
    @patch("collectors.osint_geolocation.socket.getaddrinfo")
    def test_lookup_domain_deduplicates_ips(self, mock_dns, mock_get):
        # Two entries resolving to the same IP
        mock_dns.return_value = [
            (None, None, None, None, ("1.2.3.4", 0)),
            (None, None, None, None, ("1.2.3.4", 0)),
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        results = geo.lookup_domain("example.com")
        assert len(results) == 1


# ── GeoIPLookup.bulk_lookup ───────────────────────────────────────────────────

class TestGeoIPLookupBulkLookup:
    @patch("collectors.osint_geolocation.requests.get")
    def test_bulk_lookup_ips(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        results = geo.bulk_lookup(["1.2.3.4", "5.6.7.8"])
        assert len(results) == 2

    @patch("collectors.osint_geolocation.requests.get")
    @patch("collectors.osint_geolocation.socket.getaddrinfo")
    def test_bulk_lookup_mixed_ip_and_domain(self, mock_dns, mock_get):
        mock_dns.return_value = [(None, None, None, None, ("9.9.9.9", 0))]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        results = geo.bulk_lookup(["1.2.3.4", "example.com"])
        assert len(results) == 2

    @patch("collectors.osint_geolocation.requests.get")
    def test_bulk_lookup_empty_list(self, mock_get):
        geo = GeoIPLookup()
        results = geo.bulk_lookup([])
        assert results == []
        mock_get.assert_not_called()


# ── GeoIPLookup.enrich_with_threat_intel ─────────────────────────────────────

class TestGeoIPLookupEnrichWithThreatIntel:
    @patch.dict(os.environ, {"ABUSEIPDB_KEY": "test-key", "VT_API_KEY": "vt-key"})
    @patch("collectors.osint_geolocation.requests.get")
    def test_enrichment_updates_threat_score(self, mock_get):
        abuse_resp = MagicMock()
        abuse_resp.raise_for_status = MagicMock()
        abuse_resp.json.return_value = {"data": {"abuseConfidenceScore": 80, "isPublic": True}}

        vt_resp = MagicMock()
        vt_resp.raise_for_status = MagicMock()
        vt_resp.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 10,
                        "suspicious": 2,
                        "harmless": 50,
                        "undetected": 10,
                    }
                }
            }
        }
        mock_get.side_effect = [abuse_resp, vt_resp]

        geo = GeoIPLookup()
        result = _make_geo(threat_score=0)
        enriched = geo.enrich_with_threat_intel(result)
        assert enriched.threat_score > 0
        assert enriched.threat_score <= 100

    @patch.dict(os.environ, {}, clear=True)
    def test_enrichment_no_api_keys_graceful(self):
        """Should not raise when API keys are missing — just returns result unchanged."""
        # Ensure relevant keys are absent
        os.environ.pop("ABUSEIPDB_KEY", None)
        os.environ.pop("VT_API_KEY", None)
        geo = GeoIPLookup()
        result = _make_geo(threat_score=10)
        enriched = geo.enrich_with_threat_intel(result)
        # No keys → threat_score unchanged
        assert enriched.threat_score == 10

    @patch.dict(os.environ, {"ABUSEIPDB_KEY": "test-key"})
    @patch("collectors.osint_geolocation.requests.get")
    def test_enrichment_api_error_is_handled_gracefully(self, mock_get):
        mock_get.side_effect = Exception("connection error")
        geo = GeoIPLookup()
        result = _make_geo()
        # Should not raise
        enriched = geo.enrich_with_threat_intel(result)
        assert enriched is not None

    @patch.dict(os.environ, {"ABUSEIPDB_KEY": "test-key"})
    @patch("collectors.osint_geolocation.requests.get")
    def test_enrichment_tor_flag_set(self, mock_get):
        abuse_resp = MagicMock()
        abuse_resp.raise_for_status = MagicMock()
        abuse_resp.json.return_value = {
            "data": {
                "abuseConfidenceScore": 90,
                "isPublic": True,
                "usageType": "Tor Exit Node",
            }
        }
        mock_get.return_value = abuse_resp

        geo = GeoIPLookup()
        result = _make_geo()
        enriched = geo.enrich_with_threat_intel(result)
        assert enriched.is_tor is True


# ── InfrastructureMapper ──────────────────────────────────────────────────────

class TestInfrastructureMapper:
    @patch("collectors.osint_geolocation.requests.get")
    def test_map_infrastructure_groups_by_country(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mapper = InfrastructureMapper()
        result = mapper.map_infrastructure(["1.2.3.4"])
        assert "by_country" in result
        assert "by_asn" in result
        assert "by_isp" in result
        assert result["total"] == 1

    def test_find_clusters_single_cluster(self):
        geos = [
            _make_geo(ip="1.1.1.1", lat=51.5, lon=-0.1),
            _make_geo(ip="2.2.2.2", lat=51.52, lon=-0.09),
        ]
        mapper = InfrastructureMapper()
        clusters = mapper.find_clusters(geos, radius_km=50.0)
        # Both points are very close — should be in the same cluster
        assert len(clusters) == 1
        assert clusters[0]["count"] == 2

    def test_find_clusters_multiple_clusters(self):
        geos = [
            _make_geo(ip="1.1.1.1", lat=51.5, lon=-0.1),   # London
            _make_geo(ip="2.2.2.2", lat=40.7, lon=-74.0),  # New York
        ]
        mapper = InfrastructureMapper()
        clusters = mapper.find_clusters(geos, radius_km=50.0)
        assert len(clusters) == 2

    def test_find_clusters_skips_results_without_coords(self):
        geos = [
            _make_geo(ip="1.1.1.1", lat=51.5, lon=-0.1),
            GeoLocationResult(ip="2.2.2.2"),  # No lat/lon
        ]
        mapper = InfrastructureMapper()
        clusters = mapper.find_clusters(geos, radius_km=50.0)
        # Only the one with coords should be processed
        assert sum(c["count"] for c in clusters) == 1

    def test_generate_heatmap_data(self):
        geos = [
            _make_geo(ip="1.1.1.1", lat=51.5, lon=-0.1, threat_score=80),
            _make_geo(ip="2.2.2.2", lat=40.7, lon=-74.0, threat_score=20),
        ]
        mapper = InfrastructureMapper()
        heatmap = mapper.generate_heatmap_data(geos)
        assert len(heatmap) == 2
        assert all("lat" in h and "lon" in h and "weight" in h for h in heatmap)

    def test_generate_heatmap_data_skips_no_coords(self):
        geos = [
            _make_geo(ip="1.1.1.1", lat=51.5, lon=-0.1),
            GeoLocationResult(ip="2.2.2.2"),  # No lat/lon
        ]
        mapper = InfrastructureMapper()
        heatmap = mapper.generate_heatmap_data(geos)
        assert len(heatmap) == 1

    def test_timeline_analysis_with_dates(self):
        ti = ThreatInfrastructure(
            indicator="1.2.3.4",
            geo_results=[_make_geo()],
            first_seen="2025-01-01T00:00:00+00:00",
            last_seen="2025-03-01T00:00:00+00:00",
            associated_campaigns=["campaign-alpha"],
        )
        mapper = InfrastructureMapper()
        result = mapper.timeline_analysis([ti])
        assert result["total_indicators"] == 1
        assert "timeline" in result
        entry = result["timeline"][0]
        assert entry["active_days"] == 59

    def test_timeline_analysis_campaigns_grouped(self):
        ti1 = ThreatInfrastructure(
            indicator="1.2.3.4",
            associated_campaigns=["campaign-alpha"],
        )
        ti2 = ThreatInfrastructure(
            indicator="5.6.7.8",
            associated_campaigns=["campaign-alpha", "campaign-beta"],
        )
        mapper = InfrastructureMapper()
        result = mapper.timeline_analysis([ti1, ti2])
        assert "campaign-alpha" in result["campaigns"]
        assert len(result["campaigns"]["campaign-alpha"]) == 2


# ── PredictiveLocationAnalyzer ────────────────────────────────────────────────

class TestPredictiveLocationAnalyzer:
    def _make_infra(self, country_code="RU", asn="AS44477") -> ThreatInfrastructure:
        geo = _make_geo(country_code=country_code, asn=asn)
        return ThreatInfrastructure(
            indicator="1.2.3.4",
            geo_results=[geo],
            first_seen="2025-01-01T00:00:00+00:00",
            last_seen="2025-02-01T00:00:00+00:00",
        )

    def test_analyze_patterns_counts_countries(self):
        data = [self._make_infra("RU"), self._make_infra("CN"), self._make_infra("RU")]
        analyzer = PredictiveLocationAnalyzer()
        patterns = analyzer.analyze_patterns(data)
        assert patterns["total_indicators"] == 3
        top = {e["value"]: e["count"] for e in patterns["top_countries"]}
        assert top["RU"] == 2
        assert top["CN"] == 1

    def test_analyze_patterns_empty_data(self):
        analyzer = PredictiveLocationAnalyzer()
        patterns = analyzer.analyze_patterns([])
        assert patterns["total_indicators"] == 0
        assert patterns["total_geo_results"] == 0

    def test_predict_next_locations_returns_list(self):
        data = [self._make_infra("RU") for _ in range(5)]
        analyzer = PredictiveLocationAnalyzer()
        predictions = analyzer.predict_next_locations(data, top_n=3)
        assert isinstance(predictions, list)
        assert len(predictions) <= 3
        # Each prediction has required fields
        for p in predictions:
            assert "rank" in p
            assert "country_code" in p
            assert "predicted_score" in p
            assert "confidence" in p

    def test_predict_next_locations_empty_data(self):
        analyzer = PredictiveLocationAnalyzer()
        predictions = analyzer.predict_next_locations([])
        assert predictions == []

    def test_predict_next_locations_bulletproof_asn_boosted(self):
        # Bulletproof ASN should boost the associated country
        geo_bulletproof = _make_geo(country_code="NL", asn="AS44477")  # AS44477 is bulletproof
        ti = ThreatInfrastructure(indicator="1.2.3.4", geo_results=[geo_bulletproof])
        analyzer = PredictiveLocationAnalyzer()
        predictions = analyzer.predict_next_locations([ti] * 5)
        nl_pred = next((p for p in predictions if p["country_code"] == "NL"), None)
        if nl_pred:
            assert nl_pred["is_bulletproof_asn_associated"] is True

    def test_calculate_risk_score_tor_exit(self):
        geo = _make_geo(is_tor=True, country_code="RU")
        analyzer = PredictiveLocationAnalyzer()
        score = analyzer.calculate_risk_score(geo)
        assert score > 40  # Tor + Russia should be high risk

    def test_calculate_risk_score_bulletproof_asn(self):
        geo = _make_geo(asn="AS44477")
        analyzer = PredictiveLocationAnalyzer()
        score = analyzer.calculate_risk_score(geo)
        assert score >= 30  # bulletproof ASN alone gives 30

    def test_calculate_risk_score_low_risk(self):
        geo = _make_geo(country_code="US", asn="AS99999",
                        is_proxy=False, is_vpn=False, is_tor=False, is_datacenter=False)
        analyzer = PredictiveLocationAnalyzer()
        score = analyzer.calculate_risk_score(geo)
        assert score < 50

    def test_calculate_risk_score_capped_at_100(self):
        geo = _make_geo(
            country_code="KP",
            asn="AS44477",
            is_proxy=True,
            is_vpn=True,
            is_tor=True,
            is_datacenter=True,
            threat_score=100,
        )
        analyzer = PredictiveLocationAnalyzer()
        score = analyzer.calculate_risk_score(geo)
        assert score <= 100.0

    def test_generate_forecast_report_structure(self):
        data = [self._make_infra("RU") for _ in range(3)]
        analyzer = PredictiveLocationAnalyzer()
        report = analyzer.generate_forecast_report(data)
        assert "generated_at" in report
        assert "summary" in report
        assert "patterns" in report
        assert "predicted_locations" in report
        assert "recommended_monitoring" in report

    def test_generate_forecast_report_empty_data(self):
        analyzer = PredictiveLocationAnalyzer()
        report = analyzer.generate_forecast_report([])
        assert report["summary"]["total_historical_indicators"] == 0


# ── Convenience functions ─────────────────────────────────────────────────────

class TestConvenienceFunctions:
    @patch("collectors.osint_geolocation.requests.get")
    def test_lookup_ip_convenience(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = lookup_ip("1.2.3.4")
        assert isinstance(result, GeoLocationResult)
        assert result.ip == "1.2.3.4"

    @patch("collectors.osint_geolocation.requests.get")
    @patch("collectors.osint_geolocation.socket.getaddrinfo")
    def test_lookup_domain_convenience(self, mock_dns, mock_get):
        mock_dns.return_value = [(None, None, None, None, ("1.2.3.4", 0))]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        results = lookup_domain("example.com")
        assert len(results) == 1
        assert isinstance(results[0], GeoLocationResult)

    def test_predict_locations_convenience(self):
        ti = ThreatInfrastructure(
            indicator="1.2.3.4",
            geo_results=[_make_geo(country_code="CN", asn="AS4134")],
        )
        predictions = predict_locations([ti])
        assert isinstance(predictions, list)

    @patch("collectors.osint_geolocation.requests.get")
    def test_map_threat_infrastructure_convenience(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipinfo_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = map_threat_infrastructure(["1.2.3.4"])
        assert "by_country" in result
        assert "total" in result


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    @patch("collectors.osint_geolocation.requests.get")
    def test_ipapi_returns_fail_status(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "fail", "message": "reserved range"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        # ip-api.com fails → should fall through to other sources (all fail here too)
        result = geo._lookup_ipapi("192.168.1.1")
        assert result is None

    @patch("collectors.osint_geolocation.requests.get")
    def test_ipinfo_error_field_returns_none(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": True, "reason": "no data"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        result = geo._lookup_ipinfo("10.0.0.1")
        assert result is None

    def test_find_clusters_empty_list(self):
        mapper = InfrastructureMapper()
        clusters = mapper.find_clusters([])
        assert clusters == []

    def test_generate_heatmap_empty_list(self):
        mapper = InfrastructureMapper()
        heatmap = mapper.generate_heatmap_data([])
        assert heatmap == []

    def test_timeline_analysis_empty_list(self):
        mapper = InfrastructureMapper()
        result = mapper.timeline_analysis([])
        assert result["total_indicators"] == 0

    def test_bulletproof_asns_contains_known_entries(self):
        assert "AS44477" in BULLETPROOF_ASNS
        assert "AS202425" in BULLETPROOF_ASNS
        assert "AS9009" in BULLETPROOF_ASNS

    def test_haversine_same_point(self):
        mapper = InfrastructureMapper()
        dist = mapper._haversine(51.5, -0.1, 51.5, -0.1)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_haversine_known_distance(self):
        """London → Paris ≈ 341 km."""
        mapper = InfrastructureMapper()
        dist = mapper._haversine(51.5074, -0.1278, 48.8566, 2.3522)
        assert 330 < dist < 360

    @patch("collectors.osint_geolocation.requests.get")
    def test_rate_limiting_respected(self, mock_get):
        """Ensure _throttle does not raise when called within rate limit."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_ipapi_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geo = GeoIPLookup()
        geo._req_times = []  # reset rate limit state
        # Should not raise for a small number of lookups
        for _ in range(3):
            geo._lookup_ipapi("1.2.3.4")
        assert mock_get.call_count >= 3
