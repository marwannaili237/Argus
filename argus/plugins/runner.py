import asyncio
import re
from datetime import datetime, timezone
from sqlalchemy import select
from database import AsyncSessionLocal
from models import Investigation, Evidence

# Domain / URL / IP plugins
from plugins.whois_plugin import WhoisPlugin
from plugins.dns_plugin import DnsPlugin
from plugins.certs_plugin import CertsPlugin
from plugins.ip_plugin import IpPlugin
from plugins.http_plugin import HttpPlugin
from plugins.shodan_plugin import ShodanPlugin
from plugins.wayback_plugin import WaybackPlugin
from plugins.bgp_plugin import BgpPlugin
from plugins.reputation_plugin import ReputationPlugin
from plugins.subdomain_plugin import SubdomainPlugin
from plugins.passivedns_plugin import PassiveDnsPlugin
from plugins.pastebin_plugin import PastebinPlugin
from plugins.github_osint_plugin import GithubOsintPlugin

# Email plugins
from plugins.email_plugin import EmailPlugin
from plugins.breach_plugin import BreachPlugin
from plugins.social_email_plugin import SocialEmailPlugin

# Username / Phone / Image
from plugins.username_plugin import UsernamePlugin
from plugins.phone_plugin import PhonePlugin
from plugins.image_plugin import ImagePlugin

# AI
from plugins.ai_analysis import AiAnalysisPlugin

IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
USERNAME_RE = re.compile(r"^@?[a-zA-Z0-9_\.]{2,40}$")
IMAGE_HOSTS = {
    "imgur.com", "i.imgur.com", "pbs.twimg.com", "cdn.discordapp.com",
    "images.unsplash.com", "upload.wikimedia.org", "i.redd.it",
}

ALL_PLUGINS = {
    "domain": [
        WhoisPlugin(), DnsPlugin(), CertsPlugin(), IpPlugin(), HttpPlugin(),
        ShodanPlugin(), WaybackPlugin(), ReputationPlugin(),
        SubdomainPlugin(), PassiveDnsPlugin(), PastebinPlugin(), GithubOsintPlugin(),
    ],
    "url": [
        WhoisPlugin(), DnsPlugin(), CertsPlugin(), IpPlugin(), HttpPlugin(),
        ShodanPlugin(), WaybackPlugin(), ReputationPlugin(),
        SubdomainPlugin(), PassiveDnsPlugin(), GithubOsintPlugin(),
    ],
    "ip": [
        IpPlugin(), DnsPlugin(), ShodanPlugin(), BgpPlugin(),
        ReputationPlugin(), PassiveDnsPlugin(),
    ],
    "email": [
        EmailPlugin(), BreachPlugin(), SocialEmailPlugin(), GithubOsintPlugin(), PastebinPlugin(),
    ],
    "username": [
        UsernamePlugin(), GithubOsintPlugin(), PastebinPlugin(),
    ],
    "phone": [PhonePlugin()],
    "image": [ImagePlugin()],
}
AI_PLUGIN = AiAnalysisPlugin()


def classify_target(target: str) -> str:
    t = target.strip()

    if t.startswith(("http://", "https://")):
        lower = t.lower().split("?")[0]
        if any(lower.endswith(ext) for ext in IMAGE_EXTS):
            return "image"
        host = lower.split("://")[1].split("/")[0]
        if host in IMAGE_HOSTS:
            return "image"
        return "url"

    if IP_RE.match(t):
        return "ip"
    if EMAIL_RE.match(t):
        return "email"

    if t.startswith("+") and PHONE_RE.match(t):
        return "phone"
    digits_only = re.sub(r"[\s\-\(\)]", "", t)
    if digits_only.isdigit() and 7 <= len(digits_only) <= 15:
        return "phone"

    if t.startswith("@") and USERNAME_RE.match(t):
        return "username"

    if DOMAIN_RE.match(t):
        return "domain"

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
            inv.summary = (
                f"⚠️ No plugins available for target type: `{inv.target_type}`\n\n"
                "Supported: domain · URL · IP · email · @username · phone · image URL"
            )
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


def _trunc(s, n=80):
    s = str(s)
    return s[:n] + "…" if len(s) > n else s


def _build_summary(target: str, target_type: str, results) -> str:
    type_emoji = {
        "domain": "🌐", "url": "🔗", "ip": "🖥️", "email": "📧",
        "username": "👤", "phone": "📞", "image": "🖼️", "unknown": "❓",
    }
    lines = [f"{type_emoji.get(target_type, '🔍')} *Investigation: {target}*", f"Type: `{target_type}`", ""]

    for r in results:
        if not r.success:
            continue
        d = r.data or {}

        # ─── Domain/URL/IP ────────────────────────────────────────────────
        if r.plugin_name == "whois":
            lines.append("📋 *WHOIS*")
            if d.get("registrar"):
                lines.append(f"  Registrar: {d['registrar']}")
            if d.get("creation_date"):
                lines.append(f"  Created: {str(d['creation_date'])[:10]}")
            if d.get("expiration_date"):
                lines.append(f"  Expires: {str(d['expiration_date'])[:10]}")
            if d.get("country"):
                lines.append(f"  Country: {d['country']}")
            if d.get("emails"):
                lines.append(f"  Contacts: {', '.join(list(d['emails'])[:2])}")
            lines.append("")

        elif r.plugin_name == "dns":
            lines.append("🌐 *DNS*")
            rec = d.get("records", {})
            if rec.get("A"):
                lines.append(f"  A: {', '.join(rec['A'][:3])}")
            if rec.get("MX"):
                lines.append(f"  MX: {rec['MX'][0]}")
            if rec.get("NS"):
                lines.append(f"  NS: {', '.join(rec['NS'][:2])}")
            if rec.get("TXT"):
                lines.append(f"  TXT: {rec['TXT'][0][:60]}")
            lines.append("")

        elif r.plugin_name == "certs":
            lines.append("🔐 *Cert Transparency*")
            lines.append(f"  Certs: {d.get('total_certs', 0)}")
            subs = d.get("subdomains", [])
            if subs:
                lines.append(f"  Subdomains: {d.get('total_subdomains', len(subs))}")
                lines.append(f"  Sample: {', '.join(subs[:4])}")
            lines.append("")

        elif r.plugin_name == "ip_geo":
            lines.append("📍 *IP Geolocation*")
            lines.append(f"  IP: {d.get('ip')}")
            if d.get("city"):
                lines.append(f"  {d['city']}, {d.get('region')}, {d.get('country')}")
            if d.get("isp"):
                lines.append(f"  ISP: {d['isp']}")
            if d.get("asn"):
                lines.append(f"  ASN: {d['asn']}")
            flags = []
            if d.get("is_proxy"):
                flags.append("⚠️ Proxy/VPN")
            if d.get("is_hosting"):
                flags.append("🏢 DC/Hosting")
            if flags:
                lines.append(f"  {', '.join(flags)}")
            lines.append("")

        elif r.plugin_name == "http":
            lines.append("🌍 *HTTP*")
            if d.get("title"):
                lines.append(f"  Title: {_trunc(d['title'])}")
            lines.append(f"  Status: {d.get('status_code')}")
            techs = d.get("technologies", [])
            if techs:
                lines.append(f"  Tech: {', '.join(techs[:6])}")
            sec = d.get("security_headers", {})
            if isinstance(sec, dict):
                lines.append(f"  Security headers: {len(sec)} present")
            lines.append("")

        elif r.plugin_name == "shodan":
            ports = d.get("all_open_ports", [])
            vulns = d.get("all_vulns", [])
            tags = d.get("all_tags", [])
            if ports or vulns or tags:
                lines.append("🔌 *Shodan (InternetDB)*")
                if ports:
                    lines.append(f"  Open ports: {', '.join(str(p) for p in ports[:15])}")
                if tags:
                    lines.append(f"  Tags: {', '.join(tags)}")
                if vulns:
                    lines.append(f"  ⚠️ CVEs: {', '.join(vulns[:5])}")
                for flag in d.get("risk_flags", []):
                    lines.append(f"  {flag}")
                lines.append("")

        elif r.plugin_name == "wayback":
            if d.get("has_archive"):
                lines.append("📦 *Wayback Machine*")
                if d.get("first_seen"):
                    lines.append(f"  First seen: {d['first_seen']}")
                if d.get("last_seen"):
                    lines.append(f"  Last seen: {d['last_seen']}")
                if d.get("snapshot_pages"):
                    lines.append(f"  Snapshot pages: {d['snapshot_pages']}")
                if d.get("first_snapshot_url"):
                    lines.append(f"  [Oldest snapshot]({d['first_snapshot_url']})")
                recent = d.get("recent_snapshots", [])
                if recent:
                    lines.append(f"  Recent: {' · '.join(s['date'] for s in recent[:3])}")
                lines.append("")

        elif r.plugin_name == "bgp":
            if d.get("asn"):
                lines.append("🌐 *BGP / ASN*")
                lines.append(f"  ASN: AS{d['asn']} — {d.get('asn_name', '')}")
                if d.get("prefix"):
                    lines.append(f"  Prefix: {d['prefix']}")
                if d.get("country"):
                    lines.append(f"  Country: {d['country']}")
                if d.get("peer_count"):
                    lines.append(f"  Peers: {d['peer_count']}")
                abuse = d.get("abuse_contacts", [])
                if abuse:
                    lines.append(f"  Abuse: {', '.join(abuse[:2])}")
                ixs = d.get("ix_presence", [])
                if ixs:
                    ix_names = [ix.get("name", "") for ix in ixs[:3]]
                    lines.append(f"  IXPs: {', '.join(ix_names)}")
                lines.append("")

        elif r.plugin_name == "reputation":
            threats = d.get("threats", [])
            if threats:
                lines.append("🚨 *Threat Intelligence*")
                for t in threats[:6]:
                    lines.append(f"  {t}")
                lines.append("")
            elif d.get("threat_count") == 0:
                lines.append("🟢 *Threat Intel*: No threats detected\n")

        elif r.plugin_name == "subdomains":
            total = d.get("total_found", 0)
            if total:
                lines.append("🔎 *Subdomain Enumeration*")
                lines.append(f"  Found: {total} subdomains")
                subs = d.get("subdomains", [])
                if subs:
                    lines.append(f"  Sample: {', '.join(subs[:8])}")
                confirmed = d.get("brute_force_confirmed", [])
                if confirmed:
                    lines.append(f"  DNS-confirmed: {len(confirmed)}")
                lines.append("")

        elif r.plugin_name == "passive_dns":
            rev = d.get("reverse_ip_domains", [])
            hist = d.get("ip_history", [])
            nmap = d.get("nmap_scan")
            if rev or hist or nmap:
                lines.append("📡 *Passive DNS / Reverse IP*")
                if rev:
                    lines.append(f"  Shared hosting: {d.get('shared_hosting_count', len(rev))} domains")
                    lines.append(f"  Sample: {', '.join(rev[:4])}")
                if hist:
                    lines.append(f"  IP history:")
                    for h in hist[:3]:
                        lines.append(f"    {h.get('ip')} ({h.get('location')}) — {h.get('date')}")
                if nmap:
                    # Extract just open ports line
                    for line in nmap.splitlines():
                        if "open" in line.lower():
                            lines.append(f"  Nmap: {line.strip()[:80]}")
                lines.append("")

        elif r.plugin_name == "pastes":
            exposure = d.get("exposure_score", 0)
            gh = d.get("github_code_results", 0)
            pb = len(d.get("pastebin_urls", []))
            ps = len(d.get("psbdmp_pastes", []))
            intelx = d.get("intelx", {})
            if exposure or gh or pb or ps:
                lines.append("📋 *Paste / Leak Exposure*")
                if gh:
                    lines.append(f"  GitHub code mentions: {gh}")
                    sample = d.get("github_code_sample", [])
                    for s in sample[:2]:
                        lines.append(f"    [{s.get('repo')}]({s.get('url')})")
                if pb:
                    lines.append(f"  Pastebin hits: {pb}")
                    for url in d.get("pastebin_urls", [])[:3]:
                        lines.append(f"    {url}")
                if ps:
                    lines.append(f"  PSBDMP hits: {ps}")
                if intelx and intelx.get("total"):
                    lines.append(f"  IntelX: {intelx['total']} records")
                lines.append("")

        elif r.plugin_name == "github_osint":
            total = d.get("total_github_exposure", 0)
            if total:
                lines.append("🐙 *GitHub OSINT*")
                code = d.get("code_mentions", {})
                commits = d.get("commits", {})
                repos = d.get("repos", {})
                users = d.get("users", {})
                if code.get("total"):
                    lines.append(f"  Code mentions: {code['total']}")
                    for item in code.get("items", [])[:2]:
                        lines.append(f"    [{item.get('repo')}]({item.get('url')})")
                if commits.get("total"):
                    lines.append(f"  Commit mentions: {commits['total']}")
                if repos.get("total"):
                    lines.append(f"  Repo mentions: {repos['total']}")
                if users.get("total"):
                    lines.append(f"  Users found: {users['total']}")
                    for u in users.get("items", [])[:2]:
                        lines.append(f"    [{u['login']}]({u['url']})")
                lines.append("")

        # ─── Email plugins ────────────────────────────────────────────────
        elif r.plugin_name == "email":
            lines.append("📧 *Email Intel*")
            lines.append(f"  Domain MX: {'✅' if d.get('domain_has_mx') else '❌'}")
            lines.append(f"  Gravatar: {'✅' if d.get('gravatar') else '❌'}")
            rep = d.get("reputation", "unknown")
            lines.append(f"  Reputation: {rep}")
            if d.get("disposable"):
                lines.append(f"  🗑️ Disposable email")
            if d.get("free_provider"):
                lines.append(f"  Free provider")
            profiles = d.get("profiles", [])
            if profiles:
                lines.append(f"  Profiles: {', '.join(profiles[:5])}")
            gh = d.get("github_users", [])
            if gh:
                lines.append(f"  GitHub: [{gh[0]['login']}]({gh[0]['url']})")
            for flag in d.get("risk_flags", []):
                lines.append(f"  {flag}")
            lines.append("")

        elif r.plugin_name == "breach":
            lines.append("🔓 *Breach Check*")
            found = d.get("breach_found", False)
            lines.append(f"  {'🚨 FOUND IN BREACHES' if found else '✅ Not found'}")
            lines.append(f"  Risk: {d.get('risk_level', 'Unknown')}")
            if d.get("credentials_leaked"):
                lines.append("  ⚠️ Credentials/passwords leaked!")
            sources = d.get("breach_sources", [])
            if sources:
                lines.append(f"  Sources: {', '.join(str(s) for s in sources[:5])}")
            lines.append("")

        elif r.plugin_name == "social_email":
            found_list = d.get("registered_on", [])
            count = d.get("registered_count", 0)
            checked = d.get("sites_checked", 0)
            lines.append("🔗 *Email → Social Accounts*")
            lines.append(f"  Checked: {checked} sites | Found: {count}")
            for item in found_list[:8]:
                lines.append(f"  ✓ {item['site']}")
            lines.append("")

        # ─── Username ─────────────────────────────────────────────────────
        elif r.plugin_name == "username":
            lines.append("👤 *Username Hunt*")
            lines.append(f"  Checked: {d.get('platforms_checked', 0)} platforms")
            lines.append(f"  Found: {d.get('found_count', 0)} profiles")
            by_cat = d.get("by_category", {})
            for cat, profiles in by_cat.items():
                if profiles:
                    names = [p["platform"] for p in profiles[:6]]
                    lines.append(f"  {cat}: {', '.join(names)}")
            lines.append("")

        # ─── Phone ───────────────────────────────────────────────────────
        elif r.plugin_name == "phone":
            lines.append("📞 *Phone Intel*")
            lines.append(f"  Number: {d.get('international')}")
            lines.append(f"  Country: {d.get('country')}")
            lines.append(f"  Carrier: {d.get('carrier', 'Unknown')}")
            lines.append(f"  Type: {d.get('line_type', 'Unknown')}")
            if d.get("timezones"):
                lines.append(f"  Timezone: {d['timezones'][0]}")
            lines.append(f"  Valid: {'✅' if d.get('valid') else '⚠️'}")
            for flag in d.get("risk_flags", []):
                lines.append(f"  {flag}")
            lines.append("")

        # ─── Image ────────────────────────────────────────────────────────
        elif r.plugin_name == "image":
            lines.append("🖼️ *Image Forensics*")
            lines.append(f"  Format: {d.get('format')} {d.get('width')}×{d.get('height')}px  {d.get('file_size_kb')} KB")
            lines.append(f"  MD5: `{str(d.get('md5', ''))[:16]}…`")
            if d.get("datetime"):
                lines.append(f"  📅 {d['datetime']}")
            cam = d.get("camera", {})
            if cam:
                lines.append(f"  📷 {cam.get('Make', '')} {cam.get('Model', '')}".strip())
            if d.get("software"):
                lines.append(f"  Software: {d['software']}")
            gps = d.get("gps")
            if gps:
                lines.append(f"  📍 GPS: {gps['latitude']}, {gps['longitude']}")
                lines.append(f"  [View on Maps]({gps['maps_url']})")
            else:
                lines.append("  📍 No GPS data")
            rev = d.get("reverse_search_links", {})
            if rev:
                links = " | ".join(f"[{k}]({v})" for k, v in list(rev.items())[:4])
                lines.append(f"  🔍 {links}")
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
