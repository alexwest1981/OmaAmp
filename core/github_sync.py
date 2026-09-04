import os
import json
import ssl
import zipfile
import shutil
import base64
import urllib.request
import urllib.error
import urllib.parse

CONFIG_DIR = os.path.expanduser("~/.config/omaamp")
GITHUB_CONFIG_FILE = os.path.join(CONFIG_DIR, "github.json")
OFFICIAL_CATALOG_URL = "https://raw.githubusercontent.com/alexwest1981/omaamp-themes/main/catalog.json"

# Curated community themes available out of the box
DEFAULT_COMMUNITY_THEMES = [
    {
        "id": "cyberpunk_matrix",
        "name": "⚡ Cyberpunk Matrix 2077",
        "author": "OmaAmp Community",
        "version": "1.2.0",
        "description": "High-tech neon cyan and magenta scanlines with glowing titanium accents.",
        "repo_url": "https://github.com/alexwest1981/omaamp-theme-cyberpunk",
        "tags": ["cyberpunk", "neon", "dark", "sci-fi"],
        "stars": 42
    },
    {
        "id": "brushed_titanium",
        "name": "⚙️ Brushed Titanium Deck",
        "author": "Audiophile Studio",
        "version": "1.0.0",
        "description": "Premium industrial machined aluminum with 3D rotary hardware knobs.",
        "repo_url": "https://github.com/alexwest1981/omaamp-theme-titanium",
        "tags": ["metallic", "audiophile", "industrial", "silver"],
        "stars": 38
    },
    {
        "id": "synthwave_sunset",
        "name": "🌴 Synthwave Sunset 1984",
        "author": "RetroGrid",
        "version": "1.1.0",
        "description": "Outrun 80s aesthetics with glowing neon sunset horizon and chrome sliders.",
        "repo_url": "https://github.com/alexwest1981/omaamp-theme-synthwave",
        "tags": ["synthwave", "80s", "retrowave", "neon"],
        "stars": 55
    },
    {
        "id": "nordic_frost",
        "name": "❄️ Nordic Frost Minimal",
        "author": "ScandinavianDesign",
        "version": "1.0.0",
        "description": "Ultra-clean arctic blue and slate grey glass finish for modern minimalists.",
        "repo_url": "https://github.com/alexwest1981/omaamp-theme-nordic",
        "tags": ["minimal", "nordic", "clean", "glass"],
        "stars": 29
    },
    {
        "id": "amber_crt_terminal",
        "name": "📟 Amber CRT Phosphor",
        "author": "TerminalGeek",
        "version": "1.0.0",
        "description": "Vintage 1982 IBM terminal amber display with realistic cathode tube glow.",
        "repo_url": "https://github.com/alexwest1981/omaamp-theme-amber",
        "tags": ["crt", "terminal", "amber", "vintage"],
        "stars": 31
    }
]


class GitHubSyncManager:
    """Manages GitHub API interactions, Community Catalog, Theme Downloads & Publishing."""

    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.token = self.load_token()
        self.cached_profile = None

    # -------------------------------------------------------------------------
    # Authentication & Profile
    # -------------------------------------------------------------------------
    def load_token(self) -> str:
        if os.path.exists(GITHUB_CONFIG_FILE):
            try:
                with open(GITHUB_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("token", "")
            except Exception:
                pass
        return ""

    def save_token(self, token: str):
        self.token = token.strip()
        data = {"token": self.token}
        with open(GITHUB_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.cached_profile = None

    def clear_token(self):
        self.token = ""
        if os.path.exists(GITHUB_CONFIG_FILE):
            try:
                os.remove(GITHUB_CONFIG_FILE)
            except Exception:
                pass
        self.cached_profile = None

    def get_user_profile(self) -> dict:
        if not self.token:
            return {"authenticated": False, "username": None, "error": "No token"}
        
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "OmaAmp-Theme-Engine/1.0",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=8) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    self.cached_profile = {
                        "authenticated": True,
                        "username": data.get("login"),
                        "name": data.get("name") or data.get("login"),
                        "avatar_url": data.get("avatar_url"),
                        "html_url": data.get("html_url")
                    }
                    return self.cached_profile
        except urllib.error.HTTPError as e:
            return {"authenticated": False, "username": None, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"authenticated": False, "username": None, "error": str(e)}

    # -------------------------------------------------------------------------
    # Community Catalog & Search
    # -------------------------------------------------------------------------
    def get_community_themes(self) -> list:
        """Fetches community themes from the online catalog or falls back to curated defaults."""
        try:
            req = urllib.request.Request(
                OFFICIAL_CATALOG_URL,
                headers={"User-Agent": "OmaAmp-Theme-Engine/1.0"}
            )
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=5) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "themes" in data:
                        return data["themes"]
        except Exception:
            pass
        return DEFAULT_COMMUNITY_THEMES

    def search_github_themes(self, query: str) -> list:
        """Searches GitHub repositories for topic 'omaamp-theme'."""
        if not query.strip():
            return self.get_community_themes()

        encoded_q = urllib.parse.quote(f"{query} topic:omaamp-theme")
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc"
        headers = {
            "User-Agent": "OmaAmp-Theme-Engine/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            req = urllib.request.Request(url, headers=headers)
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=8) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    items = data.get("items", [])
                    results = []
                    for item in items:
                        results.append({
                            "id": item.get("name", "").lower().replace("-", "_"),
                            "name": item.get("name"),
                            "author": item.get("owner", {}).get("login", "Unknown"),
                            "description": item.get("description") or "GitHub Community Theme",
                            "repo_url": item.get("html_url"),
                            "stars": item.get("stargazers_count", 0),
                            "tags": item.get("topics", [])
                        })
                    return results
        except Exception as e:
            print(f"Error searching GitHub themes: {e}")
        return [t for t in self.get_community_themes() if query.lower() in t.get("name", "").lower() or query.lower() in t.get("description", "").lower()]

    # -------------------------------------------------------------------------
    # Theme Download & Installation
    # -------------------------------------------------------------------------
    def install_theme_from_github(self, repo_or_raw_url: str, target_dir: str) -> dict:
        """
        Installs a theme from a GitHub repo URL, raw JSON/ZIP URL, or Gist URL.
        Returns metadata dict of installed theme.
        """
        os.makedirs(target_dir, exist_ok=True)
        repo_or_raw_url = repo_or_raw_url.strip()

        # Case 1: Direct JSON theme URL or Gist raw URL
        if repo_or_raw_url.endswith(".json") or "raw.githubusercontent.com" in repo_or_raw_url or "/raw/" in repo_or_raw_url:
            req = urllib.request.Request(repo_or_raw_url, headers={"User-Agent": "OmaAmp-Theme-Engine/1.0"})
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
                tid = data.get("id", "downloaded_theme")
                out_path = os.path.join(target_dir, f"{tid}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return {"id": tid, "name": data.get("name", tid), "path": out_path, "success": True}

        # Case 2: GitHub Repository (e.g. https://github.com/user/repo)
        if "github.com/" in repo_or_raw_url:
            parts = repo_or_raw_url.rstrip("/").split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                zip_api_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
                
                headers = {"User-Agent": "OmaAmp-Theme-Engine/1.0", "Accept": "application/vnd.github.v3+json"}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                req = urllib.request.Request(zip_api_url, headers=headers)
                ctx = ssl.create_default_context()
                temp_zip = os.path.join(CONFIG_DIR, "temp_theme.zip")

                with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
                    with open(temp_zip, "wb") as f_out:
                        shutil.copyfileobj(res, f_out)

                theme_id = repo.lower().replace("-", "_")
                dest_theme_folder = os.path.join(target_dir, theme_id)
                os.makedirs(dest_theme_folder, exist_ok=True)

                with zipfile.ZipFile(temp_zip, "r") as z:
                    members = z.namelist()
                    for m in members:
                        if m.endswith("theme.json") or m.endswith(".json"):
                            content = z.read(m)
                            try:
                                tdata = json.loads(content.decode("utf-8"))
                                theme_id = tdata.get("id", theme_id)
                            except Exception:
                                pass
                    for m in members:
                        parts_m = m.split("/", 1)
                        if len(parts_m) > 1 and parts_m[1]:
                            rel_path = parts_m[1]
                            target_file = os.path.join(dest_theme_folder, rel_path)
                            if m.endswith("/"):
                                os.makedirs(target_file, exist_ok=True)
                            else:
                                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                                with open(target_file, "wb") as out_f:
                                    out_f.write(z.read(m))

                if os.path.exists(temp_zip):
                    os.remove(temp_zip)

                return {"id": theme_id, "name": theme_id, "path": dest_theme_folder, "success": True}

        raise ValueError(f"Unrecognized GitHub URL format: {repo_or_raw_url}")

    # -------------------------------------------------------------------------
    # Theme Publishing to GitHub
    # -------------------------------------------------------------------------
    def publish_theme_to_gist(self, theme_data: dict, description: str = "") -> dict:
        """Publishes a theme JSON as a public GitHub Gist."""
        if not self.token:
            return {"success": False, "error": "GitHub Personal Access Token required to publish."}

        theme_id = theme_data.get("id", "custom_theme")
        filename = f"{theme_id}.omaamp-theme.json"
        
        payload = {
            "description": description or f"OmaAmp Music Player Theme: {theme_data.get('name', theme_id)}",
            "public": True,
            "files": {
                filename: {
                    "content": json.dumps(theme_data, indent=2)
                }
            }
        }

        req = urllib.request.Request(
            "https://api.github.com/gists",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "OmaAmp-Theme-Engine/1.0",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github.v3+json"
            },
            method="POST"
        )
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=12) as res:
                if res.status in (200, 201):
                    result = json.loads(res.read().decode("utf-8"))
                    raw_url = result.get("files", {}).get(filename, {}).get("raw_url")
                    html_url = result.get("html_url")
                    return {
                        "success": True,
                        "gist_url": html_url,
                        "raw_url": raw_url,
                        "id": result.get("id")
                    }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return {"success": False, "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_theme_package(self, theme_dir_or_json: str, output_path: str) -> str:
        """Packages a theme folder or JSON into a .omaamp-theme zip archive."""
        if os.path.isfile(theme_dir_or_json) and theme_dir_or_json.endswith(".json"):
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(theme_dir_or_json, arcname="theme.json")
            return output_path
        elif os.path.isdir(theme_dir_or_json):
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
                for root, _, files in os.walk(theme_dir_or_json):
                    for f in files:
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, theme_dir_or_json)
                        z.write(full_p, arcname=rel_p)
            return output_path
        return ""
