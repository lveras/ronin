# -*- coding: utf-8 -*-
"""Script de validação de ponta a ponta do pipeline de IA Híbrida (ML + LLM)."""

import time
from agents.meta_analyzer import OriginsMetaAnalyzer
from core.train_ml import train_model
from agents.sniper_agent import SniperAgent

def run_hybrid_pipeline_demo():
    print("==================================================================")
    print("INICIANDO INTEGRACAO DO PIPELINE DE IA HIBRIDA DATA-DRIVEN (TOP 100)")
    print("==================================================================")
    
    # Passo 1: O Agente MetaAnalyzer varre o Leaderboard e mapeia as frequencias no SQLite
    print("\n--- PASSO 1: MAPEAMENTO ESTATISTICO DO META VIA TOP 100 LEADERBOARD ---")
    meta_analyzer = OriginsMetaAnalyzer()
    meta_analyzer.run_meta_analysis(limit=100)
    
    # Passo 2: O modelo de Machine Learning é retreinado com base no novo estado do banco
    print("\n--- PASSO 2: RETREINAMENTO ADAPTATIVO DO MODELO DE ML ---")
    train_success = train_model()
    if train_success:
        print("[OK] Modelo de ML RandomForest treinado e reajustado com sucesso!")
    else:
        print("[ERRO] Falha ao retreinar modelo de ML.")
        return

    # Passo 3: O Sniper roda um novo ciclo de varredura usando a valoração do modelo atualizado
    print("\n--- PASSO 3: ESCANEAMENTO SNIPER COM INFERÊNCIA DE ML ---")
    sniper = SniperAgent()
    # Executa a busca nas 15 listagens mais recentes
    sniper.run_sniper_cycle(limit=15, dry_run=True)
    
    print("\n==================================================================")
    print("PIPELINE DE IA HÍBRIDA EXECUTADO E VALIDADO COM SUCESSO!")
    print("==================================================================")

if __name__ == "__main__":
    run_hybrid_pipeline_demo()
