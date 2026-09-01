"""
Configurable list of public Telegram sources to collect from.
Modify this list to add or remove channels.

IMPORTANT: Only collect from public/authorized channels that the
authenticated Telegram account is permitted to access.
"""

TELEGRAM_CHANNELS: list[str] = [
    "DevelopmentNewsIndia",
    "indiainlast24hrr",
    "PIB_Backgrounders",
    "MIB_India",
    "PIB_FactCheck",
    "governmentschemesandprogrammes",
]

# Minimum relevance score (0.0 – 1.0) for a message to be retained
RELEVANCE_THRESHOLD: float = 0.10
