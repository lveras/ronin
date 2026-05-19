# -*- coding: utf-8 -*-
"""Motor de valoração estatística (ML Inference Engine) baseado em Machine Learning."""

import os
import pickle
import pandas as pd
from core.database import MarketDatabase
from core.decoder import AxieDecoder
from core.valuation import AxieValuationEngine

MODEL_PATH = os.path.join("data", "price_model.pkl")

class AxieMLValuationEngine:
    """Motor de precificação estatística rápida baseado no modelo de ML treinado."""

    def __init__(self, db: MarketDatabase = None):
        self.db = db or MarketDatabase()
        self.deterministic_engine = AxieValuationEngine(self.db)
        self.model = self._load_model()

    def _load_model(self):
        """Carrega o modelo RandomForest salvo. Retorna None se falhar."""
        if not os.path.exists(MODEL_PATH):
            return None
        try:
            with open(MODEL_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"[ML-Valuation] Erro ao carregar arquivo de modelo pkl: {e}")
            return None

    def evaluate_axie(self, axie_data: dict) -> dict:
        """Estima o valor de mercado (Fair Value) do Axie usando Machine Learning com Fallback."""
        # Se o modelo não estiver carregado, recorre automaticamente ao motor determinístico
        if self.model is None:
            return self.deterministic_engine.evaluate_axie(axie_data)

        try:
            parts = axie_data.get("parts", [])
            title = axie_data.get("title", "")
            level = int(axie_data.get("battleInfo", {}).get("level", 1) or 1)
            
            # 1. Feature Engineering
            rarity = AxieDecoder.decode_axie_rarity(title, parts)
            evolved = AxieDecoder.parse_evolved_parts(parts)
            
            # Calcula o score meta total
            meta_synergy = 0.0
            for p in parts:
                special_genes = p.get("specialGenes") or ""
                # Apenas peças trocáveis/livres entram no score meta para ponderação correta
                if not special_genes:
                    meta_synergy += self.db.get_meta_part_score(p.get("id", ""))

            # Cria o DataFrame de entrada com as mesmas colunas usadas no treino
            features = pd.DataFrame([{
                "is_collectible": 1 if rarity["is_collectible"] else 0,
                "axie_level": level,
                "upgraded_parts_count": evolved["upgraded_count"],
                "meta_synergy": meta_synergy
            }])

            # 2. Faz a previsão
            predicted_price_usd = float(self.model.predict(features)[0])

            return {
                "axie_id": str(axie_data.get("id")),
                "estimated_value_usd": round(max(0.2, predicted_price_usd), 2),
                "breakdown": {
                    "ml_model_prediction": round(predicted_price_usd, 2),
                    "meta_synergy": round(meta_synergy, 2)
                },
                "is_collectible": rarity["is_collectible"],
                "collectible_type": rarity["collectible_type"],
                "upgraded_parts_count": evolved["upgraded_count"],
                "level": level,
                "engine": "Machine Learning (RandomForest)"
            }

        except Exception as e:
            print(f"[ML-Valuation] Falha na inferência ML: {e}. Usando Fallback Determinístico...")
            return self.deterministic_engine.evaluate_axie(axie_data)
