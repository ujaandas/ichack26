from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.database import get_session

from .models import User
from .service import delete_user, get_user, list_users

router = APIRouter()


@router.get("/", response_model=list[User])
def route_list_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    return list_users(session)


@router.get("/{user_id}", response_model=User)
def route_get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    user = get_user(user_id, session)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.delete("/{user_id}")
def route_delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    if not delete_user(user_id, session):
        raise HTTPException(404, "User not found")
    return {"status": "deleted"}
