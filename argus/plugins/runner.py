import asyncio
import re
from datetime import datetime, timezone
from sqlalchemy import select
from database import AsyncSessionLocal
from models import Investigation, Evidence
from plugins.whois_plugin import WhoisPlugin
from plugins.dns_plugin import DnsPlugin
from plugins.certs_plugin import CertsPlugin
from plugins.ip_plugin import IpPlugin
from plugins.http_plugin import HttpPlugin

IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")

ALL_PLUGINS = [WhoisPlugin(), DnsPlugin(), CertsPlugin(), IpPlugin(), HttpPlugin()]


def classify_target(target: str) -> str:
    t = target.strip()
    if t.startswith(("http://", "https://")):
        return "url"
    if IP_RE.match(t):
        return "ip"
    if EMAIL_RE.match(t):
        return "email"
    if DOMAIN_RE.match(t):
        return "domain"
    return "unknown"


def get_plugins_for_type(target_type: str):
    return [p for p in ALL_PLUGINS if p.supports(target_type)]


async def run_investigation(investigation_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
        inv = result.scalar_one_or_none()
        if not inv:
            return

        plugins = get_plugins_for_type(inv.target_type)

        if not plugins:
            inv.status = "completed"
            inv.summary = f"No plugins available for target type: {inv.target_type}"
            inv.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()
            await _notify_telegram(inv, [])
            return

        plugin_tasks = [plugin.run(inv.target) for plugin in plugins]
        results = await asyncio.gather(*plugin_tasks, return_exceptions=True)

        evidence_list = []
        for r in results:
            if isinstance(r, Exception):
                continue
            evidence = Evidence(
                investigation_id=inv.id,
                plugin_name=r.plugin_name,
                data=r.data if r.success else {"error": r.error},
            )
            db.add(evidence)
            evidence_list.append(r)

        inv.status = "completed"
        inv.summary = _build_summary(inv.target, inv.target_type, evidence_list)
        inv.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        await _notify_telegram(inv, evidence_list)


def _build_summary(target: str, target_type: str, results) -> str:
    lines = [f"🔍 *Investigation: {target}*", f"Type: `{target_type}`", ""]

    for r in results:
        if not r.success:
            continue
        if r.plugin_name == "whois" and r.data:
            lines.append("📋 *WHOIS*")
            if r.data.get("registrar"):
                lines.append(f"  Registrar: {r.data['registrar']}")
            if r.data.get("creation_date"):
                lines.append(f"  Created: {r.data['creation_date'][:10]}")
            if r.data.get("expiration_date"):
                lines.append(f"  Expires: {r.data['expiration_date'][:10]}")
            if r.data.get("country"):
                lines.append(f"  Country: {r.data['country']}")
            lines.append("")

        elif r.plugin_name == "dns" and r.data:
            lines.append("🌐 *DNS Records*")
            records = r.data.get("records", {})
            if records.get("A"):
                lines.append(f"  A: {', '.join(records['A'][:3])}")
            if records.get("AAAA"):
                lines.append(f"  AAAA: {records['AAAA'][0]}")
            if records.get("MX"):
                lines.append(f"  MX: {records['MX'][0]}")
            if records.get("NS"):
                lines.append(f"  NS: {', '.join(records['NS'][:2])}")
            if records.get("TXT"):
                txts = [t[:60] for t in records["TXT"][:2]]
                lines.append(f"  TXT: {', '.join(txts)}")
            lines.append("")

        elif r.plugin_name == "certs" and r.data:
            lines.append("🔐 *Certificate Transparency*")
            lines.append(f"  Total certs found: {r.data.get('total_certs', 0)}")
            subs = r.data.get("subdomains", [])
            if subs:
                lines.append(f"  Subdomains discovered: {r.data.get('total_subdomains', len(subs))}")
                lines.append(f"  Sample: {', '.join(subs[:5])}")
            lines.append("")

        elif r.plugin_name == "ip_geo" and r.data:
            lines.append("📍 *IP Geolocation*")
            lines.append(f"  IP: {r.data.get('ip')}")
            if r.data.get("city"):
                lines.append(f"  Location: {r.data['city']}, {r.data.get('region')}, {r.data.get('country')}")
            if r.data.get("isp"):
                lines.append(f"  ISP: {r.data['isp']}")
            if r.data.get("asn"):
                lines.append(f"  ASN: {r.data['asn']}")
            flags = []
            if r.data.get("is_proxy"):
                flags.append("⚠️ Proxy/VPN")
            if r.data.get("is_hosting"):
                flags.append("🏢 Hosting/DC")
            if flags:
                lines.append(f"  Flags: {', '.join(flags)}")
            lines.append("")

        elif r.plugin_name == "http" and r.data:
            lines.append("🌍 *HTTP Info*")
            if r.data.get("title"):
                lines.append(f"  Title: {r.data['title'][:80]}")
            lines.append(f"  Status: {r.data.get('status_code')}")
            techs = r.data.get("technologies", [])
            if techs:
                lines.append(f"  Tech: {', '.join(techs[:5])}")
            lines.append("")

    return "\n".join(lines)


async def _notify_telegram(inv: Investigation, results):
    if not inv.telegram_chat_id or not inv.telegram_message_id:
        return

    try:
        from config import get_settings
        import aiohttp

        settings = get_settings()
        if not settings.telegram_bot_token:
            return

        text = inv.summary or "Investigation completed."
        text += f"\n\n✅ Done | /results\\_{inv.id}"

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/editMessageText"
        payload = {
            "chat_id": inv.telegram_chat_id,
            "message_id": inv.telegram_message_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
    except Exception:
        pass
