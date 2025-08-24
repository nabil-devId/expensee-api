from dateutil.parser import parse
from datetime import datetime
import logging
from typing import Union

logger = logging.getLogger(__name__)

def parse_with_dateutil(date_string: Union[str, None]) -> Union[datetime, None]:
    """
    Intelligently parses a date string using dateutil.parser.
    Returns a datetime object or None if parsing fails.
    """
    if not date_string:
        return None
    
    try:
        # The `dayfirst=True` argument helps resolve ambiguity for dates like 07/07/2025.
        # It tells the parser to interpret the first number as the day, not the month.
        return parse(date_string, dayfirst=True)
    except (ValueError, TypeError):
        # ValueError: Catches unparseable strings like "not a date"
        # TypeError: Catches if date_string is not a string (e.g., a number)
        logger.warning(f"dateutil could not parse date: '{date_string}'.")
        return None