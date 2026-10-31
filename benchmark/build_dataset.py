"""Download and normalize the PokeAPI records needed by the first benchmark.

The generated dataset is intentionally local. Gameplay never calls PokeAPI.
"""

from __future__ import annotations

import json
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).parent
DATA = ROOT / "data"
RAW = DATA / "raw"
API = "https://pokeapi.co/api/v2"
USER_AGENT = "PokeTox-benchmark/0.1 (local research project)"
WORKERS = 8


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch(url: str) -> dict:
    # A URL may contain '?' and '&', which are invalid in Windows file names.
    # Keep a readable prefix and add a stable digest to make every cache key safe.
    readable_name = url.removeprefix(API).split("?", maxsplit=1)[0].strip("/").replace("/", "__")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    safe_name = f"{readable_name}__{digest}.json"
    cache = RAW / safe_name
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            save_json(cache, payload)
            time.sleep(0.12)
            return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError(f"Could not fetch {url}: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def english_text(entries: list[dict], key: str) -> str:
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get(key, "").replace("\n", " ").replace("\f", " ").strip()
    return ""


def get_id(url: str) -> int:
    return int(url.rstrip("/").split("/")[-1])


def fetch_many(urls: list[str], label: str) -> list[dict]:
    """Fetch independent API resources concurrently; fetch() remains cache-first."""
    total = len(urls)
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        results = []
        for index, payload in enumerate(executor.map(fetch, urls), start=1):
            results.append(payload)
            if index % 100 == 0 or index == total:
                print(f"{label}: {index}/{total}", flush=True)
    return results


def version_group_generations() -> dict[str, int]:
    listing = fetch(f"{API}/version-group?limit=200")
    payloads = fetch_many([ref["url"] for ref in listing["results"]], "Version groups")
    return {payload["name"]: get_id(payload["generation"]["url"]) for payload in payloads}


def normalize_species(version_generations: dict[str, int]) -> tuple[list[dict], dict[str, dict]]:
    listing = fetch(f"{API}/pokemon-species?limit=2000")
    species_payloads = fetch_many([ref["url"] for ref in listing["results"]], "Pokemon species")
    pokemon_payloads = fetch_many(
        [next((v for v in species["varieties"] if v["is_default"]), species["varieties"][0])["pokemon"]["url"] for species in species_payloads],
        "Default Pokemon forms",
    )
    records: list[dict] = []
    by_name: dict[str, dict] = {}
    for species, pokemon in zip(species_payloads, pokemon_payloads):
        generation = get_id(species["generation"]["url"])
        types = [t["type"]["name"] for t in sorted(pokemon["types"], key=lambda x: x["slot"])]
        stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon["stats"]}
        abilities = [a["ability"]["name"] for a in pokemon["abilities"]]
        move_generations = {
            move["move"]["name"]: sorted({
                version_generations[detail["version_group"]["name"]]
                for detail in move["version_group_details"]
                if detail["version_group"]["name"] in version_generations
            })
            for move in pokemon["moves"]
        }
        record = {
            "id": f"pokemon:{species['name']}",
            "name": species["name"],
            "category": "pokemon",
            "generation": generation,
            "pokedex_number": species["id"],
            "description": english_text(species["flavor_text_entries"], "flavor_text"),
            "types": types,
            "stats": stats,
            "height": pokemon["height"],
            "weight": pokemon["weight"],
            "abilities": abilities,
            "moves": sorted(move_generations),
            "move_learnset_generations": move_generations,
            "evolution_chain_url": species["evolution_chain"]["url"],
        }
        records.append(record)
        by_name[record["name"]] = record
    return records, by_name


def evolution_families(pokemon: list[dict]) -> dict[str, list[str]]:
    families: dict[str, list[str]] = {}
    urls = list(dict.fromkeys(record["evolution_chain_url"] for record in pokemon))
    payloads = fetch_many(urls, "Evolution chains")
    for payload in payloads:
        chain = payload["chain"]
        names: list[str] = []

        def visit(node: dict) -> None:
            names.append(node["species"]["name"])
            for child in node["evolves_to"]:
                visit(child)

        visit(chain)
        for name in names:
            families[name] = names
    return families


def normalize_collection(kind: str) -> list[dict]:
    listing = fetch(f"{API}/{kind}?limit=2000")
    payloads = fetch_many([ref["url"] for ref in listing["results"]], kind.title() + "s")
    records: list[dict] = []
    for source in payloads:
        generation = get_id(source["generation"]["url"])
        if kind == "move":
            record = {
                "id": f"move:{source['name']}", "name": source["name"], "category": "move",
                "generation": generation, "type": source["type"]["name"],
                "damage_class": source["damage_class"]["name"], "power": source["power"] or 0,
                "accuracy": source["accuracy"] or 0,
                "description": english_text(source["flavor_text_entries"], "flavor_text") or english_text(source["effect_entries"], "short_effect"),
            }
        elif kind == "ability":
            record = {
                "id": f"ability:{source['name']}", "name": source["name"], "category": "ability",
                "generation": generation,
                "description": english_text(source["flavor_text_entries"], "flavor_text") or english_text(source["effect_entries"], "short_effect"),
            }
        else:
            # Unknown and Shadow are placeholders; Stellar is a Gen IX Tera Type,
            # not an innate species type for this MVP's normal type-guess pool.
            if source["name"] in {"unknown", "shadow", "stellar"}:
                continue
            record = {
                "id": f"type:{source['name']}", "name": source["name"], "category": "type",
                "generation": get_id(source["generation"]["url"]),
            }
        records.append(record)
    return records


def main() -> None:
    print("Downloading/caching version groups...")
    version_generations = version_group_generations()
    print("Downloading/caching Pokemon species and default forms...")
    pokemon, _ = normalize_species(version_generations)
    print("Downloading/caching evolution chains...")
    families = evolution_families(pokemon)
    for record in pokemon:
        record["evolution_family"] = families.get(record["name"], [record["name"]])
        del record["evolution_chain_url"]
    print("Downloading/caching moves...")
    moves = normalize_collection("move")
    print("Downloading/caching abilities...")
    abilities = normalize_collection("ability")
    print("Downloading/caching types...")
    types = normalize_collection("type")
    save_json(DATA / "entities.json", {"pokemon": pokemon, "moves": moves, "abilities": abilities, "types": types})
    print(f"Wrote {len(pokemon)} Pokemon, {len(moves)} moves, {len(abilities)} abilities, and {len(types)} types to {DATA / 'entities.json'}")


if __name__ == "__main__":
    main()
