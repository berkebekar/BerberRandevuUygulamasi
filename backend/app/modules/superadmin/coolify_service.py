"""
Coolify integration for tenant domain activation.

The production VPS uses Coolify + Traefik. With HTTP-01 certificates, Traefik
cannot issue one wildcard certificate for *.bbsoft.com.tr. Instead, we keep the
frontend app's domain and Host labels in sync with the tenant list so each
tenant gets its own Let's Encrypt certificate automatically.
"""

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
    updated: bool = False
    reason: str | None = None


def _clean_base_url(value: str) -> str:
    return (value or "").strip().rstrip("/")


def _tenant_domain(subdomain: str, app_domain: str) -> str:
    return f"https://{subdomain.strip().lower()}.{app_domain.strip().lower()}"


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


def _merge_domains(current_value: str | None, tenant_domain: str) -> tuple[str, bool]:
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

    tenant_key = tenant_domain.lower()
    if tenant_key in seen:
        return ",".join(domains), False

    domains.append(tenant_domain)
    return ",".join(domains), True


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
        if not hostname.endswith(f".{app_domain}"):
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
            "caddy_0.encode=zstd gzip",
            "caddy_0.handle_path.0_reverse_proxy={{upstreams 3000}}",
            "caddy_0.handle_path=/*",
            "caddy_0.header=-Server",
            "caddy_0.try_files={path} /index.html /index.php",
            f"caddy_0={domains_value}",
            "caddy_ingress_network=coolify",
        ]
    )


def _is_configured(settings: Settings) -> bool:
    return bool(
        _clean_base_url(settings.coolify_api_url)
        and settings.coolify_api_token.strip()
        and settings.coolify_frontend_app_uuid.strip()
        and settings.app_domain.strip()
    )


async def ensure_tenant_frontend_domain(subdomain: str) -> CoolifyTenantSyncResult:
    settings = get_settings()
    if not _is_configured(settings):
        return CoolifyTenantSyncResult(enabled=False, reason="coolify_not_configured")

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
        next_domains, changed = _merge_domains(current_domains, domain)
        if not changed:
            return CoolifyTenantSyncResult(enabled=True, domain=domain, updated=False, reason="already_present")

        labels = _build_frontend_labels(app_uuid, next_domains, settings.app_domain)
        patch_payload = {
            "domains": next_domains,
            "custom_labels": labels,
            "instant_deploy": settings.coolify_instant_deploy_on_tenant_create,
            "force_domain_override": True,
        }
        patch_response = await client.patch(f"applications/{app_uuid}", json=patch_payload)
        patch_response.raise_for_status()

    logger.info("Coolify frontend domain synced for tenant %s", subdomain)
    return CoolifyTenantSyncResult(enabled=True, domain=domain, updated=True)
