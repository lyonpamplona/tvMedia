"""Pacote principal da aplicação AdSignage (backend FastAPI).

Este pacote concentra toda a lógica do servidor responsável por:

* Gerenciar mídias (imagens, vídeos, textos, HTML e URLs).
* Montar playlists com ordem e tempo de exibição de cada item.
* Vincular playlists a telas (TVs) específicas.
* Notificar as telas em tempo real, via WebSocket, sempre que algo muda.

A versão semântica do pacote é exposta em :data:`__version__`.
"""

__version__ = "1.0.0"
