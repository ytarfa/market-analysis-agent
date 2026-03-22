# Market Analysis Agent

An agentic market intelligence system for e-commerce. Given a product name or market query (e.g., "iPhone 16 Pro"), it autonomously researches the competitive landscape, pricing, customer sentiment, and market trends, then produces a comprehensive Markdown report with strategic recommendations and embedded charts.

## How It Works

1. **Brief Generation** -- An LLM converts your raw query into a structured research brief with product name, market category, target audience, and research questions.
2. **Research Planning & Execution** -- A coordinator agent decomposes the brief into research topics and spawns independent researcher agents. Each researcher runs a ReAct loop calling tools (web search, Amazon reviews, Google Trends) to collect data.
3. **Report Generation** -- A senior-analyst LLM synthesizes all research into a 2500-3000 word Markdown report covering executive summary, competitive landscape, pricing analysis, customer sentiment, market trends, and strategic recommendations.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker & Docker Compose (optional, for containerized usage)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd market-analysis-agent-moov-ai
```

### 2. Create your environment file

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```
ANTHROPIC_API_KEY=your-anthropic-key
TAVILY_API_KEY=your-tavily-key
SERPAPI_API_KEY=your-serpapi-key
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | API key for Anthropic Claude models (powers all LLM calls) |
| `TAVILY_API_KEY` | **Yes** | API key for Tavily web search |
| `SERPAPI_API_KEY` | No | API key for SerpAPI (Amazon reviews + Google Trends) |

> **Note on SerpAPI:** The `SERPAPI_API_KEY` is optional. However, without it the system falls back to mock services that only return cached data. This means the Amazon reviews and Google Trends sections of the report will be based on stale or placeholder data, which will significantly reduce the quality and accuracy of the final report.

### 3. Install dependencies

```bash
uv sync
```

## Running the Project

### Local

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### Docker

```bash
docker compose up --build
```

## Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Run a Market Analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "iPhone 16 Pro"}'
```

The response contains the research brief, individual research results, and the final Markdown report. Reports are also saved to the `reports/` directory.

## Cost

Running a single market analysis report can cost up to **~$1 USD** in API usage across Anthropic and search API calls. Keep this in mind when running multiple analyses.

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Type check
mypy .
```

## Project Structure

```
app/
├── main.py                  # FastAPI entry point
├── config.py                # Settings and model configuration
├── api/routes.py            # API endpoints
├── agent/                   # LangGraph agent orchestration
│   ├── analysis_pipeline.py # Top-level pipeline: brief -> research -> report
│   ├── coordinator.py       # Research coordinator: plan -> spawn -> evaluate
│   └── researcher.py        # Researcher subgraph: ReAct tool-calling loop
├── schemas/                 # Pydantic models
├── services/                # External API wrappers (SerpAPI, etc.)
├── tools/                   # LangChain tools (web search, reviews, trends)
└── utils/cache.py           # JSON file-based response cache
```
