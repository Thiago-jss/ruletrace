import httpx


def model_digest(base_url: str, name: str) -> str:
    expected = name if ":" in name.rsplit("/", 1)[-1] else name + ":latest"
    response = httpx.get(base_url.rstrip("/") + "/api/tags", timeout=5)
    response.raise_for_status()
    for model in response.json()["models"]:
        if model["name"] == expected:
            return model["digest"]
    raise ConnectionError("Configured model is not loaded into the local registry")
