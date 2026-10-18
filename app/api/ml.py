from fastapi import APIRouter, HTTPException, status
from backend.app.schemas import (
    MLStatusResponse, MLPredictRequest, MLPredictResponse, MLTrainRequest, MLTrainResponse
)
from backend.app.ml.predict import inference_service
from backend.app.ml.train import train_and_evaluate

router = APIRouter(prefix="/ml", tags=["Machine Learning"])

@router.get("/status", response_model=MLStatusResponse)
def get_ml_status():
    """
    Returns active ML model status, algorithm, version, features count,
    chronological validation metrics, and analytical limitations.
    """
    status_data = inference_service.get_status()
    return MLStatusResponse(**status_data)

@router.post("/predict", response_model=MLPredictResponse)
def predict_transaction(req: MLPredictRequest):
    """
    Evaluates a transaction feature vector against the active forensic classifier.
    Returns predicted classification (illicit/licit), risk score, and confidence explanation.
    """
    try:
        return inference_service.predict(
            features=req.features,
            tx_id=req.tx_id or "tx_custom",
            network=req.network
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inference error: {str(e)}")

@router.post("/train", response_model=MLTrainResponse)
def train_model_endpoint(req: MLTrainRequest):
    """
    Triggers bounded, reproducible model training and evaluation.
    Compares baseline models against tree-based ensembles on chronological partitions.
    """
    try:
        res = train_and_evaluate(
            dataset_name=req.dataset_name,
            max_rows=min(req.max_rows or 20000, 46564)
        )
        return MLTrainResponse(
            status="completed",
            model_name=res["champion_model"],
            algorithm=res["champion_model"],
            version="v1.0.0",
            train_rows=29894,
            test_rows=16670,
            metrics=res["champion_metrics"],
            artifacts_saved=[res["artifact_path"]]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Training failed: {str(e)}")
