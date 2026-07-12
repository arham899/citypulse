from .allevents import AllEventsSource
from .cinepax import CinepaxSource
from .eventbrite_scrape import EventbriteScrapeSource
from .meta_graph import MetaGraphSource
from .ticketmaster import TicketmasterSource

ALL_SOURCES = [
    AllEventsSource(),
    EventbriteScrapeSource(),
    CinepaxSource(),
    MetaGraphSource(),     # activates when META_ACCESS_TOKEN + META_PAGE_IDS are set
    TicketmasterSource(),  # activates when TICKETMASTER_API_KEY is set
]
