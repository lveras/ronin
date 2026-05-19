# -*- coding: utf-8 -*-
"""Motor de valoração ponderada (Valuation Engine) para precificação de Axies."""

from core.database import MarketDatabase
from core.decoder import AxieDecoder

# Configuração de preços base em USD (caso não haja dados locais suficientes)
BASE_FLOOR_USD = 0.55

# Valores adicionais por raridades colecionáveis base (USD)
COLLECTIBLE_BASE_BONUS = {
    "Origin": 50.0,
    "Mystic (1 part)": 150.0,
    "Mystic (2 parts)": 800.0,
    "Mystic (3 parts)": 3000.0,
    "Shiny": 20.0,
    "Japanese": 10.0,
    "Christmas": 15.0
}

# Custo estimado de evolução/evolução on-chain por parte (USD)
UPGRADED_PART_VALUATION = 5.00  # Pondera o custo de mementos e taxas de ascensão
LEVEL_XP_VALUATION_COEFF = 0.10  # Adiciona $0.10 por nível de experiência do Axie

class AxieValuationEngine:
    """Motor de cálculo de valor sólido de mercado (Fair Value) para arbitragem."""

    def __init__(self, db: MarketDatabase = None):
        self.db = db or MarketDatabase()

    def get_parts_synergy_score(self, parts_list: list) -> float:
        """Calcula o score acumulado de sinergia com base nas partes que pertencem ao Meta."""
        total_score = 0.0
        for part_id in parts_list:
            # Consulta o score individual da peça no banco SQLite
            score = self.db.get_meta_part_score(part_id)
            total_score += score
        return total_score

    def evaluate_axie(self, axie_data: dict) -> dict:
        """Avalia de forma ponderada o valor sólido de mercado de um Axie.

        Entrada: dicionário do Axie retornado pela API GraphQL (incluindo parts, title, level, order, etc.)
        Retorno: dicionário com o preço de mercado estimado, bônus aplicados e recomendação.
        """
        parts = axie_data.get("parts", [])
        title = axie_data.get("title", "")
        level = int(axie_data.get("battleInfo", {}).get("level", 1) or 1)
        
        # 1. Base Floor Price
        estimated_value = BASE_FLOOR_USD
        breakdown = {"base_floor": BASE_FLOOR_USD}

        # 2. Raridades Colecionáveis
        rarity = AxieDecoder.decode_axie_rarity(title, parts)
        collectible_type = rarity["collectible_type"]
        
        if rarity["is_collectible"] and collectible_type in COLLECTIBLE_BASE_BONUS:
            bonus = COLLECTIBLE_BASE_BONUS[collectible_type]
            estimated_value += bonus
            breakdown[f"collectible_{collectible_type}"] = bonus

        # 3. Sinergia de Partes Meta e Lógica de Partes Trocáveis (Requisito 5)
        # Identificamos as partes que não são fixas/colecionáveis ("partes trocáveis/livres")
        part_ids = [p.get("id", "") for p in parts]
        non_collectible_parts = []
        for p in parts:
            special_genes = p.get("specialGenes") or ""
            # Se a peça não tiver genes especiais (ex: não for mystic ou japan), é uma parte trocável/livre
            if not special_genes:
                non_collectible_parts.append(p.get("id", ""))

        # Soma a sinergia das partes trocáveis/livres
        synergy_score = self.get_parts_synergy_score(non_collectible_parts)
        
        if synergy_score > 0:
            # Se for um colecionável (ex: Mystic ou Origin), partes livres que se encaixam no meta
            # aumentam exponencialmente o seu valor de uso/combate
            if rarity["is_collectible"]:
                # Multiplicador premium de sinergia colecionável meta
                synergy_bonus = estimated_value * (0.15 * synergy_score)
                estimated_value += synergy_bonus
                breakdown["collectible_meta_synergy"] = round(synergy_bonus, 2)
            else:
                # Axie comum com partes meta ganha valor de utilidade de combate
                synergy_bonus = BASE_FLOOR_USD * (0.8 * synergy_score)
                estimated_value += synergy_bonus
                breakdown["meta_parts_utility"] = round(synergy_bonus, 2)

        # 4. Evolução e Nível do Axie (Requisito 6)
        evolved = AxieDecoder.parse_evolved_parts(parts)
        upgraded_count = evolved["upgraded_count"]
        
        if upgraded_count > 0:
            upgrade_bonus = upgraded_count * UPGRADED_PART_VALUATION
            estimated_value += upgrade_bonus
            breakdown["upgraded_parts_bonus"] = upgrade_bonus

        if level > 1:
            level_bonus = level * LEVEL_XP_VALUATION_COEFF
            estimated_value += level_bonus
            breakdown["axie_level_bonus"] = round(level_bonus, 2)

        return {
            "axie_id": str(axie_data.get("id")),
            "estimated_value_usd": round(estimated_value, 2),
            "breakdown": breakdown,
            "is_collectible": rarity["is_collectible"],
            "collectible_type": collectible_type,
            "upgraded_parts_count": upgraded_count,
            "level": level
        }
