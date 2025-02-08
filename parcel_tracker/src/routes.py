from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import time
from tracking import trackings, dhl_fetch, save_trackings
from config import load_config

bp = Blueprint("routes", __name__)

config = load_config()

@bp.route("/", methods=["GET"])
def overview():
    """
    Renders the overview page.
    """
    return render_template("overview.html", trackings=trackings, config=config)

@bp.route("/trackings", methods=["GET"])
def get_trackings():
    """
    Returns the current tracking data as JSON.
    """
    results = []
    for tn, info in trackings.items():
        last_update_str = info.get("last_update", "")
        try:
            try:
                last_update_timestamp = int(time.mktime(time.strptime(last_update_str, "%d.%m.%Y %H:%M:%S")))
            except ValueError:
                last_update_timestamp = int(time.mktime(time.strptime(last_update_str, "%Y-%m-%dT%H:%M:%S%z")))
        except ValueError:
            last_update_timestamp = None
        if last_update_timestamp:
            last_update_str = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(last_update_timestamp))
        results.append({
            "tracking_number": tn,
            "tracking_name": info.get("tracking_name", ""),
            "status": info.get("status", "unknown"),
            "last_update": last_update_str,
            "last_update_timestamp": last_update_timestamp,
            "progress": info.get("progress"),
            "maxProgress": info.get("maxProgress")
        })
    return jsonify(results)

@bp.route("/add", methods=["POST"])
def add_tracking():
    """
    Adds a new tracking number.
    """
    tn = request.form.get("tracking_number")
    package_name = request.form.get("package_name")
    if not tn:
        return redirect(url_for("routes.overview"))
    if tn in trackings:
        return redirect(url_for("routes.overview"))
    new_info = dhl_fetch(tn)
    new_info["tracking_name"] = package_name if package_name else ""
    trackings[tn] = new_info
    save_trackings()
    return redirect(url_for("routes.overview"))

@bp.route("/delete/<tracking_number>", methods=["POST"])
def delete_tracking(tracking_number):
    """
    Deletes a tracking entry.
    """
    if tracking_number in trackings:
        del trackings[tracking_number]
    save_trackings()
    return redirect(url_for("routes.overview"))
