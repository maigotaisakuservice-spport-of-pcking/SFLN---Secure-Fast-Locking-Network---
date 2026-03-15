import asyncio
import aiohttp
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SFLN-DDNS")

async def update_ddns(domain, token, record_type=None, value=None):
    """
    Updates f5.si DDNS.
    https://f5.si/update.php?domain=sub.user&password=TOKEN&[ip/ipv6/txt/cname]=VALUE
    """
    url = "https://f5.si/update.php"
    params = {
        "domain": domain,
        "password": token
    }
    if record_type and value:
        params[record_type] = value

    logger.info(f"Updating DDNS for {domain} ({record_type or 'A'} -> {value or 'Auto IP'})...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                if response.status == 200:
                    logger.info(f"DDNS Update Success: {text.strip()}")
                    return True
                else:
                    logger.error(f"DDNS Update Failed ({response.status}): {text.strip()}")
                    return False
    except Exception as e:
        logger.error(f"DDNS Update Error: {e}")
        return False

if __name__ == "__main__":
    # Usage: python3 ddns_update.py sfln-server.pdg [cname] [value]
    if len(sys.argv) < 2:
        print("Usage: python3 ddns_update.py <sub.user> [record_type] [value]")
        sys.exit(1)

    domain = sys.argv[1]
    token = os.environ.get("SFLN_DDNS_TOKEN")

    if not token:
        logger.error("SFLN_DDNS_TOKEN environment variable not set.")
        sys.exit(1)

    record_type = sys.argv[2] if len(sys.argv) > 2 else None
    value = sys.argv[3] if len(sys.argv) > 3 else None

    asyncio.run(update_ddns(domain, token, record_type, value))
