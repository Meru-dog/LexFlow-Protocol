"""
LexFlow Protocol - RBAC & ACL API (V3)
役割管理、権限管理、契約書単位アクセス制御のエンドポイント
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, or_
from sqlalchemy.orm import selectinload
import json
import re

from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.models.models import (
    Workspace, User, UserStatus, Role, Permission, RolePermission,
    WorkspaceUser, WorkspaceUserStatus, ContractACL, ACLSubjectType, Contract, AuditEventType
)
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service


router = APIRouter(tags=["権限管理 (RBAC & ACL)"])


# ===== リクエスト/レスポンススキーマ =====

class WorkspaceCreate(BaseModel):
    """ワークスペース作成リクエスト"""
    name: str = Field(..., min_length=1, max_length=255)
    user_id: Optional[str] = None
    role_name: Optional[str] = "Owner"


class WorkspaceResponse(BaseModel):
    """ワークスペースレスポンス"""
    id: str
    name: str
    created_at: datetime


class RoleCreate(BaseModel):
    """ロール作成リクエスト"""
    name: str = Field(..., min_length=1, max_length=100)
    permission_ids: List[str] = []


class RoleResponse(BaseModel):
    """ロールレスポンス"""
    id: str
    workspace_id: str
    name: str
    is_custom: bool
    permissions: List[str] = []  # 権限キーのリスト


class RoleUpdate(BaseModel):
    """ロール更新リクエスト"""
    name: Optional[str] = None
    permission_ids: Optional[List[str]] = None


class PermissionResponse(BaseModel):
    """権限レスポンス"""
    id: str
    key: str
    description: Optional[str]
    category: Optional[str]


class WorkspaceUserInvite(BaseModel):
    """ワークスペースユーザー招待リクエスト"""
    user_id: str
    role_id: Optional[str] = None
    role_name: Optional[str] = None


class WorkspaceUserResponse(BaseModel):
    """ワークスペースユーザーレスポンス"""
    id: str
    workspace_id: str
    user_id: str
    role_id: str
    role_name: str
    status: str
    joined_at: Optional[datetime]
    email: Optional[str] = None
    display_name: Optional[str] = None


class WorkspaceUserRoleUpdate(BaseModel):
    """ワークスペースユーザーロール変更リクエスト"""
    role_id: str


class ContractACLCreate(BaseModel):
    """契約書ACL作成リクエスト"""
    subject_type: str = Field(..., pattern="^(user|role|external)$")
    subject_id: str
    permissions: List[str] = Field(..., description='["view", "edit", "approve"]')


class ContractACLResponse(BaseModel):
    """契約書ACLレスポンス"""
    id: str
    contract_id: str
    subject_type: str
    subject_id: str
    permissions: List[str]
    created_at: datetime


# ===== 標準権限の定義 =====
STANDARD_PERMISSIONS = [
    # ワークスペース管理
    {"key": "workspace:view", "description": "ワークスペース情報の閲覧", "category": "workspace"},
    {"key": "workspace:edit", "description": "ワークスペース設定の編集", "category": "workspace"},
    {"key": "workspace:invite", "description": "ユーザーの招待", "category": "workspace"},
    {"key": "workspace:remove_user", "description": "ユーザーの削除", "category": "workspace"},
    {"key": "workspace:manage_roles", "description": "ロールの管理", "category": "workspace"},
    
    # 契約書管理
    {"key": "contract:create", "description": "契約書の作成", "category": "contract"},
    {"key": "contract:view", "description": "契約書の閲覧（ACLによる制限あり）", "category": "contract"},
    {"key": "contract:edit", "description": "契約書の編集（ACLによる制限あり）", "category": "contract"},
    {"key": "contract:delete", "description": "契約書の削除", "category": "contract"},
    {"key": "contract:manage_acl", "description": "契約書ACLの管理", "category": "contract"},
    
    # 承認管理
    {"key": "approval:create_flow", "description": "承認フローの作成", "category": "approval"},
    {"key": "approval:request", "description": "承認依頼の作成", "category": "approval"},
    {"key": "approval:approve", "description": "承認の実行（ACLによる制限あり）", "category": "approval"},
    
    # 監査
    {"key": "audit:view", "description": "監査ログの閲覧", "category": "audit"},
    {"key": "audit:export", "description": "監査ログのエクスポート", "category": "audit"},
    
    # 通知
    {"key": "notification:manage", "description": "通知設定の管理", "category": "notification"},
]

# 標準ロールと権限のマッピング
STANDARD_ROLES = {
    "Owner": ["workspace:view", "workspace:edit", "workspace:invite", "workspace:remove_user", 
              "workspace:manage_roles", "contract:create", "contract:view", "contract:edit", 
              "contract:delete", "contract:manage_acl", "approval:create_flow", "approval:request",
              "approval:approve", "audit:view", "audit:export", "notification:manage"],
    "Admin": ["workspace:view", "workspace:invite", "workspace:remove_user", "workspace:manage_roles",
              "contract:create", "contract:view", "contract:edit", "contract:manage_acl",
              "approval:create_flow", "approval:request", "approval:approve", "audit:view", 
              "notification:manage"],
    "Manager": ["workspace:view", "contract:create", "contract:view", "contract:edit",
                "approval:create_flow", "approval:request", "approval:approve"],
    "Member": ["workspace:view", "contract:view", "contract:edit", "approval:request", "approval:approve"],
    "Approver": ["workspace:view", "contract:view", "approval:approve"],
    "Auditor": ["workspace:view", "contract:view", "audit:view", "audit:export"],
}


# ===== ワークスペースエンドポイント =====

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    ワークスペースを作成
    
    - 標準権限とロールを自動的に初期化
    """
    workspace_id = str(uuid.uuid4())
    
    # ワークスペース作成
    workspace = Workspace(id=workspace_id, name=request.name)
    db.add(workspace)
    
    # 標準権限を初期化（まだ存在しない場合）
    for perm_def in STANDARD_PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.key == perm_def["key"]))
        existing = result.scalar_one_or_none()
        if not existing:
            perm = Permission(
                id=str(uuid.uuid4()),
                key=perm_def["key"],
                description=perm_def["description"],
                category=perm_def["category"]
            )
            db.add(perm)
    await db.flush()  # 権限をコミットしてIDを確定
    
    # 標準ロールを作成
    target_role_id = None
    for role_name, permission_keys in STANDARD_ROLES.items():
        role_id = str(uuid.uuid4())
        role = Role(
            id=role_id,
            workspace_id=workspace_id,
            name=role_name,
            is_custom=False
        )
        db.add(role)
        
        # ターゲットとなるロールを特定
        if role_name == request.role_name:
            target_role_id = role_id
            
        # ロールに権限を紐付け
        for perm_key in permission_keys:
            result = await db.execute(select(Permission).where(Permission.key == perm_key))
            perm = result.scalar_one_or_none()
            if perm:
                role_perm = RolePermission(
                    id=str(uuid.uuid4()),
                    role_id=role_id,
                    permission_id=perm.id
                )
                db.add(role_perm)
    
    await db.flush()
    
    # 指定されたユーザー（デフォルトは作成者）をワークスペースに追加
    target_user_id = request.user_id or current_user_id
    if target_role_id:
        workspace_user = WorkspaceUser(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=target_user_id,
            role_id=target_role_id,
            status=WorkspaceUserStatus.ACTIVE,
            joined_at=datetime.utcnow()
        )
        db.add(workspace_user)
    
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.RBAC_ROLE_CREATED, # ロール作成も含む広義のRBAC操作として記録
        actor_id=current_user_id,
        workspace_id=workspace_id,
        resource_id=workspace_id,
        resource_type="workspace",
        detail={"name": request.name, "action": "workspace_created"}
    )
    
    await db.commit()
    await db.refresh(workspace)
    
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at
    )


@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """ユーザーが所属するワークスペース一覧を取得"""
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceUser)
        .where(WorkspaceUser.user_id == user_id)
    )
    workspaces = result.scalars().all()
    
    return [
        WorkspaceResponse(
            id=w.id,
            name=w.name,
            created_at=w.created_at
        )
        for w in workspaces
    ]


@router.get("/workspaces/{workspace_id}/roles", response_model=List[RoleResponse])
async def list_roles(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """ワークスペース内のロール一覧を取得"""
    result_roles = await db.execute(
        select(Role)
        .where(Role.workspace_id == workspace_id)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
    )
    roles = result_roles.scalars().all()
    
    result = []
    for role in roles:
        permission_keys = []
        for rp in role.permissions:
            if rp.permission:
                permission_keys.append(rp.permission.key)
        
        result.append(RoleResponse(
            id=role.id,
            workspace_id=role.workspace_id,
            name=role.name,
            is_custom=role.is_custom,
            permissions=permission_keys
        ))
    
    return result


@router.post("/workspaces/{workspace_id}/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(workspace_id: str, request: RoleCreate, db: AsyncSession = Depends(get_db)):
    """カスタムロールを作成"""
    # ワークスペース存在確認
    result_ws = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result_ws.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="ワークスペースが見つかりません")
    
    role_id = str(uuid.uuid4())
    role = Role(
        id=role_id,
        workspace_id=workspace_id,
        name=request.name,
        is_custom=True
    )
    db.add(role)
    db.flush()
    
    # 権限を紐付け
    for perm_id in request.permission_ids:
        result_perm = await db.execute(select(Permission).where(Permission.id == perm_id))
        perm = result_perm.scalar_one_or_none()
        if perm:
            role_perm = RolePermission(
                id=str(uuid.uuid4()),
                role_id=role_id,
                permission_id=perm_id
            )
            db.add(role_perm)
    
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.RBAC_ROLE_CREATED,
        workspace_id=workspace_id,
        resource_id=role_id,
        resource_type="role",
        detail={"name": request.name}
    )
    
    await db.commit()
    
    return RoleResponse(
        id=role_id,
        workspace_id=workspace_id,
        name=request.name,
        is_custom=True,
        permissions=[p.permission.key for p in role.permissions if p.permission]
    )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(role_id: str, request: RoleUpdate, db: AsyncSession = Depends(get_db)):
    """ロールを更新（カスタムロールのみ）"""
    result_role = await db.execute(select(Role).where(Role.id == role_id))
    role = result_role.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="ロールが見つかりません")
    
    if not role.is_custom:
        raise HTTPException(status_code=400, detail="標準ロールは編集できません")
    
    if request.name:
        role.name = request.name
    
    if request.permission_ids is not None:
        # 既存の権限を削除
        await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        
        # 新しい権限を追加
        for perm_id in request.permission_ids:
            role_perm = RolePermission(
                id=str(uuid.uuid4()),
                role_id=role_id,
                permission_id=perm_id
            )
            db.add(role_perm)
    
    await db.commit()
    await db.refresh(role)
    
    return RoleResponse(
        id=role.id,
        workspace_id=role.workspace_id,
        name=role.name,
        is_custom=role.is_custom,
        permissions=[p.permission.key for p in role.permissions if p.permission]
    )


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(db: AsyncSession = Depends(get_db)):
    """利用可能な権限一覧を取得"""
    result = await db.execute(select(Permission))
    permissions = result.scalars().all()
    return [
        PermissionResponse(
            id=p.id,
            key=p.key,
            description=p.description,
            category=p.category
        )
        for p in permissions
    ]


# ===== ワークスペースユーザーエンドポイント =====

@router.post("/workspaces/{workspace_id}/users", response_model=WorkspaceUserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(workspace_id: str, request: WorkspaceUserInvite, db: AsyncSession = Depends(get_db)):
    """ワークスペースにユーザーを招待"""
    # 存在確認
    result_ws = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result_ws.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="ワークスペースが見つかりません")
    
    # ユーザー特定 (ID, メール, または表示名で検索)
    result_user = await db.execute(
        select(User).where(
            or_(
                User.id == request.user_id,
                User.email == request.user_id,
                User.display_name == request.user_id
            )
     
        )
    )
    user = result_user.scalar_one_or_none()
    
    if not user:
        # 新しいユーザーを自動作成 (Quick Create)
        user_id = str(uuid.uuid4())
        # メールアドレス形式かチェック
        is_email = re.match(r"[^@]+@[^@]+\.[^@]+", request.user_id)
        email = request.user_id if is_email else f"{request.user_id}@pending.local"
        display_name = request.user_id
        
        user = User(
            id=user_id,
            email=email,
            display_name=display_name,
            password_hash="pending_invite", # プレースホルダー
            status=UserStatus.PENDING
        )
        db.add(user)
        # Flush to get user.id available for WorkspaceUser
        await db.flush()
    
    role = None
    if request.role_id:
        result_role = await db.execute(select(Role).where(Role.id == request.role_id, Role.workspace_id == workspace_id))
        role = result_role.scalar_one_or_none()
    elif request.role_name:
        # ロール名による検索 (大文字小文字を区別しない)
        result_role = await db.execute(
            select(Role).where(
                func.lower(Role.name) == func.lower(request.role_name),
                Role.workspace_id == workspace_id
            )
        )
        role = result_role.scalar_one_or_none()
        
    if not role:
        if request.role_name:
            # 新しいロールを自動作成 (Auto-Role Creation)
            role_id = str(uuid.uuid4())
            role = Role(
                id=role_id,
                workspace_id=workspace_id,
                name=request.role_name,
                is_custom=True
            )
            db.add(role)
            
            # 標準的な権限を付与 (Memberレベル)
            member_perms = ["contract:view", "approval:view", "workspace:view"]
            for perm_key in member_perms:
                res_perm = await db.execute(select(Permission).where(Permission.key == perm_key))
                perm = res_perm.scalar_one_or_none()
                if perm:
                    rp = RolePermission(
                        id=str(uuid.uuid4()),
                        role_id=role_id,
                        permission_id=perm.id
                    )
                    db.add(rp)
            
            await db.flush()
        else:
            raise HTTPException(status_code=404, detail=f"ロール '{request.role_id}' が見つかりません")
    
    # 重複チェック (user.id を使用)
    result_existing = await db.execute(select(WorkspaceUser).where(
        WorkspaceUser.workspace_id == workspace_id,
        WorkspaceUser.user_id == user.id
    ))
    existing = result_existing.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="このユーザーは既にワークスペースに所属しています")
    
    ws_user = WorkspaceUser(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        user_id=user.id, # Use found user.id instead of request.user_id (which could be email)
        role_id=role.id,
        status=WorkspaceUserStatus.INVITED
    )
    db.add(ws_user)
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.RBAC_USER_INVITED,
        workspace_id=workspace_id,
        resource_id=ws_user.id,
        resource_type="workspace_user",
        detail={"user_id": user.id, "role": role.name}
    )
    
    await db.commit()
    await db.refresh(ws_user)
    
    # ユーザーに招待通知を送信
    try:
        from app.core.config import settings
        payload = {
            "body": f"LexFlow Protocolのワークスペース「{workspace.name}」に招待されました。\n\n以下のリンクからログインしてください:\n{settings.FRONTEND_URL}/login",
            "html_body": f"""
            <h2>🏢 ワークスペースへの招待</h2>
            <p>LexFlow Protocolのワークスペース<strong>「{workspace.name}」</strong>に招待されました。</p>
            <p>役割: {role.name}</p>
            <p><a href="{settings.FRONTEND_URL}/login" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">ログインして開始する</a></p>
            """,
            "message": f"🏢 ワークスペース「{workspace.name}」に招待されました"
        }
        await notification_service.notify_user(
            db=db,
            user=user,
            subject=f"【LexFlow】ワークスペース招待: {workspace.name}",
            payload=payload
        )
    except Exception as e:
        print(f"[NOTIFICATION ERROR] 招待通知の送信に失敗しました: {str(e)}")
    
    return WorkspaceUserResponse(
        id=ws_user.id,
        workspace_id=ws_user.workspace_id,
        user_id=ws_user.user_id,
        role_id=ws_user.role_id,
        role_name=role.name,
        status=ws_user.status.value,
        joined_at=ws_user.joined_at
    )


@router.get("/workspaces/{workspace_id}/users", response_model=List[WorkspaceUserResponse])
async def list_workspace_users(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """ワークスペースのユーザー一覧を取得"""
    result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.workspace_id == workspace_id)
        .options(selectinload(WorkspaceUser.role), selectinload(WorkspaceUser.user))
    )
    ws_users = result.scalars().all()
    
    return [
        WorkspaceUserResponse(
            id=wu.id,
            workspace_id=wu.workspace_id,
            user_id=wu.user_id,
            role_id=wu.role_id,
            role_name=wu.role.name if wu.role else "",
            status=wu.status.value,
            joined_at=wu.joined_at,
            email=wu.user.email if wu.user else None,
            display_name=wu.user.display_name if wu.user else None
        )
        for wu in ws_users
    ]


@router.put("/workspace-users/{ws_user_id}/role", response_model=WorkspaceUserResponse)
async def update_user_role(ws_user_id: str, request: WorkspaceUserRoleUpdate, db: AsyncSession = Depends(get_db)):
    """ワークスペースユーザーのロールを変更"""
    result_wu = await db.execute(select(WorkspaceUser).where(WorkspaceUser.id == ws_user_id))
    ws_user = result_wu.scalar_one_or_none()
    if not ws_user:
        raise HTTPException(status_code=404, detail="ワークスペースユーザーが見つかりません")
    
    result_role = await db.execute(select(Role).where(
        Role.id == request.role_id,
        Role.workspace_id == ws_user.workspace_id
    ))
    role = result_role.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="ロールが見つかりません")
    
    ws_user.role_id = request.role_id
    await db.commit()
    await db.refresh(ws_user)
    
    return WorkspaceUserResponse(
        id=ws_user.id,
        workspace_id=ws_user.workspace_id,
        user_id=ws_user.user_id,
        role_id=ws_user.role_id,
        role_name=role.name,
        status=ws_user.status.value,
        joined_at=ws_user.joined_at
    )


# ===== 契約書ACLエンドポイント =====

@router.get("/contracts/{contract_id}/acl", response_model=List[ContractACLResponse])
async def list_contract_acl(contract_id: str, db: AsyncSession = Depends(get_db)):
    """契約書のACL一覧を取得"""
    result = await db.execute(select(ContractACL).where(ContractACL.contract_id == contract_id))
    acls = result.scalars().all()
    
    return [
        ContractACLResponse(
            id=acl.id,
            contract_id=acl.contract_id,
            subject_type=acl.subject_type.value,
            subject_id=acl.subject_id,
            permissions=json.loads(acl.permissions) if acl.permissions else [],
            created_at=acl.created_at
        )
        for acl in acls
    ]


@router.post("/contracts/{contract_id}/acl", response_model=ContractACLResponse, status_code=status.HTTP_201_CREATED)
async def create_contract_acl(contract_id: str, request: ContractACLCreate, db: AsyncSession = Depends(get_db)):
    """契約書にACLエントリを追加"""
    # 契約書存在確認
    result_contract = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result_contract.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="契約書が見つかりません")
    
    # subject_typeの変換
    subject_type = ACLSubjectType(request.subject_type)
    
    # 重複チェック
    result_existing = await db.execute(select(ContractACL).where(
        ContractACL.contract_id == contract_id,
        ContractACL.subject_type == subject_type,
        ContractACL.subject_id == request.subject_id
    ))
    existing = result_existing.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="このACLエントリは既に存在します")
    
    acl = ContractACL(
        id=str(uuid.uuid4()),
        contract_id=contract_id,
        subject_type=subject_type,
        subject_id=request.subject_id,
        permissions=json.dumps(request.permissions)
    )
    db.add(acl)
    await db.commit()
    await db.refresh(acl)
    
    return ContractACLResponse(
        id=acl.id,
        contract_id=acl.contract_id,
        subject_type=acl.subject_type.value,
        subject_id=acl.subject_id,
        permissions=request.permissions,
        created_at=acl.created_at
    )


@router.delete("/contracts/{contract_id}/acl/{acl_id}")
async def delete_contract_acl(contract_id: str, acl_id: str, db: AsyncSession = Depends(get_db)):
    """契約書のACLエントリを削除"""
    result_acl = await db.execute(select(ContractACL).where(
        ContractACL.id == acl_id,
        ContractACL.contract_id == contract_id
    ))
    acl = result_acl.scalar_one_or_none()
    if not acl:
        raise HTTPException(status_code=404, detail="ACLエントリが見つかりません")
    
    await db.delete(acl)
    await db.commit()
    
    return {"message": "ACLエントリを削除しました"}
