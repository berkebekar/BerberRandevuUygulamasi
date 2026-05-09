"""
Coolify integration for tenant domain activation.

The production VPS uses Coolify + Traefik. With HTTP-01 certificates, Traefik
cannot issue one wildcard certificate for *.bbsoft.com.tr. Instead, we keep the
frontend app's domain and Host labels in sync with the tenant list so each
tenant gets its own Let's Encrypt certificate automatically.
"""

import base64
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoolifyTenantSyncResult:
    enabled: bool
    domain: str | None = None
    domains: list[str] | None = None
    updated: bool = False
    deploy_requested: bool = False
    deployment_uuid: str | None = None
    reason: str | None = None


def _clean_base_url(value: str) -> str:
    return (value or "").strip().rstrip("/")


def _tenant_domain(subdomain: str, app_domain: str) -> str:
    return f"https://{subdomain.strip().lower()}.{app_domain.strip().lower()}"


def _tenant_domains(subdomains: list[str], app_domain: str) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for subdomain in subdomains:
        clean = subdomain.strip().lower()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        domains.append(_tenant_domain(clean, app_domain))
    return domains


def _platform_frontend_domains(app_domain: str) -> list[str]:
    domain = app_domain.strip().lower()
    if not domain:
        return []
    return [f"https://{domain}", f"https://www.{domain}"]


def _split_domains(value: str | None) -> list[str]:
    if not value:
        return []
    domains: list[str] = []
    for item in value.split(","):
        domain = item.strip()
        if domain:
            domains.append(domain)
    return domains


def _is_valid_specific_domain(domain: str) -> bool:
    parsed = urlparse(domain)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.hostname or "*" in parsed.hostname:
        return False
    return True


def _merge_domains(
    current_value: str | None,
    tenant_domain: str,
    extra_domains: list[str] | None = None,
) -> tuple[str, bool]:
    seen: set[str] = set()
    domains: list[str] = []
    for domain in _split_domains(current_value):
        if not _is_valid_specific_domain(domain):
            continue
        key = domain.lower()
        if key in seen:
            continue
        seen.add(key)
        domains.append(domain)

    changed = False
    for domain in [*(extra_domains or []), tenant_domain]:
        if not _is_valid_specific_domain(domain):
            continue
        key = domain.lower()
        if key in seen:
            continue
        seen.add(key)
        domains.append(domain)
        changed = True

    return ",".join(domains), changed


def _build_domains_value(domains: list[str]) -> str:
    seen: set[str] = set()
    clean_domains: list[str] = []
    for domain in domains:
        if not _is_valid_specific_domain(domain):
            continue
        key = domain.lower()
        if key in seen:
            continue
        seen.add(key)
        clean_domains.append(domain)
    return ",".join(clean_domains)


def _domains_changed(current_value: str | None, next_value: str) -> bool:
    current = [domain.lower() for domain in _split_domains(current_value) if _is_valid_specific_domain(domain)]
    next_domains = [domain.lower() for domain in _split_domains(next_value)]
    return current != next_domains


def _hostnames_for_frontend(domains_value: str, app_domain: str) -> list[str]:
    app_domain = app_domain.strip().lower()
    hostnames: list[str] = []
    seen: set[str] = set()
    for domain in _split_domains(domains_value):
        parsed = urlparse(domain)
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            continue
        if hostname == f"api.{app_domain}":
            continue
        if hostname != app_domain and not hostname.endswith(f".{app_domain}"):
            continue
        if "*" in hostname or hostname in seen:
            continue
        seen.add(hostname)
        hostnames.append(hostname)
    return hostnames


def _build_host_rule(hostnames: list[str]) -> str:
    if not hostnames:
        raise ValueError("at least one hostname is required")
    if len(hostnames) == 1:
        return f"Host(`{hostnames[0]}`) && PathPrefix(`/`)"
    hosts = " || ".join(f"Host(`{hostname}`)" for hostname in hostnames)
    return f"({hosts}) && PathPrefix(`/`)"


def _build_frontend_labels(app_uuid: str, domains_value: str, app_domain: str) -> str:
    host_rule = _build_host_rule(_hostnames_for_frontend(domains_value, app_domain))
    http_router = f"http-0-{app_uuid}"
    https_router = f"https-0-{app_uuid}"

    return "\n".join(
        [
            "traefik.enable=true",
            "traefik.http.middlewares.gzip.compress=true",
            "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https",
            f"traefik.http.routers.{http_router}.entryPoints=http",
            f"traefik.http.routers.{http_router}.middlewares=redirect-to-https",
            f"traefik.http.routers.{http_router}.rule={host_rule}",
            f"traefik.http.routers.{http_router}.service={http_router}",
            f"traefik.http.routers.{https_router}.entryPoints=https",
            f"traefik.http.routers.{https_router}.middlewares=gzip",
            f"traefik.http.routers.{https_router}.rule={host_rule}",
            f"traefik.http.routers.{https_router}.service={https_router}",
            f"traefik.http.routers.{https_router}.tls.certresolver=letsencrypt",
            f"traefik.http.routers.{https_router}.tls=true",
            f"traefik.http.services.{http_router}.loadbalancer.server.port=3000",
            f"traefik.http.services.{https_router}.loadbalancer.server.port=3000",
        ]
    )


def _encode_custom_labels(labels: str) -> str:
    return base64.b64encode(labels.encode("utf-8")).decode("ascii")


def _raise_for_status(response: httpx.Response, action: str) -> None:
    if not response.is_error:
        return
    body = response.text.strip()
    logger.error("Coolify %s rejected: %s", action, body)
    raise RuntimeError(f"Coolify {action} failed: {response.status_code} {body[:500]}")


def _is_configured(settings: Settings) -> bool:
    return bool(
        _clean_base_url(settings.coolify_api_url)
        and settings.coolify_api_token.strip()
        and settings.coolify_frontend_app_uuid.strip()
        and settings.app_domain.strip()
    )


def _missing_config(settings: Settings) -> list[str]:
    missing: list[str] = []
    if not _clean_base_url(settings.coolify_api_url):
        missing.append("COOLIFY_API_URL")
    if not settings.coolify_api_token.strip():
        missing.append("COOLIFY_API_TOKEN")
    if not settings.coolify_frontend_app_uuid.strip():
        missing.append("COOLIFY_FRONTEND_APP_UUID")
    if not settings.app_domain.strip():
        missing.append("APP_DOMAIN")
    return missing


async def ensure_tenant_frontend_domain(subdomain: str) -> CoolifyTenantSyncResult:
    settings = get_settings()
    if not _is_configured(settings):
        missing = ",".join(_missing_config(settings))
        return CoolifyTenantSyncResult(enabled=False, reason=f"coolify_not_configured:{missing}")

    app_uuid = settings.coolify_frontend_app_uuid.strip()
    api_url = _clean_base_url(settings.coolify_api_url)
    domain = _tenant_domain(subdomain, settings.app_domain)
    headers = {
        "Authorization": f"Bearer {settings.coolify_api_token.strip()}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(base_url=api_url, headers=headers, timeout=15.0) as client:
        response = await client.get(f"applications/{app_uuid}")
        response.raise_for_status()
        application = response.json()

        current_domains = application.get("fqdn") or application.get("domains") or ""
        next_domains, changed = _merge_domains(
            current_domains,
            domain,
            extra_domains=_platform_frontend_domains(settings.app_domain),
        )
        if not changed:
            return CoolifyTenantSyncResult(
                enabled=True,
                domain=domain,
                domains=_split_domains(next_domains),
                updated=False,
                reason="already_present",
            )

        labels = _build_frontend_labels(app_uuid, next_domains, settings.app_domain)
        patch_payload = {
            "domains": next_domains,
            "custom_labels": _encode_custom_labels(labels),
            "is_container_label_escape_enabled": True,
            "instant_deploy": settings.coolify_instant_deploy_on_tenant_create,
            "force_domain_override": True,
        }
        patch_response = await client.patch(f"applications/{app_uuid}", json=patch_payload)
        _raise_for_status(patch_response, "frontend domain sync")

        deploy_requested = False
        deployment_uuid = None
        if settings.coolify_instant_deploy_on_tenant_create:
            start_response = await client.post(
                f"applications/{app_uuid}/start",
                params={"force": "false", "instant_deploy": "true"},
            )
            _raise_for_status(start_response, "frontend deploy request")
            deploy_requested = True
            deployment_uuid = start_response.json().get("deployment_uuid")

    logger.info("Coolify frontend domain synced for tenant %s", subdomain)
    return CoolifyTenantSyncResult(
        enabled=True,
        domain=domain,
        domains=_split_domains(next_domains),
        updated=True,
        deploy_requested=deploy_requested,
        deployment_uuid=deployment_uuid,
    )


async def sync_tenant_frontend_domains(subdomains: list[str]) -> CoolifyTenantSyncResult:
    settings = get_settings()
    if not _is_configured(settings):
        missing = ",".join(_missing_config(settings))
        return CoolifyTenantSyncResult(enabled=False, reason=f"coolify_not_configured:{missing}", domains=[])

    app_uuid = settings.coolify_frontend_app_uuid.strip()
    api_url = _clean_base_url(settings.coolify_api_url)
    tenant_domains = _tenant_domains(subdomains, settings.app_domain)
    next_domains = _build_domains_value([*_platform_frontend_domains(settings.app_domain), *tenant_domains])
    headers = {
        "Authorization": f"Bearer {settings.coolify_api_token.strip()}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(base_url=api_url, headers=headers, timeout=15.0) as client:
        response = await client.get(f"applications/{app_uuid}")
        response.raise_for_status()
        application = response.json()
        current_domains = application.get("fqdn") or application.get("domains") or ""
        changed = _domains_changed(current_domains, next_domains)

        labels = _build_frontend_labels(app_uuid, next_domains, settings.app_domain)
        patch_payload = {
            "domains": next_domains,
            "custom_labels": _encode_custom_labels(labels),
            "is_container_label_escape_enabled": True,
            "instant_deploy": settings.coolify_instant_deploy_on_tenant_create,
            "force_domain_override": True,
        }
        patch_response = await client.patch(f"applications/{app_uuid}", json=patch_payload)
        _raise_for_status(patch_response, "frontend full domain sync")

        deploy_requested = False
        deployment_uuid = None
        if settings.coolify_instant_deploy_on_tenant_create:
            start_response = await client.post(
                f"applications/{app_uuid}/start",
                params={"force": "false", "instant_deploy": "true"},
            )
            _raise_for_status(start_response, "frontend deploy request")
            deploy_requested = True
            deployment_uuid = start_response.json().get("deployment_uuid")

    logger.info("Coolify frontend domains synced for %d tenants", len(tenant_domains))
    return CoolifyTenantSyncResult(
        enabled=True,
        domains=_split_domains(next_domains),
        updated=changed,
        deploy_requested=deploy_requested,
        deployment_uuid=deployment_uuid,
        reason="synced",
    )
