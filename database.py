from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus
from urllib.parse import quote_plus

# Your original password with special characters
password = ""
db_name =""
# Encode it for URL use
encoded_password = quote_plus(password)  

# Correct connection URL
DATABASE_URL = f"mysql+pymysql://root:{encoded_password}@127.0.0.1:3306/{db_name}"
engine = create_engine(DATABASE_URL, echo=True,pool_pre_ping=True,pool_recycle=1800   )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

try:
    with engine.connect() as conn:
        print("✅ Connected to FreeSQLDatabase successfully!")
except Exception as e:
    print("❌ Connection failed:", e)
