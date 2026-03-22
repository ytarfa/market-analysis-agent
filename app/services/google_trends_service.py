from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.config import settings
from app.services.serpapi_service import SerpapiService
from app.utils.cache import FileCache

ENGINE = "google_trends"

TRENDS_TIMESERIES_RESTRICTOR = [
    "interest_over_time.timeline_data[].{date, timestamp, values}",
    "interest_over_time.averages",
]

TRENDS_RELATED_TOPICS_RESTRICTOR = [
    "related_topics.rising[].{topic, value, extracted_value, link}",
    "related_topics.top[].{topic, value, extracted_value, link}",
]

TRENDS_RELATED_QUERIES_RESTRICTOR = [
    "related_queries.rising[].{query, value, extracted_value, link}",
    "related_queries.top[].{query, value, extracted_value, link}",
]


class TimelineValue(BaseModel):
    query: str = ""
    value: str = "0"
    extracted_value: int = 0


class TimelineDataPoint(BaseModel):
    date: str = ""
    timestamp: str = ""
    values: list[TimelineValue] = Field(default_factory=list)


class InterestOverTime(BaseModel):
    timeline_data: list[TimelineDataPoint] = Field(default_factory=list)
    averages: list[int] = Field(default_factory=list)


class TopicInfo(BaseModel):
    value: str = ""
    title: str = ""
    type: str = ""


class RelatedTopic(BaseModel):
    topic: TopicInfo = Field(default_factory=TopicInfo)
    value: str = ""
    extracted_value: int = 0
    link: str = ""


class RelatedTopics(BaseModel):
    rising: list[RelatedTopic] = Field(default_factory=list)
    top: list[RelatedTopic] = Field(default_factory=list)


class RelatedQuery(BaseModel):
    query: str = ""
    value: str = ""
    extracted_value: int = 0
    link: str = ""


class RelatedQueries(BaseModel):
    rising: list[RelatedQuery] = Field(default_factory=list)
    top: list[RelatedQuery] = Field(default_factory=list)


class GoogleTrendsResponse(BaseModel):
    query: str
    date: str
    interest_over_time: InterestOverTime | None = None
    related_topics: RelatedTopics | None = None
    related_queries: RelatedQueries | None = None

    @model_validator(mode="before")
    @classmethod
    def flatten(cls, data: dict[str, object]) -> dict[str, object]:
        raw_timeseries: dict[str, Any] | None = data.get("_timeseries")  # type: ignore
        raw_topics: dict[str, Any] | None = data.get("_related_topics")  # type: ignore
        raw_queries: dict[str, Any] | None = data.get("_related_queries")  # type: ignore

        return {
            "query": data.get("query"),
            "date": data.get("date"),
            "interest_over_time": (
                raw_timeseries.get("interest_over_time") if raw_timeseries else None
            ),
            "related_topics": (
                raw_topics.get("related_topics") if raw_topics else None
            ),
            "related_queries": (
                raw_queries.get("related_queries") if raw_queries else None
            ),
        }


class GoogleTrendsService(ABC):
    @abstractmethod
    def search_trend(self, query: str, date: str) -> GoogleTrendsResponse:
        pass


class SerpapiGoogleTrendsService(GoogleTrendsService, SerpapiService):
    def __init__(self) -> None:
        super().__init__()
        self._cache: FileCache = FileCache(namespace="google_trends")

    def search_trend(self, query: str, date: str) -> GoogleTrendsResponse:
        cache_key: str = f"{query}::{date}"
        cached: dict[str, Any] | None = self._cache.read(cache_key)
        if cached is not None:
            return GoogleTrendsResponse.model_validate(cached)

        timeseries_result: dict[str, Any] = dict(
            self.search(
                engine=ENGINE,
                q=query,
                date=date,
                data_type="TIMESERIES",
                json_restrictor=",".join(TRENDS_TIMESERIES_RESTRICTOR),
            )
        )

        related_topics_result: dict[str, Any] = dict(
            self.search(
                engine=ENGINE,
                q=query,
                date=date,
                data_type="RELATED_TOPICS",
                json_restrictor=",".join(TRENDS_RELATED_TOPICS_RESTRICTOR),
            )
        )

        related_queries_result: dict[str, Any] = dict(
            self.search(
                engine=ENGINE,
                q=query,
                date=date,
                data_type="RELATED_QUERIES",
                json_restrictor=",".join(TRENDS_RELATED_QUERIES_RESTRICTOR),
            )
        )

        raw: dict[str, Any] = {
            "query": query,
            "date": date,
            "_timeseries": dict(timeseries_result),
            "_related_topics": dict(related_topics_result),
            "_related_queries": dict(related_queries_result),
        }

        self._cache.write(cache_key, raw)
        return GoogleTrendsResponse.model_validate(raw)


class MockGoogleTrendsService(GoogleTrendsService):
    def __init__(self) -> None:
        self._cache: FileCache = FileCache(namespace="google_trends")

    def search_trend(self, query: str, date: str) -> GoogleTrendsResponse:
        cache_key: str = f"{query}::{date}"
        cached: dict[str, Any] | None = self._cache.read(cache_key)
        if cached is None:
            raise Exception("Google Trends cache wasn't hit...")
        return GoogleTrendsResponse.model_validate(cached)


def get_google_trends_service() -> GoogleTrendsService:
    if settings.serpapi_api_key:
        return SerpapiGoogleTrendsService()
    return MockGoogleTrendsService()
