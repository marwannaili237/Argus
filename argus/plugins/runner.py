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
from plugins.email_plugin import EmailPlugin
from plugins.username_plugin import UsernamePlugin
from plugins.phone_plugin import PhonePlugin
from plugins.image_plugin import ImagePlugin
from plugins.breach_plugin import BreachPlugin
from plugins.ai_analysis import AiAnalysisPlugin

IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
USERNAME_RE = re.compile(r"^@?[a-zA-Z0-9_\.]{2,40}$")

ALL_PLUGINS = {
    "domain": [WhoisPlugin(), DnsPlugin(), CertsPlugin(), IpPlugin(), HttpPlugin()],
    "url":    [WhoisPlugin(), DnsPlugin(), CertsPlugin(), IpPlugin(), HttpPlugin()],
    "ip":     [IpPlugin(), DnsPlugin()],
    "email":  [EmailPlugin(), BreachPlugin()],
    "username": [UsernamePlugin()],
    "phone":  [PhonePlugin()],
    "image":  [ImagePlugin()],
}
AI_PLUGIN = AiAnalysisPlugin()


def classify_target(target: str) -> str:
    t = target.strip()

    # Image URL (by extension or image hosting)
    if t.startswith(("http://", "https://")):
        lower = t.lower().split("?")[0]
        if any(lower.endswith(ext) for ext in IMAGE_EXTS):
            return "image"
        image_hosts = ["imgur.com", "i.imgur.com", "pbs.twimg.com", "cdn.discordapp.com",
                       "images.unsplash.com", "upload.wikimedia.org", "i.redd.it"]
        if any(h in lower for h in image_hosts):
            return "image"
        return "url"

    if IP_RE.match(t):
        return "ip"
    if EMAIL_RE.match(t):
        return "email"

    # Phone: starts with + and has digits, or all digits with spaces/dashes
    if t.startswith("+") and PHONE_RE.match(t):
        return "phone"
    # Phone: clearly numeric (10-15 digits with optional formatting)
    digits_only = re.sub(r"[\s\-\(\)]", "", t)
    if digits_only.isdigit() and 7 <= len(digits_only) <= 15:
        return "phone"

    # Username: @handle or explicit username flag
    if t.startswith("@") and USERNAME_RE.match(t):
        return "username"

    if DOMAIN_RE.match(t):
        return "domain"

    # Fallback: looks like a username
    if USERNAME_RE.match(t) and "." not in t:
        return "username"

    return "unknown"


def get_plugins_for_type(target_type: str):
    return ALL_PLUGINS.get(target_type, [])


async def run_investigation(investigation_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
        inv = result.scalar_one_or_none()
        if not inv:
            return

        plugins = get_plugins_for_type(inv.target_type)

        if not plugins:
            inv.status = "completed"
            inv.summary = f"⚠️ No plugins available for target type: `{inv.target_type}`\n\nSupported types: domain, URL, IP, email, username, phone, image URL"
            inv.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()
            await _notify_telegram(inv, [], ai_report=None)
            return

        plugin_tasks = [plugin.run(inv.target) for plugin in plugins]
        results = await asyncio.gather(*plugin_tasks, return_exceptions=True)

        evidence_list = []
        combined_data = {}
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
            if r.success:
                combined_data[r.plugin_name] = r.data

        await db.flush()

        ai_report = None
        if combined_data and AI_PLUGIN._configured:
            ai_result = await AI_PLUGIN.run(inv.target, evidence_data=combined_data)
            if ai_result.success:
                ai_report = ai_result.data.get("report")
                db.add(Evidence(
                    investigation_id=inv.id,
                    plugin_name="ai_analysis",
                    data=ai_result.data,
                ))

        inv.status = "completed"
        inv.summary = _build_summary(inv.target, inv.target_type, evidence_list)
        inv.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        await _notify_telegram(inv, evidence_list, ai_report=ai_report)


def _build_summary(target: str, target_type: str, results) -> str:
    type_emoji = {
        "domain": "🌐", "url": "🔗", "ip": "🖥️", "email": "📧",
        "username": "👤", "phone": "📞", "image": "🖼️", "unknown": "❓"
    }
    lines = [f"{type_emoji.get(target_type, '🔍')} *Investigation: {target}*", f"Type: `{target_type}`", ""]

    for r in results:
        if not r.success:
            lines.append(f"⚠️ *{r.plugin_name}*: {r.error or 'failed'}\n")
            continue

        # ── Domain/URL/IP plugins ───────────────────────────────────────
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
            if r.data.get("emails"):
                lines.append(f"  Contacts: {', '.join(r.data['emails'][:2])}")
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
                lines.append(f"  TXT: {records['TXT'][0][:60]}")
            lines.append("")

        elif r.plugin_name == "certs" and r.data:
            lines.append("🔐 *Certificate Transparency*")
            lines.append(f"  Certs found: {r.data.get('total_certs', 0)}")
            subs = r.data.get("subdomains", [])
            if subs:
                lines.append(f"  Subdomains: {r.data.get('total_subdomains', len(subs))}")
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
            sec = r.data.get("security_headers", {})
            if sec:
                lines.append(f"  Security headers: {len(sec)}/4 present")
            lines.append("")

        # ── Email plugins ───────────────────────────────────────────────
        elif r.plugin_name == "email" and r.data:
            lines.append("📧 *Email Intelligence*")
            lines.append(f"  Address: {r.data.get('email')}")
            lines.append(f"  Domain MX valid: {'✅' if r.data.get('domain_has_mx') else '❌'}")
            lines.append(f"  Gravatar: {'✅ Has avatar' if r.data.get('gravatar') else '❌ None'}")
            rep = r.data.get("reputation", "unknown")
            lines.append(f"  Reputation: {rep}")
            if r.data.get("disposable"):
                lines.append(f"  ⚠️ Disposable email")
            if r.data.get("free_provider"):
                lines.append(f"  Free provider (Gmail/Outlook etc)")
            profiles = r.data.get("profiles", [])
            if profiles:
                lines.append(f"  Known profiles: {', '.join(profiles[:5])}")
            gh = r.data.get("github_users", [])
            if gh:
                lines.append(f"  GitHub: {gh[0]['login']} ({gh[0]['url']})")
            flags = r.data.get("risk_flags", [])
            if flags:
                lines.append("\n  *Risk Flags:*")
                for f in flags:
                    lines.append(f"  {f}")
            lines.append("")

        elif r.plugin_name == "breach" and r.data:
            lines.append("🔓 *Breach Database Check*")
            found = r.data.get("breach_found", False)
            risk = r.data.get("risk_level", "Unknown")
            lines.append(f"  Status: {'🚨 FOUND IN BREACHES' if found else '✅ Not found'}")
            lines.append(f"  Risk Level: {risk}")
            if r.data.get("credentials_leaked"):
                lines.append(f"  ⚠️ Credentials/passwords leaked!")
            sources = r.data.get("breach_sources", [])
            if sources:
                lines.append(f"  Sources: {', '.join(str(s) for s in sources[:5])}")
            if r.data.get("domain_breach_count", 0) > 0:
                lines.append(f"  Domain appears in {r.data['domain_breach_count']} breach(es)")
            lines.append("")

        # ── Username plugin ─────────────────────────────────────────────
        elif r.plugin_name == "username" and r.data:
            lines.append("👤 *Username Search*")
            lines.append(f"  Username: @{r.data.get('username')}")
            lines.append(f"  Platforms checked: {r.data.get('platforms_checked', 0)}")
            lines.append(f"  Profiles found: {r.data.get('found_count', 0)}")
            by_cat = r.data.get("by_category", {})
            for cat, profiles in by_cat.items():
                if profiles:
                    names = [p["platform"] for p in profiles[:5]]
                    lines.append(f"  {cat}: {', '.join(names)}")
            lines.append("")

        # ── Phone plugin ────────────────────────────────────────────────
        elif r.plugin_name == "phone" and r.data:
            lines.append("📞 *Phone Number Intelligence*")
            lines.append(f"  Number: {r.data.get('international')}")
            lines.append(f"  Country: {r.data.get('country')}")
            lines.append(f"  Carrier: {r.data.get('carrier', 'Unknown')}")
            lines.append(f"  Line type: {r.data.get('line_type', 'Unknown')}")
            if r.data.get("timezones"):
                lines.append(f"  Timezone: {r.data['timezones'][0]}")
            lines.append(f"  Valid: {'✅' if r.data.get('valid') else '⚠️ Unverified'}")
            flags = r.data.get("risk_flags", [])
            for f in flags:
                lines.append(f"  {f}")
            lines.append("")

        # ── Image plugin ────────────────────────────────────────────────
        elif r.plugin_name == "image" and r.data:
            lines.append("🖼️ *Image Forensics*")
            lines.append(f"  Format: {r.data.get('format')} | {r.data.get('width')}×{r.data.get('height')}px")
            lines.append(f"  Size: {r.data.get('file_size_kb')} KB")
            lines.append(f"  MD5: `{r.data.get('md5', '')[:16]}…`")
            if r.data.get("datetime"):
                lines.append(f"  📅 Taken: {r.data['datetime']}")
            cam = r.data.get("camera", {})
            if cam:
                make = cam.get("Make", "")
                model = cam.get("Model", "")
                if make or model:
                    lines.append(f"  📷 Camera: {make} {model}".strip())
            if r.data.get("software"):
                lines.append(f"  Software: {r.data['software']}")
            gps = r.data.get("gps")
            if gps:
                lines.append(f"  📍 GPS: {gps['latitude']}, {gps['longitude']}")
                lines.append(f"  Maps: {gps['maps_url']}")
            else:
                lines.append(f"  📍 GPS: No location data")
            rev = r.data.get("reverse_search_links", {})
            if rev:
                links = " | ".join(f"[{k}]({v})" for k, v in list(rev.items())[:3])
                lines.append(f"  🔍 Reverse search: {links}")
            lines.append("")

    return "\n".join(lines)


async def _notify_telegram(inv: Investigation, results, ai_report: str | None = None):
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
        if ai_report:
            text += f" | 🤖 /analyze\\_{inv.id}"

        if len(text) > 4000:
            text = text[:3997] + "…"

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
