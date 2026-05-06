# app/services/search_tavily.py
# ============================================================
#  Tavily Search Service
#  Searches the web for live hotel, flight, and activity data.
# ============================================================

import asyncio
from tavily import TavilyClient
from app.core.config import get_settings
from app.core.logging import logger
from typing import List, Dict, Optional

settings = get_settings()

_tavily_client: Optional[TavilyClient] = None


def get_tavily_client() -> TavilyClient:
    global _tavily_client
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured.")
    if _tavily_client is None:
        _tavily_client = TavilyClient(api_key=settings.tavily_api_key)
    return _tavily_client


async def search_web(query: str, max_results: int = None) -> List[Dict]:
    """
    Generic search returning a list of {title, url, content} dicts.
    """
    n = max_results or settings.tavily_max_results
    client = get_tavily_client()
    try:
        logger.info(f"[Tavily] Searching: '{query}' max={n}")
        result = client.search(
            query=query,
            search_depth=settings.tavily_search_depth,
            max_results=n,
            include_answer=True,
        )
        sources = result.get("results", [])
        logger.info(f"[Tavily] Got {len(sources)} results")
        return sources
    except Exception as e:
        logger.error(f"[Tavily] Search error: {e}")
        return []


async def search_flights(origin: str, destination: str, departure_date: str) -> str:
    """
    Search for flight information with multiple queries for diversity.
    Returns formatted context string with varied flight options.
    """
    # Search for flights with different perspectives
    searches = [
        f"flights from {origin} to {destination} {departure_date} cheap budget",
        f"direct flights {origin} {destination} price booking",
        f"best airlines {origin} {destination} {departure_date}",
        f"round trip flights {destination} {departure_date} deals",
        f"economy class flights {origin} {destination} cost",
    ]
    
    # Run all searches in parallel
    tasks = [search_web(query, max_results=2) for query in searches]
    all_results = await asyncio.gather(*tasks)
    
    # Combine results, keeping up to 10
    combined = []
    seen_titles = set()
    for results in all_results:
        for r in results:
            title = r.get("title", "").lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                combined.append(r)
    
    return _format_search_context("Flights", combined[:10])


async def search_hotels(destination: str, check_in: str, check_out: str, budget_level: str) -> str:
    """
    Search for multiple types of hotel options by price point.
    Returns diverse hotel recommendations to avoid duplicates.
    """
    # Search for different price point categories
    searches = [
        f"budget cheap affordable hotels in {destination} under $100",
        f"mid-range moderate hotels in {destination} {check_in}",
        f"best luxury premium hotels in {destination}",
        f"4-star hotels in {destination} near attractions",
        f"boutique hotels {destination} city center",
    ]
    
    # Run all searches in parallel
    tasks = [search_web(query, max_results=3) for query in searches]
    all_results = await asyncio.gather(*tasks)
    
    # Combine and deduplicate results
    combined = []
    seen_titles = set()
    for results in all_results:
        for r in results:
            title = r.get("title", "").lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                combined.append(r)
    
    # Return up to 15 diverse results
    return _format_search_context("Hotels", combined[:15])


async def search_activities(destination: str, trip_type: str) -> str:
    """
    Search for diverse activities across multiple categories.
    Returns formatted context with varied activity options.
    """
    # Search for different types of activities
    searches = [
        f"best {trip_type} activities things to do in {destination} tourist attractions",
        f"adventure activities {destination} outdoor tours",
        f"cultural attractions museums {destination}",
        f"dining restaurants food experiences {destination}",
        f"shopping markets nightlife entertainment {destination}",
    ]
    
    # Run all searches in parallel
    tasks = [search_web(query, max_results=2) for query in searches]
    all_results = await asyncio.gather(*tasks)
    
    # Combine results, keeping up to 15
    combined = []
    seen_titles = set()
    for results in all_results:
        for r in results:
            title = r.get("title", "").lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                combined.append(r)
    
    return _format_search_context("Activities", combined[:15])


async def search_destination_overview(destination: str) -> str:
    """General destination research."""
    query = f"{destination} travel guide tips visa requirements weather best time to visit"
    results = await search_web(query, max_results=3)
    return _format_search_context("Destination Overview", results)


async def gather_all_travel_data(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    budget_level: str,
    trip_type: str,
) -> Dict[str, str]:
    """
    Run all searches in parallel context for a complete travel query.
    Returns a dict of context strings ready to inject into the LLM prompt.
    """
    import asyncio

    flights_task    = search_flights(origin, destination, departure_date)
    hotels_task     = search_hotels(destination, departure_date, return_date, budget_level)
    activities_task = search_activities(destination, trip_type)
    overview_task   = search_destination_overview(destination)

    flights, hotels, activities, overview = await asyncio.gather(
        flights_task, hotels_task, activities_task, overview_task
    )

    return {
        "flights":    flights,
        "hotels":     hotels,
        "activities": activities,
        "overview":   overview,
    }


def _format_search_context(category: str, results: List[Dict]) -> str:
    """Convert Tavily results into a clean text block for LLM context."""
    if not results:
        return f"[{category}]: No live data found."

    lines = [f"=== {category} (live web data) ==="]
    for r in results:
        title   = r.get("title", "")
        content = r.get("content", "")[:400]  # trim long snippets
        url     = r.get("url", "")
        lines.append(f"• {title}\n  {content}\n  Source: {url}")
    return "\n".join(lines)
