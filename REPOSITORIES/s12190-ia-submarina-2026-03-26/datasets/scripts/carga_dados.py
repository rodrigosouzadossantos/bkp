"""
Script para inserir dados de um CSV no banco PostgreSQL usando SQLAlchemy.
O script trata chaves estrangeiras, evita duplicidade de imagens (hash/phash),
cria anotador padrão xaso não exista e insere informações de empresam embarcação, OS, vídeo, frame, imagem e anotações.
"""

import pandas as pd
import uuid
import ast
import numpy as np
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(__file__, '..')))

from app.models import (
    Empresa, TipoEmbarcacao, Embarcacao, OrdemServico, Imagem,
    Anotador, Anotacao, TipoAnotacaoEnum, VideoFrame, Video
)
from app.database import engine


def safe_date(valor):
    """Garante que um campo de data é compatível com o tipo associado no banco de dados.

    Args:
        valor (Any): valor a ser verficado.

    Returns:
        Timestamp | None: Data formatada ou None
    """
    if pd.isna(valor) or valor in [np.nan, 'nan', 'NaT', '']:
        return None
    return pd.to_datetime(valor).date()

def safe_timestamp(valor):
    """Garante que um campo de timestamp é compatível com o tipo associado no banco de dados.

    Args:
        valor (Any): Valor a ser verficado.

    Returns:
        Timestamp: Timestamp formatado
    """
    if pd.isna(valor) or valor in [np.nan, 'nan', 'NaT', '', None]:
        return pd.Timestamp.now()
    return pd.to_datetime(valor)


df = pd.read_csv('dados_dataset_coral_sol.csv')


session = Session(bind=engine)

email_anotador_padrao = "default@petrobras.com"
anotador_padrao = session.query(Anotador).filter_by(email=email_anotador_padrao).first()
if not anotador_padrao:
    anotador_padrao = Anotador(
        anotador_id=uuid.uuid4(),
        nome="Anotador Padrão",
        email=email_anotador_padrao,
        especialista=False
    )
    session.add(anotador_padrao)
    session.commit()


for _, row in df.iterrows():
    imagem_existente = session.query(Imagem).filter(
        (Imagem.hash == row['hash']) | (Imagem.phash == row['phash'])
    ).first()
    if imagem_existente:
        continue
    
    empresa = session.query(Empresa).filter_by(nome=row['Empresa']).first()
    if not empresa:
        empresa = Empresa(empresa_id=uuid.uuid4(), nome=row['Empresa'])
        session.add(empresa)
        session.commit()

    tipo = session.query(TipoEmbarcacao).filter_by(tipo=row['Tipo']).first()
    if not tipo:
        tipo = TipoEmbarcacao(tipo_embarcacao_id=uuid.uuid4(), tipo=row['Tipo'])
        session.add(tipo)
        session.commit()

    embarcacao = session.query(Embarcacao).filter_by(nome=row['Nome']).first()
    if not embarcacao:
        embarcacao = Embarcacao(
            embarcacao_id=uuid.uuid4(),
            empresa_id=empresa.empresa_id,
            tipo_embarcacao_id=tipo.tipo_embarcacao_id,
            nome=row['Nome']
        )
        session.add(embarcacao)
        session.commit()
    data_inicio = safe_date(row['Arquivo mais antigo'])
    data_fim = safe_date(row['Arquivo mais novo'])

    ordem = session.query(OrdemServico).filter_by(ordem_servico=row['ordem_servico']).first()
    if not ordem:
        ordem = OrdemServico(
            ordem_servico_id=uuid.uuid4(),
            ordem_servico=row['ordem_servico'],
            empresa_id=empresa.empresa_id,
            embarcacao_id=embarcacao.embarcacao_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        session.add(ordem)
        session.commit()

    video = session.query(Video).filter_by(s3_uri=row['Caminho Completo']).first()
    if not video:
        video = Video(
            video_id=uuid.uuid4(),
            ordem_servico_id=ordem.ordem_servico_id,
            s3_uri=row['Caminho Completo']

        )
        session.add(video)
        session.commit()

    frame = VideoFrame(
        frame_id=uuid.uuid4(),
        video_id=video.video_id

    )
    session.add(frame)
    session.commit()

    imagem = Imagem(
        imagem_id=uuid.uuid4(),
        frame_id=frame.frame_id,
        nome_original=row['arquivo'],
        hash=row['hash'],
        phash=row['phash'],
        s3_uri='projeto-ia-submarina/ia-sub-dataset/' + row['hash'],
        largura=row['largura'],
        altura=row['altura'],
        latitude=None,
        longitude=None,
        profunidade=None,
        crs=None,
        criado_em=safe_timestamp(row['Arquivo mais antigo'])
    )
    session.add(imagem)
    session.commit()

    try:
        labels = ast.literal_eval(row['classes'])
        if not isinstance(labels, list):
            labels = [labels]
    except Exception:
        labels = [row['classes']]
    anotacao = Anotacao(
          anotacao_id=uuid.uuid4(),
          imagem_id=imagem.imagem_id,
          tipo=TipoAnotacaoEnum.label,
          dados={"type": "label", "label": labels},
          anotador_id=anotador_padrao.anotador_id,
          atualizado_em=pd.Timestamp.now(),
          criado_em=pd.Timestamp.now()
    )
    session.add(anotacao)
    session.commit()

session.close()