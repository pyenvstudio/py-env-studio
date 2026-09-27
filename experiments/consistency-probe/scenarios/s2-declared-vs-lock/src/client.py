def build_url(base, path):
    return base.rstrip("/") + "/" + path.lstrip("/")


def retry(times, fn):
    return [fn() for _ in range(times)]
