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
}


def init_session_state() -> None:
    defaults = {
        "upload_token": None,
        "df_original": None,
        "df_working": None,
        "column_mapping": {},
        "candidates": [],
        "decisions": {},
        "review_index": 0,
        "total_pairs_examined": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_review_state() -> None:
    st.session_state["candidates"] = []
    st.session_state["decisions"] = {}
    st.session_state["review_index"] = 0
    st.session_state["total_pairs_examined"] = 0


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
    for field in EXPECTED_COLUMNS + OPTIONAL_COLUMNS:
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


def build_dupe_flags(
    row_count: int,
    candidates: List[Dict[str, Any]],
    decisions: Dict[str, str],
    create_dates: List[Any],
) -> List[int]:
    dsu = DisjointSet(row_count)
    for candidate in candidates:
        decision = decisions.get(candidate["pair_id"])
        if decision == "duplicate":
            dsu.union(candidate["i"], candidate["j"])

    groups: Dict[int, List[int]] = {}
    for row_idx in range(row_count):
        root = dsu.find(row_idx)
        groups.setdefault(root, []).append(row_idx)

    dupe_flags = [0] * row_count
    for members in groups.values():
        if len(members) <= 1:
            continue
        primary = pick_primary_record(members, create_dates)
        for member in members:
            if member != primary:
                dupe_flags[member] = 1
    return dupe_flags


def decision_counts(decisions: Dict[str, str]) -> Tuple[int, int]:
    decided = sum(value in {"duplicate", "not_duplicate"} for value in decisions.values())
    skipped = sum(value == "skipped" for value in decisions.values())
    return decided, skipped


def detail_table(df_working: pd.DataFrame, row_idx: int) -> pd.DataFrame:
    fields = EXPECTED_COLUMNS + OPTIONAL_COLUMNS
    rows = []
    for field in fields:
        rows.append({"Field": field, "Value": clean_text(df_working.at[row_idx, field])})
    return pd.DataFrame(rows)


def build_candidate_group_lookup(
    candidates: List[Dict[str, Any]],
    row_count: int,
) -> Dict[int, List[int]]:
    dsu = DisjointSet(row_count)
    involved_rows = set()
    for candidate in candidates:
        i = candidate["i"]
        j = candidate["j"]
        dsu.union(i, j)
        involved_rows.add(i)
        involved_rows.add(j)

    grouped: Dict[int, List[int]] = {}
    for row_idx in involved_rows:
        root = dsu.find(row_idx)
        grouped.setdefault(root, []).append(row_idx)

    lookup: Dict[int, List[int]] = {}
    for members in grouped.values():
        sorted_members = sorted(members)
        for member in sorted_members:
            lookup[member] = sorted_members
    return lookup


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
    ]
    rows: List[Dict[str, Any]] = []
    for row_idx in row_indices:
        row_data: Dict[str, Any] = {"Row #": row_idx + 1}
        for field in fields:
            row_data[field] = clean_text(df_working.at[row_idx, field])
        rows.append(row_data)
    return pd.DataFrame(rows)


def set_decision_and_advance(pair_id: str, decision: str, total_candidates: int) -> None:
    st.session_state["decisions"][pair_id] = decision
    if st.session_state["review_index"] < total_candidates - 1:
        st.session_state["review_index"] += 1
    st.rerun()


def move_review_index(delta: int, total_candidates: int) -> None:
    new_index = st.session_state["review_index"] + delta
    new_index = max(0, min(total_candidates - 1, new_index))
    st.session_state["review_index"] = new_index
    st.rerun()


def candidate_preview_table(
    candidates: List[Dict[str, Any]],
    df_working: pd.DataFrame,
    decisions: Dict[str, str],
    limit: int = 50,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for candidate in candidates[:limit]:
        i = candidate["i"]
        j = candidate["j"]
        rows.append(
            {
                "Pair #": candidate["rank"],
                "Row A": i + 1,
                "Row B": j + 1,
                "Score": round(candidate["score"], 1),
                "Decision": decisions.get(candidate["pair_id"], "pending"),
                "Name A": f"{clean_text(df_working.at[i, 'First Name'])} {clean_text(df_working.at[i, 'Last Name'])}".strip(),
                "Name B": f"{clean_text(df_working.at[j, 'First Name'])} {clean_text(df_working.at[j, 'Last Name'])}".strip(),
                "Email A": clean_text(df_working.at[i, "Email"]),
                "Email B": clean_text(df_working.at[j, "Email"]),
                "Reasons": "; ".join(candidate["reasons"]),
            }
        )
    return pd.DataFrame(rows)


def build_export_bytes(df_original: pd.DataFrame, deduped_df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_original.to_excel(writer, sheet_name="Original", index=False)
        deduped_df.to_excel(writer, sheet_name="Deduped", index=False)
    output.seek(0)
    return output.getvalue()


def main() -> None:
    st.set_page_config(page_title="Participant Sign-up Deduplication", layout="wide")
    init_session_state()

    st.title("Participant Sign-up Deduplication")
    st.caption("Upload participant data, find likely duplicate sign-ups, review pairs, and export decisions.")

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
        reset_review_state()

    df_original = st.session_state["df_original"]
    df_working = st.session_state["df_working"]

    if df_original is None or df_working is None:
        st.error("No data is currently loaded. Please re-upload the file.")
        return

    st.subheader("Data preview")
    st.dataframe(df_original.head(20), use_container_width=True, hide_index=True)

    mapping_rows = []
    for field in EXPECTED_COLUMNS + OPTIONAL_COLUMNS:
        source = st.session_state["column_mapping"].get(field)
        mapping_rows.append(
            {
                "Expected Field": field,
                "Mapped Source Column": source if source else "(missing -> treated as empty)",
            }
        )
    st.caption("Column mapping")
    st.dataframe(pd.DataFrame(mapping_rows), use_container_width=True, hide_index=True)

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
        with st.spinner("Scoring candidate pairs..."):
            candidates, total_pairs = generate_candidates(
                df_working=df_working,
                threshold=float(threshold),
                max_candidates=int(max_candidates),
                weights=normalized_weights,
            )
        st.session_state["candidates"] = candidates
        st.session_state["decisions"] = {}
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

    total_candidates = len(candidates)
    st.divider()
    st.subheader("Review candidate pairs")

    st.session_state["review_index"] = max(
        0, min(st.session_state["review_index"], total_candidates - 1)
    )
    idx = st.session_state["review_index"]
    candidate = candidates[idx]

    decided_count, skipped_count = decision_counts(st.session_state["decisions"])
    reviewed_count = decided_count + skipped_count

    st.write(
        f"Progress: {decided_count} decided, {skipped_count} skipped, "
        f"{total_candidates} total candidates."
    )
    st.progress(reviewed_count / total_candidates)

    st.markdown(f"### Candidate {idx + 1} of {total_candidates}")
    st.metric("Score", f"{candidate['score']:.1f}")
    st.write("**Reasons:** " + "; ".join(candidate["reasons"]))
    current_decision = st.session_state["decisions"].get(candidate["pair_id"], "pending")
    st.caption(f"Current decision: {current_decision}")

    group_lookup = build_candidate_group_lookup(candidates, len(df_working))
    group_i = group_lookup.get(candidate["i"], [candidate["i"]])
    group_j = group_lookup.get(candidate["j"], [candidate["j"]])
    related_group_rows = sorted(set(group_i + group_j))
    if len(related_group_rows) > 2:
        st.markdown("#### Related possible duplicate group")
        st.caption(
            "This pair belongs to a larger potential duplicate set. "
            "Review all related rows together:"
        )
        st.dataframe(
            duplicate_group_table(df_working, related_group_rows),
            hide_index=True,
            use_container_width=True,
        )

    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown(f"#### Record A (row {candidate['i'] + 1})")
        st.dataframe(detail_table(df_working, candidate["i"]), hide_index=True, use_container_width=True)
        with st.expander("Show raw row A data"):
            raw_a = df_original.iloc[[candidate["i"]]].T.reset_index()
            raw_a.columns = ["Field", "Value"]
            st.dataframe(raw_a, hide_index=True, use_container_width=True)

    with right_col:
        st.markdown(f"#### Record B (row {candidate['j'] + 1})")
        st.dataframe(detail_table(df_working, candidate["j"]), hide_index=True, use_container_width=True)
        with st.expander("Show raw row B data"):
            raw_b = df_original.iloc[[candidate["j"]]].T.reset_index()
            raw_b.columns = ["Field", "Value"]
            st.dataframe(raw_b, hide_index=True, use_container_width=True)

    decision_cols = st.columns(3)
    with decision_cols[0]:
        if st.button("Confirm duplicates", type="primary", use_container_width=True):
            set_decision_and_advance(candidate["pair_id"], "duplicate", total_candidates)
    with decision_cols[1]:
        if st.button("Not duplicates", use_container_width=True):
            set_decision_and_advance(candidate["pair_id"], "not_duplicate", total_candidates)
    with decision_cols[2]:
        if st.button("Skip", use_container_width=True):
            set_decision_and_advance(candidate["pair_id"], "skipped", total_candidates)

    nav_cols = st.columns([1, 1, 2, 1])
    with nav_cols[0]:
        if st.button("Prev", disabled=idx == 0, use_container_width=True):
            move_review_index(-1, total_candidates)
    with nav_cols[1]:
        if st.button("Next", disabled=idx >= total_candidates - 1, use_container_width=True):
            move_review_index(1, total_candidates)
    with nav_cols[2]:
        jump_to = st.number_input(
            "Jump to pair #",
            min_value=1,
            max_value=total_candidates,
            value=idx + 1,
            step=1,
            key=f"jump_to_{idx}",
        )
    with nav_cols[3]:
        if st.button("Go", use_container_width=True):
            st.session_state["review_index"] = int(jump_to) - 1
            st.rerun()

    st.divider()
    st.subheader("Candidate table (first 50)")
    preview_df = candidate_preview_table(
        candidates=candidates,
        df_working=df_working,
        decisions=st.session_state["decisions"],
        limit=50,
    )
    st.dataframe(preview_df, use_container_width=True, hide_index=True)

    create_dates = pd.to_datetime(df_working["Create Date"], errors="coerce").tolist()
    dupe_flags = build_dupe_flags(
        row_count=len(df_original),
        candidates=candidates,
        decisions=st.session_state["decisions"],
        create_dates=create_dates,
    )
    deduped = df_original.copy()
    deduped["dupe"] = dupe_flags
    duplicate_rows = int(sum(dupe_flags))

    st.divider()
    st.subheader("Export reviewed result")
    st.write(
        "The export includes the original dataset and a deduped copy with `dupe` column "
        "(1 = marked as duplicate, 0 = not marked duplicate)."
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


if __name__ == "__main__":
    main()
