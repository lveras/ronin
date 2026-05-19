# -*- coding: utf-8 -*-
"""Mapeador de raridades, partes colecionáveis e evoluções de Axies."""

COLLECTIBLE_TRAITS = {
    "mystic": "Mystic",
    "shiny": "Shiny",
    "japan": "Japanese",
    "christmas": "Christmas",
    "origin": "Origin",
    "bionic": "Bionic",
    "meo": "MeoCorp",
    "meo2": "MeoCorp II"
}

class AxieDecoder:
    """Decodificador de metadados e partes retornadas pela API GraphQL."""

    @staticmethod
    def decode_axie_rarity(title: str, parts: list) -> dict:
        """Determina as qualidades colecionáveis do Axie com base no título e partes.

        Retorna um dicionário detalhado com o tipo de colecionável e a contagem de traits.
        """
        rarity_info = {
            "is_collectible": False,
            "collectible_type": None,
            "mystic_count": 0,
            "shiny_count": 0,
            "japan_count": 0,
            "christmas_count": 0,
            "is_origin": False
        }

        # Verifica pelo título do Axie (ex: Origin)
        title_lower = (title or "").lower()
        if "origin" in title_lower:
            rarity_info["is_collectible"] = True
            rarity_info["is_origin"] = True
            rarity_info["collectible_type"] = "Origin"

        # Conta traits nas partes corporais
        for part in parts:
            special_genes = part.get("specialGenes") or ""
            special_genes_lower = special_genes.lower()

            if "mystic" in special_genes_lower:
                rarity_info["mystic_count"] += 1
            if "shiny" in special_genes_lower:
                rarity_info["shiny_count"] += 1
            if "japan" in special_genes_lower:
                rarity_info["japan_count"] += 1
            if "christmas" in special_genes_lower:
                rarity_info["christmas_count"] += 1

        # Classifica com base nas contagens
        if rarity_info["mystic_count"] > 0:
            rarity_info["is_collectible"] = True
            rarity_info["collectible_type"] = f"Mystic ({rarity_info['mystic_count']} parts)"
        elif rarity_info["shiny_count"] > 0:
            rarity_info["is_collectible"] = True
            rarity_info["collectible_type"] = "Shiny"
        elif rarity_info["japan_count"] > 0:
            rarity_info["is_collectible"] = True
            rarity_info["collectible_type"] = "Japanese"
        elif rarity_info["christmas_count"] > 0:
            rarity_info["is_collectible"] = True
            rarity_info["collectible_type"] = "Christmas"

        return rarity_info

    @staticmethod
    def parse_evolved_parts(parts: list) -> dict:
        """Mapeia partes evoluídas (upadas / nível 2) baseadas no campo `stage`.

        Retorna a contagem total de partes evoluídas e a lista dos IDs dessas partes.
        """
        evolved_info = {
            "upgraded_count": 0,
            "upgraded_part_ids": []
        }

        for part in parts:
            # stage = 2 indica que a parte foi evoluída on-chain
            stage = part.get("stage", 1)
            if stage > 1:
                evolved_info["upgraded_count"] += 1
                evolved_info["upgraded_part_ids"].append(part.get("id"))

        return evolved_info
