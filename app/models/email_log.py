from datetime import datetime

from sqlalchemy import Column,Integer,String,Text,DateTime

from app.database import Base


class EmailLog(Base):
    __tablename__="email_logs"

    id=Column(Integer,primary_key=True,index=True)
    recipient_email=Column(String(255),nullable=False)
    subject=Column(String(500),nullable=False)
    body=Column(Text,nullable=False)

    status=Column(String(20),default="pending",nullable=False)
    retry_count=Column(Integer,default=0)
    max_retries=Column(Integer,default=3)

    error_message=Column(Text,nullable=True)
    last_attempted_at=Column(DateTime,nullable=True)

    created_at=Column(DateTime,default=datetime.utcnow)
