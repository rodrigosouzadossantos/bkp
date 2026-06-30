from sqlalchemy import (
    Column, String, Integer, Float, Date, Boolean, ForeignKey, UniqueConstraint, Enum, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import enum
import uuid

Base = declarative_base()

class AtividadeEnum(enum.Enum):
    classificacao = "classificacao"
    deteccao = "deteccao"
    segmentacao = "segmentacao"
    multitask = "multitask"

class StatusDatasetEnum(enum.Enum):
    rascunho = "rascunho"
    aprovado = "aprovado"
    obsoleto = "obsoleto"

class TipoAnotacaoEnum(enum.Enum):
    bbox = "bbox"
    mask = "mask"
    label = "label"

class SplitEnum(enum.Enum):
    treino = "treino"
    validacao = "validacao"
    teste = "teste"

class StatusIngestaoEnum(enum.Enum):
    aceito = "aceito"
    rejeitado = "rejeitado"

class Empresa(Base):
    __tablename__ = "empresa"
    empresa_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)

class TipoEmbarcacao(Base):
    __tablename__ = "tipo_embarcacao"
    tipo_embarcacao_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(String, nullable=False)

class Embarcacao(Base):
    __tablename__ = "embarcacao"
    embarcacao_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresa.empresa_id"), nullable=False)
    tipo_embarcacao_id = Column(UUID(as_uuid=True), ForeignKey("tipo_embarcacao.tipo_embarcacao_id"), nullable=False)
    nome = Column(String, nullable=False)

class OrdemServico(Base):
    __tablename__ = "ordem_servico"
    ordem_servico_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ordem_servico = Column(String, nullable=False)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresa.empresa_id"), nullable=False)
    embarcacao_id = Column(UUID(as_uuid=True), ForeignKey("embarcacao.embarcacao_id"), nullable=False)
    data_inicio = Column(Date, nullable=True)
    data_fim = Column(Date, nullable=True)

class Video(Base):
    __tablename__ = "video"
    video_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ordem_servico_id = Column(UUID(as_uuid=True), ForeignKey("ordem_servico.ordem_servico_id"), nullable=False)
    s3_uri = Column(String, nullable=False)
    fps = Column(Float, nullable=True)
    duracao_segundos = Column(Float, nullable=True)
    gravado_em = Column(TIMESTAMP, nullable=True)

class VideoFrame(Base):
    __tablename__ = "video_frame"
    frame_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("video.video_id"), nullable=False)
    numero_frame = Column(Integer, nullable=True)
    timestamp_segundos = Column(Float, nullable=True)

class Imagem(Base):
    __tablename__ = "imagem"
    imagem_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    frame_id = Column(UUID(as_uuid=True), ForeignKey("video_frame.frame_id"), nullable=False)
    nome_original = Column(String, nullable=True)
    hash = Column(String, unique=True, nullable=False)
    phash = Column(String, unique=True, nullable=False)
    s3_uri = Column(String, nullable=False)
    largura = Column(Integer, nullable=False)
    altura = Column(Integer, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    profunidade = Column(Float, nullable=True)
    crs = Column(String, nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False)

class Anotador(Base):
    __tablename__ = "anotador"
    anotador_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    chave = Column(String, nullable=True)
    especialista = Column(Boolean, nullable=False)

class Anotacao(Base):
    __tablename__ = "anotacao"
    anotacao_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    imagem_id = Column(UUID(as_uuid=True), ForeignKey("imagem.imagem_id"), nullable=False)
    tipo = Column(Enum(TipoAnotacaoEnum), nullable=False)
    dados = Column(JSONB, nullable=False)
    anotador_id = Column(UUID(as_uuid=True), ForeignKey("anotador.anotador_id"), nullable=False)
    atualizado_em = Column(TIMESTAMP, nullable=False)
    criado_em = Column(TIMESTAMP, nullable=False)

class Dataset(Base):
    __tablename__ = "dataset"
    dataset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    atividade = Column(Enum(AtividadeEnum), nullable=False)
    status = Column(Enum(StatusDatasetEnum), nullable=False)
    descricao = Column(String, nullable=True)
    versao = Column(String, nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False)

class DatasetItem(Base):
    __tablename__ = "dataset_item"
    dataset_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("dataset.dataset_id"), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey("imagem.imagem_id"), nullable=False)
    split = Column(Enum(SplitEnum), nullable=False)

class LogsIngestao(Base):
    __tablename__ = "logs_ingestao"
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hash = Column(String, nullable=False)
    status = Column(Enum(StatusIngestaoEnum), nullable=False)
    motivo = Column(String, nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False)