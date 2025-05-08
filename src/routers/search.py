from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database import get_db
from src.models.resume import Resume as ResumeModel
from src.schemas.resume import Resume
from src.services.hybrid_search_service import HybridSearchService
from src.dependencies.security import get_current_user   
from src.models.user import User

router = APIRouter(
    prefix="/search",
    tags=["Search"],
)

class SearchResult(BaseModel):
    id: int
    filename: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    skills: Optional[List[str]] = None
    search_score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int

@router.get("/resumes", response_model=SearchResponse)
async def search_resumes(
    query: str = Query(..., description="Search query string"),
    folder_id: Optional[int] = Query(None, description="Filter by folder ID"),
    limit: int = Query(10, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search resumes using hybrid search (keywords + semantic).
    """
    search_service = HybridSearchService()
    results = search_service.search_resumes(db, query, current_user.id, folder_id, limit)

    # Format the results
    search_results = [
        SearchResult(
            id=resume.id,
            filename=resume.filename,
            candidate_name=resume.candidate_name,
            candidate_email=resume.candidate_email,
            skills=resume.skills if isinstance(resume.skills, list) else [],
            search_score=getattr(resume, "search_score", 0.0),
        )
        for resume, _ in results
    ]

    return SearchResponse(
        results=search_results,
        total=len(search_results),
    )

