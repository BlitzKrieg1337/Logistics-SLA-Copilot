import os

from langchain_core.tools import tool
from tavily import TavilyClient


tavily_client = TavilyClient(os.environ.get("TAVILY_API_KEY"))

@tool
def check_force_majeure(search_query: str) -> str:
    """
    Executes a real-time intelligence search to identify major macro-environmental 
    disruptions that could trigger Force Majeure clauses under standard vendor MSAs.
    
    Args:
        search_query: A targeted search string combining the vendor's location or region 
                      with specific major disaster keywords.
                      
    Query Formulation Guidelines for LLM:
        - Target ONLY major, catastrophic macro-events: war/conflict, floods, droughts, 
          wildfires, earthquakes, or total port/rail infrastructure shutdowns.
        - Combine location + event type (e.g., "Germany port closure flood", 
          "Taiwan earthquake semiconductor supply", "Red Sea shipping war disruption").
        - EXCLUDE minor localized events, routine weather delays, or brief 1-day labor disputes.
        
    Post-Retrieval Reasoning Directive for LLM:
        - Once results are returned, evaluate whether the reported event geographically 
          and temporally aligns with the vendor's delay.
        - Determine if the event qualifies as an unforeseeable Act of God / Force Majeure, 
          or if standard SLA breach penalties still apply.
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


# if __name__ == "__main__":
#     # Test
#     print(check_force_majeure("Germany supply chain strikes port disruptions"))
