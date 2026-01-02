"""
LexFlow Protocol - RBAC & ACL API (V3)
役割管理、権限管理、契約書単位アクセス制御のエンドポイント
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.models import (
    Workspace, User, Role, Permission, RolePermission,
    WorkspaceUser, WorkspaceUserStatus, ContractACL, ACLSubjectType, Contract
)


router = APIRouter(tags=["権限管理 (RBAC & ACL)"])


# ===== リクエスト/レスポンススキーマ =====

class WorkspaceCreate(BaseModel):
    """ワークスペース作成リクエスト"""
    name: str = Field(..., min_length=1, max_length=255)


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
    role_id: str


class WorkspaceUserResponse(BaseModel):
    """ワークスペースユーザーレスポンス"""
    id: str
    workspace_id: str
    user_id: str
    role_id: str
    role_name: str
    status: str
    joined_at: Optional[datetime]


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
async def create_workspace(request: WorkspaceCreate, db: Session = Depends(get_db)):
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
        existing = db.query(Permission).filter(Permission.key == perm_def["key"]).first()
        if not existing:
            perm = Permission(
                id=str(uuid.uuid4()),
                key=perm_def["key"],
                description=perm_def["description"],
                category=perm_def["category"]
            )
            db.add(perm)
    db.flush()  # 権限をコミットしてIDを確定
    
    # 標準ロールを作成
    for role_name, permission_keys in STANDARD_ROLES.items():
        role_id = str(uuid.uuid4())
        role = Role(
            id=role_id,
            workspace_id=workspace_id,
            name=role_name,
            is_custom=False
        )
        db.add(role)
        db.flush()
        
        # ロールに権限を紐付け
        for perm_key in permission_keys:
            perm = db.query(Permission).filter(Permission.key == perm_key).first()
            if perm:
                role_perm = RolePermission(
                    id=str(uuid.uuid4()),
                    role_id=role_id,
                    permission_id=perm.id
                )
                db.add(role_perm)
    
    db.commit()
    db.refresh(workspace)
    
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at
    )


@router.get("/workspaces/{workspace_id}/roles", response_model=List[RoleResponse])
async def list_roles(workspace_id: str, db: Session = Depends(get_db)):
    """ワークスペース内のロール一覧を取得"""
    roles = db.query(Role).filter(Role.workspace_id == workspace_id).all()
    
    result = []
    for role in roles:
        permission_keys = []
        for rp in role.permissions:
            perm = db.query(Permission).filter(Permission.id == rp.permission_id).first()
            if perm:
                permission_keys.append(perm.key)
        
        result.append(RoleResponse(
            id=role.id,
            workspace_id=role.workspace_id,
            name=role.name,
            is_custom=role.is_custom,
            permissions=permission_keys
        ))
    
    return result


@router.post("/workspaces/{workspace_id}/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(workspace_id: str, request: RoleCreate, db: Session = Depends(get_db)):
    """カスタムロールを作成"""
    # ワークスペース存在確認
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
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
        perm = db.query(Permission).filter(Permission.id == perm_id).first()
        if perm:
            role_perm = RolePermission(
                id=str(uuid.uuid4()),
                role_id=role_id,
                permission_id=perm_id
            )
            db.add(role_perm)
    
    db.commit()
    
    return RoleResponse(
        id=role_id,
        workspace_id=workspace_id,
        name=request.name,
        is_custom=True,
        permissions=[p.permission.key for p in role.permissions if p.permission]
    )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(role_id: str, request: RoleUpdate, db: Session = Depends(get_db)):
    """ロールを更新（カスタムロールのみ）"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="ロールが見つかりません")
    
    if not role.is_custom:
        raise HTTPException(status_code=400, detail="標準ロールは編集できません")
    
    if request.name:
        role.name = request.name
    
    if request.permission_ids is not None:
        # 既存の権限を削除
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        
        # 新しい権限を追加
        for perm_id in request.permission_ids:
            role_perm = RolePermission(
                id=str(uuid.uuid4()),
                role_id=role_id,
                permission_id=perm_id
            )
            db.add(role_perm)
    
    db.commit()
    db.refresh(role)
    
    return RoleResponse(
        id=role.id,
        workspace_id=role.workspace_id,
        name=role.name,
        is_custom=role.is_custom,
        permissions=[p.permission.key for p in role.permissions if p.permission]
    )


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(db: Session = Depends(get_db)):
    """利用可能な権限一覧を取得"""
    permissions = db.query(Permission).all()
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
async def invite_user(workspace_id: str, request: WorkspaceUserInvite, db: Session = Depends(get_db)):
    """ワークスペースにユーザーを招待"""
    # 存在確認
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="ワークスペースが見つかりません")
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    role = db.query(Role).filter(Role.id == request.role_id, Role.workspace_id == workspace_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="ロールが見つかりません")
    
    # 重複チェック
    existing = db.query(WorkspaceUser).filter(
        WorkspaceUser.workspace_id == workspace_id,
        WorkspaceUser.user_id == request.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="このユーザーは既にワークスペースに所属しています")
    
    ws_user = WorkspaceUser(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        user_id=request.user_id,
        role_id=request.role_id,
        status=WorkspaceUserStatus.INVITED
    )
    db.add(ws_user)
    db.commit()
    db.refresh(ws_user)
    
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
async def list_workspace_users(workspace_id: str, db: Session = Depends(get_db)):
    """ワークスペースのユーザー一覧を取得"""
    ws_users = db.query(WorkspaceUser).filter(WorkspaceUser.workspace_id == workspace_id).all()
    
    return [
        WorkspaceUserResponse(
            id=wu.id,
            workspace_id=wu.workspace_id,
            user_id=wu.user_id,
            role_id=wu.role_id,
            role_name=wu.role.name if wu.role else "",
            status=wu.status.value,
            joined_at=wu.joined_at
        )
        for wu in ws_users
    ]


@router.put("/workspace-users/{ws_user_id}/role", response_model=WorkspaceUserResponse)
async def update_user_role(ws_user_id: str, request: WorkspaceUserRoleUpdate, db: Session = Depends(get_db)):
    """ワークスペースユーザーのロールを変更"""
    ws_user = db.query(WorkspaceUser).filter(WorkspaceUser.id == ws_user_id).first()
    if not ws_user:
        raise HTTPException(status_code=404, detail="ワークスペースユーザーが見つかりません")
    
    role = db.query(Role).filter(
        Role.id == request.role_id,
        Role.workspace_id == ws_user.workspace_id
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="ロールが見つかりません")
    
    ws_user.role_id = request.role_id
    db.commit()
    db.refresh(ws_user)
    
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
async def list_contract_acl(contract_id: str, db: Session = Depends(get_db)):
    """契約書のACL一覧を取得"""
    acls = db.query(ContractACL).filter(ContractACL.contract_id == contract_id).all()
    
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
async def create_contract_acl(contract_id: str, request: ContractACLCreate, db: Session = Depends(get_db)):
    """契約書にACLエントリを追加"""
    # 契約書存在確認
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="契約書が見つかりません")
    
    # subject_typeの変換
    subject_type = ACLSubjectType(request.subject_type)
    
    # 重複チェック
    existing = db.query(ContractACL).filter(
        ContractACL.contract_id == contract_id,
        ContractACL.subject_type == subject_type,
        ContractACL.subject_id == request.subject_id
    ).first()
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
    db.commit()
    db.refresh(acl)
    
    return ContractACLResponse(
        id=acl.id,
        contract_id=acl.contract_id,
        subject_type=acl.subject_type.value,
        subject_id=acl.subject_id,
        permissions=request.permissions,
        created_at=acl.created_at
    )


@router.delete("/contracts/{contract_id}/acl/{acl_id}")
async def delete_contract_acl(contract_id: str, acl_id: str, db: Session = Depends(get_db)):
    """契約書のACLエントリを削除"""
    acl = db.query(ContractACL).filter(
        ContractACL.id == acl_id,
        ContractACL.contract_id == contract_id
    ).first()
    if not acl:
        raise HTTPException(status_code=404, detail="ACLエントリが見つかりません")
    
    db.delete(acl)
    db.commit()
    
    return {"message": "ACLエントリを削除しました"}
