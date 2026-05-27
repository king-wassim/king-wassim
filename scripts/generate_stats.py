import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

USERNAME = os.environ.get("USERNAME", "")
THEME = os.environ.get("THEME", "dark")

OUT_DIR = os.path.join("assets", "stats")
os.makedirs(OUT_DIR, exist_ok=True)

API_BASE = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json"}


def gh_get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def format_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def theme_colors(theme):
    if theme == "dark":
        return {
            "bg": (13, 17, 23),
            "card": (22, 27, 34),
            "border": (48, 54, 61),
            "text": (230, 237, 243),
            "muted": (139, 148, 158),
            "accent": (88, 166, 255),
        }
    return {
        "bg": (255, 255, 255),
        "card": (245, 245, 245),
        "border": (200, 200, 200),
        "text": (0, 0, 0),
        "muted": (90, 90, 90),
        "accent": (0, 102, 204),
    }


def draw_card(title, lines, out_path, theme="dark"):
    c = theme_colors(theme)
    w, h = 900, 260
    img = Image.new("RGB", (w, h), c["bg"])
    draw = ImageDraw.Draw(img)

    pad = 18
    draw.rounded_rectangle(
        (pad, pad, w - pad, h - pad),
        radius=18,
        fill=c["card"],
        outline=c["border"],
        width=2,
    )

    title_font = load_font(28)
    text_font = load_font(22)
    small_font = load_font(16)

    x = pad + 22
    y = pad + 18

    draw.text((x, y), title, fill=c["text"], font=title_font)
    y += 46

    for label, value in lines:
        draw.text((x, y), label, fill=c["muted"], font=text_font)
        draw.text((x + 340, y), value, fill=c["accent"], font=text_font)
        y += 34

    stamp = datetime.utcnow().strftime("Generated %Y-%m-%d %H:%M UTC")
    draw.text((x, h - pad - 26), stamp, fill=c["muted"], font=small_font)

    img.save(out_path)


def main():
    if not USERNAME:
        raise SystemExit("USERNAME env var is required")

    user = gh_get(f"{API_BASE}/users/{USERNAME}")

    public_repos = user.get("public_repos", 0)
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    repos = []
    page = 1
    while True:
        r = requests.get(
            f"{API_BASE}/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "type": "owner", "sort": "pushed"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
        if page > 10:
            break

    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    forks = sum(int(r.get("forks_count", 0)) for r in repos)

    lang_totals = {}
    for r in repos[:20]:
        full = r.get("full_name")
        if not full:
            continue
        lr = requests.get(f"{API_BASE}/repos/{full}/languages", headers=HEADERS, timeout=30)
        if lr.status_code != 200:
            continue
        for k, v in lr.json().items():
            lang_totals[k] = lang_totals.get(k, 0) + int(v)

    top_langs = sorted(lang_totals.items(), key=lambda kv: kv[1], reverse=True)[:5]
    top_langs_str = ", ".join([k for k, _ in top_langs]) if top_langs else "N/A"

    draw_card(
        f"{USERNAME} • GitHub Stats",
        [
            ("Public repos", format_num(public_repos)),
            ("Followers", format_num(followers)),
            ("Following", format_num(following)),
            ("Stars (public)", format_num(stars)),
            ("Forks (public)", format_num(forks)),
        ],
        os.path.join(OUT_DIR, "stats.png"),
        theme=THEME,
    )

    draw_card(
        f"{USERNAME} • Top Languages (public)",
        [("Top 5", top_langs_str)],
        os.path.join(OUT_DIR, "top-langs.png"),
        theme=THEME,
    )

    last_push = repos[0].get("pushed_at") if repos else "N/A"
    draw_card(
        f"{USERNAME} • Activity",
        [
            ("Last push", str(last_push)),
            ("Repos scanned", format_num(len(repos))),
        ],
        os.path.join(OUT_DIR, "activity.png"),
        theme=THEME,
    )


if __name__ == "__main__":
    main()
  
