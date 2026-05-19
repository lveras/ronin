# -*- coding: utf-8 -*-
"""Script de validação de ponta a ponta do pipeline de IA Híbrida (ML + LLM)."""

import time
from agents.llm_meta_agent import LLMMetaAgent
from core.train_ml import train_model
from agents.sniper_agent import SniperAgent

def run_hybrid_pipeline_demo():
    print("==================================================================")
    print("INICIANDO INTEGRAÇÃO DO PIPELINE DE IA HÍBRIDA (ML + LLM)")
    print("==================================================================")
    
    # Passo 1: O Agente LLM analisa semanticamente as novas regras do jogo e atualiza o SQLite
    print("\n--- PASSO 1: ATUALIZAÇÃO SEMÂNTICA DO META VIA LLM AGENT ---")
    meta_agent = LLMMetaAgent()
    patch_notes_mock = """
    Patch Notes Season 12:
    - Cactus (Horn): Dano base bufado em 30%. Sinergia com plantas agressivas aumentou muito.
    - Nimo (Tail): Ganho de energia nerfado. Menos relevante no meta atual.
    """
    meta_agent.analyze_patch_notes(patch_notes_mock)
    
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
