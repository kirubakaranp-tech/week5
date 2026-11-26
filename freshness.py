import sys
from datetime import datetime, timedelta

from ingest import load_json, save_json
from secure_store import REGISTRY_FILE, SECURE_FOLDER, get_collection, sync_document

MAX_AGE_HOURS = 24


def hours_since(timestamp, now):
    return (now - datetime.fromisoformat(timestamp)).total_seconds() / 3600


def refresh_stale_documents(max_age_hours=MAX_AGE_HOURS):
    registry = load_json(REGISTRY_FILE)
    now = datetime.now()
    refreshed = []

    for file_name, entry in list(registry.items()):
        age = hours_since(entry["last_synced_at"], now)
        if age <= max_age_hours:
            print(f"{file_name}: synced {age:.1f} h ago -> fresh, skipped")
            continue

        path = SECURE_FOLDER / file_name
        if not path.exists():
            print(f"{file_name}: synced {age:.1f} h ago -> file is gone, removed from the index")
            get_collection().delete(where={"source": file_name})
            del registry[file_name]
            continue

        status = sync_document(path, registry, now.isoformat(timespec="seconds"))
        action = "re-indexed" if status == "changed" else "checked, content unchanged"
        print(f"{file_name}: synced {age:.1f} h ago -> re-synced ({action})")
        refreshed.append(file_name)

    save_json(REGISTRY_FILE, registry)
    return refreshed


def make_stale_for_demo(file_name, hours=30):
    registry = load_json(REGISTRY_FILE)
    old_time = datetime.now() - timedelta(hours=hours)
    registry[file_name]["last_synced_at"] = old_time.isoformat(timespec="seconds")
    save_json(REGISTRY_FILE, registry)
    print(f"Demo: set last_synced_at of {file_name} to {hours} hours ago\n")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        make_stale_for_demo("leave_policy.docx")
    refresh_stale_documents()
