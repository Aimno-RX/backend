from typing import Optional
import os

from fastapi import Form, HTTPException
from pydantic import BaseModel, Field


class Neo4jCredentials(BaseModel):
    """
    Neo4j database credentials model with validation.
    Used as a dependency for FastAPI endpoints requiring database access.
    """
    uri: Optional[str] = Field(None, description="Neo4j database URI")
    userName: Optional[str] = Field(None, description="Neo4j username")
    password: Optional[str] = Field(None, description="Neo4j password")
    database: Optional[str] = Field(None, description="Neo4j database name")
    email: Optional[str] = Field(None, description="User email for logging")

    def validate_required(self) -> None:
        """Validate that required credentials are present."""
        if not self.uri or not self.userName or not self.password:
            raise HTTPException(
                status_code=400,
                detail="Missing required credentials: uri, userName, and password are required"
            )

    class Config:
        str_strip_whitespace = True


async def get_neo4j_credentials(
    uri: Optional[str] = Form(None),
    userName: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    database: Optional[str] = Form(None),
    email: Optional[str] = Form(None)
) -> Neo4jCredentials:
    """
    优先读取请求表单；如果没传，则回退到环境变量。
    """
    resolved_uri = uri or os.getenv("NEO4J_URI")
    resolved_user = userName or os.getenv("NEO4J_USERNAME")
    resolved_password = password or os.getenv("NEO4J_PASSWORD")
    resolved_database = database or os.getenv("NEO4J_DATABASE", "neo4j")

    credentials = Neo4jCredentials(
        uri=resolved_uri,
        userName=resolved_user,
        password=resolved_password,
        database=resolved_database,
        email=email
    )
    credentials.validate_required()
    return credentials