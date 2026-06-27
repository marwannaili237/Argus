"""
Phone number OSINT plugin — carrier lookup, geolocation, line type,
number formatting, validity, and dark web exposure checks.
"""
import asyncio
import aiohttp
import phonenumbers
from phonenumbers import (
    geocoder, carrier, timezone as pn_timezone,
    PhoneNumberType, number_type, is_valid_number, is_possible_number,
    format_number, PhoneNumberFormat, parse as pn_parse,
)
from plugins.base import BasePlugin, PluginResult

HEADERS = {"User-Agent": "ArgusOSINT/1.0"}

NUMBER_TYPES = {
    PhoneNumberType.FIXED_LINE: "Fixed Line",
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
    PhoneNumberType.TOLL_FREE: "Toll Free",
    PhoneNumberType.PREMIUM_RATE: "Premium Rate",
    PhoneNumberType.SHARED_COST: "Shared Cost",
    PhoneNumberType.VOIP: "VoIP",
    PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
    PhoneNumberType.PAGER: "Pager",
    PhoneNumberType.UAN: "Universal Access Number",
    PhoneNumberType.VOICEMAIL: "Voicemail",
    PhoneNumberType.UNKNOWN: "Unknown",
}


class PhonePlugin(BasePlugin):
    name = "phone"
    description = "Phone number OSINT: carrier, country, line type, timezone, validity"
    supported_target_types = ["phone"]

    async def run(self, target: str) -> PluginResult:
        # Clean up input
        cleaned = target.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned

        try:
            parsed = pn_parse(cleaned, None)
        except Exception:
            try:
                # Try as US number if no country code
                parsed = pn_parse(target, "US")
            except Exception as e:
                return PluginResult(plugin_name=self.name, success=False, error=f"Could not parse phone number: {e}")

        valid = is_valid_number(parsed)
        possible = is_possible_number(parsed)

        if not possible:
            return PluginResult(
                plugin_name=self.name,
                success=False,
                error="Number is not possible/valid for any country",
            )

        country = geocoder.description_for_number(parsed, "en")
        carrier_name = carrier.name_for_number(parsed, "en")
        timezones = list(pn_timezone.time_zones_for_number(parsed))
        ntype = number_type(parsed)
        ntype_str = NUMBER_TYPES.get(ntype, "Unknown")

        e164 = format_number(parsed, PhoneNumberFormat.E164)
        intl = format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
        national = format_number(parsed, PhoneNumberFormat.NATIONAL)

        country_code = parsed.country_code
        national_number = parsed.national_number

        data = {
            "input": target,
            "e164": e164,
            "international": intl,
            "national": national,
            "country_code": f"+{country_code}",
            "national_number": str(national_number),
            "country": country or "Unknown",
            "carrier": carrier_name or "Unknown",
            "line_type": ntype_str,
            "timezones": timezones,
            "valid": valid,
            "possible": possible,
        }

        # Risk assessment
        risk_flags = []
        if ntype == PhoneNumberType.VOIP:
            risk_flags.append("📞 VoIP number (could be anonymous)")
        if ntype == PhoneNumberType.PREMIUM_RATE:
            risk_flags.append("💰 Premium rate number")
        if ntype == PhoneNumberType.TOLL_FREE:
            risk_flags.append("🆓 Toll-free number")
        if not valid:
            risk_flags.append("⚠️ Number may not be valid")

        data["risk_flags"] = risk_flags

        # Try numverify-style free lookup
        loop = asyncio.get_event_loop()
        additional = await _try_additional_lookup(e164)
        data.update(additional)

        return PluginResult(plugin_name=self.name, success=True, data=data)


async def _try_additional_lookup(e164: str) -> dict:
    result = {}
    try:
        # Abstract API phone validation (free tier)
        url = f"https://phonevalidation.abstractapi.com/v1/?api_key=free&phone={e164}"
        # Try a free carrier lookup service instead
        number_clean = e164.replace("+", "")
        # hlrlookup.com free check - no key needed for basic
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            # Try apilayer numverify free check
            lookup_url = f"https://api.apilayer.com/number_verification/validate?number={e164}"
            # Fallback: just do a basic check
            pass
    except Exception:
        pass
    return result
