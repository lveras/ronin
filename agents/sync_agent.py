# -*- coding: utf-8 -*-
"""Agente de Sincronização Incremental (Data Ingestor Agent)."""

import time
from core.database import MarketDatabase
from core.decoder import AxieDecoder
from api.marketplace_graphql import MarketplaceGraphQL

# Lista de peças meta clássicas/atuais com seus scores de utilidade/sinergia
DEFAULT_META_PARTS = [
    # Chifres (Horns)
    ("horn-cactus", 0.8, "Aggro Plant"),
    ("horn-pliers", 0.7, "Midrange Bug"),
    ("horn-bamboo-shoot", 0.75, "Defense Reptile"),
    ("horn-scaly-spoon", 0.9, "Sustain Reptile"),
    ("horn-dual-blade", 0.85, "Aggro Beast"),
    # Bocas (Mouths)
    ("mouth-tiny-fan", 0.85, "Aggro Aquatic"),
    ("mouth-silence-whisper", 0.8, "Sustain Plant"),
    ("mouth-kotaro", 0.9, "Ramp Beast / Bug"),
    ("mouth-goda", 0.75, "Disrupt Beast"),
    ("mouth-nut-cracker", 0.8, "Nut Beast"),
    # Costas (Backs)
    ("back-goldfish", 0.85, "Aggro Aquatic"),
    ("back-sponge", 0.8, "Sustain Aquatic"),
    ("back-garish-worm", 0.9, "Debuff Bug / Reptile"),
    ("back-ronin", 0.85, "Burst Beast"),
    ("back-bidens", 0.95, "Sustain Plant / Reptile"),
    # Caudas (Tails)
    ("tail-nimo", 0.95, "Energy Ramp Aquatic"),
    ("tail-koi", 0.8, "Finisher Aquatic"),
    ("tail-thorny-caterpillar", 0.9, "Debuff Bug"),
    ("tail-hot-butt", 0.75, "Disrupt Plant"),
    ("tail-cattail", 0.8, "Cycle Beast / Plant")
]

class SyncAgent:
    """Agente responsável por alimentar e manter a base histórica incremental."""

    def __init__(self):
        self.db = MarketDatabase()
        self.api = MarketplaceGraphQL()
        self._prepopulate_meta_parts()

    def _prepopulate_meta_parts(self):
        """Popula a tabela de meta_parts com valores padrão se estiver vazia."""
        for part_id, score, archetype in DEFAULT_META_PARTS:
            self.db.add_meta_part(part_id, score, archetype)
        print(f"[SyncAgent] {len(DEFAULT_META_PARTS)} partes Meta padrão carregadas/atualizadas.")

    def sync_recently_sold(self, limit: int = 50) -> int:
        """Sincroniza as vendas concludas recentemente de forma incremental.

        Retorna a quantidade de novos eventos salvos.
        """
        last_ts = self.db.get_last_processed_timestamp(key="sales")
        print(f"[SyncAgent] Iniciando sincronização incremental de vendas. ltimo timestamp: {last_ts}")

        # Busca recentemente vendidos (ordenados por Latest por padrão)
        data = self.api.get_recently_sold(size=limit)
        results = data.get("results", [])

        if not results:
            print("[SyncAgent] Nenhuma nova venda encontrada no marketplace.")
            return 0

        new_events_count = 0
        max_ts = last_ts

        for axie in results:
            # Obtém informações de transferência / venda
            transfer_history = axie.get("transferHistory", {})
            history_results = transfer_history.get("results", [])
            
            if not history_results:
                continue
                
            latest_sale = history_results[0]
            timestamp = int(latest_sale.get("timestamp", 0))
            tx_hash = latest_sale.get("txHash", "")

            # Pula se o timestamp for menor ou igual ao já processado (Regra Incremental)
            if timestamp <= last_ts:
                continue

            # Atualiza o maior timestamp visto nesta rodada
            if timestamp > max_ts:
                max_ts = timestamp

            # Decodifica raridades e evoluções
            parts = axie.get("parts", [])
            title = axie.get("title", "")
            rarity = AxieDecoder.decode_axie_rarity(title, parts)
            evolved = AxieDecoder.parse_evolved_parts(parts)

            # Salva o evento no banco local
            event_id = f"sale_{tx_hash}"
            self.db.save_historical_event(
                event_id=event_id,
                axie_id=str(axie.get("id")),
                axie_class=axie.get("class") or "Unknown",
                price_wei=latest_sale.get("withPrice", "0"),
                price_usd=float(latest_sale.get("withPriceUsd", 0.0)),
                is_collectible=rarity["is_collectible"],
                collectible_type=rarity["collectible_type"],
                level=int(axie.get("battleInfo", {}).get("level", 1) or 1),
                upgraded_count=evolved["upgraded_count"],
                parts=[p.get("id") for p in parts],
                event_type="SALE",
                timestamp=timestamp
            )
            new_events_count += 1

        # Salva o progresso
        if max_ts > last_ts:
            self.db.update_last_processed_timestamp(max_ts, key="sales")
            print(f"[SyncAgent] Progresso de vendas salvo. Novo timestamp: {max_ts}")

        return new_events_count

    def sync_active_listings(self, limit: int = 50) -> int:
        """Sincroniza listagens ativas no marketplace.

        Retorna a quantidade de novas listagens processadas.
        """
        last_ts = self.db.get_last_processed_timestamp(key="listings")
        print(f"[SyncAgent] Sincronizando listagens ativas a partir de: {last_ts}")

        # Busca axies listados (ordenados por PriceAsc para pegar os mais baratos/floor)
        data = self.api.get_axies_for_sale(size=limit, sort="Latest")
        results = data.get("results", [])

        if not results:
            print("[SyncAgent] Nenhuma listagem ativa encontrada.")
            return 0

        new_listings_count = 0
        max_ts = last_ts

        for axie in results:
            order = axie.get("order") or {}
            # O timestamp da listagem no order não é retornado de forma direta às vezes, 
            # então usamos a expiração ou o tempo atual se não fornecido.
            # Caso a API use expiredAt ou outro timestamp, o capturamos.
            # Como queremos ser incrementais, também podemos usar o ID da ordem ou timestamp.
            timestamp = int(time.time())

            # Decodifica raridades e evoluções
            parts = axie.get("parts", [])
            title = axie.get("title", "")
            rarity = AxieDecoder.decode_axie_rarity(title, parts)
            evolved = AxieDecoder.parse_evolved_parts(parts)

            order_id = order.get("id", f"listing_{axie.get('id')}")
            
            self.db.save_historical_event(
                event_id=order_id,
                axie_id=str(axie.get("id")),
                axie_class=axie.get("class") or "Unknown",
                price_wei=order.get("currentPrice", "0"),
                price_usd=float(order.get("currentPriceUsd", 0.0)),
                is_collectible=rarity["is_collectible"],
                collectible_type=rarity["collectible_type"],
                level=int(axie.get("battleInfo", {}).get("level", 1) or 1),
                upgraded_count=evolved["upgraded_count"],
                parts=[p.get("id") for p in parts],
                event_type="LISTING",
                timestamp=timestamp
            )
            new_listings_count += 1

        return new_listings_count

if __name__ == "__main__":
    agent = SyncAgent()
    vendas = agent.sync_recently_sold(limit=30)
    listagens = agent.sync_active_listings(limit=30)
    print(f"[SyncAgent] Sincronização concluída: +{vendas} vendas registradas, +{listagens} listagens ativas catalogadas.")
