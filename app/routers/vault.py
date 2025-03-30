from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Vault, Post, VaultPost
from app.schemas import VaultBase, VaultResponse, VaultPostBase
from app.utils import get_user
from app.types import PrivacyType


router = APIRouter(tags=["Vault"])


@router.post("/vaults", response_model=VaultResponse)
def create_vault(
    vault: VaultBase, user: dict = Depends(get_user), db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_vault = (
        db.query(Vault)
        .filter(Vault.user_id == user.id, Vault.title == vault.title)
        .first()
    )
    if db_vault:
        raise HTTPException(status_code=409, detail="Vault already exists")

    new_vault = Vault(title=vault.title, user_id=user.id, privacy=vault.privacy)
    db.add(new_vault)
    db.commit()
    return new_vault


@router.get("/vaults/{vault_id}", response_model=VaultResponse)
def get_vault(
    vault_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    vault = db.query(Vault).filter(Vault.id == vault_id).first()
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    if vault.privacy == PrivacyType.PRIVATE and not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return vault


@router.put("/vaults/{vault_id}", response_model=VaultResponse)
def update_vault(
    vault: VaultBase,
    vault_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vault = (
        db.query(Vault).filter(Vault.id == vault_id, Vault.user_id == user.id).first()
    )
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    for key, value in vault.model_dump(exclude_unset=True).items():
        setattr(vault, key, value)

    db.commit()
    return vault


@router.delete("/vaults/{vault_id}")
def delete_vault(
    vault_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vault = (
        db.query(Vault).filter(Vault.id == vault_id, Vault.user_id == user.id).first()
    )
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    db.delete(vault)
    db.commit()
    return {"detail": "Successfully deleted vault"}


@router.get("/vaults/{vault_id}/posts", response_model=Page[VaultPostBase])
def get_vault_posts(
    vault_id: int, user: dict = Depends(get_user), db: Session = Depends(get_db)
):
    vault = db.query(Vault).filter(Vault.id == vault_id).first()
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    if vault.privacy == PrivacyType.PRIVATE and not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    posts = (
        db.query(VaultPost)
        .order_by(desc(VaultPost.date_created))
        .filter(VaultPost.vault_id == vault.id)
    )

    paginated_posts = paginate(posts)
    return paginated_posts


@router.post("/vaults/{vault_id}/posts/{post_id}")
def add_post_to_vault(
    vault_id: int,
    post_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vault = (
        db.query(Vault).filter(Vault.id == vault_id, Vault.user_id == user.id).first()
    )
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    new_entry = VaultPost(vault_id=vault.id, post_id=post.id)
    db.add(new_entry)
    db.commit()
    return {"detail": "Added post to vault"}


@router.delete("/vaults/{vault_id}/entries/{entry_id}")
def remove_post_from_vault(
    vault_id: int,
    entry_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vault = (
        db.query(Vault).filter(Vault.id == vault_id, Vault.user_id == user.id).first()
    )
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    post_entry = db.get(VaultPost, entry_id)
    if not post_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    db.delete(post_entry)
    db.commit()
    return {"detail": "Removed entry from vault"}
