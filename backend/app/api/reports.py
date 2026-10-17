"""Crew hazard reports with photos. Everyone can browse and search them; the reporter
or a supervisor can edit or delete one; only supervisors change its status."""
import re
import uuid
from datetime import timedelta

from flask import Blueprint, current_app, request, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..models import REPORT_STATUSES, REPORT_TYPES, HazardReport, Site, User, utcnow
from ..security import error
from ..services import ingest
from ..services.events import bus
from .validation import number

bp = Blueprint("reports", __name__)

# Accepted photo formats, recognized by their first bytes (not by the file name).
SIGNATURES = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png", b"GIF87a": "gif", b"GIF89a": "gif"}
STORED_NAME = re.compile(r"^[a-f0-9]{32}\.(jpg|png|gif|webp)$")
MAX_SEARCH_CHARS = 100


def photo_extension(head):
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return next((ext for magic, ext in SIGNATURES.items() if head.startswith(magic)), None)


def remove_photo(filename):
    """Delete a stored photo (a missing file is fine)."""
    if filename and STORED_NAME.match(filename):
        (current_app.config["UPLOAD_FOLDER"] / filename).unlink(missing_ok=True)


def contains(text):
    """LIKE pattern matching `text` anywhere, with LIKE's own wildcards (% and _) escaped."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@bp.get("/reports")
@login_required
def list_reports():
    """Newest first. Filters: siteId, type, status, days (reported in the last N days),
    q (words in the description, reporter or site name), mine=true (your own reports)."""
    args = request.args
    query = HazardReport.query
    if args.get("siteId"):
        query = query.filter_by(site_id=args["siteId"])
    if args.get("type") in REPORT_TYPES:
        query = query.filter_by(type=args["type"])
    if args.get("status") in REPORT_STATUSES:
        query = query.filter_by(status=args["status"])
    if args.get("mine") == "true":
        query = query.filter_by(user_id=current_user.id)
    if args.get("days"):
        try:
            days = int(args["days"])
            if not 1 <= days <= 3650:
                raise ValueError
        except ValueError:
            return error("days must be a whole number from 1 to 3650", 400)
        query = query.filter(HazardReport.created_at >= utcnow() - timedelta(days=days))
    q = (args.get("q") or "").strip()[:MAX_SEARCH_CHARS]
    if q:
        pattern = contains(q)
        query = (query.outerjoin(User, HazardReport.user_id == User.id).join(Site, HazardReport.site_id == Site.id)
                 .filter(or_(HazardReport.description.ilike(pattern, escape="\\"),
                             User.username.ilike(pattern, escape="\\"),
                             Site.name.ilike(pattern, escape="\\"))))
    reports = query.order_by(HazardReport.created_at.desc()).limit(500)
    return {"reports": [r.to_dict(current_user) for r in reports]}


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
    return {"report": report.to_dict(current_user)}, 201


@bp.patch("/reports/<int:report_id>")
@login_required
def update_report(report_id):
    """JSON with any of: type, description, lat, lng, removePhoto (reporter or supervisor);
    status (supervisors only: verify, resolve or dismiss)."""
    report = db.session.get(HazardReport, report_id)
    if not report:
        return error("Report not found", 404)
    if not report.editable_by(current_user):
        return error("You can only change hazard reports you made", 403)
    data = request.get_json(silent=True) or {}
    if "status" in data:
        if not current_user.is_supervisor:
            return error("Only supervisors can change a report's status", 403)
        if data["status"] not in REPORT_STATUSES:
            return error(f"Status must be one of: {', '.join(REPORT_STATUSES)}", 400)
    if "type" in data and data["type"] not in REPORT_TYPES:
        return error("Choose a hazard type", 400)
    description = data.get("description")
    if description is not None and (not isinstance(description, str) or not 1 <= len(description.strip()) <= 1000):
        return error("Describe the hazard in 1-1000 characters", 400)
    try:
        lat = number(data["lat"], -90, 90, "Latitude") if "lat" in data else None
        lng = number(data["lng"], -180, 180, "Longitude") if "lng" in data else None
    except ValueError as exc:
        return error(str(exc), 400)

    was_wildlife = report.type == "wildlife"
    report.status = data.get("status", report.status)
    report.type = data.get("type", report.type)
    if description is not None:
        report.description = description.strip()
    report.lat = report.lat if lat is None else lat
    report.lng = report.lng if lng is None else lng
    old_photo = report.photo_filename if data.get("removePhoto") else None
    if old_photo:
        report.photo_filename = None
    db.session.commit()
    remove_photo(old_photo)
    bus.publish({"type": "report", "reportId": report.id, "siteId": report.site_id})
    if was_wildlife or report.type == "wildlife":
        ingest.rescore([db.session.get(Site, report.site_id)])
    return {"report": report.to_dict(current_user)}


@bp.delete("/reports/<int:report_id>")
@login_required
def delete_report(report_id):
    """The reporter or a supervisor can delete a report (its photo goes too)."""
    report = db.session.get(HazardReport, report_id)
    if not report:
        return error("Report not found", 404)
    if not report.editable_by(current_user):
        return error("You can only delete hazard reports you made", 403)
    site, photo, was_wildlife = db.session.get(Site, report.site_id), report.photo_filename, report.type == "wildlife"
    db.session.delete(report)
    db.session.commit()
    remove_photo(photo)
    bus.publish({"type": "report", "reportId": report_id, "siteId": site.id, "deleted": True})
    if was_wildlife:
        ingest.rescore([site])
    return {"message": "Report deleted"}


@bp.get("/uploads/<filename>")
@login_required
def uploaded_photo(filename):
    if not STORED_NAME.match(filename):
        return error("Not found", 404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, max_age=86400)
