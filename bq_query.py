from google.cloud import bigquery
import pandas as pd

PARTICIPANT_LIST_QUERY = """
WITH participant_demo AS (
    SELECT
    sign_ups.*
    FROM
    (
        SELECT distinct
        participant.id as participant_id,
        createDate as create_date,
        participant.first as first_name,
        participant.last as last_name,
        response.label as email,
        t1.tracking.medium as utm_medium,
        t1.invitation.solutionId as invitation_id,
        row_number() OVER (PARTITION BY participant.id, createDate) as rownum
        FROM `sandbox-bigquery-466820.efg_pii.sign_up_feedback` t1,
        UNNEST(t1.response.components) as components,
        UNNEST(components.questions) as questions,
        UNNEST(questions.response) as response
        WHERE lower(questions.businessKey) like 'email'
        AND response.label not like '%hundredxinc%'
        AND response.label not like '%bbacchus@alumni.nd.edu%'
        AND response.label not like '%christina.ingrassia@gmail.com%'
        AND response.label not like '%cm.oe@westmont.edu%'
        AND response.label not like '%c.aroline.s.moe@gmail.com%'
        AND response.label not like '%car.oline.s.moe@gmail.com%'
        ) sign_ups
    WHERE rownum = 1
    AND invitation_id = @sign_up_solution_id
), affiliation_a AS (
    SELECT
    participant_id,
    affiliate_question,
    invitation_id,
    FROM
        (
        SELECT
        participant.id as participant_id,
        response.label as affiliate_question,
        t1.invitation.solutionId as invitation_id,
        FROM `sandbox-bigquery-466820.efg_pii.sign_up_feedback` t1,
        UNNEST(t1.response.components) as components,
        UNNEST(components.questions) as questions,
        UNNEST(questions.response) as response
        WHERE questions.businessKey = @affil_1
        AND t1.invitation.solutionId = @sign_up_solution_id
        and response.label != ''
        )
), affiliation_b AS (
    SELECT
    participant_id,
    affiliate_question,
    invitation_id,
    FROM
        (
        SELECT
        participant.id as participant_id,
        response.label as affiliate_question,
        t1.invitation.solutionId as invitation_id,
        FROM `sandbox-bigquery-466820.efg_pii.sign_up_feedback` t1,
        UNNEST(t1.response.components) as components,
        UNNEST(components.questions) as questions,
        UNNEST(questions.response) as response
        WHERE questions.businessKey = @affil_2
        AND t1.invitation.solutionId = @sign_up_solution_id
        and response.label != ''
        )
), affiliation_c AS (
    SELECT
    participant_id,
    affiliate_question,
    invitation_id,
    FROM
        (
        SELECT
        participant.id as participant_id,
        response.label as affiliate_question,
        t1.invitation.solutionId as invitation_id,
        FROM `sandbox-bigquery-466820.efg_pii.sign_up_feedback` t1,
        UNNEST(t1.response.components) as components,
        UNNEST(components.questions) as questions,
        UNNEST(questions.response) as response
        WHERE questions.businessKey = @affil_3
        AND t1.invitation.solutionId = @sign_up_solution_id
        and response.label != ''
        )
), contact_preference AS (
    SELECT
    participant.id as participant_id,
    response.label as contact
    FROM `sandbox-bigquery-466820.efg_pii.sign_up_feedback` t1,
    UNNEST(t1.response.components) as components,
    UNNEST(components.questions) as questions,
    UNNEST(questions.response) as response
    WHERE questions.label = 'Contact Preference'
    AND t1.invitation.solutionId = @sign_up_solution_id
), gross_feedback AS (
    SELECT
    participant_id,
    program_id,
    COUNT(distinct feedback_id) as gross_feedback_count
    FROM `listen-reporting.dwh_production_hxc_core.fact_feedback_unfiltered` t1
    WHERE program_id = @program_solution_id
    GROUP BY 1,2
), payout_eligible_feedback AS (
    SELECT
    participant_id,
    program_id,
    COUNT(distinct feedback_id) as payout_eligible_feedback_count
    FROM `listen-reporting.dwh_production_hxc_core.fact_feedback` t1
    WHERE program_id = @program_solution_id
    AND payout_eligible = true
    GROUP BY 1,2
), company_suggestions AS (
    SELECT
    participant.id as participant_id,
    t1.invitation.solutionId,
    COUNT (distinct t1.id) as company_suggestions_count
    FROM `sandbox-bigquery-466820.efg_data.program_feedback` t1
    WHERE
    (lower(t1.path.nodes[safe_offset(0)].name) like '%find a company?%'
    OR lower(t1.path.nodes[safe_offset(1)].name) like '%suggest a company%')
    AND t1.invitation.solutionId = @program_solution_id
    GROUP BY 1,2
), under_min_duration AS (
    SELECT
    participant.id as participant_id,
    t1.invitation.solutionId,
    COUNT (distinct t1.id) as under_min_duration_count
    FROM `sandbox-bigquery-466820.efg_data.program_feedback` t1
    WHERE duration_in_seconds < 20
    AND lower(t1.path.nodes[safe_offset(0)].name) not like '%find a company?%'
    AND lower(t1.path.nodes[safe_offset(0)].name) not like '%hundredx causes program%'
    AND lower(t1.path.nodes[safe_offset(0)].name) not like '%100x causes program%'
    AND lower(t1.path.nodes[safe_offset(0)].name) not like '%express feedback program%'
    AND t1.invitation.solutionId = @program_solution_id
    GROUP BY 1,2
), hxc_program_feedback AS (
    SELECT
    participant.id as participant_id,
    t1.invitation.solutionId,
    COUNT (distinct t1.id) as hxc_program_feedback_count
    FROM `sandbox-bigquery-466820.efg_data.program_feedback` t1
    WHERE
    (lower(t1.path.nodes[safe_offset(0)].name) like '%hundredx causes program%'
    OR lower(t1.path.nodes[safe_offset(0)].name) like '%100x causes program%'
    OR lower(t1.path.nodes[safe_offset(0)].name) like '%express feedback program%')
    AND t1.invitation.solutionId = @program_solution_id
    GROUP BY 1,2
), over_company_max AS (
    SELECT
    participant.id as participant_id,
    t1.invitation.solutionId,
    t1.path.nodes[safe_offset(2)].name,
    (COUNT (distinct t1.id) - 5) as over_company_max_count
    FROM `sandbox-bigquery-466820.efg_data.program_feedback` t1
    WHERE lower(t1.path.nodes[safe_offset(0)].name) not like '%hundredx causes program%'
    and lower(t1.path.nodes[safe_offset(0)].name) not like '%find a company?%'
    and lower(t1.path.nodes[safe_offset(0)].name) not like '%express feedback program%'
    and duration_in_seconds >= 20
    and t1.invitation.solutionId = @program_solution_id
    GROUP BY 1,2,3
    HAVING over_company_max_count > 0
), over_program_limit AS (
    SELECT
    participant.id as participant_id,
    t1.invitation.solutionId,
    (COUNT (distinct t1.id) - @feedback_limit) as over_program_limit_count
    FROM `sandbox-bigquery-466820.efg_data.program_feedback` t1
    WHERE lower(t1.path.nodes[safe_offset(0)].name) not like '%hundredx causes program%'
    and lower(t1.path.nodes[safe_offset(0)].name) not like '%find a company?%'
    and lower(t1.path.nodes[safe_offset(0)].name) not like '%express feedback program%'
    and duration_in_seconds >= 20
    and t1.invitation.solutionId = @program_solution_id
    GROUP BY 1,2
    HAVING over_program_limit_count > 0
), name_email_consent AS (
    SELECT
    participant.id as participant_id,
    response.label as consent
    FROM `sandbox-bigquery-466820.efg_pii.sign_up_feedback`,
    UNNEST(response.components) as components,
    UNNEST(components.questions) as questions,
    UNNEST(questions.response) as response
    WHERE lower(questions.businessKey) like 'name_email_consent'
    AND solution.id = @sign_up_solution_id
)
SELECT
eligible_feedback.participant_id,
eligible_feedback.invitation_id,
eligible_feedback.create_date,
CASE WHEN eligible_feedback.consent IN ('Yes','Please share') THEN eligible_feedback.first_name ELSE '****' END as first_name,
CASE WHEN eligible_feedback.consent IN ('Yes','Please share') THEN eligible_feedback.last_name ELSE '****' END as last_name,
CASE WHEN eligible_feedback.consent IN ('Yes','Please share') THEN eligible_feedback.email ELSE '****' END as email,
eligible_feedback.* EXCEPT(participant_id, invitation_id, create_date, first_name, last_name, email, consent),
CASE
WHEN (eligible_feedback.gross_feedback - eligible_feedback.hxc_program_feedback - eligible_feedback.company_suggestions) = 0 THEN "0"
WHEN (eligible_feedback.gross_feedback - eligible_feedback.hxc_program_feedback - eligible_feedback.company_suggestions) BETWEEN 1 AND 9 THEN "1 to 9"
WHEN (eligible_feedback.gross_feedback - eligible_feedback.hxc_program_feedback - eligible_feedback.company_suggestions) BETWEEN 10 AND 24 THEN "10 to 24"
WHEN (eligible_feedback.gross_feedback - eligible_feedback.hxc_program_feedback - eligible_feedback.company_suggestions) BETWEEN 25 and 49 then "25 to 49"
WHEN (eligible_feedback.gross_feedback - eligible_feedback.hxc_program_feedback - eligible_feedback.company_suggestions) BETWEEN 50 AND 74 THEN "50 to 74"
WHEN (eligible_feedback.gross_feedback - eligible_feedback.hxc_program_feedback - eligible_feedback.company_suggestions) >= 75 THEN "75+"
ELSE NULL
END
as feedback_group
FROM
(
    SELECT distinct
    participant_list.* EXCEPT(gross_feedback),
    (gross_feedback + company_suggestions + hxc_program_feedback) as gross_feedback,
    row_number() OVER (PARTITION BY participant_list.participant_id ORDER BY create_date DESC) as rownum,
    FROM
        (
        SELECT
        pd.participant_id as participant_id,
        pd.invitation_id as invitation_id,
        pd.create_date as create_date,
        pd.first_name as first_name,
        pd.last_name as last_name,
        pd.email as email,
        afa.affiliate_question as affiliation_a,
        afb.affiliate_question as affiliation_b,
        afc.affiliate_question as affiliation_c,
        cp.contact as contact_preference,
        pd.utm_medium as utm_medium,
        nec.consent as consent,
        (CASE WHEN gf.gross_feedback_count IS NOT NULL THEN gf.gross_feedback_count ELSE 0 END) as gross_feedback,
        (CASE WHEN pef.payout_eligible_feedback_count IS NOT NULL THEN pef.payout_eligible_feedback_count ELSE 0 END) as eligible_feedback,
        (CASE WHEN cs.company_suggestions_count IS NOT NULL THEN cs.company_suggestions_count ELSE 0 END) as company_suggestions,
        (CASE WHEN pf.hxc_program_feedback_count IS NOT NULL THEN pf.hxc_program_feedback_count ELSE 0 END) as hxc_program_feedback,
        (CASE WHEN ud.under_min_duration_count IS NOT NULL THEN ud.under_min_duration_count ELSE 0 END) as under_min_duration,
        (CASE WHEN cm.over_company_max_count IS NOT NULL THEN cm.over_company_max_count ELSE 0 END) as over_company_limit,
        (CASE WHEN pl.over_program_limit_count IS NOT NULL THEN pl.over_program_limit_count ELSE 0 END) as over_program_limit
        FROM participant_demo pd
        LEFT JOIN affiliation_a afa
        USING (participant_id)
        LEFT JOIN affiliation_b afb
        USING (participant_id)
        LEFT JOIN affiliation_c afc
        USING (participant_id)
        LEFT JOIN contact_preference cp
        USING (participant_id)
        LEFT JOIN gross_feedback gf
        USING (participant_id)
        LEFT JOIN payout_eligible_feedback pef
        USING (participant_id)
        LEFT JOIN company_suggestions cs
        USING (participant_id)
        LEFT JOIN under_min_duration ud
        USING (participant_id)
        LEFT JOIN hxc_program_feedback pf
        USING (participant_id)
        LEFT JOIN over_company_max cm
        USING (participant_id)
        LEFT JOIN over_program_limit pl
        USING (participant_id)
        LEFT JOIN name_email_consent nec
        USING (participant_id)
        ) participant_list
    ) eligible_feedback
WHERE eligible_feedback.rownum = 1
ORDER BY participant_id
"""


def run_participant_query(
    sign_up_solution_id: int,
    program_solution_id: int,
    feedback_limit: int,
    affil_1: str = "",
    affil_2: str = "",
    affil_3: str = "",
    credentials=None,
    project: str = "sandbox-bigquery-466820",
) -> pd.DataFrame:
    client = bigquery.Client(credentials=credentials, project=project)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("sign_up_solution_id", "INT64", sign_up_solution_id),
            bigquery.ScalarQueryParameter("program_solution_id", "INT64", program_solution_id),
            bigquery.ScalarQueryParameter("feedback_limit", "INT64", feedback_limit),
            bigquery.ScalarQueryParameter("affil_1", "STRING", affil_1),
            bigquery.ScalarQueryParameter("affil_2", "STRING", affil_2),
            bigquery.ScalarQueryParameter("affil_3", "STRING", affil_3),
        ]
    )

    query_job = client.query(PARTICIPANT_LIST_QUERY, job_config=job_config)
    return query_job.to_dataframe()
