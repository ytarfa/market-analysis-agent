from langchain.tools import tool

from app.services.google_trends_service import (
    GoogleTrendsResponse,
    InterestOverTime,
    RelatedQueries,
    RelatedQuery,
    RelatedTopic,
    RelatedTopics,
    TimelineDataPoint,
    get_google_trends_service,
)


def _format_interest_over_time(interest: InterestOverTime) -> str:
    if not interest.timeline_data:
        return "No interest-over-time data available."

    lines: list[str] = ["## Interest Over Time", ""]

    # Show a sampled subset to keep output concise for the LLM
    data_points: list[TimelineDataPoint] = interest.timeline_data
    step: int = max(1, len(data_points) // 12)
    sampled: list[TimelineDataPoint] = data_points[::step]

    # Include the last point if it wasn't already sampled
    if data_points and data_points[-1] not in sampled:
        sampled.append(data_points[-1])

    for point in sampled:
        values_str: str = ", ".join(
            f"{v.query}: {v.extracted_value}" for v in point.values
        )
        lines.append(f"- {point.date} → {values_str}")

    if interest.averages:
        avg_str: str = ", ".join(str(a) for a in interest.averages)
        lines.append(f"\nPeriod averages: {avg_str}")

    return "\n".join(lines)


def _format_related_topics(topics: RelatedTopics) -> str:
    lines: list[str] = ["## Related Topics", ""]

    if topics.rising:
        lines.append("**Rising:**")
        topic: RelatedTopic
        for topic in topics.rising[:10]:
            lines.append(f"- {topic.topic.title} ({topic.topic.type}) — {topic.value}")

    if topics.top:
        lines.append("\n**Top:**")
        for topic in topics.top[:10]:
            lines.append(f"- {topic.topic.title} ({topic.topic.type}) — {topic.value}")

    if not topics.rising and not topics.top:
        lines.append("No related topics found.")

    return "\n".join(lines)


def _format_related_queries(queries: RelatedQueries) -> str:
    lines: list[str] = ["## Related Queries", ""]

    if queries.rising:
        lines.append("**Rising:**")
        query: RelatedQuery
        for query in queries.rising[:10]:
            lines.append(f'- "{query.query}" — {query.value}')

    if queries.top:
        lines.append("\n**Top:**")
        for query in queries.top[:10]:
            lines.append(f'- "{query.query}" — {query.value}')

    if not queries.rising and not queries.top:
        lines.append("No related queries found.")

    return "\n".join(lines)


def _format_response(response: GoogleTrendsResponse) -> str:
    sections: list[str] = [
        f'# Google Trends: "{response.query}" ({response.date})',
        "",
    ]

    if response.interest_over_time:
        sections.append(_format_interest_over_time(response.interest_over_time))
        sections.append("")

    if response.related_topics:
        sections.append(_format_related_topics(response.related_topics))
        sections.append("")

    if response.related_queries:
        sections.append(_format_related_queries(response.related_queries))
        sections.append("")

    if (
        not response.interest_over_time
        and not response.related_topics
        and not response.related_queries
    ):
        sections.append("No trend data found for this keyword.")

    return "\n".join(sections)


@tool
async def google_trends(
    keyword: str,
    timeframe: str = "today 3-m",
) -> str:
    """Look up Google Trends data for a keyword or product.

    Returns search interest over time and related rising queries.
    Use this to understand market demand, seasonal patterns, and
    emerging trends related to a product or topic.

    Args:
        keyword: The search term to look up (e.g. "iPhone 16 Pro").
        timeframe: Time range — "today 1-m", "today 3-m", "today 12-m", "today 5-y".

    Returns:
        Formatted trend data including interest over time and related queries.
    """
    service = get_google_trends_service()
    response: GoogleTrendsResponse = service.search_trend(query=keyword, date=timeframe)
    return _format_response(response)
