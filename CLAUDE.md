# DodakTalk - AI Healthcare Chatbot

## Project Overview
- **Level**: Dynamic (PDCA applied to existing FastAPI backend)
- **Stack**: Python 3.14 / FastAPI / Tortoise ORM / MySQL / OpenAI
- **Name**: DodakTalk (도닥톡)

## Architecture
- Backend: FastAPI + Tortoise ORM (async)
- AI Engine: OpenAI GPT-4o-mini (AsyncOpenAI)
- Auth: Kakao OAuth
- DB: MySQL (asyncmy)
- Migration: Aerich

## Key Paths
- API Routers: `app/apis/v1/`
- DTOs: `app/dtos/`
- Models: `app/models/`
- AI Engine: `ai_worker/tasks/`
- DB Config: `app/db/databases.py`
- Env: `envs/.local.env`

## Coding Conventions
- Async/await for all I/O operations
- Pydantic v2 for DTOs (BaseModel, Field)
- Tortoise ORM models in `app/models/`
- Router prefix pattern: `APIRouter(prefix="/resource", tags=["resource"])`
- Environment variables via `python-dotenv` (load before imports in main.py)

## PDCA Documents
- `docs/00-pm/` - PM analysis, PRD
- `docs/01-plan/` - Feature plans
- `docs/02-design/` - Design documents (data model, API spec)
- `docs/03-analysis/` - Gap analysis
- `docs/04-report/` - Completion reports

## Current Features
- Kakao OAuth login/signup
- User management (me, update)
- AI Healthcare Chatbot (`/api/v1/chat/ask`)
  - Crisis keyword detection (Direct/Indirect/Substance)
  - OpenAI GPT-4o-mini integration
  - ChatLog DB persistence

## Pending Features
- System persona (friendly pharmacist + disclaimer)
- KFDA (e약은요) API integration
- RAG (Vector DB for medical guidelines)
- LLM output safety check
- Real user_id linking (Kakao auth)
