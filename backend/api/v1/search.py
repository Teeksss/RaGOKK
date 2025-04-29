# Last reviewed: 2025-04-29 13:36:58 UTC (User: TeeksssMobil)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum
import time
from datetime import datetime, date, timedelta
import logging

from ...db.session import get_db
from ...auth.jwt import get_current_active_user, get_current_user_optional
from ...services.search_service import SearchService, SearchType, FilterOperator, SortOrder
from ...schemas.search import SearchRequest, SearchResponse, FacetResponse, AggregateFacetRequest

router = APIRouter(
    prefix="/api/search",
    tags=["search"],
    responses={401: {"description": "Unauthorized"}}
)

logger = logging.getLogger(__name__)

class DateRangePreset(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "