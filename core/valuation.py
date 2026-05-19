# -*- coding: utf-8 -*-
"""Motor de valoração ponderada (Valuation Engine) para precificação de Axies com coerência de arquétipo."""

from core.database import MarketDatabase
from core.decoder import AxieDecoder

# Configuração de preços base em USD
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

# Custo de ascensão on-chain (apenas para partes taticamente úteis no Meta)
UPGRADED_PART_VALUATION = 5.00  
LEVEL_XP_VALUATION_COEFF = 0.10  # Adiciona $0.10 por nível de experiência do Axie

class AxieValuationEngine:
    """Motor de cálculo de valor sólido de mercado (Fair Value) para arbitragem."""

    def __init__(self, db: MarketDatabase = None):
        self.db = db or MarketDatabase()

    def get_tactical_synergy(self, parts: list) -> tuple:
        """Agrupa e calcula a sinergia com base no arquétipo dominante (Coerência Tática).

        Ignora misturas 'quimera' de peças que não pertencem ao mesmo arquétipo/tática.
        Retorna: (dominant_archetype, synergy_score, list_of_dominant_part_ids)
        """
        cursor = self.db.conn.cursor()
        archetype_groups = {}

        for p in parts:
            part_id = p.get("id", "").lower()
            special_genes = p.get("specialGenes") or ""
            # Peças com genes especiais (ex: mystic) não são livres/trocáveis da mesma forma
            if special_genes:
                continue

            cursor.execute("SELECT sinergy_score, archetype FROM meta_parts WHERE part_id = ?", (part_id,))
            row = cursor.fetchone()
            if row:
                score, archetype = row[0], row[1] or "General Meta"
                if archetype not in archetype_groups:
                    archetype_groups[archetype] = {"score": 0.0, "parts": []}
                archetype_groups[archetype]["score"] += score
                archetype_groups[archetype]["parts"].append(part_id)

        if not archetype_groups:
            return None, 0.0, []

        # Identifica o arquétipo dominante (aquele com maior pontuação acumulada)
        dominant_arch = max(archetype_groups, key=lambda k: archetype_groups[k]["score"])
        dominant_data = archetype_groups[dominant_arch]
        
        # Filtro de Coerência: se houver apenas 1 peça meta isolada do arquétipo, 
        # ela não possui sinergia tática real com o resto do deck (não é um combo)
        if len(dominant_data["parts"]) < 2:
            return dominant_arch, dominant_data["score"] * 0.5, dominant_data["parts"]

        return dominant_arch, dominant_data["score"], dominant_data["parts"]

    def evaluate_axie(self, axie_data: dict) -> dict:
        """Avalia o valor de mercado ponderado baseando-se estritamente na coerência de arquétipos."""
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

        # 3. Sinergia Meta Coerente por Arquétipo (Requisito 5 refinado)
        dominant_arch, synergy_score, dominant_parts = self.get_tactical_synergy(parts)
        
        if synergy_score > 0:
            if rarity["is_collectible"]:
                # Multiplicador premium de sinergia colecionável meta
                synergy_bonus = estimated_value * (0.15 * synergy_score)
                estimated_value += synergy_bonus
                breakdown[f"collectible_{dominant_arch.replace(' ', '_').lower()}_synergy"] = round(synergy_bonus, 2)
            else:
                # Axie comum com partes meta coerentes ganha valor de utilidade
                synergy_bonus = BASE_FLOOR_USD * (0.8 * synergy_score)
                estimated_value += synergy_bonus
                breakdown[f"meta_utility_{dominant_arch.replace(' ', '_').lower()}"] = round(synergy_bonus, 2)

        # 4. Evoluções Condicionais no Meta (Requisito 6 refinado)
        # Uma parte evoluída (Stage 2) SÓ adiciona valor se for parte do combo dominante Meta!
        evolved = AxieDecoder.parse_evolved_parts(parts)
        upgraded_count_meta = 0
        
        for part_id in evolved["upgraded_part_ids"]:
            if part_id.lower() in dominant_parts:
                upgraded_count_meta += 1

        if upgraded_count_meta > 0:
            upgrade_bonus = upgraded_count_meta * UPGRADED_PART_VALUATION
            estimated_value += upgrade_bonus
            breakdown["upgraded_meta_parts_bonus"] = upgrade_bonus

        # Bônus de XP do Nível (mantido para utilidade off-chain ascendida)
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
            "upgraded_parts_count": upgraded_count_meta,  # Apenas conta partes evoluídas que são META úteis!
            "level": level,
            "dominant_archetype": dominant_arch or "Nenhum"
        }
