# -*- coding: utf-8 -*-
"""Camada de persistência em banco de dados SQLite local para rastreamento incremental."""

import os
import sqlite3
import json

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "marketplace.db")

class MarketDatabase:
    """Interface de banco de dados SQLite para o sistema Multi-Agente."""

    def __init__(self):
        # Garante a existência do diretório 'data'
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
        
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Inicializa as tabelas se não existirem."""
        cursor = self.conn.cursor()
        
        # Tabela para controlar o estado da sincronização incremental
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS axie_sync_state (
            key TEXT PRIMARY KEY,
            last_processed_timestamp INTEGER NOT NULL
        )
        """)
        
        # Tabela para vendas e listagens históricas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS axie_historical_events (
            id TEXT PRIMARY KEY, -- id único: 'sale_<txHash>' ou 'listing_<orderId>'
            axie_id TEXT NOT NULL,
            class TEXT NOT NULL,
            price_wei TEXT NOT NULL,
            price_usd REAL NOT NULL,
            is_collectible BOOLEAN DEFAULT 0,
            collectible_type TEXT,
            axie_level INTEGER DEFAULT 1,
            upgraded_parts_count INTEGER DEFAULT 0,
            parts_list TEXT NOT NULL, -- JSON string de array das partes
            event_type TEXT CHECK(event_type IN ('LISTING', 'SALE')),
            timestamp INTEGER NOT NULL
        )
        """)

        # Tabela para definir pesos de peças do meta atual
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta_parts (
            part_id TEXT PRIMARY KEY,
            sinergy_score REAL NOT NULL, -- Grau de força/utilidade no meta (ex: 0.1 a 1.0)
            archetype TEXT
        )
        """)
        
        self.conn.commit()

    def get_last_processed_timestamp(self, key: str = "default") -> int:
        """Obtém o último timestamp processado para sincronização incremental.

        Retorna 0 se nenhuma sincronização prévia tiver ocorrido.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_processed_timestamp FROM axie_sync_state WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["last_processed_timestamp"] if row else 0

    def update_last_processed_timestamp(self, timestamp: int, key: str = "default"):
        """Atualiza o último timestamp processado de forma atômica."""
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO axie_sync_state (key, last_processed_timestamp)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET last_processed_timestamp = excluded.last_processed_timestamp
        """, (key, timestamp))
        self.conn.commit()

    def save_historical_event(self, event_id: str, axie_id: str, axie_class: str, price_wei: str, 
                              price_usd: float, is_collectible: bool, collectible_type: str, 
                              level: int, upgraded_count: int, parts: list, event_type: str, timestamp: int):
        """Salva uma listagem ou venda no banco local."""
        cursor = self.conn.cursor()
        parts_json = json.dumps(parts)
        cursor.execute("""
        INSERT INTO axie_historical_events (
            id, axie_id, class, price_wei, price_usd, is_collectible, 
            collectible_type, axie_level, upgraded_parts_count, parts_list, event_type, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            price_wei = excluded.price_wei,
            price_usd = excluded.price_usd,
            timestamp = excluded.timestamp
        """, (
            event_id, axie_id, axie_class, price_wei, float(price_usd), 
            1 if is_collectible else 0, collectible_type, level, 
            upgraded_count, parts_json, event_type, timestamp
        ))
        self.conn.commit()

    def get_meta_part_score(self, part_id: str) -> float:
        """Busca o score de sinergia de uma parte meta. Retorna 0 se não for meta."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT sinergy_score FROM meta_parts WHERE part_id = ?", (part_id.lower(),))
        row = cursor.fetchone()
        return row["sinergy_score"] if row else 0.0

    def add_meta_part(self, part_id: str, score: float, archetype: str = None):
        """Adiciona ou atualiza uma parte na tabela de partes meta."""
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO meta_parts (part_id, sinergy_score, archetype)
        VALUES (?, ?, ?)
        ON CONFLICT(part_id) DO UPDATE SET
            sinergy_score = excluded.sinergy_score,
            archetype = excluded.archetype
        """, (part_id.lower(), score, archetype))
        self.conn.commit()

    def close(self):
        """Fecha a conexão do banco de dados."""
        self.conn.close()
