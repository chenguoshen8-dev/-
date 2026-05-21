import json, os, uuid, time


class ConversationStore:
    """Persistent multi-conversation store backed by JSON files."""

    def __init__(self, base_dir):
        self._dir = os.path.join(base_dir, 'conversations')
        os.makedirs(self._dir, exist_ok=True)
        self._index_path = os.path.join(self._dir, 'index.json')
        self._cache = {}

    # ── index ──────────────────────────────────────────
    def _load_index(self):
        try:
            with open(self._index_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"active_conversation": None, "conversations": []}

    def _save_index(self, idx):
        with open(self._index_path, 'w', encoding='utf-8') as f:
            json.dump(idx, f, indent=2, ensure_ascii=False)

    # ── public API ─────────────────────────────────────
    def list_all(self):
        idx = self._load_index()
        idx["conversations"].sort(key=lambda c: c.get("updated_at", ""), reverse=True)
        return idx["conversations"]

    def get(self, conv_id):
        if conv_id in self._cache:
            return self._cache[conv_id]
        path = self._conv_path(conv_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            self._cache[conv_id] = data
            return data
        except Exception:
            return None

    def create(self, api_index=0):
        conv_id = uuid.uuid4().hex
        now = _now()
        data = {
            "id": conv_id,
            "title": "",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "api_index": api_index,
            "messages": [],
        }
        self._save_conv(conv_id, data)
        idx = self._load_index()
        idx["active_conversation"] = conv_id
        idx["conversations"].append(self._idx_entry(data))
        self._save_index(idx)
        self._cache[conv_id] = data
        return conv_id

    def update(self, conv_id, messages, api_index=None, title=None):
        data = self.get(conv_id)
        if not data:
            return
        data["messages"] = messages
        data["message_count"] = len(messages)
        data["updated_at"] = _now()
        if api_index is not None:
            data["api_index"] = api_index
        if title is not None:
            data["title"] = title
        self._save_conv(conv_id, data)
        self._cache[conv_id] = data
        self._update_index_entry(conv_id)
        self._ensure_active(conv_id)

    def delete(self, conv_id):
        path = self._conv_path(conv_id)
        if os.path.exists(path):
            os.remove(path)
        self._cache.pop(conv_id, None)
        idx = self._load_index()
        idx["conversations"] = [c for c in idx["conversations"] if c["id"] != conv_id]
        if idx["active_conversation"] == conv_id:
            remaining = idx["conversations"]
            idx["active_conversation"] = remaining[0]["id"] if remaining else None
        self._save_index(idx)

    def set_active(self, conv_id):
        idx = self._load_index()
        idx["active_conversation"] = conv_id
        self._save_index(idx)

    def get_active_id(self):
        return self._load_index().get("active_conversation")

    def auto_title(self, messages):
        for m in messages:
            if m["role"] == "user":
                t = m["content"].strip()[:35]
                return t + ("..." if len(m["content"]) > 35 else "")
        return ""

    def migrate_legacy(self, old_history, api_index=0):
        """Convert old single history list into first conversation."""
        if not old_history:
            return self.create(api_index)
        conv_id = self.create(api_index)
        self.update(conv_id, old_history, api_index)
        title = self.auto_title(old_history)
        if title:
            self.update(conv_id, old_history, api_index, title=title)
        return conv_id

    # ── internal ───────────────────────────────────────
    def _conv_path(self, conv_id):
        return os.path.join(self._dir, f"conv_{conv_id}.json")

    def _save_conv(self, conv_id, data):
        with open(self._conv_path(conv_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _idx_entry(self, data):
        return {k: data[k] for k in ("id", "title", "created_at", "updated_at", "message_count", "api_index") if k in data}

    def _update_index_entry(self, conv_id):
        data = self.get(conv_id)
        if not data:
            return
        entry = self._idx_entry(data)
        idx = self._load_index()
        for i, c in enumerate(idx["conversations"]):
            if c["id"] == conv_id:
                idx["conversations"][i] = entry
                break
        else:
            idx["conversations"].append(entry)
        self._save_index(idx)

    def _ensure_active(self, conv_id):
        idx = self._load_index()
        if idx["active_conversation"] != conv_id:
            idx["active_conversation"] = conv_id
            self._save_index(idx)


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")
