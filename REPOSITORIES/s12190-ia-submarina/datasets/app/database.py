from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Carregue a string de conexão do .env ou defina manualmente
DATABASE_URL = "postgresql+psycopg2://usuario:senha@localhost:5432/dbname"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)