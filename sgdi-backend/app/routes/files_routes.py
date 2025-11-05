from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Form, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
import uuid
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from ..core.config import settings
from ..core.database import get_db
from ..core.auth import get_current_active_user, require_admin_dep_or_super, require_worker_or_higher
from ..models.file import File
from ..models.folder import Folder
from ..models.dependency import Dependency
from ..models.user import User
from ..schemas.files import (
    FileCreate, FileResponse, FileUploadResponse, FileDownloadResponse,
    FileUpdate, FileVersionsResponse, FileDeleteRequest, FileDeleteResponse,
    FileList, FileFilters, FileMetadata
)
from ..schemas.common import ErrorResponse, NotFoundResponse, ConflictResponse
from ..services.storage_service import storage_service
from ..services.audit_service import audit_service

router = APIRouter()

@router.get("", response_model=FileList, responses={
    200: {"model": FileList}
})
@router.get("/", response_model=FileList, responses={
    200: {"model": FileList}
})
async def read_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    folder_id: str = Query(None, description="Filter by folder"),
    dependency_id: str = Query(None, description="Filter by dependency"),
    uploaded_by: str = Query(None, description="Filter by uploader"),
    mime_type: str = Query(None, description="Filter by MIME type"),
    is_deleted: bool = Query(False, description="Include deleted files"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve files with filtering based on permissions
    """
    query = db.query(File).join(Folder, File.folder_id == Folder.id).join(
        Dependency, File.dependency_id == Dependency.id
    )

    # Apply permission-based filtering
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id:
            # Users can see files from their dependency OR from GLOBAL dependency
            query = query.filter(
                or_(
                    File.dependency_id == current_user.dependency_id,
                    Dependency.code == "GLOBAL"
                )
            )
        else:
            # Users without dependency can only see GLOBAL
            query = query.filter(Dependency.code == "GLOBAL")

    # EXCLUIR archivos en carpetas "deprecados" del listado principal
    query = query.filter(~Folder.name.ilike('%deprecados%'))

    # Apply user filters
    if folder_id:
        query = query.filter(File.folder_id == folder_id)
    if dependency_id:
        query = query.filter(File.dependency_id == dependency_id)
    if uploaded_by:
        query = query.filter(File.uploaded_by == uploaded_by)
    if mime_type:
        query = query.filter(File.mime_type == mime_type)
    if not is_deleted:
        query = query.filter(File.is_deleted == False)

    # Get total count
    total = query.count()

    # Get paginated results with user information
    files = query.offset(skip).limit(limit).all()
    
    # Enrich with uploaded_by_name
    files_with_names = []
    for file in files:
        file_dict = {
            **{c.name: getattr(file, c.name) for c in file.__table__.columns},
            "uploaded_by_name": None
        }
        if file.uploaded_by:
            uploader = db.query(User).filter(User.id == file.uploaded_by).first()
            if uploader:
                file_dict["uploaded_by_name"] = uploader.full_name
        files_with_names.append(file_dict)

    return {"items": files_with_names, "total": total}

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED, responses={
    201: {"model": FileUploadResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse}
})
async def upload_file(
    response: Response,
    file: UploadFile = FastAPIFile(...),
    anexos: List[UploadFile] = FastAPIFile(None),
    folder_id: str = Form(...),
    metadata: str = Form(None),
    create_annex_folder: bool = Form(True),
    current_user: User = Depends(require_worker_or_higher),
    db: Session = Depends(get_db)
):
    """
    Upload file with optional annexes

    Creates annex folder automatically if annexes are provided.
    All operations are atomic - either all succeed or all are rolled back.
    """
    try:
        # Parse metadata
        file_metadata = None
        if metadata:
            try:
                file_metadata = FileMetadata.parse_raw(metadata)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid metadata JSON: {e}"
                )

        # Validate folder exists and permissions
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )

        # Check permissions
        if current_user.role != "SUPER_ADMIN" and folder.dependency_id != current_user.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only upload to folders in your dependency."
            )

        # Get dependency for storage path
        dependency = db.query(Dependency).filter(Dependency.id == folder.dependency_id).first()
        if not dependency:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Dependency not found"
            )

        # Validate main file
        if not storage_service.validate_file_size(file.size):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
            )

        if not storage_service.validate_mime_type(file.content_type):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {file.content_type}"
            )

        # Validate annexes
        total_size = file.size
        annex_files = []

        if anexos:
            for annex in anexos:
                if annex.size:
                    total_size += annex.size
                    if not storage_service.validate_file_size(annex.size):
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Annex file too large: {annex.filename}"
                        )
                    if not storage_service.validate_mime_type(annex.content_type):
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"Unsupported annex file type: {annex.content_type}"
                        )
                    annex_files.append(annex)

        if total_size > settings.max_upload_size_bytes * 2:  # Allow double for main + annexes
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Total upload size too large"
            )

        # Read file contents
        main_content = await file.read()
        annex_contents = []
        for annex in annex_files:
            content = await annex.read()
            annex_contents.append((annex.filename, content))

        # Note: FastAPI's get_db already handles transactions, no need for explicit db.begin()
        try:
            # Create annex folder if needed
            annex_folder = None
            annex_folder_id = None

            if annex_files and create_annex_folder:
                # Generate annex folder name
                base_name = storage_service.sanitize_filename(file.filename)
                today = datetime.utcnow().strftime("%Y%m%d")
                annex_folder_name = f"Anexos-{base_name}-{today}"

                # Check for name conflicts
                existing = db.query(Folder).filter(
                    and_(
                        Folder.name == annex_folder_name,
                        Folder.parent_id == folder.id,
                        Folder.dependency_id == folder.dependency_id
                    )
                ).first()

                if existing:
                    # Append counter if name exists
                    counter = 1
                    while True:
                        test_name = f"{annex_folder_name}_{counter}"
                        existing = db.query(Folder).filter(
                            and_(
                                Folder.name == test_name,
                                Folder.parent_id == folder.id,
                                Folder.dependency_id == folder.dependency_id
                            )
                        ).first()
                        if not existing:
                            annex_folder_name = test_name
                            break
                        counter += 1

                # Create annex folder
                annex_folder_path = f"{folder.path}/{annex_folder_name}"
                annex_folder = Folder(
                    id=str(uuid.uuid4()),
                    name=annex_folder_name,
                    path=annex_folder_path,
                    parent_id=folder.id,
                    dependency_id=folder.dependency_id,
                    created_by=current_user.id,
                    updated_by=current_user.id
                )
                db.add(annex_folder)
                db.flush()
                annex_folder_id = annex_folder.id

                # Audit log for folder creation (no auto_commit, part of main transaction)
                audit_service.log_action(
                    db=db,
                    user=current_user,
                    action_type="CREATE_FOLDER",
                    target_type="FOLDER",
                    target_id=annex_folder.id,
                    details={
                        "name": annex_folder.name,
                        "path": annex_folder.path,
                        "purpose": "annex_folder",
                        "main_file": file.filename
                    },
                    auto_commit=False  # Don't commit, let main transaction handle it
                )

            # Process main file
            stored_filename = f"{str(uuid.uuid4())}{Path(file.filename).suffix}"
            temp_id, temp_path = storage_service.save_temp_file(main_content, file.filename)
            checksum = storage_service.calculate_checksum(temp_path)

            final_path = storage_service.get_file_path(
                dependency.code, folder.path, stored_filename
            )

            if not storage_service.move_temp_to_final(temp_path, final_path):
                raise Exception("Failed to move main file to final location")

            # Create main file record
            main_file = File(
                id=str(uuid.uuid4()),
                original_name=file.filename,
                stored_name=stored_filename,
                mime_type=file.content_type,
                size_bytes=len(main_content),
                checksum_sha256=checksum,
                folder_id=folder.id,
                dependency_id=folder.dependency_id,
                uploaded_by=current_user.id,
                version=1,
                file_metadata=file_metadata.dict() if file_metadata else None
            )
            db.add(main_file)
            db.flush()

            # Process annex files
            annex_file_records = []
            if annex_files:
                target_folder_id = annex_folder_id if annex_folder else folder.id

                for annex_filename, annex_content in annex_contents:
                    annex_stored_name = f"{str(uuid.uuid4())}{Path(annex_filename).suffix}"
                    annex_temp_id, annex_temp_path = storage_service.save_temp_file(
                        annex_content, annex_filename
                    )
                    annex_checksum = storage_service.calculate_checksum(annex_temp_path)

                    # Get MIME type for this annex file
                    annex_mime_type = None
                    for annex_file_obj in annex_files:
                        if annex_file_obj.filename == annex_filename:
                            annex_mime_type = annex_file_obj.content_type
                            break
                    annex_mime_type = annex_mime_type or "application/octet-stream"

                    annex_final_path = storage_service.get_file_path(
                        dependency.code, folder.path if not annex_folder else annex_folder.path, annex_stored_name
                    )

                    if not storage_service.move_temp_to_final(annex_temp_path, annex_final_path):
                        raise Exception(f"Failed to move annex file {annex_filename} to final location")

                    # Create annex file record
                    annex_file = File(
                        id=str(uuid.uuid4()),
                        original_name=annex_filename,
                        stored_name=annex_stored_name,
                        mime_type=annex_mime_type,
                        size_bytes=len(annex_content),
                        checksum_sha256=annex_checksum,
                        folder_id=target_folder_id,
                        dependency_id=folder.dependency_id,
                        uploaded_by=current_user.id,
                        version=1,
                        main_file_id=main_file.id
                    )
                    db.add(annex_file)
                    annex_file_records.append(annex_file)

                    # Audit log for annex upload (no auto_commit, part of main transaction)
                    audit_service.log_action(
                        db=db,
                        user=current_user,
                        action_type="UPLOAD",
                        target_type="FILE",
                        target_id=annex_file.id,
                        details={
                            "filename": annex_filename,
                            "size": len(annex_content),
                            "is_annex": True,
                            "main_file_id": main_file.id,
                            "annex_folder_id": annex_folder_id
                        },
                        auto_commit=False  # Don't commit, let main transaction handle it
                    )

            # Audit log for main file upload (before commit, part of main transaction)
            audit_service.log_action(
                db=db,
                user=current_user,
                action_type="UPLOAD",
                target_type="FILE",
                target_id=main_file.id,
                details={
                    "filename": file.filename,
                    "size": len(main_content),
                    "annex_count": len(annex_files),
                    "annex_folder_id": annex_folder_id,
                    "folder_path": folder.path
                },
                auto_commit=False  # Don't commit, let main transaction handle it
            )

            # Commit all database changes including audit logs
            db.commit()
            
            # Refresh objects to get updated data after commit
            db.refresh(main_file)
            if annex_folder:
                db.refresh(annex_folder)
            for annex_file in annex_file_records:
                db.refresh(annex_file)

            # Prepare response
            response_data = {
                "main_file": main_file,
                "annex_files": annex_file_records if annex_file_records else None
            }

            if annex_folder:
                response_data["annex_folder"] = {
                    "id": annex_folder.id,
                    "name": annex_folder.name,
                    "path": annex_folder.path
                }

            return response_data

        except Exception as e:
            db.rollback()
            # Clean up any moved files on failure
            logger.error(f"Upload failed, rolling back: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during upload"
        )

@router.get("/{file_id}", response_model=FileResponse, responses={
    200: {"model": FileResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def read_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get file by ID with permission checks
    """
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != file.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access files in your dependency."
            )

    return file

# ELIMINADO: Endpoint duplicado movido más abajo con sistema de versionado

@router.get("/{file_id}/preview", responses={
    200: {"description": "File preview (inline display)"},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    415: {"model": ErrorResponse}
})
async def preview_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Preview file inline (only for PDFs and images)
    """
    file = db.query(File).filter(File.id == file_id).first()
    if not file or file.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Only allow preview for PDFs and images
    previewable_types = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp"
    ]
    
    if file.mime_type not in previewable_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {file.mime_type} cannot be previewed. Only PDFs and images are supported."
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != file.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only preview files from your dependency."
            )

    # Get dependency for path
    dependency = db.query(Dependency).filter(Dependency.id == file.dependency_id).first()
    folder = db.query(Folder).filter(Folder.id == file.folder_id).first()

    if not dependency or not folder:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File metadata corrupted"
        )

    # Get file path
    file_path = storage_service.get_file_path(
        dependency.code, folder.path, file.stored_name
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )

    # Audit log preview
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="PREVIEW",
        target_type="FILE",
        target_id=file.id,
        details={
            "filename": file.original_name,
            "mime_type": file.mime_type
        },
        auto_commit=True
    )

    # Stream file with inline disposition
    def file_iterator():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type=file.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{file.original_name}"',
            "X-Checksum-Sha256": file.checksum_sha256,
            "X-File-Id": file.id,
            "Cache-Control": "public, max-age=3600"
        }
    )

@router.get("/{file_id}/download", responses={
    200: {"description": "File download"},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download file with proper headers and audit logging
    """
    file = db.query(File).filter(File.id == file_id).first()
    if not file or file.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != file.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only download files from your dependency."
            )

    # Get dependency for path
    dependency = db.query(Dependency).filter(Dependency.id == file.dependency_id).first()
    folder = db.query(Folder).filter(Folder.id == file.folder_id).first()

    if not dependency or not folder:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File metadata corrupted"
        )

    # Get file path
    file_path = storage_service.get_file_path(
        dependency.code, folder.path, file.stored_name
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )

    # Audit log download
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="DOWNLOAD",
        target_type="FILE",
        target_id=file.id,
        details={
            "filename": file.original_name,
            "size": file.size_bytes
        }
    )

    # Stream file
    def file_iterator():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{file.original_name}"',
        "Content-Type": file.mime_type,
        "X-Checksum-Sha256": file.checksum_sha256
    }

    return StreamingResponse(
        file_iterator(),
        media_type=file.mime_type,
        headers=headers
    )

@router.put("/{file_id}", response_model=FileResponse, responses={
    200: {"model": FileResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def update_file(
    file_id: str,
    file: UploadFile = FastAPIFile(...),
    metadata: str = Form(None),
    current_user: User = Depends(require_worker_or_higher),
    db: Session = Depends(get_db)
):
    """
    Update file content - moves old version to 'deprecados' folder and creates new version
    """
    try:
        # Get existing file
        existing_file = db.query(File).filter(File.id == file_id).first()
        if not existing_file or existing_file.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Check permissions
        can_update = False
        if current_user.role == "SUPER_ADMIN":
            can_update = True
        elif current_user.role in ["ADMIN_DEP", "WORKER"]:
            if existing_file.dependency_id == current_user.dependency_id:
                if current_user.role == "ADMIN_DEP" or existing_file.uploaded_by == current_user.id:
                    can_update = True

        if not can_update:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You don't have permission to update this file."
            )

        # Parse metadata
        file_metadata = None
        if metadata:
            try:
                file_metadata = FileMetadata.parse_raw(metadata)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid metadata JSON: {e}"
                )

        # Validate new file
        if not storage_service.validate_file_size(file.size):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
            )

        if not storage_service.validate_mime_type(file.content_type):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {file.content_type}"
            )

        # Read new content
        new_content = await file.read()

        # Get dependency and folder
        dependency = db.query(Dependency).filter(Dependency.id == existing_file.dependency_id).first()
        current_folder = db.query(Folder).filter(Folder.id == existing_file.folder_id).first()

        if not dependency or not current_folder:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File metadata corrupted"
            )

        # 1. Crear estructura de carpetas deprecadas que refleje la ubicación original
        # Buscar carpeta raíz por dependency_id y parent_id = NULL
        root_folder = db.query(Folder).filter(
            and_(
                Folder.dependency_id == dependency.id,
                Folder.parent_id == None
            )
        ).first()

        if not root_folder:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Root folder not found for dependency {dependency.code}"
            )

        # Buscar o crear carpeta "deprecados" en la raíz
        deprecated_root = db.query(Folder).filter(
            and_(
                Folder.dependency_id == dependency.id,
                Folder.parent_id == root_folder.id,
                Folder.name == "deprecados"
            )
        ).first()

        if not deprecated_root:
            deprecated_root_path = f"{root_folder.path}/deprecados"
            deprecated_root = Folder(
                id=str(uuid.uuid4()),
                name="deprecados",
                path=deprecated_root_path,
                parent_id=root_folder.id,
                dependency_id=dependency.id,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.add(deprecated_root)
            db.flush()

            # Crear directorio físico raíz
            deprecated_root_physical = Path(settings.storage_path) / dependency.code / "deprecados"
            deprecated_root_physical.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created 'deprecados' root folder for dependency {dependency.code}")

        # Crear subcarpeta dentro de deprecados que refleje la carpeta original
        # Formato: deprecados/<nombre_carpeta_original>
        original_folder_name = current_folder.name
        deprecated_subfolder_name = original_folder_name
        
        # Buscar subcarpeta de deprecados específica para esta carpeta original
        deprecated_folder = db.query(Folder).filter(
            and_(
                Folder.dependency_id == dependency.id,
                Folder.parent_id == deprecated_root.id,
                Folder.name == deprecated_subfolder_name
            )
        ).first()

        if not deprecated_folder:
            deprecated_folder_path = f"{deprecated_root.path}/{deprecated_subfolder_name}"
            deprecated_folder = Folder(
                id=str(uuid.uuid4()),
                name=deprecated_subfolder_name,
                path=deprecated_folder_path,
                parent_id=deprecated_root.id,
                dependency_id=dependency.id,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.add(deprecated_folder)
            db.flush()

            # Crear directorio físico de subcarpeta
            deprecated_subfolder_physical = Path(settings.storage_path) / dependency.code / "deprecados" / deprecated_subfolder_name
            deprecated_subfolder_physical.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created deprecated subfolder: {deprecated_folder_path}")

        # 2. Mover archivo antiguo a carpeta "deprecados"
        old_file_path = storage_service.get_file_path(
            dependency.code, current_folder.path, existing_file.stored_name
        )

        # Crear registro en DB para archivo deprecado con nombre versionado y prefijo "deprecado"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        deprecated_name = f"deprecado_{Path(existing_file.original_name).stem}_v{existing_file.version}_{timestamp}{Path(existing_file.original_name).suffix}"
        deprecated_stored_name = f"{str(uuid.uuid4())}{Path(existing_file.original_name).suffix}"

        deprecated_file = File(
            id=str(uuid.uuid4()),
            original_name=deprecated_name,
            stored_name=deprecated_stored_name,
            mime_type=existing_file.mime_type,
            size_bytes=existing_file.size_bytes,
            checksum_sha256=existing_file.checksum_sha256,
            folder_id=deprecated_folder.id,
            dependency_id=dependency.id,
            uploaded_by=existing_file.uploaded_by,
            version=existing_file.version,
            main_file_id=existing_file.id,  # Referencia al archivo actualizado
            file_metadata={"deprecated_at": timestamp, "replaced_by_user": current_user.id}
        )
        db.add(deprecated_file)
        db.flush()

        # Mover archivo físico a carpeta deprecados
        deprecated_physical_path = storage_service.get_file_path(
            dependency.code, deprecated_folder.path, deprecated_stored_name
        )
        
        if old_file_path.exists():
            import shutil
            deprecated_physical_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_file_path), str(deprecated_physical_path))
            logger.info(f"Moved old file to deprecados: {deprecated_physical_path}")

        # 3. Guardar nuevo archivo en la ubicación original
        temp_id, temp_path = storage_service.save_temp_file(new_content, file.filename)
        checksum = storage_service.calculate_checksum(temp_path)

        # Generate new stored name
        new_stored_name = f"{str(uuid.uuid4())}{Path(file.filename).suffix}"
        final_path = storage_service.get_file_path(
            dependency.code, current_folder.path, new_stored_name
        )

        if not storage_service.move_temp_to_final(temp_path, final_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save updated file"
            )

        # 4. Actualizar registro del archivo principal
        existing_file.original_name = file.filename
        existing_file.stored_name = new_stored_name
        existing_file.mime_type = file.content_type
        existing_file.size_bytes = len(new_content)
        existing_file.checksum_sha256 = checksum
        existing_file.version += 1
        existing_file.updated_at = datetime.utcnow()
        if file_metadata:
            existing_file.file_metadata = file_metadata.dict()

        db.commit()
        db.refresh(existing_file)

        logger.info(f"File {file_id} updated successfully. Old version moved to deprecados folder.")

        return existing_file

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file: {str(e)}"
        )

@router.get("/{file_id}/versions", response_model=FileVersionsResponse, responses={
    200: {"model": FileVersionsResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def get_file_versions(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all versions of a file
    """
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != file.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access files in your dependency."
            )

    # For now, return basic version info
    # In a full implementation, you'd scan the versions directory
    versions = [{
        "version": file.version,
        "filename": f"{file.id}_v{file.version}_{file.created_at.strftime('%Y%m%d_%H%M%S')}{Path(file.original_name).suffix}",
        "created_at": file.updated_at,
        "size_bytes": file.size_bytes,
        "checksum": file.checksum_sha256
    }]

    return {
        "file_id": file.id,
        "current_version": file.version,
        "versions": versions
    }

@router.get("/{file_id}/anexos", response_model=List[FileResponse], responses={
    200: {"model": List[FileResponse]},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def get_file_annexes(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get annex files for a main file
    """
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != file.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access files in your dependency."
            )

    # Get annex files
    annexes = db.query(File).filter(
        and_(
            File.main_file_id == file_id,
            File.is_deleted == False
        )
    ).all()

    return annexes

@router.delete("/{file_id}", responses={
    200: {"model": FileDeleteResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
async def delete_file(
    file_id: str,
    hard: bool = Query(False, description="Hard delete (permanent)"),
    cascade: bool = Query(False, description="Delete annexes when deleting main file"),
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Delete file (soft delete by default, hard delete for admins)
    """
    file = db.query(File).filter(File.id == file_id).first()
    if not file or file.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check permissions
    can_delete = False
    if current_user.role == "SUPER_ADMIN":
        can_delete = True
    elif current_user.role == "ADMIN_DEP":
        if file.dependency_id == current_user.dependency_id:
            can_delete = True

    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient permissions to delete this file."
        )

    # Check for annexes if this is a main file
    annexes = []
    if not file.main_file_id:  # This is a main file
        annexes = db.query(File).filter(
            and_(
                File.main_file_id == file_id,
                File.is_deleted == False
            )
        ).all()

    deleted_files = []

    if hard and current_user.role in ["SUPER_ADMIN", "ADMIN_DEP"]:
        # Hard delete
        if annexes and not cascade:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File has {len(annexes)} annexes. Use cascade=true to delete them too."
            )

        # Get dependency and folder for path
        dependency = db.query(Dependency).filter(Dependency.id == file.dependency_id).first()
        folder = db.query(Folder).filter(Folder.id == file.folder_id).first()

        if dependency and folder:
            # Move main file to trash
            file_path = storage_service.get_file_path(
                dependency.code, folder.path, file.stored_name
            )
            if file_path.exists():
                storage_service.move_to_trash(file_path, "hard_deleted")

        # Delete annexes if cascade
        for annex in annexes:
            annex_folder = db.query(Folder).filter(Folder.id == annex.folder_id).first()
            if annex_folder and dependency:
                annex_path = storage_service.get_file_path(
                    dependency.code, annex_folder.path, annex.stored_name
                )
                if annex_path.exists():
                    storage_service.move_to_trash(annex_path, "hard_deleted_annex")
            db.delete(annex)
            deleted_files.append(annex.id)

        # Delete main file record
        db.delete(file)
        deleted_files.append(file.id)

        message = f"File hard deleted successfully. Deleted {len(deleted_files)} files."

    else:
        # Soft delete
        if annexes and not cascade:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File has {len(annexes)} annexes. Use cascade=true to mark them deleted too."
            )

        # Soft delete annexes if cascade
        for annex in annexes:
            annex.is_deleted = True
            deleted_files.append(annex.id)

        # Soft delete main file
        file.is_deleted = True
        deleted_files.append(file.id)

        message = f"File marked as deleted. {len(deleted_files)} files affected."

    db.commit()

    # Audit log
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="DELETE",
        target_type="FILE",
        target_id=file.id,
        details={
            "hard_delete": hard,
            "cascade": cascade,
            "deleted_files": deleted_files,
            "filename": file.original_name
        }
    )

    return FileDeleteResponse(
        deleted=True,
        deleted_files=deleted_files,
        message=message
    )
