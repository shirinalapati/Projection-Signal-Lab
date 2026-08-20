"""Public metrics-glossary copy. Presentation only; does not change admission."""

from __future__ import annotations

# Feature name -> glossary "What it measures" text for Hitting.
HITTER_METRIC_GLOSSARY: dict[str, str] = {
    "barrel_pct_w2": (
        "A hitter’s Barrel Rate across the current and previous season, weighted by plate "
        "appearances so the larger sample has more influence."
    ),
    "ev_w2": (
        "A hitter’s average Exit Velocity across the current and previous season, weighted by "
        "plate appearances."
    ),
    "k_pct_w2": (
        "A hitter’s strikeout rate across the current and previous season, weighted by plate "
        "appearances."
    ),
    "bb_pct_w2": (
        "A hitter’s walk rate across the current and previous season, weighted by plate "
        "appearances."
    ),
    "woba_w2": (
        "A hitter’s wOBA across the current and previous season, weighted by plate appearances. "
        "If no previous season is available, the current season is used."
    ),
    "xwoba_w2": (
        "A hitter’s expected wOBA across the current and previous season, weighted by plate "
        "appearances. It provides a more stable view of recent expected offensive performance "
        "than one season alone."
    ),
    "covid_season": (
        "Identifies observations from the shortened 2020 MLB season so its unusual schedule "
        "and smaller samples can be accounted for."
    ),
    "woba_w3": (
        "A hitter’s wOBA across the most recent three seasons, weighted by plate appearances."
    ),
    "age": "The player’s age during that season.",
    "avg_best_speed": (
        "A Statcast contact-quality measure emphasizing a hitter’s harder batted balls rather "
        "than allowing weak contact to dominate his average."
    ),
    "babip": (
        "Batting Average on Balls in Play: how often a hitter’s balls put into the field of play "
        "become hits, excluding home runs from the basic calculation."
    ),
    "barrel_pct": (
        "The percentage of batted balls classified as barrels—combinations of exit velocity and "
        "launch angle associated with especially productive contact."
    ),
    "bats_left": (
        "Indicates whether the hitter bats left-handed. Used as handedness context rather than "
        "a measure of hitting ability itself."
    ),
    "avg": (
        "Hits divided by at-bats. It measures how often a hitter records a hit but does not "
        "account for walks or distinguish the value of different types of hits."
    ),
    "is_catcher": (
        "Indicates whether catcher is the player’s primary position. It provides positional "
        "context because catchers face different workloads and offensive environments than "
        "other position players."
    ),
    "cent_pct": "The percentage of a hitter’s batted balls directed toward the middle of the field.",
    "o_contact_pct": (
        "How often a hitter makes contact when he swings at pitches outside the strike zone."
    ),
    "o_swing_pct": (
        "How often a hitter swings at pitches outside the strike zone. Also commonly called "
        "O-Swing%. Lower values generally indicate greater selectivity."
    ),
    "edge_pct": (
        "The share of pitches a hitter sees that are located around the edges of the strike zone "
        "rather than clearly down the middle or clearly outside it."
    ),
    "ev": (
        "The average speed of a hitter’s batted balls as they leave the bat. It is a direct "
        "measure of how hard the hitter typically makes contact."
    ),
    "xba": (
        "Statcast’s estimate of what a hitter’s batting average would be expected to look like "
        "based largely on the quality of his batted balls rather than only their actual outcomes."
    ),
    "xiso": (
        "An expected measure of extra-base power derived from underlying contact quality rather "
        "than only the extra-base hits that actually occurred."
    ),
    "xslg": (
        "Statcast’s estimate of a hitter’s expected slugging percentage based largely on the "
        "quality of his contact rather than only observed results."
    ),
    "fb_pct": "The percentage of batted balls classified as fly balls.",
    "gb_pct": "The percentage of batted balls classified as ground balls.",
    "hard_hit_pct": (
        "The percentage of batted balls hit at or above Statcast’s hard-hit threshold."
    ),
    "z_contact_pct": (
        "How often a hitter makes contact when swinging at pitches located inside the strike zone."
    ),
    "z_swing_pct": (
        "How often a hitter swings at pitches located inside the strike zone."
    ),
    "iso": (
        "A measure of extra-base power calculated as slugging percentage minus batting average. "
        "It removes singles from slugging to focus more directly on power."
    ),
    "k_pct": "The percentage of a hitter’s plate appearances that end in a strikeout.",
    "la": (
        "The average vertical angle at which a hitter’s batted balls leave the bat. It helps "
        "describe whether the hitter tends to produce ground balls, line drives, or fly balls."
    ),
    "lg_woba": (
        "The league-wide level of wOBA during that season. It provides context because offensive "
        "conditions across MLB change from year to year."
    ),
    "woba_z": (
        "The hitter’s wOBA expressed relative to the offensive environment of that particular "
        "MLB season, allowing performances from different run environments to be compared more "
        "fairly."
    ),
    "ld_pct": "The percentage of batted balls classified as line drives.",
    "meatball_swing_pct": (
        "How often a hitter swings at especially hittable, center-cut pitches. It helps describe "
        "whether the hitter attacks obvious mistakes."
    ),
    "obp": (
        "The share of plate appearances in which a hitter reaches base through hits, walks, or "
        "hit-by-pitches, with standard baseball scoring adjustments."
    ),
    "oppo_pct": "The percentage of batted balls a hitter sends to the opposite field.",
    "ops": (
        "On-base percentage plus slugging percentage. It provides a simple summary of a hitter’s "
        "ability to reach base and hit for power."
    ),
    "platoon_ops_diff": (
        "The difference between a hitter’s OPS against left-handed pitching and his OPS against "
        "right-handed pitching. It measures the size and direction of his platoon split."
    ),
    "ops_vs_lhp": "The hitter’s OPS against left-handed pitchers.",
    "ops_vs_rhp": "The hitter’s OPS against right-handed pitchers.",
    "park_factor": (
        "An estimate of how much a hitter’s home ballpark tends to increase or suppress offense "
        "compared with a more neutral environment."
    ),
    "wrc_plus": (
        "An offensive-performance measure adjusted for both the player’s park environment and "
        "the league scoring environment, making results more comparable across teams and seasons."
    ),
    "pa": (
        "The number of completed trips a hitter makes to the plate. It represents both playing "
        "time and the amount of evidence available about his performance."
    ),
    "woba_lag1": "The hitter’s wOBA from the season immediately before the current one.",
    "pull_pct": "The percentage of a hitter’s batted balls hit toward his pull side.",
    "seasons_since_debut": (
        "The number of MLB seasons since the player first appeared in the major leagues. It "
        "provides career-stage context beyond age alone."
    ),
    "slg": (
        "Total bases divided by at-bats. Unlike batting average, it gives additional credit for "
        "doubles, triples, and home runs."
    ),
    "sweet_spot_pct": (
        "The percentage of batted balls hit within Statcast’s favorable launch-angle range "
        "associated with productive contact."
    ),
    "swing_pct": (
        "The percentage of pitches at which a hitter swings, regardless of whether the pitch is "
        "inside or outside the strike zone."
    ),
    "bats_switch": (
        "Indicates whether the player bats from both sides of the plate. It provides handedness "
        "and matchup context rather than representing hitting quality by itself."
    ),
    "bb_pct": "The percentage of plate appearances ending in a walk.",
    "swstr_pct": (
        "The percentage of swings that result in a miss. In this study it uses Statcast "
        "swings-and-misses divided by total swings."
    ),
    "woba": (
        "Weighted On-Base Average for the current season. It measures overall offensive "
        "production while assigning different values to different outcomes—for example, a home "
        "run receives more credit than a single."
    ),
    "woba_x_age": (
        "An interaction between current-season wOBA and the player’s age relative to age 27. It "
        "tests whether the relationship between current offensive performance and future "
        "performance changes as players age."
    ),
    "xwoba": (
        "Expected Weighted On-Base Average. It estimates offensive performance from underlying "
        "events such as walks, strikeouts, and quality of contact instead of relying entirely "
        "on observed results."
    ),
    "xwobacon": (
        "Expected wOBA considering only balls that are put into play. It focuses on the quality "
        "of a hitter’s contact rather than walks and strikeouts."
    ),
    "woba_yoy": (
        "The difference between the hitter’s current-season wOBA and his previous-season wOBA. "
        "It measures whether his recent offensive production improved or declined."
    ),
}


def glossary_description(feature: str, player_type: str, fallback: str) -> str:
    if player_type == "hitter" and feature in HITTER_METRIC_GLOSSARY:
        return HITTER_METRIC_GLOSSARY[feature]
    return fallback


# Term -> definition for the Metrics glossary "Model and validation terms" section.
MODEL_VALIDATION_TERMS: tuple[tuple[str, str], ...] = (
    (
        "Baseline model",
        "The starting projection containing information the model should reasonably know before a "
        "new candidate metric is tested. Candidate metrics must provide value beyond this baseline, "
        "rather than being compared with an intentionally weak model.",
    ),
    (
        "Performance-history baseline",
        "Recent multi-year performance used as the foundation of a projection. For example, the "
        "hitting model uses recent wOBA history so another hitting statistic must show that it "
        "contributes information beyond what recent results already tell us.",
    ),
    (
        "Admitted-feature model",
        "A model built primarily from the features that survived the project's feature-admission "
        "process, along with the baseline and contextual information required to make the projection.",
    ),
    (
        "Kitchen-sink model",
        "A comparison model that uses a much larger collection of available features rather than "
        "carefully selecting them first. It tests whether simply giving the model more information "
        "performs better than selective feature admission.",
    ),
    (
        "Out-of-sample / OOS",
        "Evaluation on data that was not used to fit the model. This gives a more realistic measure "
        "of whether a model can predict new observations rather than simply explaining data it "
        "already saw.",
    ),
    (
        "Out-of-time validation",
        "A form of out-of-sample testing that respects time. The model is trained only on earlier "
        "seasons and evaluated on a later season. This is especially important for projections "
        "because the real task is always to use the past to predict the future.",
    ),
    (
        "Expanding-window validation",
        "A historical testing method in which the training data grows over time. For example, a "
        "model might train on all seasons through 2018 and test 2019, then train through 2019 and "
        "test 2020, and continue forward. Future seasons never enter the training data for an "
        "earlier prediction.",
    ),
    (
        "Temporal fold / Test period",
        "One historical train-and-test period in the expanding-window evaluation. “Improved in all "
        "seven temporal folds” means the metric helped in each of seven separate future-season tests.",
    ),
    (
        "Leakage",
        "When information that would not actually have been known at prediction time accidentally "
        "enters the model. Leakage can make a model appear much more accurate than it really is.",
    ),
    (
        "Regularization",
        "A modeling technique that discourages the model from relying too heavily on unnecessary "
        "or overlapping variables. This helps reduce overfitting and can make future predictions "
        "more reliable.",
    ),
    (
        "Ridge regression",
        "A regularized regression model that shrinks the influence of features rather than "
        "allowing unstable coefficients to become excessively large.",
    ),
    (
        "Elastic Net",
        "A regularized regression method that can both shrink feature weights and reduce the "
        "influence of redundant features. It is useful when many baseball statistics describe "
        "overlapping skills.",
    ),
)
