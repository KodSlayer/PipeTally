from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from database.database import Base

class DetectionResult(Base):
    __tablename__ = "detection_results"

    id            = Column(Integer, primary_key=True, index=True)
    model_used    = Column(String, nullable=False)        # "yolo" | "maskrcnn" | "hybrid"
    image_name    = Column(String, nullable=False)
    pipe_count    = Column(Integer, nullable=False)
    # output_image_base64 = Column(Text, nullable=True)     # base64-encoded output image
    confidence    = Column(Float,  nullable=True)
    extra_info    = Column(Text,   nullable=True)         # JSON string for extra metadata
    created_at    = Column(DateTime(timezone=True), server_default=func.now())