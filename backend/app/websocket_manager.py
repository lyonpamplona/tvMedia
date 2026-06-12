"""Gerenciador de conexões WebSocket para atualização em tempo real.

Cada tela (``Screen``) possui um canal identificado pelo seu ``slug``. Os
players abertos nas TVs se conectam ao canal correspondente e ficam aguardando
mensagens. Quando o conteúdo muda (mídia, playlist ou vínculo de tela), o
backend chama :meth:`ConnectionManager.broadcast` para avisar os players, que
então recarregam o conteúdo.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Mantém o registro das conexões WebSocket ativas por tela.

    A estrutura interna mapeia ``slug`` da tela -> conjunto de WebSockets
    conectados. Um :class:`asyncio.Lock` protege o dicionário contra
    condições de corrida em conexões/desconexões concorrentes.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, screen_slug: str, websocket: WebSocket) -> None:
        """Aceita e registra uma nova conexão de player.

        Args:
            screen_slug: identificador público da tela.
            websocket: conexão WebSocket a ser registrada.
        """
        await websocket.accept()
        async with self._lock:
            self._connections[screen_slug].add(websocket)

    async def disconnect(self, screen_slug: str, websocket: WebSocket) -> None:
        """Remove uma conexão encerrada do registro.

        Args:
            screen_slug: identificador público da tela.
            websocket: conexão a ser removida.
        """
        async with self._lock:
            self._connections[screen_slug].discard(websocket)
            if not self._connections[screen_slug]:
                self._connections.pop(screen_slug, None)

    async def broadcast(self, screen_slug: str, message: dict) -> None:
        """Envia uma mensagem JSON a todos os players de uma tela.

        Conexões que falharem no envio são descartadas silenciosamente.

        Args:
            screen_slug: tela alvo do envio.
            message: dicionário serializável em JSON.
        """
        async with self._lock:
            targets = list(self._connections.get(screen_slug, set()))

        stale: list[WebSocket] = []
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001 - conexão caída/instável
                stale.append(connection)

        for connection in stale:
            await self.disconnect(screen_slug, connection)

    async def broadcast_all(self, message: dict) -> None:
        """Envia uma mensagem para os players de todas as telas.

        Útil quando uma playlist compartilhada por várias telas é alterada.

        Args:
            message: dicionário serializável em JSON.
        """
        async with self._lock:
            slugs = list(self._connections.keys())
        for slug in slugs:
            await self.broadcast(slug, message)

    def connection_count(self, screen_slug: str) -> int:
        """Retorna quantos players estão conectados a uma tela.

        Args:
            screen_slug: identificador público da tela.

        Returns:
            int: número de conexões ativas.
        """
        return len(self._connections.get(screen_slug, set()))


# Instância única compartilhada por toda a aplicação.
manager = ConnectionManager()
