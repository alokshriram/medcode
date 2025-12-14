from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenPayload, verify_token

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[TokenPayload, Depends(verify_token)]
