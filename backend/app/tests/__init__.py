"""Pacote de testes do AdSignage (stdlib ``unittest``).

Os testes que dependem de SQLAlchemy/FastAPI são automaticamente pulados
quando essas bibliotecas não estão instaladas, permitindo rodar a suíte de
segurança (sem dependências externas) em qualquer ambiente.
"""
