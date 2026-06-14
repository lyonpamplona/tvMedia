"""Configurações da aplicação carregadas a partir de variáveis de ambiente.

Centraliza todos os parâmetros configuráveis em um único objeto
:class:`Settings`. Os valores são lidos de variáveis de ambiente (com suporte a
um arquivo ``.env`` via ``python-dotenv``) e possuem padrões seguros para uso
local/autohospedado.

Novidades desta versão (endurecimento de segurança):

* ``environment`` distingue desenvolvimento de produção.
* :meth:`Settings.validate_security` recusa subir em produção com segredos
  padrão (chave de assinatura e senha de admin).
* CORS com credenciais só é habilitado quando as origens são explícitas.
* Parâmetros de rate-limit de login e de backup automático.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Diretório base do backend (.../backend).
BASE_DIR = Path(__file__).resolve().parent.parent

# Valores padrão considerados inseguros para produção.
DEFAULT_SECRET_KEY = "troque-esta-chave-em-producao"
DEFAULT_ADMIN_PASSWORD = "admin"


def _env_bool(name: str, default: bool) -> bool:
    """Lê uma variável de ambiente booleana de forma tolerante."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on", "sim")


class Settings:
    """Agrupa todas as configurações da aplicação.

    Os atributos são resolvidos uma única vez na construção do objeto. Use a
    função :func:`get_settings` para obter uma instância em cache.

    Attributes:
        app_name: Nome exibido na documentação e nos logs.
        environment: ``development`` ou ``production``.
        debug: Habilita modo de depuração.
        database_url: URL de conexão do SQLAlchemy.
        media_dir: Diretório dos arquivos de mídia enviados.
        frontend_dir: Diretório com os arquivos estáticos do frontend.
        max_upload_mb: Tamanho máximo de upload de mídia (MB).
        cors_origins: Lista de origens permitidas para CORS.
        admin_password: Senha inicial do usuário administrador semeado.
        secret_key: Chave usada para assinar os tokens de sessão (HMAC).
        token_ttl_hours: Validade do token de sessão, em horas.
        default_timezone: Fuso horário IANA padrão para agendamentos.
        login_max_attempts: Tentativas de login antes do bloqueio temporário.
        login_window_seconds: Janela de contagem das tentativas (segundos).
        login_block_seconds: Duração do bloqueio após estourar o limite.
        backup_enabled: Liga/desliga o backup automático do banco.
        backup_dir: Pasta onde os backups são gravados.
        backup_interval_hours: Intervalo entre backups automáticos.
        backup_keep: Quantos backups manter (rotação).
    """

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "tvMedia")
        self.environment: str = os.getenv("ENVIRONMENT", "development").lower()
        self.debug: bool = _env_bool("DEBUG", False)

        default_db = f"sqlite:///{BASE_DIR / 'data' / 'adsignage.db'}"
        self.database_url: str = os.getenv("DATABASE_URL", default_db)

        self.media_dir: Path = Path(
            os.getenv("MEDIA_DIR", str(BASE_DIR / "data" / "media"))
        )
        self.frontend_dir: Path = Path(
            os.getenv("FRONTEND_DIR", str(BASE_DIR.parent / "frontend"))
        )

        self.max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "200"))

        # Processamento de midia (reescala/transcodificacao) server-side.
        # Requer Pillow (imagens) e ffmpeg/ffprobe no PATH (videos). Quando as
        # ferramentas nao estao disponiveis, o processamento e ignorado com
        # seguranca (status 'skipped') e o arquivo original e servido.
        self.media_processing_enabled: bool = _env_bool(
            "MEDIA_PROCESSING_ENABLED", True
        )
        self.image_max_dimension: int = int(os.getenv("IMAGE_MAX_DIMENSION", "3840"))
        self.image_quality: int = int(os.getenv("IMAGE_QUALITY", "82"))
        self.video_max_height: int = int(os.getenv("VIDEO_MAX_HEIGHT", "1080"))
        self.video_crf: int = int(os.getenv("VIDEO_CRF", "23"))
        self.video_preset: str = os.getenv("VIDEO_PRESET", "veryfast")
        self.media_process_timeout: int = int(
            os.getenv("MEDIA_PROCESS_TIMEOUT", "1800")
        )
        self.cors_origins: list[str] = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ]

        self.admin_password: str = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
        self.secret_key: str = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
        self.token_ttl_hours: int = int(os.getenv("TOKEN_TTL_HOURS", "24"))

        self.default_timezone: str = os.getenv(
            "DEFAULT_TIMEZONE", "America/Sao_Paulo"
        )

        # Rate-limit de login (proteção contra força bruta).
        self.login_max_attempts: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
        self.login_window_seconds: int = int(
            os.getenv("LOGIN_WINDOW_SECONDS", "300")
        )
        self.login_block_seconds: int = int(
            os.getenv("LOGIN_BLOCK_SECONDS", "300")
        )

        # Backup automático do banco SQLite.
        self.backup_enabled: bool = _env_bool("BACKUP_ENABLED", True)
        self.backup_dir: Path = Path(
            os.getenv("BACKUP_DIR", str(BASE_DIR / "data" / "backups"))
        )
        self.backup_interval_hours: int = int(
            os.getenv("BACKUP_INTERVAL_HOURS", "24")
        )
        self.backup_keep: int = int(os.getenv("BACKUP_KEEP", "7"))

        # Garante que os diretórios necessários existam.
        self.media_dir.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

    @property
    def is_production(self) -> bool:
        """True quando a aplicação roda em ambiente de produção."""
        return self.environment in ("production", "prod")

    @property
    def max_upload_bytes(self) -> int:
        """Retorna o limite de upload convertido para bytes."""
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_allow_credentials(self) -> bool:
        """Permite credenciais no CORS apenas com origens explícitas.

        O navegador rejeita a combinação de ``Access-Control-Allow-Origin: *``
        com credenciais; além disso, liberar tudo amplia a superfície a CSRF.
        """
        return bool(self.cors_origins) and "*" not in self.cors_origins

    @property
    def effective_cors_origins(self) -> list[str]:
        """Origens efetivas para o middleware de CORS."""
        return self.cors_origins or ["*"]

    def security_warnings(self) -> list[str]:
        """Lista problemas de segurança de configuração detectados."""
        problems: list[str] = []
        if self.secret_key == DEFAULT_SECRET_KEY:
            problems.append(
                "SECRET_KEY está com o valor padrão; defina uma chave forte."
            )
        if self.admin_password == DEFAULT_ADMIN_PASSWORD:
            problems.append(
                "ADMIN_PASSWORD está com o valor padrão 'admin'; troque-a."
            )
        if self.cors_allow_credentials is False and "*" in self.effective_cors_origins:
            problems.append(
                "CORS liberado para qualquer origem ('*'); restrinja em produção."
            )
        return problems

    def validate_security(self) -> None:
        """Recusa inicializar em produção com configuração insegura.

        Em desenvolvimento, apenas registra avisos. Em produção, levanta
        :class:`RuntimeError` se segredos padrão forem detectados.

        Raises:
            RuntimeError: em produção, quando há segredos padrão.
        """
        problems = self.security_warnings()
        if not problems:
            return
        message = "Configuração insegura detectada:\n - " + "\n - ".join(problems)
        if self.is_production:
            raise RuntimeError(message)
        # Em desenvolvimento, apenas avisa no log padrão.
        import logging

        logging.getLogger("tvmedia.config").warning(message)


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância única (cacheada) de :class:`Settings`.

    Returns:
        Settings: objeto de configuração compartilhado por toda a aplicação.
    """
    return Settings()


# Instância global de conveniência.
settings = get_settings()
