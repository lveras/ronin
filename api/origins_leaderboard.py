# -*- coding: utf-8 -*-
"""Módulo para buscar o Top 100 de jogadores do Axie Infinity Origins via Sky Mavis API."""

import requests
import json
from core.config import config

class OriginsLeaderboard:
    """Classe para interação com o Leaderboard oficial do Axie Infinity Origins."""

    @classmethod
    def get_top_100(cls, limit: int = 100) -> list:
        """Busca o ranking do Top 100 usando o API Gateway oficial da Sky Mavis.

        Requer que a chave API configurada possua permissão 'Origins API' ativa 
        no painel de desenvolvedores (developers.skymavis.com).
        """
        url = "https://api-gateway.skymavis.com/origins/v2/season-leaderboards"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": config.get("api_key", "")
        }
        params = {
            "limit": limit,
            "offset": 0
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get("data", []) or data.get("leaderboards", [])
                return results
            elif response.status_code == 401:
                raise PermissionError(
                    "Nao autorizado (401). Verifique se a sua API Key do Sky Mavis possui "
                    "a permissao 'Origins Game API' ativada no console de desenvolvedor "
                    "(https://developers.skymavis.com/)."
                )
            else:
                raise Exception(f"Erro na API Sky Mavis ({response.status_code}): {response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro na conexao com o servidor Sky Mavis: {e}")

    @classmethod
    def print_leaderboard(cls, limit: int = 20):
        """Busca o ranking e imprime uma tabela estilizada no console."""
        print(f"\n==================================================================")
        print(f"  BUSCANDO OS TOP {limit} DE AXIE INFINITY ORIGINS")
        print(f"==================================================================")
        
        try:
            players = cls.get_top_100(limit=limit)
            if not players:
                print("[OriginsLeaderboard] Nenhum jogador retornado ou temporada inativa.")
                return
            
            print(f"{'Rank':<6} | {'Ronin Address / ID':<44} | {'Stars':<10} | {'Wins':<10}")
            print("-" * 80)
            for p in players:
                rank = p.get("rank", "-")
                userID = p.get("userID") or p.get("roninAddress") or p.get("name") or "Desconhecido"
                stars = p.get("stars") or p.get("victoryStars") or 0
                win_count = p.get("winCount") or p.get("victoryCount") or "-"
                
                if userID.startswith("0x") or userID.startswith("ronin:"):
                    display_id = f"{userID[:10]}...{userID[-8:]}"
                else:
                    display_id = userID[:38]

                print(f"{rank:<6} | {display_id:<44} | {stars:<10} | {win_count:<10}")
            
            print(f"==================================================================")
        except PermissionError as pe:
            print(f"\n[ERRO DE PERMISSAO]:")
            print(f"  {pe}")
            print(f"==================================================================")
        except Exception as e:
            print(f"\n[ERRO AO CARREGAR LEADERBOARD]:")
            print(f"  {e}")
            print(f"==================================================================")

if __name__ == '__main__':
    OriginsLeaderboard.print_leaderboard(limit=15)
