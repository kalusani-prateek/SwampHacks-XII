"""Crew hazard reports with photos, plus supervisor moderation."""
import re
import uuid

from flask import Blueprint, current_app, request, send_from_directory
from flask_login import current_user, login_required

from ..extensions import db
from ..models import REPORT_STATUSES, REPORT_TYPES, HazardReport, Site
from ..security import error, supervisor_required
from ..services import ingest
from ..services.events import bus
from .validation import number

bp = Blueprint("reports", __name__)

# Accepted photo formats, recognized by their first bytes (not by the file name).
SIGNATURES = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png", b"GIF87a": "gif", b"GIF89a": "gif"}
STORED_NAME = re.compile(r"^[a-f0-9]{32}\.(jpg|png|gif|webp)$")


def photo_extension(head):
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return next((ext for magic, ext in SIGNATURES.items() if head.startswith(magic)), None)


@bp.get("/reports")
@login_required
def list_reports():
    query = HazardReport.query
    if request.args.get("siteId"):
        query = query.filter_by(site_id=request.args["siteId"])
    if request.args.get("status") in REPORT_STATUSES:
        query = query.filter_by(status=request.args["status"])
    return {"reports": [r.to_dict() for r in query.order_by(HazardReport.created_at.desc()).limit(500)]}


@bp.post("/reports")
@login_required
def create_report():
    """multipart/form-data: siteId, type, description, lat, lng, photo (optional image)."""
    form = request.form
    site = db.session.get(Site, form.get("siteId") or "")
    if not site or not site.active:
        return error("Choose a valid site", 400)
    if form.get("type") not in REPORT_TYPES:
        return error("Choose a hazard type", 400)
    description = (form.get("description") or "").strip()
    if not 1 <= len(description) <= 1000:
        return error("Describe the hazard in 1-1000 characters", 400)
    try:
        lat = number(form.get("lat"), -90, 90, "Latitude")
        lng = number(form.get("lng"), -180, 180, "Longitude")
    except ValueError as exc:
        return error(str(exc), 400)

    filename = None
    photo = request.files.get("photo")
    if photo and photo.filename:
        head = photo.stream.read(16)
        ext = photo_extension(head)
        if not ext:
            return error("Photo must be a JPEG, PNG, GIF or WebP image", 400)
        photo.stream.seek(0)
        filename = f"{uuid.uuid4().hex}.{ext}"  # random name: never trust the uploaded file name
        photo.save(current_app.config["UPLOAD_FOLDER"] / filename)

    report = HazardReport(site_id=site.id, user_id=current_user.id, type=form["type"], description=description,
                          lat=lat, lng=lng, photo_filename=filename)
    db.session.add(report)
    db.session.commit()
    bus.publish({"type": "report", "reportId": report.id, "siteId": site.id})
    if report.type == "wildlife":
        ingest.rescore([site])  # crew wildlife reports raise the site's wildlife score
    return {"report": report.to_dict()}, 201


@bp.patch("/reports/<int:report_id>")
@supervisor_required
def update_report(report_id):
    report = db.session.get(HazardReport, report_id)
    if not report:
        return error("Report not found", 404)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in REPORT_STATUSES:
        return error(f"Status must be one of: {', '.join(REPORT_STATUSES)}", 400)
    report.status = status
    db.session.commit()
    if report.type == "wildlife":
        ingest.rescore([db.session.get(Site, report.site_id)])
    return {"report": report.to_dict()}


@bp.get("/uploads/<filename>")
@login_required
def uploaded_photo(filename):
    if not STORED_NAME.match(filename):
        return error("Not found", 404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, max_age=86400)
