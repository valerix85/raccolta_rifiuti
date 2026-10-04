# Creato da domoticafacile.it

DOMAIN = "raccolta_rifiuti"
PLATFORMS = ["sensor"]

CONF_CALENDAR = "calendar_entity_id"
CONF_LOOKAHEAD_DAYS = "lookahead_days"
CONF_LANGUAGE = "language"
# Extra user-defined phrases: {"multimateriale": ["plastic", "metal"], ...}
CONF_KEYWORDS = "keywords"

DEFAULT_LOOKAHEAD_DAYS = 7

# "auto" = use Home Assistant's configured language (hass.config.language),
# falling back to English if it isn't one of the supported languages.
CONF_LANGUAGE_AUTO = "auto"
DEFAULT_LANGUAGE_OPTION = CONF_LANGUAGE_AUTO

# Image path (served from config/www/... via the /local/ alias)
IMAGE_BASE_PATH = "/local/images/img_raccolta_rifiuti/"

# Attributes describing TODAY's calendar entry (unchanged contract).
ATTR_EVENT_SUMMARY = "event_summary"
ATTR_EVENT_START_TIME = "event_start_time"
ATTR_COLLECTION_TYPES = "collection_types"
# Language-independent version of collection_types (canonical English
# identifiers, e.g. "paper", "glass"), stable regardless of `language:`.
ATTR_COLLECTION_TYPE_CODES = "collection_type_codes"

# Attributes describing the NEXT upcoming collection within lookahead_days
# (0 days away if today has one, otherwise the first matching day ahead).
ATTR_DAYS_REMAINING = "days_remaining"
ATTR_NEXT_COLLECTION_DATE = "next_collection_date"
ATTR_NEXT_COLLECTION_TYPES = "next_collection_types"
ATTR_NEXT_COLLECTION_TYPE_CODES = "next_collection_type_codes"
