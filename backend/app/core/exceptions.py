"""Custom application exceptions with structured error responses."""
import uuid


class AppException(Exception):
    """Base application exception with code, message, details."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict | None = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.request_id = str(uuid.uuid4())
        self.status_code = status_code
        super().__init__(message)


# -- Business Exceptions --

class NotFoundException(AppException):
    def __init__(self, entity: str, identifier: str | None = None):
        super().__init__(
            code=f"{entity.upper()}_NOT_FOUND",
            message=f"{entity} not found" + (f": {identifier}" if identifier else ""),
            status_code=404,
        )


class ValidationException(AppException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details=details,
            status_code=400,
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


class ConflictException(AppException):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=409,
        )


# -- Specific Business Error Codes --

class InsufficientInventoryException(AppException):
    def __init__(self, available_grams: int, required_grams: int):
        super().__init__(
            code="INSUFFICIENT_INVENTORY",
            message="采购批次剩余库存不足",
            details={
                "available_grams": available_grams,
                "required_grams": required_grams,
            },
            status_code=409,
        )


class InvalidBatchStatusException(AppException):
    def __init__(self, current_status: str, expected: str):
        super().__init__(
            code="INVALID_BATCH_STATUS",
            message=f"批次当前状态为 {current_status}，无法执行此操作",
            details={"current_status": current_status, "expected": expected},
            status_code=409,
        )


class RoastingBatchNotCompletedException(AppException):
    def __init__(self):
        super().__init__(
            code="ROASTING_BATCH_NOT_COMPLETED",
            message="待烘批次不能创建问卷，请先完成烘焙",
            status_code=409,
        )


class QuestionnaireClosedException(AppException):
    def __init__(self):
        super().__init__(
            code="QUESTIONNAIRE_CLOSED",
            message="问卷已关闭，无法提交评价",
            status_code=409,
        )


class QuestionnaireExpiredException(AppException):
    def __init__(self):
        super().__init__(
            code="QUESTIONNAIRE_EXPIRED",
            message="问卷已过期，无法提交评价",
            status_code=409,
        )


class DuplicateCurveFileException(AppException):
    def __init__(self):
        super().__init__(
            code="CURVE_FILE_DUPLICATED",
            message="已上传过相同文件",
            status_code=409,
        )


class CurveParseFailedException(AppException):
    def __init__(self, error_message: str):
        super().__init__(
            code="CURVE_PARSE_FAILED",
            message=f"CSV 解析失败: {error_message}",
            status_code=422,
        )


class CurveAlignmentEventMissingException(AppException):
    """Raised when a required alignment event is missing during curve comparison."""
    def __init__(self, batch_id: str, event_type: str):
        super().__init__(
            code="CURVE_ALIGNMENT_EVENT_MISSING",
            message=f"批次 {batch_id} 缺少对齐事件: {event_type}",
            details={"batch_id": batch_id, "missing_event": event_type},
            status_code=400,
        )


class RegistrationClosedException(AppException):
    def __init__(self):
        super().__init__(
            code="REGISTRATION_CLOSED",
            message="系统已存在管理员，不再接受自助注册",
            status_code=403,
        )
