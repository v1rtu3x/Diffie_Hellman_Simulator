class DHSession:
    def __init__(self, session_id, p, g):
        self.session_id = session_id
        self.p = p
        self.g = g

        self.devices_ready = set()
        self.public_keys = {}
        self.results = {}

        self.status = "IDLE"

    def mark_ready(self, device_id):
        self.devices_ready.add(device_id)

    def add_public_key(self, device_id, key):
        self.public_keys[device_id] = key

    def add_result(self, device_id, secret):
        self.results[device_id] = secret

    def is_ready(self):
        return len(self.devices_ready) == 2

    def has_both_public_keys(self):
        return len(self.public_keys) == 2

    def has_both_results(self):
        return len(self.results) == 2

    def verify(self):
        values = list(self.results.values())
        return len(values) == 2 and values[0] == values[1]

    def reset_runtime_data(self):
        self.devices_ready.clear()
        self.public_keys.clear()
        self.results.clear()
        self.status = "IDLE"

    def set_params(self, p, g):
        self.p = p
        self.g = g