# -*- coding: utf-8 -*-
"""Script de treinamento e engenharia de características para o modelo de Machine Learning."""

import os
import sqlite3
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

DB_PATH = os.path.join("data", "marketplace.db")
MODEL_PATH = os.path.join("data", "price_model.pkl")

def get_parts_synergy_score(parts_list_str, conn):
    """Calcula o score meta total para um Axie a partir da string JSON de partes."""
    try:
        parts = json.loads(parts_list_str)
    except:
        return 0.0
    
    cursor = conn.cursor()
    total_score = 0.0
    for part in parts:
        cursor.execute("SELECT sinergy_score FROM meta_parts WHERE part_id = ?", (part.lower(),))
        row = cursor.fetchone()
        if row:
            total_score += row[0]
    return total_score

def train_model():
    """Treina o modelo de regressão baseado nas vendas salvas no SQLite local."""
    print("[ML-Train] Carregando dados para engenharia de características...")
    
    if not os.path.exists(DB_PATH):
        print("[ML-Train] Banco de dados não localizado. Abortando treinamento.")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Carrega dados de vendas (Sales)
    query = "SELECT * FROM axie_historical_events WHERE event_type = 'SALE'"
    df = pd.read_sql_query(query, conn)
    
    # Tratamento de Cold Start: Se não houver vendas suficientes cadastradas no banco,
    # injetamos dados sintéticos coerentes para permitir o treinamento do modelo inicial!
    if len(df) < 5:
        print("[ML-Train] Dados insuficientes no banco. Injetando dataset de bootstrap estruturado...")
        bootstrap_data = []
        # Injeta uma faixa de axies comuns, colecionáveis e evoluídos com preços coerentes
        for i in range(50):
            is_coll = 1 if i % 10 == 0 else 0
            lvl = int(1 + (i % 60))
            upgrad = int(i % 3)
            syn = float((i % 4) * 0.8)
            
            # Equação base para precificação sintética + ruído
            price = 0.55
            if is_coll:
                price += 50.0
            price += upgrad * 5.0
            price += lvl * 0.10
            price += syn * 0.8
            price += np.random.normal(0, 0.05) # Ruído Gaussiano
            
            bootstrap_data.append({
                "id": f"dummy_{i}",
                "axie_id": f"{1000000 + i}",
                "class": "Plant" if i % 2 == 0 else "Aquatic",
                "price_wei": "0",
                "price_usd": max(0.2, price),
                "is_collectible": is_coll,
                "collectible_type": "Origin" if is_coll else None,
                "axie_level": lvl,
                "upgraded_parts_count": upgrad,
                "parts_list": "[]",
                "event_type": "SALE",
                "timestamp": 1779209555
            })
        df = pd.DataFrame(bootstrap_data)
        print(f"[ML-Train] Dataset de bootstrap gerado com {len(df)} registros.")

    # 2. Feature Engineering
    # Extrai o score meta dinamicamente para cada linha
    df["meta_synergy"] = df["parts_list"].apply(lambda x: get_parts_synergy_score(x, conn))
    
    # Define as variáveis independentes (X) e dependente (y)
    features = ["is_collectible", "axie_level", "upgraded_parts_count", "meta_synergy"]
    X = df[features]
    y = df["price_usd"]
    
    # 3. Treina o Regressor RandomForest
    print(f"[ML-Train] Treinando RandomForestRegressor com {len(X)} amostras...")
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # 4. Salva o modelo
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
        
    print(f"[ML-Train] Modelo treinado e salvo com sucesso em: {MODEL_PATH}")
    conn.close()
    return True

if __name__ == "__main__":
    train_model()
