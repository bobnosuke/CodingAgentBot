import json
import os
from typing import List, Dict

class AIModelManager:
    def __init__(self, config_path: str = "config/models.json"):
        self.config_path = config_path
        self.models = self._load_models()
        self.model_status = {}  # {model_name: {"status": "active", "retry_after": 0, "error_count": 0, "success_time": None, "usage_count": 0}}

    def _load_models(self) -> Dict[str, List[str]]:
        if not os.path.exists(self.config_path):
            # Fallback if file not found
            return {
                "high_quality": ["qwen/qwen3-coder:free"],
                "reasoning": ["meta-llama/llama-3.3-70b-instruct:free"],
                "standard": ["qwen/qwen3-32b:free"],
                "fast": ["meta-llama/llama-3.1-8b-instruct:free"]
            }
        with open(self.config_path, "r") as f:
            return json.load(f)

    def get_models_by_quality(self, quality: str) -> List[str]:
        """
        Returns a list of models for the given quality level.
        quality: "fast", "standard", "high_quality"
        """
        if quality == "high_quality":
            # Combine high quality coding models and reasoning models
            return self.models.get("high_quality", []) + self.models.get("reasoning", [])
        elif quality == "standard":
            return self.models.get("standard", [])
        elif quality == "fast":
            return self.models.get("fast", [])
        return self.models.get("standard", [])

    def get_next_available_model(self, quality: str, excluded_models: List[str] = None) -> str:
        models = self.get_models_by_quality(quality)
        if excluded_models:
            models = [m for m in models if m not in excluded_models]
        
        for model in models:
            status = self.model_status.get(model, {"status": "active"})
            if status["status"] == "active":
                return model
        
        # If all models are in cooldown, return the first one (or handle error)
        return models[0] if models else "openrouter/auto"

    def update_model_status(self, model: str, status: str, retry_after: int = 0):
        import datetime
        if model not in self.model_status:
            self.model_status[model] = {"status": "active", "retry_after": 0, "error_count": 0, "success_time": None, "usage_count": 0}
        
        self.model_status[model]["status"] = status
        self.model_status[model]["retry_after"] = retry_after
        if status == "cooldown":
            self.model_status[model]["error_count"] += 1
        elif status == "active":
            self.model_status[model]["error_count"] = 0
            self.model_status[model]["success_time"] = datetime.datetime.now().isoformat()
            self.model_status[model]["usage_count"] += 1

model_manager = AIModelManager()
