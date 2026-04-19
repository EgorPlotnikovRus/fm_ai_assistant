import pandas as pd
import sqlite3
import re

XLSX_PATH = "./data/fm23data.xlsx"
DB_PATH   = "data/fm_players.db"
LNC_PATH  = "./data/real_name_fix.lnc"
CSV_PATH  = "./data/div_based.csv"

POSITION_FLAGS = {
    "pos_gk":   lambda s: "GK" in s,
    "pos_dc":   lambda s: "D (C)" in s or "D (LC)" in s or "D (RC)" in s or "D (C," in s,
    "pos_dl":   lambda s: "D (L)" in s or "D (LC)" in s or "WB (L)" in s,
    "pos_dr":   lambda s: "D (R)" in s or "D (RC)" in s or "WB (R)" in s,
    "pos_wbl":  lambda s: "WB (L)" in s,
    "pos_wbr":  lambda s: "WB (R)" in s,
    "pos_mc":   lambda s: "M (C)" in s or "DM (C)" in s or "M (LC)" in s or "M (RC)" in s or "M (C," in s,
    "pos_ml":   lambda s: "M (L)" in s or "M (LC)" in s,
    "pos_mr":   lambda s: "M (R)" in s or "M (RC)" in s,
    "pos_dm":   lambda s: "DM" in s,
    "pos_aml":  lambda s: "AM (L)" in s or "AM (LC)" in s,
    "pos_amr":  lambda s: "AM (R)" in s or "AM (RC)" in s,
    "pos_amc":  lambda s: "AM (C)" in s or "AM (LC)" in s or "AM (RC)" in s or "AM (C," in s,
    "pos_st":   lambda s: "ST" in s or "CF" in s,
}

COL_MAP = {
    " UID        ":                          "uid",
    " Name                               ":  "name",
    " DoB                       ":           "dob",
    " Nat ":                                 "nationality",
    " Division                                      ": "league_fm",
    " Club                         ":        "club_fm",
    " Preferred Foot ":                      "preferred_foot",
    " Position                        ":     "position_raw",
    " Height ":                              "height_cm",
    " Weight ":                              "weight_kg",
    " Age ":                                 "age",
    " Transfer Value  ":                     "transfer_value",
    " Wage           ":                      "wage",
    " Best Role               ":             "best_role",
    " Best Duty ":                           "best_duty",
    " Best Pos ":                            "best_pos",
    " Acc ": "acceleration",    " Aer ": "aerial_reach",
    " Agg ": "aggression",      " Agi ": "agility",
    " Ant ": "anticipation",    " Bal ": "balance",
    " Bra ": "bravery",         " Cmd ": "command_of_area",
    " Cmp ": "composure",       " Cnt ": "concentration",
    " Cor ": "corners",         " Cro ": "crossing",
    " Dec ": "decisions",       " Det ": "determination",
    " Dri ": "dribbling",       " Fin ": "finishing",
    " Fir ": "first_touch",     " Fre ": "free_kick",
    " Hea ": "heading",         " Jum ": "jumping_reach",
    " Ldr ": "leadership",      " Lon ": "long_shots",
    " L Th ": "long_throws",    " Mar ": "marking",
    " OtB ": "off_the_ball",    " Pac ": "pace",
    " Pas ": "passing",         " Pen ": "penalty_taking",
    " Pos ": "positioning",     " Sta ": "stamina",
    " Str ": "strength",        " Tck ": "tackling",
    " Tea ": "teamwork",        " Tec ": "technique",
    " Vis ": "vision",          " Wor ": "work_rate",
    " Nat .1": "natural_fitness", " 1v1 ": "one_v_one",
    " Han ": "handling",        " Kic ": "kicking",
    " Ref ": "reflexes",        " Thr ": "throwing",
    " Pun ": "punching",        " Ecc ": "eccentricity",
    " TRO ": "tendency_rush_out", " Fla ": "flair",
    " Com ": "communication",
}

def parse_lnc(filepath):
    clubs = {}
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(filepath, encoding="latin-1") as f:
            lines = f.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        m = re.match(r'"CLUB_NAME_CHANGE"\s+(\d+)\s+"([^"]+)"', line)
        if m:
            clubs.setdefault(m.group(1), {})["full"] = m.group(2)
            continue
        m = re.match(r'"CLUB_SHORT_NAME_CHANGE"\s+(\d+)\s+"([^"]+)"', line)
        if m:
            clubs.setdefault(m.group(1), {})["short"] = m.group(2)
    club_map = {v["short"]: v["full"] for v in clubs.values() if "short" in v and "full" in v}
    print(f"  Клубов из .lnc: {len(club_map)}")
    return club_map

def parse_div_csv(filepath):
    """Строит словарь league_fm -> country из CSV файла div_based."""
    df = pd.read_csv(filepath)
    df.columns = [c.strip() for c in df.columns]
    # Находим нужные колонки по подстроке
    div_col   = [c for c in df.columns if "Division" in c][0]
    based_col = [c for c in df.columns if "Based" in c][0]
    df["_div"]   = df[div_col].astype(str).str.strip()
    df["_based"] = df[based_col].astype(str).str.strip()
    # Убираем всё что в скобках: "Brazil (First Division)" -> "Brazil"
    df["_country"] = df["_based"].apply(
        lambda x: re.sub(r"\s*\(.*?\)", "", x).strip()
        if x not in ("-", "nan") else None
    )
    result = dict(zip(df["_div"], df["_country"]))
    print(f"  Лиг из CSV: {len(result)}")
    return result

def parse_height(val):
    if pd.isna(val): return None
    m = re.search(r"(\d+)", str(val))
    return int(m.group(1)) if m else None

def parse_weight(val):
    if pd.isna(val): return None
    m = re.search(r"(\d+)", str(val))
    return int(m.group(1)) if m else None

def parse_money(val):
    if pd.isna(val): return None
    s = str(val).replace(",", "").replace(" ", "")
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None

def parse_age(val):
    if pd.isna(val): return None
    m = re.search(r"(\d+)", str(val))
    return int(m.group(1)) if m else None


print(f"Парсю {LNC_PATH}...")
club_map = parse_lnc(LNC_PATH)

print(f"Парсю {CSV_PATH}...")
league_country_map = parse_div_csv(CSV_PATH)

print(f"Читаю {XLSX_PATH}...")
df = pd.read_excel(XLSX_PATH)
df = df.rename(columns=COL_MAP)
df = df[[c for c in COL_MAP.values() if c in df.columns]]

for col in ["name", "nationality", "league_fm", "club_fm",
            "best_role", "best_duty", "best_pos", "position_raw"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().replace("nan", None)

df["height_cm"]      = df["height_cm"].apply(parse_height)
df["weight_kg"]      = df["weight_kg"].apply(parse_weight)
df["age"]            = df["age"].apply(parse_age)
df["transfer_value"] = df["transfer_value"].apply(parse_money)
df["wage"]           = df["wage"].apply(parse_money)

# club  = реальное название из .lnc, club_fm = оригинал FM
df["club"]    = df["club_fm"].apply(lambda x: club_map.get(x, x) if x else x)
df["league"]  = df["league_fm"]
# country = страна лиги из CSV
df["country"] = df["league_fm"].map(league_country_map)

for flag, check_fn in POSITION_FLAGS.items():
    df[flag] = df["position_raw"].apply(
        lambda s: 1 if (s and s != "None" and check_fn(s)) else 0
    )

ordered_cols = [
    "uid", "name", "dob", "nationality", "age",
    "club", "club_fm", "league", "league_fm", "country",
    "preferred_foot", "position_raw", "height_cm", "weight_kg",
    "transfer_value", "wage", "best_role", "best_duty", "best_pos",
    "pos_gk", "pos_dc", "pos_dl", "pos_dr", "pos_wbl", "pos_wbr",
    "pos_mc", "pos_ml", "pos_mr", "pos_dm",
    "pos_aml", "pos_amr", "pos_amc", "pos_st",
    "acceleration", "aerial_reach", "aggression", "agility", "anticipation",
    "balance", "bravery", "command_of_area", "communication", "composure",
    "concentration", "corners", "crossing", "decisions", "determination",
    "dribbling", "eccentricity", "finishing", "first_touch", "flair",
    "free_kick", "handling", "heading", "jumping_reach", "kicking",
    "leadership", "long_shots", "long_throws", "marking", "natural_fitness",
    "off_the_ball", "one_v_one", "pace", "passing", "penalty_taking",
    "positioning", "punching", "reflexes", "stamina", "strength",
    "tackling", "teamwork", "technique", "tendency_rush_out", "throwing",
    "vision", "work_rate",
]
df = df[[c for c in ordered_cols if c in df.columns]]

print(f"Пишу в {DB_PATH}...")
conn = sqlite3.connect(DB_PATH)
df.to_sql("players", conn, if_exists="replace", index=True, index_label="id")

for col in ["league", "club", "country", "age", "pos_mc", "pos_st", "pos_dc", "pos_amc"]:
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{col} ON players({col})")
conn.commit()

total   = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
cols    = [r[1] for r in conn.execute("PRAGMA table_info(players)").fetchall()]
matched = conn.execute("SELECT COUNT(*) FROM players WHERE club != club_fm").fetchone()[0]

print(f"\nГотово! Игроков: {total}")
print(f"Колонок: {len(cols)}")
print(f"Позиционные флаги: {[c for c in cols if c.startswith('pos_')]}")
print(f"Клубов с реальным названием: {matched} / {total}")

print("\nПримеры country:")
for r in conn.execute("SELECT DISTINCT league_fm, country FROM players WHERE country IS NOT NULL LIMIT 5").fetchall():
    print(f"  {r[0]!r:45} -> {r[1]!r}")

conn.close()