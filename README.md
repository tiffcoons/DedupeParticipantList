# Participant Duplicate Sign-up Review App

A local Streamlit web app for non-technical users to upload participant lists, detect likely duplicate sign-ups, review duplicate groups, and export a deduped result.

## What this app does

1. Uploads a participant file (`.csv` or `.xlsx`)
2. Prompts for Program PPF (default `1.6`) after upload
3. Standardizes expected fields (missing fields are treated as empty)
4. Scores likely duplicate pairs using fuzzy + exact signals
5. Lets users review one duplicate group at a time:
   - Confirm Duplicates
   - Not Duplicates
   - Some Duplicates (then review that group as individual pairs)
6. Exports an Excel workbook with:
   - `Original` sheet: unchanged uploaded data
   - `Deduped` sheet: original data plus:
     - `dupe` (`1` duplicate, `0` not duplicate)
     - `dupe participant id` (canonical participant id for dedupe grouping)
     - `dedupe eligible` (participant-id + affiliation eligibility sum, capped at 75; only first/original row has value)
     - `Total Value` (`dedupe eligible * Program PPF`; only first/original row has value)

Everything runs locally (no external API calls).

---

## Expected fields

The app looks for these labels (case/spacing-insensitive matching with aliases):

- Participant ID
- Already Flagged?
- Original Signup ID
- Create Date
- First Name
- Last Name
- Email
- Same Cookie Signups
- Recaptcha Score
- Emailable Score
- Signup IP
- Device
- Country Name
- City Name
- Zip Code
- Gender
- Age Group
- Ethnicity
- Affiliation
- Contact Preference
- UTM Medium
- Total Referrals
- Referral Feedback
- Feedback Group
- Gross Feedback
- Company Suggestions
- HXC Program Feedback
- Over Program Limit (>75)
- Insights Elig. Feedback
- Elig. Feedback
- Feedback Left to Give
- Payout Elig. Feedback (Last 300 Days)
- Payout Elig. Net

Optional extra signal:

- Phone

If a field is missing, it is safely treated as empty.

### Export calculations

- **dupe participant id**
  - Duplicate-linked rows are assigned the same canonical participant id (based on the original/earliest row in that dedupe group).
- **dedupe eligible**
  - For each `(dupe participant id, affiliation)` combination, the app sums `Elig. Feedback`.
  - The sum is capped at `75`.
  - Only the first/original signup row in that combination gets the value; all other rows are blank.
- **Total Value**
  - `dedupe eligible * Program PPF`
  - Only populated on the same first/original row as `dedupe eligible`.

---

## Matching logic

### Core weighted score (defaults)

- Name similarity (`rapidfuzz.fuzz.token_set_ratio`) -> weight `0.55`
- Email similarity (`rapidfuzz.fuzz.ratio`, exact match treated as strong) -> weight `0.25`
- Phone exact match (digits only, keep last 10 digits if longer) -> weight `0.15`
- IP exact match (trimmed string) -> weight `0.05`

The app normalizes configured weights to sum to 1.0.

The following fields are still loaded and available for review/export, but are **not used as matching signals**:

- Total Referrals
- Referral Feedback
- Feedback Group
- Gross Feedback
- Company Suggestions
- HXC Program Feedback
- Over Program Limit (>75)
- Insights Elig. Feedback
- Elig. Feedback
- Feedback Left to Give
- Payout Elig. Feedback (Last 300 Days)
- Payout Elig. Net

### Additional helpful signals (small bonus points)

- Original Signup ID exact match
- Participant ID exact match
- Device exact match
- City/ZIP or City/Country exact match
- Affiliation exact match
- Contact preference exact match
- UTM medium exact match
- Close signup dates

Candidate pairs are sorted by score descending.

---

## Review workflow

- Generate candidates above a minimum score threshold (default `75`)
- Limit output with **Max candidate pairs to generate** (default `1000`)
- **Exact name match section**:
  - Groups containing First + Last exact-name matches are shown together in one place
  - Users can click **Confirm All Exact Name Match Groups** to confirm those groups at once
- Only the remaining groups are shown in the regular review workflow
- Review groups in a table with:
  - Confirm Duplicates
  - Not Duplicates
  - Some Duplicates
  - Prev / Next / Jump to group number
- If **Some Duplicates** is selected, the app switches that group to pair-by-pair review so each pair can be marked independently
- Progress shows decided/in-progress/total group counts
- A table of the first 50 candidates appears below the review panel

When exporting, confirmed duplicate links are grouped transitively (A-B and B-C means A/B/C group). One primary record in each group stays `dupe=0`; others are marked `dupe=1`.

---

## Run locally

### 1) Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Start the app

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal (usually `http://localhost:8501`).

---

## Performance and scaling notes

This implementation evaluates row pairs with pairwise comparisons, which is `O(n^2)` in the number of rows.

- Good for small/medium files
- Can become slow for very large datasets

The app includes a **max candidate pairs** limit to control output size, but scoring still examines pair combinations.

For larger datasets, add **blocking keys** before pair scoring (for example):

- same email domain + first letter of last name
- same phone area code + zip
- same normalized last name + city

Blocking reduces comparisons and is the standard next step for scaling.

---

## Friendly validation behavior

- Invalid file type -> clear error message
- Empty file -> clear error message
- Too few rows -> warning
- Missing mapped fields -> shown in mapping table and treated as empty

