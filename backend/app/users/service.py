from sqlmodel import Session, select

from app.auth.service import hash_password

from .models import User


def list_users(session: Session):
    return session.exec(select(User)).all()


def get_user(user_id: int, session: Session):
    return session.get(User, user_id)


def create_user(user: User, session: Session):
    user.password_hash = hash_password(user.password_hash)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def delete_user(user_id: int, session: Session):
    user = session.get(User, user_id)
    if not user:
        return False
    session.delete(user)
    session.commit()
    return True
