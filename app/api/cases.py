from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.database import get_db
from backend.app.schemas import (
    CaseCreate, CaseResponse, GraphDataResponse, TimelineEvent, EvidenceItem,
    InvestigationReportResponse, CaseLeadsResponse, MatricesResponse,
    ExposureResponse, CashoutForecastResponse
)
from backend.app.services.case_service import case_service
from backend.app.services.report_service import report_service

router = APIRouter(prefix="/cases", tags=["Investigation Cases"])

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_in: CaseCreate, db = Depends(get_db)):
    """
    Creates a new investigation case, ingests initial transaction data,
    correlates threat intelligence, and commits genesis/audit blocks to TraceChain.
    """
    try:
        return case_service.create_and_ingest_case(case_in, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create case: {str(e)}"
        )

@router.get("", response_model=List[CaseResponse])
def list_cases(db = Depends(get_db)):
    """Lists all stored investigation cases."""
    return case_service.list_cases(db)

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db = Depends(get_db)):
    """Retrieves metadata and status for a specific case."""
    case = case_service.get_case(case_id, db)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found."
        )
    return case

@router.post("/{case_id}/analyze")
def analyze_case(case_id: str, db = Depends(get_db)):
    """
    Executes NetworkX graph forensics, temporal burst calculation,
    fan-out/fan-in detection, peeling chain recognition, and investigation lead ranking.
    Mines a forensic audit block into TraceChain upon completion.
    """
    try:
        return case_service.analyze_case(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failure: {str(e)}")

@router.get("/{case_id}/graph", response_model=GraphDataResponse)
def get_case_graph(case_id: str, db = Depends(get_db)):
    """Retrieves directed transaction graph nodes, edges, and cluster assignments."""
    try:
        return case_service.get_case_graph(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{case_id}/evidence", response_model=List[EvidenceItem])
def get_case_evidence(case_id: str, db = Depends(get_db)):
    """Retrieves correlated threat intelligence evidence records with source URLs and provenance."""
    return case_service.get_case_evidence(case_id, db)

@router.get("/{case_id}/timeline", response_model=List[TimelineEvent])
def get_case_timeline(case_id: str, db = Depends(get_db)):
    """Retrieves chronological transaction event sequence with forensic anomaly flags."""
    try:
        return case_service.get_case_timeline(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{case_id}/report", response_model=InvestigationReportResponse)
def get_case_report(case_id: str, db = Depends(get_db)):
    """
    Generates a full, cryptographically verified forensic investigation report in JSON format.
    Includes executive summary, methodology, network separation guarantee, ranked leads,
    timeline, TraceChain audit log, and ML assessments.
    """
    try:
        return report_service.generate_report(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{case_id}/leads", response_model=CaseLeadsResponse)
def get_case_leads(case_id: str, db = Depends(get_db)):
    """Retrieves ranked suspect leads and forensic reason codes for an investigation case."""
    try:
        return case_service.get_case_leads(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{case_id}/matrices", response_model=MatricesResponse)
def get_case_matrices(case_id: str, db = Depends(get_db)):
    """Computes wallet-to-wallet transfer flow matrix, temporal activity matrix, and structural graph tensor features."""
    try:
        return case_service.get_case_matrices(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{case_id}/exposure", response_model=ExposureResponse)
def get_case_exposure(case_id: str, db = Depends(get_db)):
    """Computes observed source outflow, candidate exit gateways, and non-cumulative path summaries."""
    try:
        return case_service.get_case_exposure(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{case_id}/cashout-forecast", response_model=CashoutForecastResponse)
def get_case_cashout_forecast(case_id: str, db = Depends(get_db)):
    """Computes probabilistic cashout liquidation timelines and routing likelihoods based on temporal burst patterns."""
    try:
        return case_service.get_case_cashout_forecast(case_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

