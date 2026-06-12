"""Configurações da aplicação carregadas a partir de variáveis de ambiente.

O objetivo deste módulo é centralizar todos os parâmetros configuráveis do
sistema em um único objeto :class:`Settings`, evitando valores "mágicos"
espalhados pelo código. As configurações são lidas de variáveis de ambiente
(com suporte a um arquivo ``.env`` via ``python-dotenv``) e possuem valores
padrão seguros para execução local/autohospedada.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Carrega o arquivo .env (se existir) para dentro de os.environ.
load_dotenv()

# Diretório base do backend (…/backend).
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Agrupa todas as configurações da aplicação.

    Os atributos são resolvidos uma única vez na construção do objeto. Use a
    função :func:`get_settings` para obter uma instância em cache.

    Attributes:
        app_name: Nome exibido na documentação e nos logs.
        debug: Habilita modo de depuração (recarga e logs mais verbosos).
        database_url: URL de conexão do SQLAlchemy. Por padrão usa SQLite
            em arquivo, ideal para ambientes autohospedados simples.
        media_dir: Diretório onde os arquivos de mídia enviados são salvos.
        frontend_dir: Diretório com os arquivos estáticos do frontend.
        max_upload_mb: Tamanho máximo permitido para upload de mídia (MB).
        cors_origins: Lista de origens permitidas para requisições CORS.
    """

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "AdSignage")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"

        # Persistência: por padrão SQLite em /data para facilitar volume Docker.
        default_db = f"sqlite:///{BASE_DIR / 'data' / 'adsignage.db'}"
        self.database_url: str = os.getenv("DATABASE_URL", default_db)

        # Diretórios de mídia e frontend.
        self.media_dir: Path = Path(
            os.getenv("MEDIA_DIR", str(BASE_DIR / "data" / "media"))
        )
        self.frontend_dir: Path = Path(
            os.getenv("FRONTEND_DIR", str(BASE_DIR.parent / "frontend"))
        )

        self.max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "200"))
        self.cors_origins: list[str] = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ]

        # Garante que os diretórios necessários existam.
        self.media_dir.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

    @property
    def max_upload_bytes(self) -> int:
        """Retorna o limite de upload convertido para bytes."""
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância única (cacheada) de :class:`Settings`.

    Returns:
        Settings: objeto de configuração compartilhado por toda a aplicação.
    """
    return Settings()


# Instância global de conveniência.
settings = get_settings()
