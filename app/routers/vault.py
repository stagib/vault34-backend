from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import desc, func, Select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db

""" from app.db.neo4j import * """
from app.models import Post, Vault, VaultPost, Reaction
from app.schemas.vault import VaultCreate, EntryPreview, VaultResponse, VaultBase
from app.schemas.reaction import ReactionCreate
from app.types import PrivacyType, TargetType, ReactionType
from app.utils import update_reaction_count
from app.utils.auth import get_user
from app.utils.vault import log_vault_metric

router = APIRouter(tags=["Vault"])


@router.post("/vaults", response_model=VaultResponse)
def create_vault(
    vault: VaultCreate,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    new_vault = Vault(
        user_id=user.id,
        title=vault.title,
        description=vault.description,
        privacy=vault.privacy,
        layout=vault.layout,
    )

    try:
        db.add(new_vault)
        db.flush()

        """ with driver.session() as session:
            session.execute_write(create_vault_, new_vault) """

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return new_vault


@router.get("/vaults/recommend", response_model=Page[VaultBase])
def get_vault_recommendation(db: Session = Depends(get_db)):
    vaults = (
        db.query(Vault)
        .order_by(desc(Vault.score))
        .filter(Vault.privacy == PrivacyType.PUBLIC)
    )
    return paginate(vaults)


@router.get("/vaults/{vault_id}", response_model=VaultResponse)
def get_vault(
    vault_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    if vault.privacy == PrivacyType.PRIVATE:
        if not user or user.id != vault.user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
    if user:
        stmt = Select(Reaction.type).where(
            Reaction.target_type == TargetType.VAULT,
            Reaction.target_id == vault_id,
            Reaction.user_id == user.id,
        )
        result = db.execute(stmt).scalar_one_or_none()
        if result:
            vault.user_reaction = result
    return vault


@router.put("/vaults/{vault_id}", response_model=VaultResponse)
def update_vault(
    vault: VaultCreate,
    vault_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_vault = (
        db.query(Vault).filter(Vault.id == vault_id, Vault.user_id == user.id).first()
    )
    if not db_vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    db_vault.title = vault.title
    db_vault.description = vault.description
    db_vault.privacy = vault.privacy
    db_vault.layout = vault.layout

    try:
        """with driver.session() as session:
        session.execute_write(update_vault_, db_vault)"""

        db.commit()
    except:
        raise HTTPException(status_code=500, detail="Internal error")
    return db_vault


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

    try:
        """with driver.session() as session:
        session.execute_write(delete_vault_, vault.id)"""

        db.delete(vault)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "Successfully deleted vault"}


@router.post("/vaults/{vault_id}/log")
def update_vault_log(vault_id: int, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    if not vault.last_updated:
        vault.last_updated = now

    if vault.last_updated and vault.last_updated + timedelta(days=1) < now:
        vault.last_updated = now
        log_vault_metric(db, vault, now)

    try:
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail"}


@router.post("/vaults/{vault_id}/reactions")
def react_to_vault(
    reaction: ReactionCreate,
    vault_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    stmt = Select(Reaction).where(
        Reaction.target_type == TargetType.VAULT,
        Reaction.target_id == vault_id,
        Reaction.user_id == user.id,
    )

    prev_reaction = ReactionType.NONE
    db_reaction = db.execute(stmt).scalar_one_or_none()
    if not db_reaction:
        new_reaction = Reaction(
            target_type=TargetType.VAULT,
            target_id=vault_id,
            user_id=user.id,
            type=reaction.type,
        )
        db.add(new_reaction)
    else:
        prev_reaction = db_reaction.type
        db_reaction.type = reaction.type

    try:
        update_reaction_count(vault, prev_reaction, reaction.type)
        """ with driver.session() as session:
            session.execute_write(
                react_to_vault_, user.id, vault.id, reaction.type.value
            ) """

        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "reaction added"}


@router.get("/vaults/{vault_id}/posts", response_model=CursorPage[EntryPreview])
def get_vault_posts(
    vault_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    if vault.privacy == PrivacyType.PRIVATE:
        if not user or user.id != vault.user_id:
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

    index = 0
    previous_index = (
        db.query(func.max(VaultPost.index))
        .filter(VaultPost.vault_id == vault.id)
        .scalar()
    )
    if previous_index is not None:
        index = previous_index + 1

    new_entry = VaultPost(vault_id=vault.id, post_id=post.id, index=index)
    post.saves += 1
    vault.post_count += 1

    # update previews
    previews = vault.previews or []
    previews.append(post.preview_url)
    vault.previews = previews[-3:]  # limit to 3
    flag_modified(vault, "previews")

    try:
        db.add(new_entry)

        """ with driver.session() as session:
            session.execute_write(add_post_, vault.id, post.id) """

        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
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

    vault_post = db.get(VaultPost, entry_id)
    if not vault_post:
        raise HTTPException(status_code=404, detail="Entry not found")

    try:
        """with driver.session() as session:
        session.execute_write(remove_post_, vault.id, vault_post.post_id)"""

        vault_post.post.saves -= 1
        vault.post_count -= 1
        db.delete(vault_post)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "Removed entry from vault"}
