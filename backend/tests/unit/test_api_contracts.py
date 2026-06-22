"""OpenAPI-level acceptance checks for internal and public route contracts."""

from app.main import app


def test_bulk_import_and_backfill_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "/api/v1/purchase-batches/{purchase_batch_id}/roasting-batches/bulk-preview" in paths
    assert "/api/v1/purchase-batches/{purchase_batch_id}/roasting-batches/bulk-commit" in paths
    assert "/api/v1/backfills/roasting-csv/preview" in paths
    assert "/api/v1/backfills/roasting-csv/commit" in paths


def test_internal_routes_require_bearer_authentication():
    paths = app.openapi()["paths"]
    protected = (
        ("/api/v1/green-beans/tree", "get"),
        ("/api/v1/roasting-batches", "get"),
        ("/api/v1/purchase-batches/{purchase_batch_id}/roasting-batches/bulk-preview", "post"),
        ("/api/v1/backfills/roasting-csv/preview", "post"),
        ("/api/v1/dashboard", "get"),
    )
    for path, method in protected:
        assert paths[path][method]["security"] == [{"HTTPBearer": []}]


def test_public_questionnaire_routes_remain_anonymous():
    paths = app.openapi()["paths"]
    assert "security" not in paths["/api/v1/public/questionnaires/{share_code}"]["get"]
    assert "security" not in paths["/api/v1/public/questionnaires/{share_code}/evaluations"]["post"]
