import os

from langchain_core.tools import tool
from tavily import TavilyClient


tavily_client = TavilyClient(os.environ.get("TAVILY_API_KEY"))

@tool
def check_force_majeure(search_query: str) -> str:
    """
    Search for major external events that may have materially disrupted
    a vendor's ability to perform its contractual obligations.

    
    Args: search_query
    The search query should be a complete, intent-driven question that
    contains:
    - the relevant location or supply-chain region
    - the potential disruption
    - the affected logistics/operations
    - the relevant time period, when known

    Example:
    "Have there been any major events in or around Germany that materially
    disrupted ports, railways, roads, or freight operations during September 2026?"

    Another example:
    "Did any major natural disaster, armed conflict, or infrastructure
    shutdown in Taiwan materially disrupt semiconductor supply or exports
    during September 2026?"

    Search only for major events with a plausible causal connection to
    the vendor's inability to perform. Ignore routine weather, minor
    disruptions, and short-lived local incidents.

                      
    Query Formulation Guidelines for LLM:
        - Target ONLY major, catastrophic macro-events: war/conflict, floods, droughts, 
          wildfires, earthquakes, or total port/rail infrastructure shutdowns.
        - Combine location + event type (e.g., "Germany port closure flood", 
          "Taiwan earthquake semiconductor supply", "Red Sea shipping war disruption").
        - EXCLUDE minor localized events, routine weather delays, or brief 1-day labor disputes.
        
    Post-Retrieval Directive:
        - Present the geographical and temporal timeline of the retrieved events to the user 
          so they can manually adjudicate the Force Majeure claim.
    """

    try:
        response = tavily_client.search(
            query = search_query,
            topic = "news",
            days=14,
            max_results = 3
        )
        if not response.get("results"):
            return f"No relevant Force Majeure or disruption news found."

        formatted_news = "--- TAVILY NEWS SEARCH RESULTS ---\n\n"
        for result in response["results"]:
            formatted_news += f"Title: {result['title']}\n"
            formatted_news += f"Summary: {result['content']}\n"
            formatted_news += f"Source: {result['url']}\n\n"

        return formatted_news

    except Exception as e:
        return f"Unable to fetch results -> {e}"


if __name__ == "__main__":
    # Test
    print(
        check_force_majeure.invoke({"search_query" : "Germany supply chain strikes port disruptions"})
    )
