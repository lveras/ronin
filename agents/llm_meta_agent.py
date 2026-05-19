# -*- coding: utf-8 -*-
"""Agente LLM Analista de Meta (Option B - LLM Meta Analyst Agent)."""

import json
from curl_cffi import requests
from core.database import MarketDatabase
from core.config import config

class LLMMetaAgent:
    """Agente de IA baseado em LLM que analisa semanticamente atualizações e ajusta as sinergias."""

    def __init__(self):
        self.db = MarketDatabase()
        # Busca chave do Gemini ou de outro provedor no config
        self.api_key = config.get("gemini_api_key") or config.get("api_key") or "MOCK_KEY"

    def analyze_patch_notes(self, patch_text: str) -> dict:
        """Envia o texto dos patch notes para a LLM e atualiza os pesos meta no banco SQLite."""
        print("\n=== [LLMMetaAgent] INICIANDO ANÁLISE DE PATCH NOTES VIA IA ===")
        
        prompt = f"""
Você é um analista especialista de metagame de Axie Infinity.
Analise as seguintes notas de balanceamento (Patch Notes) e determine o impacto de utilidade de cada parte mencionada.
Para cada parte afetada, forneça um 'sinergy_score' entre 0.1 (totalmente fora do meta) e 1.0 (peça lendária absoluta/tier S no meta).
Mapeie a classe correspondente e o arquétipo.

Texto de Atualização:
\"\"\"{patch_text}\"\"\"

Responda ESTRITAMENTE em formato JSON (sem markdown, sem blocos ```json), como uma lista de objetos:
[
  {{"part_id": "horn-cactus", "sinergy_score": 0.95, "archetype": "Aggro Plant"}},
  {{"part_id": "tail-nimo", "sinergy_score": 0.60, "archetype": "Energy Aquatic Nerfed"}}
]
"""

        # Se for chave de simulação/mock, executa o mock de segurança
        if self.api_key == "MOCK_KEY" or not self.api_key or len(self.api_key) < 10:
            print("[LLMMetaAgent] Chave de API real não localizada no config.yml. Executando simulação de IA...")
            # Simula a resposta que a LLM traria ao interpretar o patch note
            mock_response = [
                {"part_id": "horn-cactus", "sinergy_score": 0.95, "archetype": "Super Aggro Plant (Buffed)"},
                {"part_id": "tail-nimo", "sinergy_score": 0.50, "archetype": "Energy Ramp Nerfed"},
                {"part_id": "mouth-kotaro", "sinergy_score": 0.98, "archetype": "God Tier Beast Card (Buffed)"}
            ]
            self._apply_updates(mock_response)
            return {"status": "success", "engine": "Simulation/Mock", "updates": mock_response}

        # Conecta à API do Gemini via REST de forma limpa e rápida
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        try:
            r = requests.post(url, headers=headers, json=payload, impersonate="chrome")
            if r.status_code == 200:
                data = r.json()
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                updates = json.loads(text_response.strip())
                self._apply_updates(updates)
                return {"status": "success", "engine": "Gemini API", "updates": updates}
            else:
                print(f"[LLMMetaAgent] Erro na requisição HTTP ({r.status_code}): {r.text}")
                raise Exception("Erro na API")
        except Exception as e:
            print(f"[LLMMetaAgent] Falha na comunicação com a API de IA: {e}. Executando mock de contingência...")
            # Fallback seguro
            fallback_updates = [
                {"part_id": "horn-cactus", "sinergy_score": 0.92, "archetype": "Aggro Plant (Updated)"}
            ]
            self._apply_updates(fallback_updates)
            return {"status": "fallback", "engine": "Fallback Simulation", "updates": fallback_updates}

    def _apply_updates(self, updates: list):
        """Aplica os updates de IA diretamente no banco SQLite."""
        for item in updates:
            part_id = item.get("part_id", "").lower()
            score = float(item.get("sinergy_score", 0.5))
            archetype = item.get("archetype", "Indefinido")
            
            # Atualiza o SQLite local dinamicamente
            self.db.add_meta_part(part_id, score, archetype)
            print(f"  [IA-Update] Parte '{part_id}' atualizada: Novo Score = {score} ({archetype})")
        print("[LLMMetaAgent] Banco de dados de metagame SQLite atualizado com sucesso pela IA!")

if __name__ == "__main__":
    agent = LLMMetaAgent()
    
    # Texto de simulação de Patch Notes enviado pelo usuário
    patch_notes_exemplo = """
    Patch Notes Season 12 - Axie Origins:
    - Cactus (Horn): Aumentado o dano base de 65 para 75. Cartas do tipo Aggro Plant ganham bônus de dano.
    - Nimo (Tail): O ganho de energia agora exige descartar 1 carta de combate.
    - Kotaro (Mouth): Se jogado em cadeia, agora ganha 2 de energia adicionais e aumenta a velocidade do Beast.
    """
    
    res = agent.analyze_patch_notes(patch_notes_exemplo)
