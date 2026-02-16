import io
from heapq import heappush, heappushpop
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from rapidfuzz import fuzz


EXPECTED_COLUMNS = [
    "Participant ID",
    "Already Flagged?",
    "Original Signup ID",
    "Create Date",
    "First Name",
    "Last Name",
    "Email",
    "Same Cookie Signups",
    "Recaptcha Score",
    "Emailable Score",
    "Signup IP",
    "Device",
    "Country Name",
    "City Name",
    "Zip Code",
    "Gender",
    "Age Group",
    "Ethnicity",
    "Affiliation",
]

OPTIONAL_COLUMNS = ["Phone"]

ADDITIONAL_COLUMNS = [
    "Contact Preference",
    "UTM Medium",
    "Total Referrals",
    "Referral Feedback",
    "Feedback Group",
    "Gross Feedback",
    "Company Suggestions",
    "HXC Program Feedback",
    "Over Program Limit (>75)",
    "Insights Elig. Feedback",
    "Elig. Feedback",
    "Feedback Left to Give",
    "Payout Elig. Feedback (Last 300 Days)",
    "Payout Elig. Net",
]

STANDARDIZED_COLUMNS = EXPECTED_COLUMNS + OPTIONAL_COLUMNS + ADDITIONAL_COLUMNS

FIELD_ALIASES = {
    "Participant ID": ["ParticipantID", "Respondent ID", "User ID"],
    "Already Flagged?": ["Already Flagged", "Flagged", "Is Flagged"],
    "Original Signup ID": ["OriginalSignupID", "Signup ID", "SignupID"],
    "Create Date": ["Created Date", "Created At", "Signup Date", "Date"],
    "First Name": ["Firstname", "Given Name"],
    "Last Name": ["Lastname", "Surname", "Family Name"],
    "Email": ["Email Address", "E-mail"],
    "Same Cookie Signups": ["Cookie Signups", "Same Cookie", "Cookie Count"],
    "Recaptcha Score": ["Recaptcha", "reCAPTCHA Score"],
    "Emailable Score": ["Emailable", "Emailable Score"],
    "Signup IP": ["IP", "IP Address", "SignupIP"],
    "Device": ["Device Type", "Browser Device"],
    "Country Name": ["Country"],
    "City Name": ["City"],
    "Zip Code": ["Zip", "Postal Code", "Postcode"],
    "Gender": [],
    "Age Group": ["Age"],
    "Ethnicity": [],
    "Affiliation": ["Organization", "Organisation", "Employer"],
    "Phone": ["Phone Number", "Mobile", "Cell", "Cell Phone", "Telephone"],
    "Contact Preference": ["ContactPref", "Preferred Contact"],
    "UTM Medium": ["UTM_Medium", "Utm Medium"],
    "Total Referrals": ["Referrals Total", "Referral Count"],
    "Referral Feedback": [],
    "Feedback Group": [],
    "Gross Feedback": [],
    "Company Suggestions": ["Company Suggestion"],
    "HXC Program Feedback": ["HXC Feedback", "Program Feedback"],
    "Over Program Limit (>75)": [
        "Over Program Limit",
        "Over Program Limit (> 75)",
        "Over Program Limit (75+)",
    ],
    "Insights Elig. Feedback": ["Insights Eligibility Feedback", "Insights Elig Feedback"],
    "Elig. Feedback": ["Eligibility Feedback", "Elig Feedback"],
    "Feedback Left to Give": [],
    "Payout Elig. Feedback (Last 300 Days)": [
        "Payout Eligibility Feedback (Last 300 Days)",
        "Payout Elig Feedback (Last 300 Days)",
    ],
    "Payout Elig. Net": ["Payout Eligibility Net", "Payout Net"],
}


def inject_custom_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --co-blue: #0077c8;
                --co-blue-dark: #005fa3;
                --co-text: #212121;
                --co-muted: #6c757d;
                --co-bg: #ececec;
                --co-card: #f7f7f7;
                --co-border: #c7c7c7;
            }

            html, body, [class*="css"] {
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                color: var(--co-text);
            }

            .stApp {
                background: var(--co-bg);
            }

            [data-testid="stHeader"] {
                background: transparent;
            }

            .main .block-container {
                background: var(--co-card);
                border: 1px solid #d8d8d8;
                border-radius: 14px;
                padding-top: 1.25rem;
                padding-bottom: 1.5rem;
                box-shadow: 0 1px 0 rgba(0, 0, 0, 0.04);
            }

            h1 {
                text-align: center;
                font-size: 1.6rem;
                font-weight: 600;
                margin-bottom: 0.25rem;
            }

            h2, h3 {
                color: var(--co-text);
                font-weight: 600;
            }

            p, .stMarkdown, .stCaption, label {
                color: var(--co-text);
            }

            [data-testid="stCaptionContainer"] p {
                color: var(--co-muted);
            }

            div[data-testid="stButton"] button {
                border-radius: 9px;
                font-weight: 500;
                min-height: 40px;
            }

            div[data-testid="stButton"] button[kind="primary"] {
                background: var(--co-blue);
                border: 1px solid var(--co-blue);
                color: #ffffff !important;
            }

            div[data-testid="stButton"] button[kind="primary"]:hover {
                background: var(--co-blue-dark);
                border-color: var(--co-blue-dark);
                color: #ffffff !important;
            }

            div[data-testid="stButton"] button[kind="secondary"] {
                background: #ffffff;
                color: var(--co-blue);
                border: 1px solid #8ab8da;
            }

            div[data-testid="stButton"] button[kind="secondary"]:hover {
                border-color: var(--co-blue);
                color: var(--co-blue-dark);
            }

            [data-testid="stFileUploader"] {
                border: 1px dashed #97bdd8;
                border-radius: 10px;
                background: #ffffff;
                padding: 0.5rem;
            }

            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] > div {
                border-radius: 9px;
                border-color: var(--co-border);
                background: #ffffff;
            }

            .stTextInput input,
            .stNumberInput input,
            textarea {
                border-radius: 9px !important;
            }

            [data-testid="stDataFrame"] {
                border: 1px solid #d7d7d7;
                border-radius: 10px;
                overflow: hidden;
                background: #ffffff;
            }

            [data-testid="stMetricValue"] {
                color: var(--co-blue);
            }

            [data-testid="stSidebar"] {
                background: #f3f3f3;
                border-left: 1px solid #d5d5d5;
            }

            [data-testid="stProgressBar"] div[role="progressbar"] {
                background: var(--co-blue);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    defaults = {
        "upload_token": None,
        "df_original": None,
        "df_working": None,
        "column_mapping": {},
        "candidates": [],
        "decisions": {},
        "group_decisions": {},
        "pair_review_index": {},
        "review_index": 0,
        "total_pairs_examined": 0,
        "program_ppf": 1.6,
        "has_generated_candidates": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_review_state() -> None:
    st.session_state["candidates"] = []
    st.session_state["decisions"] = {}
    st.session_state["group_decisions"] = {}
    st.session_state["pair_review_index"] = {}
    st.session_state["review_index"] = 0
    st.session_state["total_pairs_examined"] = 0
    st.session_state["has_generated_candidates"] = False


def normalize_column_name(column_name: str) -> str:
    return "".join(ch.lower() for ch in str(column_name) if ch.isalnum())


def clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_email(value: Any) -> str:
    return clean_text(value).lower()


def normalize_phone(value: Any) -> str:
    digits_only = "".join(ch for ch in clean_text(value) if ch.isdigit())
    if len(digits_only) > 10:
        return digits_only[-10:]
    return digits_only


def normalize_ip(value: Any) -> str:
    return clean_text(value).strip()


def normalize_generic(value: Any) -> str:
    return clean_text(value).lower()


def parse_number(value: Any) -> Optional[float]:
    raw = clean_text(value)
    if not raw:
        return None
    normalized = raw.replace(",", "").replace("$", "")
    try:
        return float(normalized)
    except ValueError:
        return None


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    uploaded_file.seek(0)
    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if file_name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file, engine="openpyxl")
    raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")


def map_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    available: Dict[str, str] = {}
    for column in df.columns:
        normalized = normalize_column_name(column)
        if normalized not in available:
            available[normalized] = column

    mapping: Dict[str, Optional[str]] = {}
    for field, aliases in FIELD_ALIASES.items():
        source_col = None
        candidates = [field, *aliases]
        for candidate in candidates:
            candidate_norm = normalize_column_name(candidate)
            if candidate_norm in available:
                source_col = available[candidate_norm]
                break
        mapping[field] = source_col
    return mapping


def standardize_dataframe(df_original: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    mapping = map_columns(df_original)
    standardized = pd.DataFrame(index=df_original.index)
    for field in STANDARDIZED_COLUMNS:
        source_col = mapping.get(field)
        if source_col and source_col in df_original.columns:
            standardized[field] = df_original[source_col]
        else:
            standardized[field] = ""
    return standardized, mapping


def prepare_features(df_working: pd.DataFrame) -> Dict[str, List[Any]]:
    first_name = df_working["First Name"].map(clean_text)
    last_name = df_working["Last Name"].map(clean_text)

    full_name = (first_name + " " + last_name).str.strip().tolist()
    features: Dict[str, List[Any]] = {
        "full_name": full_name,
        "first_name": first_name.map(normalize_generic).tolist(),
        "last_name": last_name.map(normalize_generic).tolist(),
        "email": df_working["Email"].map(normalize_email).tolist(),
        "phone": df_working["Phone"].map(normalize_phone).tolist(),
        "ip": df_working["Signup IP"].map(normalize_ip).tolist(),
        "device": df_working["Device"].map(normalize_generic).tolist(),
        "country": df_working["Country Name"].map(normalize_generic).tolist(),
        "city": df_working["City Name"].map(normalize_generic).tolist(),
        "zip": df_working["Zip Code"].map(normalize_generic).tolist(),
        "participant_id": df_working["Participant ID"].map(normalize_generic).tolist(),
        "original_signup_id": df_working["Original Signup ID"].map(normalize_generic).tolist(),
        "affiliation": df_working["Affiliation"].map(normalize_generic).tolist(),
        "contact_preference": df_working["Contact Preference"].map(normalize_generic).tolist(),
        "utm_medium": df_working["UTM Medium"].map(normalize_generic).tolist(),
    }
    features["create_dt"] = pd.to_datetime(df_working["Create Date"], errors="coerce").tolist()
    return features


def score_pair(
    i: int,
    j: int,
    features: Dict[str, List[Any]],
    weights: Dict[str, float],
) -> Dict[str, Any]:
    name_a = features["full_name"][i]
    name_b = features["full_name"][j]
    if name_a and name_b:
        name_score = float(fuzz.token_set_ratio(name_a, name_b))
    else:
        name_score = 0.0

    email_a = features["email"][i]
    email_b = features["email"][j]
    email_exact = bool(email_a and email_b and email_a == email_b)
    if email_exact:
        email_score = 100.0
    elif email_a and email_b:
        email_score = float(fuzz.ratio(email_a, email_b))
    else:
        email_score = 0.0

    phone_a = features["phone"][i]
    phone_b = features["phone"][j]
    phone_exact = bool(phone_a and phone_b and phone_a == phone_b)

    ip_a = features["ip"][i]
    ip_b = features["ip"][j]
    ip_exact = bool(ip_a and ip_b and ip_a == ip_b)

    base_score = (
        weights["name"] * name_score
        + weights["email"] * email_score
        + weights["phone"] * (100.0 if phone_exact else 0.0)
        + weights["ip"] * (100.0 if ip_exact else 0.0)
    )

    reasons: List[str] = []
    bonus = 0.0

    if phone_exact:
        reasons.append("Phone exact match")
    if ip_exact:
        reasons.append("IP exact match")

    if email_exact:
        reasons.append("Email exact match")
    elif email_score >= 85:
        reasons.append(f"Email similar ({email_score:.0f})")

    if name_score >= 80:
        reasons.append(f"Name similar ({name_score:.0f})")
    elif name_score >= 65:
        reasons.append(f"Name somewhat similar ({name_score:.0f})")

    first_name_exact = bool(
        features["first_name"][i]
        and features["first_name"][j]
        and features["first_name"][i] == features["first_name"][j]
    )
    last_name_exact = bool(
        features["last_name"][i]
        and features["last_name"][j]
        and features["last_name"][i] == features["last_name"][j]
    )
    exact_name_match = bool(first_name_exact and last_name_exact)
    if exact_name_match:
        reasons.append("First + Last name exact match")

    participant_id_exact = bool(
        features["participant_id"][i]
        and features["participant_id"][j]
        and features["participant_id"][i] == features["participant_id"][j]
    )
    original_signup_exact = bool(
        features["original_signup_id"][i]
        and features["original_signup_id"][j]
        and features["original_signup_id"][i] == features["original_signup_id"][j]
    )
    if original_signup_exact:
        bonus += 6.0
        reasons.append("Original Signup ID exact match")
    elif participant_id_exact:
        bonus += 4.0
        reasons.append("Participant ID exact match")

    device_exact = bool(
        features["device"][i]
        and features["device"][j]
        and features["device"][i] == features["device"][j]
    )
    if device_exact:
        bonus += 1.5
        reasons.append("Device exact match")

    city_exact = bool(
        features["city"][i]
        and features["city"][j]
        and features["city"][i] == features["city"][j]
    )
    zip_exact = bool(
        features["zip"][i]
        and features["zip"][j]
        and features["zip"][i] == features["zip"][j]
    )
    country_exact = bool(
        features["country"][i]
        and features["country"][j]
        and features["country"][i] == features["country"][j]
    )

    if city_exact and zip_exact:
        bonus += 2.5
        reasons.append("City + ZIP exact match")
    elif city_exact and country_exact:
        bonus += 2.0
        reasons.append("City + country exact match")

    affiliation_exact = bool(
        features["affiliation"][i]
        and features["affiliation"][j]
        and features["affiliation"][i] == features["affiliation"][j]
    )
    if affiliation_exact:
        bonus += 1.0
        reasons.append("Affiliation exact match")

    contact_preference_exact = bool(
        features["contact_preference"][i]
        and features["contact_preference"][j]
        and features["contact_preference"][i] == features["contact_preference"][j]
    )
    if contact_preference_exact:
        bonus += 0.5
        reasons.append("Contact preference exact match")

    utm_medium_exact = bool(
        features["utm_medium"][i]
        and features["utm_medium"][j]
        and features["utm_medium"][i] == features["utm_medium"][j]
    )
    if utm_medium_exact:
        bonus += 0.75
        reasons.append("UTM medium exact match")

    dt_a = features["create_dt"][i]
    dt_b = features["create_dt"][j]
    if pd.notna(dt_a) and pd.notna(dt_b):
        day_distance = abs((dt_a - dt_b).days)
        if day_distance == 0:
            bonus += 2.0
            reasons.append("Same signup date")
        elif day_distance <= 1:
            bonus += 1.0
            reasons.append("Signup dates are close")

    bonus = min(bonus, 12.0)
    final_score = min(100.0, base_score + bonus)

    deduped_reasons: List[str] = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)
    if not deduped_reasons:
        deduped_reasons.append(f"Combined score {final_score:.1f}")

    return {
        "i": i,
        "j": j,
        "pair_id": f"{i}:{j}",
        "score": final_score,
        "base_score": base_score,
        "name_score": name_score,
        "email_score": email_score,
        "exact_name_match": exact_name_match,
        "phone_exact": phone_exact,
        "ip_exact": ip_exact,
        "reasons": deduped_reasons[:5],
    }


def generate_candidates(
    df_working: pd.DataFrame,
    threshold: float,
    max_candidates: int,
    weights: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], int]:
    if len(df_working) < 2:
        return [], 0

    features = prepare_features(df_working)
    pair_total = len(df_working) * (len(df_working) - 1) // 2

    heap: List[Tuple[float, int, Dict[str, Any]]] = []
    serial = 0
    for i in range(len(df_working) - 1):
        for j in range(i + 1, len(df_working)):
            candidate = score_pair(i, j, features, weights)
            serial += 1
            if candidate["score"] < threshold:
                continue

            item = (candidate["score"], serial, candidate)
            if len(heap) < max_candidates:
                heappush(heap, item)
            elif candidate["score"] > heap[0][0]:
                heappushpop(heap, item)

    candidates = [item[2] for item in sorted(heap, key=lambda entry: entry[0], reverse=True)]
    for idx, candidate in enumerate(candidates, start=1):
        candidate["rank"] = idx
    return candidates, pair_total


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, node: int) -> int:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, a: int, b: int) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return
        if self.rank[root_a] < self.rank[root_b]:
            self.parent[root_a] = root_b
        elif self.rank[root_a] > self.rank[root_b]:
            self.parent[root_b] = root_a
        else:
            self.parent[root_b] = root_a
            self.rank[root_a] += 1


def pick_primary_record(
    member_indices: List[int],
    create_dates: List[Any],
) -> int:
    with_dates = [idx for idx in member_indices if pd.notna(create_dates[idx])]
    if with_dates:
        return min(with_dates, key=lambda idx: (create_dates[idx], idx))
    return min(member_indices)


def build_confirmed_groups(
    row_count: int,
    candidates: List[Dict[str, Any]],
    decisions: Dict[str, str],
) -> Dict[int, List[int]]:
    dsu = DisjointSet(row_count)
    for candidate in candidates:
        decision = decisions.get(candidate["pair_id"])
        if decision == "duplicate":
            dsu.union(candidate["i"], candidate["j"])

    groups: Dict[int, List[int]] = {}
    for row_idx in range(row_count):
        root = dsu.find(row_idx)
        groups.setdefault(root, []).append(row_idx)
    for members in groups.values():
        members.sort()
    return groups


def choose_group_participant_id(df_working: pd.DataFrame, primary_idx: int) -> str:
    participant_id = clean_text(df_working.at[primary_idx, "Participant ID"])
    if participant_id:
        return participant_id
    signup_id = clean_text(df_working.at[primary_idx, "Original Signup ID"])
    if signup_id:
        return signup_id
    return f"ROW-{primary_idx + 1}"


def build_dedupe_export_columns(
    df_working: pd.DataFrame,
    candidates: List[Dict[str, Any]],
    decisions: Dict[str, str],
    create_dates: List[Any],
    program_ppf: float,
) -> Tuple[List[int], List[str], List[Any], List[Any]]:
    row_count = len(df_working)
    groups = build_confirmed_groups(row_count, candidates, decisions)

    dupe_flags = [0] * row_count
    dupe_participant_ids = [""] * row_count

    for members in groups.values():
        primary = pick_primary_record(members, create_dates)
        canonical_participant_id = choose_group_participant_id(df_working, primary)
        for member in members:
            dupe_participant_ids[member] = canonical_participant_id
            if len(members) > 1 and member != primary:
                dupe_flags[member] = 1

    combo_members: Dict[Tuple[str, str], List[int]] = {}
    combo_elig_sum: Dict[Tuple[str, str], float] = {}
    combo_has_elig_value: Dict[Tuple[str, str], bool] = {}

    for row_idx in range(row_count):
        participant_id_key = dupe_participant_ids[row_idx]
        affiliation_key = normalize_generic(df_working.at[row_idx, "Affiliation"])
        combo_key = (participant_id_key, affiliation_key)
        combo_members.setdefault(combo_key, []).append(row_idx)

        elig_value = parse_number(df_working.at[row_idx, "Elig. Feedback"])
        combo_elig_sum[combo_key] = combo_elig_sum.get(combo_key, 0.0) + (
            elig_value if elig_value is not None else 0.0
        )
        combo_has_elig_value[combo_key] = combo_has_elig_value.get(combo_key, False) or (
            elig_value is not None
        )

    dedupe_eligible: List[Any] = [""] * row_count
    total_value: List[Any] = [""] * row_count
    ppf = max(float(program_ppf), 0.0)

    for combo_key, members in combo_members.items():
        if not combo_has_elig_value.get(combo_key, False):
            continue
        combo_primary = pick_primary_record(members, create_dates)
        combo_sum = combo_elig_sum.get(combo_key, 0.0)
        capped_sum = min(combo_sum, 75.0)
        dedupe_eligible[combo_primary] = round(capped_sum, 2)
        total_value[combo_primary] = round(capped_sum * ppf, 2)

    return dupe_flags, dupe_participant_ids, dedupe_eligible, total_value


def detail_table(df_working: pd.DataFrame, row_idx: int) -> pd.DataFrame:
    fields = STANDARDIZED_COLUMNS
    rows = []
    for field in fields:
        rows.append({"Field": field, "Value": clean_text(df_working.at[row_idx, field])})
    return pd.DataFrame(rows)


def build_review_groups(
    candidates: List[Dict[str, Any]],
    row_count: int,
) -> List[Dict[str, Any]]:
    dsu = DisjointSet(row_count)
    for candidate in candidates:
        dsu.union(candidate["i"], candidate["j"])

    group_rows: Dict[int, set] = {}
    group_pairs: Dict[int, List[Dict[str, Any]]] = {}
    for candidate in candidates:
        root = dsu.find(candidate["i"])
        group_rows.setdefault(root, set()).update([candidate["i"], candidate["j"]])
        group_pairs.setdefault(root, []).append(candidate)

    groups: List[Dict[str, Any]] = []
    for root, pairs in group_pairs.items():
        rows = sorted(group_rows[root])
        sorted_pairs = sorted(pairs, key=lambda item: item["score"], reverse=True)
        exact_name_pair_count = sum(bool(pair.get("exact_name_match")) for pair in sorted_pairs)
        group_id = "group:" + "-".join(str(row_idx) for row_idx in rows)
        groups.append(
            {
                "group_id": group_id,
                "rows": rows,
                "pairs": sorted_pairs,
                "pair_ids": [pair["pair_id"] for pair in sorted_pairs],
                "max_score": sorted_pairs[0]["score"],
                "avg_score": sum(pair["score"] for pair in sorted_pairs) / len(sorted_pairs),
                "exact_name_pair_count": exact_name_pair_count,
                "has_exact_name_pair": exact_name_pair_count > 0,
            }
        )

    groups.sort(key=lambda item: (item["max_score"], len(item["rows"])), reverse=True)
    for rank, group in enumerate(groups, start=1):
        group["rank"] = rank
    return groups


def group_review_status(
    group: Dict[str, Any],
    decisions: Dict[str, str],
    group_decisions: Dict[str, str],
) -> str:
    group_id = group["group_id"]
    group_decision = group_decisions.get(group_id)
    if group_decision in {"duplicate", "not_duplicate"}:
        return group_decision
    if group_decision == "some_duplicates":
        resolved_pairs = sum(
            decisions.get(pair_id) in {"duplicate", "not_duplicate"} for pair_id in group["pair_ids"]
        )
        if resolved_pairs == len(group["pair_ids"]):
            return "some_duplicates_complete"
        return "some_duplicates_in_progress"
    return "pending"


def group_progress_counts(
    review_groups: List[Dict[str, Any]],
    decisions: Dict[str, str],
    group_decisions: Dict[str, str],
) -> Tuple[int, int, int]:
    decided = 0
    in_progress = 0
    for group in review_groups:
        status = group_review_status(group, decisions, group_decisions)
        if status in {"duplicate", "not_duplicate", "some_duplicates_complete"}:
            decided += 1
        elif status == "some_duplicates_in_progress":
            in_progress += 1
    return decided, in_progress, len(review_groups)


def is_group_fully_reviewed(
    group: Dict[str, Any],
    decisions: Dict[str, str],
    group_decisions: Dict[str, str],
) -> bool:
    status = group_review_status(group, decisions, group_decisions)
    return status in {"duplicate", "not_duplicate", "some_duplicates_complete"}


def find_next_unreviewed_group_index(
    review_groups: List[Dict[str, Any]],
    decisions: Dict[str, str],
    group_decisions: Dict[str, str],
    start_index: int,
) -> Optional[int]:
    if not review_groups:
        return None
    total = len(review_groups)
    for offset in range(total):
        idx = (start_index + offset) % total
        if not is_group_fully_reviewed(review_groups[idx], decisions, group_decisions):
            return idx
    return None


def find_next_unreviewed_pair_index(
    group_pairs: List[Dict[str, Any]],
    decisions: Dict[str, str],
    start_index: int,
) -> Optional[int]:
    if not group_pairs:
        return None
    total = len(group_pairs)
    for offset in range(total):
        idx = (start_index + offset) % total
        decision = decisions.get(group_pairs[idx]["pair_id"])
        if decision not in {"duplicate", "not_duplicate"}:
            return idx
    return None


def duplicate_group_table(df_working: pd.DataFrame, row_indices: List[int]) -> pd.DataFrame:
    fields = [
        "Participant ID",
        "Original Signup ID",
        "Create Date",
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Signup IP",
        "City Name",
        "Country Name",
        "Affiliation",
        "Contact Preference",
        "UTM Medium",
        "Total Referrals",
        "Referral Feedback",
        "Feedback Group",
        "Gross Feedback",
        "Company Suggestions",
        "HXC Program Feedback",
        "Over Program Limit (>75)",
        "Insights Elig. Feedback",
        "Elig. Feedback",
        "Feedback Left to Give",
        "Payout Elig. Feedback (Last 300 Days)",
        "Payout Elig. Net",
    ]
    rows: List[Dict[str, Any]] = []
    for row_idx in row_indices:
        row_data: Dict[str, Any] = {"Row #": row_idx + 1}
        for field in fields:
            row_data[field] = clean_text(df_working.at[row_idx, field])
        rows.append(row_data)
    return pd.DataFrame(rows)


def exact_name_match_rows_table(
    groups: List[Dict[str, Any]],
    df_working: pd.DataFrame,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for group in groups:
        for row_idx in group["rows"]:
            rows.append(
                {
                    "Group #": group["rank"],
                    "Row #": row_idx + 1,
                    "Participant ID": clean_text(df_working.at[row_idx, "Participant ID"]),
                    "First Name": clean_text(df_working.at[row_idx, "First Name"]),
                    "Last Name": clean_text(df_working.at[row_idx, "Last Name"]),
                    "Email": clean_text(df_working.at[row_idx, "Email"]),
                    "Affiliation": clean_text(df_working.at[row_idx, "Affiliation"]),
                }
            )
    return pd.DataFrame(rows)


def build_group_pairs_table(
    group: Dict[str, Any],
    df_working: pd.DataFrame,
    decisions: Dict[str, str],
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for idx, pair in enumerate(group["pairs"], start=1):
        i = pair["i"]
        j = pair["j"]
        rows.append(
            {
                "Pair #": idx,
                "Row A": i + 1,
                "Row B": j + 1,
                "Score": round(pair["score"], 1),
                "Decision": decisions.get(pair["pair_id"], "pending"),
                "Name A": f"{clean_text(df_working.at[i, 'First Name'])} {clean_text(df_working.at[i, 'Last Name'])}".strip(),
                "Name B": f"{clean_text(df_working.at[j, 'First Name'])} {clean_text(df_working.at[j, 'Last Name'])}".strip(),
                "Email A": clean_text(df_working.at[i, "Email"]),
                "Email B": clean_text(df_working.at[j, "Email"]),
                "Reasons": "; ".join(pair["reasons"]),
            }
        )
    return pd.DataFrame(rows)


def confirm_all_exact_name_groups(exact_name_groups: List[Dict[str, Any]]) -> None:
    for group in exact_name_groups:
        st.session_state["group_decisions"][group["group_id"]] = "duplicate"
        for pair_id in group["pair_ids"]:
            st.session_state["decisions"][pair_id] = "duplicate"
    st.rerun()


def set_group_decision_and_update_pairs(
    group: Dict[str, Any],
    decision: str,
    review_groups: List[Dict[str, Any]],
) -> None:
    group_id = group["group_id"]
    if decision == "some_duplicates":
        previous = st.session_state["group_decisions"].get(group_id)
        st.session_state["group_decisions"][group_id] = "some_duplicates"
        first_pending_pair = find_next_unreviewed_pair_index(
            group["pairs"],
            st.session_state["decisions"],
            0,
        )
        st.session_state["pair_review_index"][group_id] = first_pending_pair or 0
        if previous != "some_duplicates":
            for pair_id in group["pair_ids"]:
                st.session_state["decisions"].pop(pair_id, None)
        st.rerun()
        return

    pair_decision = "duplicate" if decision == "duplicate" else "not_duplicate"
    for pair_id in group["pair_ids"]:
        st.session_state["decisions"][pair_id] = pair_decision
    st.session_state["group_decisions"][group_id] = decision

    current_index = int(st.session_state["review_index"])
    next_group_index = find_next_unreviewed_group_index(
        review_groups=review_groups,
        decisions=st.session_state["decisions"],
        group_decisions=st.session_state["group_decisions"],
        start_index=current_index + 1,
    )
    if next_group_index is not None:
        st.session_state["review_index"] = next_group_index
    st.rerun()


def move_review_index(delta: int, total_groups: int) -> None:
    if total_groups <= 0:
        return
    new_index = (int(st.session_state["review_index"]) + delta) % total_groups
    st.session_state["review_index"] = new_index
    st.rerun()


def set_pair_decision_and_advance(
    group: Dict[str, Any],
    group_pairs: List[Dict[str, Any]],
    decision: str,
    review_groups: List[Dict[str, Any]],
) -> None:
    group_id = group["group_id"]
    pair_idx = int(st.session_state["pair_review_index"].get(group_id, 0))
    pair_idx = max(0, min(len(group_pairs) - 1, pair_idx))
    pair_id = group_pairs[pair_idx]["pair_id"]
    st.session_state["decisions"][pair_id] = decision

    next_pair_index = find_next_unreviewed_pair_index(
        group_pairs=group_pairs,
        decisions=st.session_state["decisions"],
        start_index=pair_idx + 1,
    )
    if next_pair_index is not None:
        st.session_state["pair_review_index"][group_id] = next_pair_index
    else:
        current_group_index = int(st.session_state["review_index"])
        next_group_index = find_next_unreviewed_group_index(
            review_groups=review_groups,
            decisions=st.session_state["decisions"],
            group_decisions=st.session_state["group_decisions"],
            start_index=current_group_index + 1,
        )
        if next_group_index is not None:
            st.session_state["review_index"] = next_group_index
    st.rerun()


def move_group_pair_index(group_id: str, delta: int, total_pairs: int) -> None:
    if total_pairs <= 0:
        return
    pair_idx = int(st.session_state["pair_review_index"].get(group_id, 0))
    pair_idx = (pair_idx + delta) % total_pairs
    st.session_state["pair_review_index"][group_id] = pair_idx
    st.rerun()


def build_export_bytes(df_original: pd.DataFrame, deduped_df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_original.to_excel(writer, sheet_name="Original", index=False)
        deduped_df.to_excel(writer, sheet_name="Deduped", index=False)
    output.seek(0)
    return output.getvalue()


def build_partner_report_table(deduped_df: pd.DataFrame) -> pd.DataFrame:
    report_source = deduped_df.copy()

    if "Affiliation 2" not in report_source.columns and "Affiliation2" in report_source.columns:
        report_source["Affiliation 2"] = report_source["Affiliation2"]
    if "Affiliation" not in report_source.columns:
        report_source["Affiliation"] = ""
    if "Affiliation 2" not in report_source.columns:
        report_source["Affiliation 2"] = ""
    if "Email" not in report_source.columns:
        report_source["Email"] = ""

    report_source["_affiliation"] = report_source["Affiliation"].map(clean_text)
    report_source["_affiliation_2"] = report_source["Affiliation 2"].map(clean_text)
    report_source["_email_non_empty"] = report_source["Email"].map(lambda value: 1 if clean_text(value) else 0)
    report_source["_dedupe_eligible_num"] = pd.to_numeric(
        report_source.get("dedupe eligible", 0),
        errors="coerce",
    ).fillna(0.0)
    report_source["_total_value_num"] = pd.to_numeric(
        report_source.get("Total Value", 0),
        errors="coerce",
    ).fillna(0.0)

    grouped = (
        report_source.groupby(["_affiliation", "_affiliation_2"], dropna=False, as_index=False)
        .agg(
            sign_ups=("_email_non_empty", "sum"),
            total_eligible_feedback=("_dedupe_eligible_num", "sum"),
            total_value_created=("_total_value_num", "sum"),
        )
        .sort_values(by=["_affiliation", "_affiliation_2"], kind="stable")
    )

    def org_label(affiliation: Any, affiliation_2: Any) -> str:
        primary = clean_text(affiliation)
        secondary = clean_text(affiliation_2)
        if primary and secondary:
            return f"{primary} | {secondary}"
        if primary:
            return primary
        if secondary:
            return secondary
        return "(blank)"

    grouped["Organization"] = grouped.apply(
        lambda row: org_label(row["_affiliation"], row["_affiliation_2"]),
        axis=1,
    )
    grouped["sign_ups"] = grouped["sign_ups"].astype(int)
    grouped["total_eligible_feedback"] = grouped["total_eligible_feedback"].round(2)
    grouped["total_value_created"] = grouped["total_value_created"].round(2)

    partner_report = grouped[
        ["Organization", "sign_ups", "total_eligible_feedback", "total_value_created"]
    ].rename(
        columns={
            "sign_ups": "Sign Ups",
            "total_eligible_feedback": "Total Eligible Feedback",
            "total_value_created": "Total $ Created",
        }
    )
    return partner_report


def build_program_report_out_bytes(df_original: pd.DataFrame, deduped_df: pd.DataFrame) -> bytes:
    partner_report = build_partner_report_table(deduped_df)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_original.to_excel(writer, sheet_name="Original", index=False)
        deduped_df.to_excel(writer, sheet_name="Deduped", index=False)
        partner_report.to_excel(writer, sheet_name="For Partner", index=False)
    output.seek(0)
    return output.getvalue()


def main() -> None:
    st.set_page_config(page_title="Participant Sign-up Deduplication", layout="wide")
    inject_custom_styles()
    init_session_state()

    st.title("Participant Sign-up Deduplication")
    st.caption("Upload participant data, find likely duplicate sign-ups, review groups, and export decisions.")

    with st.sidebar:
        st.header("Settings")
        threshold = st.slider("Minimum candidate score", min_value=0, max_value=100, value=75, step=1)
        max_candidates = st.number_input(
            "Max candidate pairs to generate",
            min_value=50,
            max_value=20000,
            value=1000,
            step=50,
        )
        st.markdown("### Weights")
        name_weight = st.slider("Name weight", min_value=0.0, max_value=1.0, value=0.55, step=0.01)
        email_weight = st.slider("Email weight", min_value=0.0, max_value=1.0, value=0.25, step=0.01)
        phone_weight = st.slider("Phone weight", min_value=0.0, max_value=1.0, value=0.15, step=0.01)
        ip_weight = st.slider("IP weight", min_value=0.0, max_value=1.0, value=0.05, step=0.01)

    uploaded_file = st.file_uploader("Upload CSV or XLSX participant file", type=["csv", "xlsx"])

    if not uploaded_file:
        st.info("Upload a CSV or XLSX file to start.")
        return

    upload_token = f"{uploaded_file.name}:{uploaded_file.size}:{uploaded_file.type}"
    if st.session_state["upload_token"] != upload_token:
        try:
            df_original = read_uploaded_file(uploaded_file)
        except Exception as exc:
            st.error(f"Could not read file: {exc}")
            return

        if df_original.empty:
            st.error("The uploaded file is empty. Please upload a file with participant rows.")
            return

        df_original = df_original.reset_index(drop=True)
        df_working, mapping = standardize_dataframe(df_original)

        st.session_state["upload_token"] = upload_token
        st.session_state["df_original"] = df_original
        st.session_state["df_working"] = df_working
        st.session_state["column_mapping"] = mapping
        st.session_state["program_ppf"] = 1.6
        reset_review_state()

    df_original = st.session_state["df_original"]
    df_working = st.session_state["df_working"]

    if df_original is None or df_working is None:
        st.error("No data is currently loaded. Please re-upload the file.")
        return

    if st.session_state["has_generated_candidates"]:
        with st.expander("Data preview (click to expand)", expanded=False):
            st.dataframe(df_original.head(20), use_container_width=True, hide_index=True)
    else:
        st.subheader("Data preview")
        st.dataframe(df_original.head(20), use_container_width=True, hide_index=True)

    st.subheader("Program settings")
    program_ppf = st.number_input(
        "Program PPF",
        min_value=0.0,
        value=float(st.session_state["program_ppf"]),
        step=0.1,
        format="%.2f",
        help="Program-level PPF value captured for context. Default is 1.6.",
    )
    st.session_state["program_ppf"] = float(program_ppf)

    total_weight = name_weight + email_weight + phone_weight + ip_weight
    if total_weight <= 0:
        st.error("At least one weight must be greater than 0.")
        return

    normalized_weights = {
        "name": name_weight / total_weight,
        "email": email_weight / total_weight,
        "phone": phone_weight / total_weight,
        "ip": ip_weight / total_weight,
    }
    st.caption(
        "Weights are normalized automatically so they sum to 1. "
        f"Current unnormalized sum: {total_weight:.2f}"
    )

    if len(df_working) < 2:
        st.warning("Need at least 2 rows to compare duplicates.")
        return

    if st.button("Find possible duplicates", type="primary", use_container_width=True):
        st.session_state["has_generated_candidates"] = True
        with st.spinner("Scoring candidate pairs..."):
            candidates, total_pairs = generate_candidates(
                df_working=df_working,
                threshold=float(threshold),
                max_candidates=int(max_candidates),
                weights=normalized_weights,
            )
        st.session_state["candidates"] = candidates
        st.session_state["decisions"] = {}
        st.session_state["group_decisions"] = {}
        st.session_state["pair_review_index"] = {}
        st.session_state["review_index"] = 0
        st.session_state["total_pairs_examined"] = total_pairs

        if candidates:
            st.success(f"Found {len(candidates)} candidate pairs above score {threshold}.")
        else:
            st.warning(
                "No candidate pairs met the threshold. Try lowering the threshold or adjusting weights."
            )

    candidates = st.session_state["candidates"]
    if not candidates:
        return

    review_groups = build_review_groups(candidates, len(df_working))
    if not review_groups:
        st.warning("No duplicate groups are available for review.")
        return

    exact_name_groups = [group for group in review_groups if group["has_exact_name_pair"]]
    remaining_groups = [group for group in review_groups if not group["has_exact_name_pair"]]

    if exact_name_groups:
        st.divider()
        st.subheader("Exact name match section")
        all_exact_confirmed = all(
            group_review_status(
                group=group,
                decisions=st.session_state["decisions"],
                group_decisions=st.session_state["group_decisions"],
            )
            == "duplicate"
            for group in exact_name_groups
        )
        if all_exact_confirmed:
            st.success("Exact Name Matches Confirmed and Saved")
        else:
            st.write(f"{len(exact_name_groups)} groups have First + Last exact-name matches.")
            st.dataframe(
                exact_name_match_rows_table(exact_name_groups, df_working),
                hide_index=True,
                use_container_width=True,
            )
            if st.button(
                "Confirm All Exact Name Match Groups",
                type="primary",
                use_container_width=True,
            ):
                confirm_all_exact_name_groups(exact_name_groups)

    if not remaining_groups:
        st.info("No remaining matches to review after the exact name match section.")
    else:
        total_groups = len(remaining_groups)
        st.divider()
        st.subheader("Duplicate group review")

        st.session_state["review_index"] = max(
            0, min(st.session_state["review_index"], total_groups - 1)
        )
        group_idx = int(st.session_state["review_index"])

        decided_groups, in_progress_groups, _ = group_progress_counts(
            review_groups=remaining_groups,
            decisions=st.session_state["decisions"],
            group_decisions=st.session_state["group_decisions"],
        )

        st.write(
            f"Progress: {decided_groups} decided, {in_progress_groups} in progress, "
            f"{total_groups} remaining groups."
        )
        st.progress(decided_groups / total_groups)

        next_unreviewed_idx = find_next_unreviewed_group_index(
            review_groups=remaining_groups,
            decisions=st.session_state["decisions"],
            group_decisions=st.session_state["group_decisions"],
            start_index=group_idx,
        )
        if next_unreviewed_idx is None:
            st.info("All groups/pairs have been reviewed.")
        else:
            if next_unreviewed_idx != group_idx:
                st.session_state["review_index"] = next_unreviewed_idx
                st.rerun()

            group = remaining_groups[next_unreviewed_idx]
            group_id = group["group_id"]

            current_status = group_review_status(
                group=group,
                decisions=st.session_state["decisions"],
                group_decisions=st.session_state["group_decisions"],
            )
            status_labels = {
                "pending": "pending",
                "duplicate": "confirmed duplicates",
                "not_duplicate": "not duplicates",
                "some_duplicates_in_progress": "some duplicates (pair review in progress)",
                "some_duplicates_complete": "some duplicates (pair review complete)",
            }

            st.markdown(f"### Group {next_unreviewed_idx + 1} of {total_groups}")
            metric_cols = st.columns(3)
            with metric_cols[0]:
                st.metric("Rows in group", len(group["rows"]))
            with metric_cols[1]:
                st.metric("Candidate pairs", len(group["pairs"]))
            with metric_cols[2]:
                st.metric("Top group score", f"{group['max_score']:.1f}")
            st.caption(f"Current group decision: {status_labels.get(current_status, current_status)}")

            st.dataframe(
                duplicate_group_table(df_working, group["rows"]),
                hide_index=True,
                use_container_width=True,
            )

            group_decision_cols = st.columns(3)
            with group_decision_cols[0]:
                if st.button(
                    "Confirm Duplicates",
                    key=f"group_confirm_{group_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    set_group_decision_and_update_pairs(group, "duplicate", remaining_groups)
            with group_decision_cols[1]:
                if st.button(
                    "Not Duplicates",
                    key=f"group_not_{group_id}",
                    use_container_width=True,
                ):
                    set_group_decision_and_update_pairs(group, "not_duplicate", remaining_groups)
            with group_decision_cols[2]:
                if st.button(
                    "Some Duplicates",
                    key=f"group_some_{group_id}",
                    use_container_width=True,
                ):
                    set_group_decision_and_update_pairs(group, "some_duplicates", remaining_groups)

            nav_cols = st.columns([1, 1, 2, 1])
            with nav_cols[0]:
                if st.button("Prev Group", use_container_width=True):
                    move_review_index(-1, total_groups)
            with nav_cols[1]:
                if st.button("Next Group", use_container_width=True):
                    move_review_index(1, total_groups)
            with nav_cols[2]:
                jump_to_group = st.number_input(
                    "Jump to group #",
                    min_value=1,
                    max_value=total_groups,
                    value=next_unreviewed_idx + 1,
                    step=1,
                    key=f"jump_group_{next_unreviewed_idx}_{total_groups}",
                )
            with nav_cols[3]:
                if st.button("Go to Group", key=f"go_group_{group_id}", use_container_width=True):
                    st.session_state["review_index"] = int(jump_to_group) - 1
                    st.rerun()

            if st.session_state["group_decisions"].get(group_id) == "some_duplicates":
                st.markdown("#### Pair review for this group")
                st.caption(
                    "You selected 'Some Duplicates'. Review this group as pairs and mark each pair."
                )
                group_pairs = group["pairs"]

                pair_idx = int(st.session_state["pair_review_index"].get(group_id, 0))
                pair_idx = max(0, min(len(group_pairs) - 1, pair_idx))
                next_unreviewed_pair_idx = find_next_unreviewed_pair_index(
                    group_pairs=group_pairs,
                    decisions=st.session_state["decisions"],
                    start_index=pair_idx,
                )

                if next_unreviewed_pair_idx is None:
                    next_group_index = find_next_unreviewed_group_index(
                        review_groups=remaining_groups,
                        decisions=st.session_state["decisions"],
                        group_decisions=st.session_state["group_decisions"],
                        start_index=next_unreviewed_idx + 1,
                    )
                    if next_group_index is not None:
                        st.session_state["review_index"] = next_group_index
                        st.rerun()
                    else:
                        st.info("All groups/pairs have been reviewed.")
                else:
                    st.session_state["pair_review_index"][group_id] = next_unreviewed_pair_idx
                    pair_idx = next_unreviewed_pair_idx

                    resolved_pairs = sum(
                        st.session_state["decisions"].get(pair["pair_id"]) in {"duplicate", "not_duplicate"}
                        for pair in group_pairs
                    )
                    st.write(f"Pair progress: {resolved_pairs} decided of {len(group_pairs)} pairs in this group.")
                    st.progress(resolved_pairs / len(group_pairs))

                    st.dataframe(
                        build_group_pairs_table(group, df_working, st.session_state["decisions"]),
                        hide_index=True,
                        use_container_width=True,
                    )

                    active_pair = group_pairs[pair_idx]
                    st.markdown(
                        f"##### Pair {pair_idx + 1} of {len(group_pairs)} "
                        f"(rows {active_pair['i'] + 1} and {active_pair['j'] + 1})"
                    )
                    st.metric("Pair score", f"{active_pair['score']:.1f}")
                    st.write("**Reasons:** " + "; ".join(active_pair["reasons"]))
                    pair_decision = st.session_state["decisions"].get(active_pair["pair_id"], "pending")
                    st.caption(f"Current pair decision: {pair_decision}")

                    left_col, right_col = st.columns(2)
                    with left_col:
                        st.markdown(f"#### Record A (row {active_pair['i'] + 1})")
                        st.dataframe(
                            detail_table(df_working, active_pair["i"]),
                            hide_index=True,
                            use_container_width=True,
                        )
                    with right_col:
                        st.markdown(f"#### Record B (row {active_pair['j'] + 1})")
                        st.dataframe(
                            detail_table(df_working, active_pair["j"]),
                            hide_index=True,
                            use_container_width=True,
                        )

                    pair_decision_cols = st.columns(2)
                    with pair_decision_cols[0]:
                        if st.button(
                            "Confirm Duplicates (Pair)",
                            key=f"pair_confirm_{group_id}_{pair_idx}",
                            type="primary",
                            use_container_width=True,
                        ):
                            set_pair_decision_and_advance(group, group_pairs, "duplicate", remaining_groups)
                    with pair_decision_cols[1]:
                        if st.button(
                            "Not Duplicates (Pair)",
                            key=f"pair_not_{group_id}_{pair_idx}",
                            use_container_width=True,
                        ):
                            set_pair_decision_and_advance(group, group_pairs, "not_duplicate", remaining_groups)

                    pair_nav_cols = st.columns([1, 1, 2, 1])
                    with pair_nav_cols[0]:
                        if st.button(
                            "Prev Pair",
                            key=f"prev_pair_{group_id}_{pair_idx}",
                            use_container_width=True,
                        ):
                            move_group_pair_index(group_id, -1, len(group_pairs))
                    with pair_nav_cols[1]:
                        if st.button(
                            "Next Pair",
                            key=f"next_pair_{group_id}_{pair_idx}",
                            use_container_width=True,
                        ):
                            move_group_pair_index(group_id, 1, len(group_pairs))
                    with pair_nav_cols[2]:
                        jump_pair = st.number_input(
                            "Jump to pair # in this group",
                            min_value=1,
                            max_value=len(group_pairs),
                            value=pair_idx + 1,
                            step=1,
                            key=f"jump_pair_{group_id}_{pair_idx}",
                        )
                    with pair_nav_cols[3]:
                        if st.button(
                            "Go to Pair",
                            key=f"go_pair_{group_id}_{pair_idx}",
                            use_container_width=True,
                        ):
                            st.session_state["pair_review_index"][group_id] = int(jump_pair) - 1
                            st.rerun()

    create_dates = pd.to_datetime(df_working["Create Date"], errors="coerce").tolist()
    dupe_flags, dupe_participant_ids, dedupe_eligible, total_value = build_dedupe_export_columns(
        df_working=df_working,
        candidates=candidates,
        decisions=st.session_state["decisions"],
        create_dates=create_dates,
        program_ppf=float(st.session_state["program_ppf"]),
    )
    deduped = df_original.copy()
    deduped["dupe"] = dupe_flags
    deduped["dupe participant id"] = dupe_participant_ids
    deduped["dedupe eligible"] = dedupe_eligible
    deduped["Total Value"] = total_value
    duplicate_rows = int(sum(dupe_flags))

    st.divider()
    st.subheader("Export reviewed result")
    st.write(
        "The export includes the original dataset and a deduped copy with `dupe`, "
        "`dupe participant id`, `dedupe eligible`, and `Total Value` columns."
    )
    st.metric("Rows currently marked dupe=1", duplicate_rows)

    export_bytes = build_export_bytes(df_original, deduped)
    st.download_button(
        label="Download Excel export",
        data=export_bytes,
        file_name="participant_dedupe_review.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Download Program Report Out")
    st.write(
        "Downloads the same export plus a third `For Partner` tab with organization-level "
        "summary metrics."
    )
    report_out_bytes = build_program_report_out_bytes(df_original, deduped)
    st.download_button(
        label="Download Program Report Out",
        data=report_out_bytes,
        file_name="program_report_out.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
