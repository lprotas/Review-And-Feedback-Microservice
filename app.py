from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timezone
import os
import uuid
import json 

app = Flask(__name__)

# CORS Configuration
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5000").split(",")
CORS(app, resources={
    r"/*": {
        "origins": [o.strip() for o in allowed_origins if o.strip()],
        "methods": ["GET", "POST", "PUT", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


# MongoDB Connection (Olivia)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["review_feedback_db"]
feedback_collection = db["feedbacks"]
# Audit log collection
audit_collection = db["audit_logs"]

def error_response(message, code=400):
    return jsonify({"error": message}), code

#  Database Helper Functions
def get_feedback(feedbackId):
    """
    Olivia: Replace MOCK_DB lookup with actual DB query. 
    """
    feedback = feedback_collection.find_one({"feedbackId": feedbackId})
    if feedback:
        feedback.pop("_id", None)
    return feedback


def save_feedback(userId, entityId, rating, comment):
    """
    Olivia: Replace MOCK_DB insertion with actual DB insert logic. 
    """
    feedbackId = str(uuid.uuid4())
    feedback_doc = {
        "feedbackId": feedbackId,
        "userId": userId,
        "entityId": entityId,
        "rating": rating,
        "comment": comment,
        "last_modified": datetime.now(timezone.utc).isoformat()
    }
    feedback_collection.insert_one(feedback_doc)
    return feedbackId


def update_feedback_entry(feedbackId, rating, comment, last_modified):
    """
    Olivia: Replace MOCK_DB update with actual DB UPDATE logic.
    """
    update_data = {
        "rating": rating,
        "comment": comment,
        "last_modified": last_modified.isoformat()
    }
    result = feedback_collection.update_one(
        {"feedbackId": feedbackId},
        {"$set": update_data}
    )
    return result.modified_count > 0


def log_audit(audit_log):
    """
    Olivia: Replace print statement with actual audit logging mechanism if needed. 
    """
    audit_collection.insert_one(audit_log)

#  Routes
@app.route("/health")
def health():
    return jsonify({"message": "Review and Feedback Microservice Online"}), 200


@app.route("/feedback", methods=["POST"])
def submit_feedback():
    try:
        data = request.get_json()
    except Exception:
        return error_response("Invalid JSON format")

    if not data:
        return error_response("No data provided")

    userId = data.get("userId")
    entityId = data.get("entityId")
    rating = data.get("rating")
    comment = data.get("comment")

    # Validation
    if not all([userId, entityId, rating]):
        return error_response("Missing required fields (userId, entityId, rating)")

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return error_response("Rating must be an integer between 1 and 5")

    feedbackId = save_feedback(userId, entityId, rating, comment)

    return jsonify({
        "message": "Feedback received",
        "feedbackId": feedbackId,
        "userId": userId,
        "entityId": entityId,
        "rating": rating,
        "comment": comment
    }), 201


@app.route("/feedback/<feedbackId>", methods=["PUT"])
def update_feedback_endpoint(feedbackId):
    try:
        data = request.get_json()
    except Exception:
        return error_response("Invalid JSON format")

    if not data:
        return error_response("No data provided")

    userId = data.get("userId")
    rating = data.get("rating")
    comment = data.get("comment")

    # Validation
    if rating is not None:
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return error_response("Rating must be an integer between 1 and 5")

    if comment is not None and not isinstance(comment, str):
        return error_response("Comment must be a string")


    original_feedback = get_feedback(feedbackId)

    if not original_feedback:
        return error_response("Feedback not found", 404)

    if original_feedback.get("userId") != userId:
        return error_response("Unauthorized", 403)

    # Audit log with before/after states
    audit_log = {
        "auditId": str(uuid.uuid4()),
        "feedbackId": feedbackId,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "userId": userId,
        "action": "UPDATE",
        "before": {
            "rating": original_feedback.get("rating"),
            "comment": original_feedback.get("comment")
        },
        "after": {
            "rating": rating,
            "comment": comment
        }
    }
    log_audit(audit_log)

    update_feedback_entry(feedbackId, rating, comment, datetime.now(timezone.utc))

    return jsonify({
        "message": "Feedback updated",
        "feedbackId": feedbackId,
        "changes": audit_log["after"]
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5005"))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
