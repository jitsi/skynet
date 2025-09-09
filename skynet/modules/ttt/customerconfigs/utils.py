import json
from typing import Optional

from skynet.modules.ttt.persistence import db


def get_customerconfig_key(customer_id: str) -> str:
    """Generate database key for customer configuration."""
    return f"customerconfig:{customer_id}"


async def get_existing_customer_config(customer_id: str) -> Optional[dict]:
    """Get the customer configuration for a customer if it exists."""
    key = get_customerconfig_key(customer_id)
    config_json = await db.get(key)

    if config_json:
        return json.loads(config_json)

    return None
