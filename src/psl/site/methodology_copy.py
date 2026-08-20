"""Public Methodology tab copy. Presentation only; does not change research outputs."""

from __future__ import annotations

from typing import Any


def render_methodology_html(audit: dict[str, Any] | None = None) -> str:
    audit = audit or {}
    h_n = int(audit.get("hitter_sample_n") or 0)
    p_n = int(audit.get("pitcher_sample_n") or 0)
    seasons = audit.get("hitter_seasons") or list(range(2015, 2026))
    season_lo = seasons[0] if seasons else 2015
    season_hi = seasons[-1] if seasons else 2025

    return f"""
    <article class="methodology">
    <h1 class="page-title">Methodology</h1>

    <h2>What this study is trying to answer</h2>
    <p>Projection Signal Lab asks a simple question with a complicated answer:</p>
    <p class="lede">Which information should actually change a projection of future player performance, and which information is more useful for explaining why that performance may happen?</p>
    <p>A metric does not automatically belong in a projection because it sounds important, correlates with future performance, or fits historical data well. It has to provide useful information on future seasons the model has not seen, remain reasonably stable, add something the model does not already know, be available for the players we need to evaluate, and hold up across different groups of players.</p>
    <p>The study applies that framework separately to five player-evaluation questions:</p>
    <ul>
      <li><b>Hitting:</b> next-season wOBA</li>
      <li><b>Pitching:</b> next-season FIP</li>
      <li><b>Baserunning:</b> next-season baserunning run-value rate</li>
      <li><b>Defense:</b> next-season fielding run-value rate</li>
      <li><b>Overall value:</b> next-season Baseball Reference WAR rate</li>
    </ul>
    <p>The same metric can therefore have different roles for different questions. Sprint Speed, for example, can contain useful information for projecting future baserunning without adding enough independent information to a hitting or WAR projection.</p>

    <h2>Why these projection targets?</h2>

    <h3>Hitting: next-season wOBA</h3>
    <p>The hitting study predicts next-season weighted on-base average, or wOBA.</p>
    <p>wOBA is used because it summarizes a hitter’s offensive production while recognizing that different outcomes have different values. A home run contributes more offensive value than a single, and a single contributes more than a walk.</p>
    <p>That makes wOBA more useful for this study than Batting Average, which treats many offensive events too similarly, or raw counting statistics such as runs and RBI, which depend heavily on playing time, lineup position, teammates, and team context.</p>
    <p>The purpose is not to claim that wOBA captures every part of hitting. Instead, it gives the study one broad offensive target against which metrics such as xwOBA, Exit Velocity, Barrel Rate, Chase Rate, contact rate, platoon performance, and recent performance history can be evaluated consistently.</p>
    <p class="method-question">The question is: Which information available today actually improves our estimate of a hitter’s offensive production next season?</p>

    <h3>Pitching: next-season FIP</h3>
    <p>The pitching study predicts next-season Fielding Independent Pitching, or FIP.</p>
    <p>FIP is used instead of ERA because ERA is influenced by factors that are not entirely controlled by the pitcher, including team defense, sequencing, and what happens to balls once they are put in play.</p>
    <p>FIP focuses more directly on outcomes a pitcher strongly influences: strikeouts, walks, hit batters, and home runs.</p>
    <p>This makes it a useful target for testing whether information such as velocity, movement, Stuff+, whiff rate, contact allowed, pitch usage, K%, BB%, K-BB%, and recent FIP history contains information about future pitching performance.</p>
    <p>K-BB% is therefore a candidate predictor, not the final pitching target. It can be extremely useful for predicting FIP without defining the entire pitching question itself.</p>
    <p>FIP is also preferable here to using ERA as the main target because the purpose of the study is to identify repeatable pitcher signal rather than reproduce all of the noise contained in past run prevention.</p>
    <p class="method-question">The question is: Which information about a pitcher today helps us forecast his underlying pitching performance next season?</p>
    <p>Lower FIP is better, so the direction of relationships must be interpreted accordingly. For example, a metric that has a negative relationship with future FIP may be favorable.</p>

    <h3>Baserunning: next-season baserunning run-value rate</h3>
    <p>The baserunning study predicts next-season baserunning run value, expressed as a rate rather than only as a counting total.</p>
    <p>This target is broader than stolen bases.</p>
    <p>Baserunning value can come from stealing a base, avoiding an out, taking an extra base, advancing from first to third, scoring from second, and other decisions that change a team’s expected runs.</p>
    <p>A player can therefore be a valuable baserunner without stealing many bases, and a player can steal bases while giving some value back through outs.</p>
    <p>Using a run-value target puts those actions onto a common baseball currency: runs gained or lost.</p>
    <p>The rate version is important because raw baserunning runs are heavily affected by opportunity and playing time. The study is more interested in the player’s baserunning ability than simply how often he reached base and had a chance to run.</p>
    <p>Candidate information includes recent baserunning history, Sprint Speed, Home-to-First Time, stolen-base attempts and success, extra-base advancement, outs on the bases, and related measures.</p>
    <p class="method-question">The question is: Which information available today tells us how much baserunning value a player is likely to create per opportunity next season?</p>

    <h3>Defense: next-season fielding run-value rate</h3>
    <p>The defensive study predicts next-season fielding run value, normalized for defensive playing time.</p>
    <p>The target is deliberately not Errors or Fielding Percentage.</p>
    <p>An official error only records certain unsuccessful plays. A defender can fail to reach a ball that another player might have converted into an out without being charged with an error at all. Conversely, a difficult attempted play can produce an error even though simply reaching the ball required significant defensive ability.</p>
    <p>A run-value target is broader. It asks how much defensive value a player created or cost relative to the opportunities he received.</p>
    <p>The rate version helps separate defensive performance from simply being on the field for more innings.</p>
    <p>The study can then evaluate information such as prior defensive run value, Outs Above Average, play-conversion measures, defensive opportunities, position, catcher defense, assists, errors, and other fielding information without assuming that any single defensive statistic represents defense perfectly.</p>
    <p>OAA is particularly useful as a process/performance measure where available, but it does not automatically become the universal defensive target. The broader fielding run-value target allows the study to cover defensive contributions across positions, including cases where one tracking statistic does not measure every relevant defensive responsibility equally.</p>
    <p class="method-question">The question is: Which information available today helps us forecast how much defensive value a player will create next season?</p>

    <h3>Overall player value: next-season WAR rate</h3>
    <p>The component studies deliberately separate hitting, pitching, baserunning, and defense because different skills behave differently.</p>
    <p>But baseball decisions ultimately concern players, not isolated skills.</p>
    <p>For that reason, the study also includes a higher-level target: next-season Baseball Reference WAR rate.</p>
    <p>WAR combines multiple ways a player contributes to winning into a common run/win framework. It allows the study to ask whether a metric that helps predict one component of performance also contains useful information about the player’s overall future value.</p>
    <p>The rate version is used because total WAR is strongly affected by playing time. A player who misses half the season can accumulate less WAR despite performing extremely well when on the field. This study primarily investigates performance signal; availability and playing time are related but distinct projection problems.</p>
    <p>The WAR study therefore does not replace the component studies.</p>
    <p>It answers a different question.</p>
    <p>For example:</p>
    <ul>
      <li>Sprint Speed may help forecast baserunning but add little new information to WAR once the model already knows a player’s recent overall value.</li>
      <li>Exit Velocity may contain information useful for both future hitting and future overall value.</li>
      <li>A pitching metric may improve future FIP without independently improving future WAR after other information is considered.</li>
    </ul>
    <p>That difference is useful. It prevents a metric from being labeled universally “predictive” simply because it works for one outcome.</p>
    <p class="method-question">The question is: Which information helps predict the player’s overall rate of value creation next season, after the model already knows his recent overall performance?</p>

    <h2>Populations</h2>
    <p>The core MLB data covers the {season_lo}–{season_hi} Statcast era.</p>
    <p>The canonical hitting modeling sample contains {h_n:,} hitter player-seasons.</p>
    <p>For the primary hitting study, a player must have at least 150 plate appearances in both year t and year t+1.</p>
    <p>The canonical pitching modeling sample contains {p_n:,} pitcher player-seasons.</p>
    <p>Pitcher eligibility is role-aware:</p>
    <ul>
      <li>Starting pitchers: at least 80 IP in both seasons</li>
      <li>Relief pitchers: at least 30 IP in both seasons</li>
      <li>2020 shortened-season exception: starters 25 IP; relievers 10 IP</li>
    </ul>
    <p>There are zero duplicated player-seasons in the canonical modeling tables.</p>
    <p>Baserunning, defense, and overall-value analyses use the eligible player-seasons for which the relevant target and required inputs are available. Component pages report the evidence for their own candidate metrics rather than silently treating unavailable data as observed.</p>

    <h2>The prediction timeline</h2>
    <p>This is a future-performance study.</p>
    <p>Information from season t and earlier is used to predict performance in season t+1.</p>
    <p>The model never gets to learn from the season it is being asked to predict.</p>
    <p>For example, when evaluating a prediction of 2025 performance, the model can use information available through 2024, but it cannot use anything from 2025 to construct the prediction.</p>
    <p>This distinction is essential. A feature can look extremely useful if future information accidentally enters training, but that result would be useless in a real front-office setting where the future has not happened yet.</p>

    <h2>Out-of-time validation</h2>
    <p>The primary validation method is an expanding time window rather than a random train/test split.</p>
    <p>For each historical test period:</p>
    <ul>
      <li>Train using only earlier seasons.</li>
      <li>Construct features using information that would have been known at the time.</li>
      <li>Predict the following season.</li>
      <li>Record how the model performs on that unseen season.</li>
      <li>Expand the training history and repeat.</li>
    </ul>
    <p>Formally, when season T is the outcome being predicted, the model is trained on earlier historical examples and evaluates season T−1 information against season T performance.</p>
    <p>A random row split is not used for headline conclusions because baseball data has a time structure. Randomly mixing earlier and later player-seasons can make a model look more reliable than it would have been in actual use.</p>
    <p>The headline results therefore answer:</p>
    <p class="method-question">Would this information have helped us predict seasons that had not happened yet?</p>

    <h2>Target-specific baselines</h2>
    <p>A candidate metric should not earn Projection status merely because it beats a weak model.</p>
    <p>Every component therefore begins with a reasonably strong baseline containing information that a real projection would already be expected to know.</p>
    <h3>Hitting baseline</h3>
    <ul>
      <li>Age</li>
      <li>Plate appearances</li>
      <li>PA-weighted 2-Year wOBA</li>
      <li>Park environment</li>
    </ul>
    <h3>Pitching baseline</h3>
    <ul>
      <li>Age</li>
      <li>Innings pitched</li>
      <li>Starter/reliever role</li>
      <li>IP-weighted 2-Year FIP</li>
      <li>Park environment</li>
    </ul>
    <h3>Baserunning baseline</h3>
    <ul>
      <li>Age</li>
      <li>Playing time</li>
      <li>2-Year baserunning run-value rate</li>
      <li>Park/context where relevant</li>
    </ul>
    <h3>Defense baseline</h3>
    <ul>
      <li>Age</li>
      <li>Defensive innings</li>
      <li>Position group</li>
      <li>2-Year fielding run-value rate</li>
    </ul>
    <h3>Overall-value baseline</h3>
    <ul>
      <li>Age</li>
      <li>Playing time</li>
      <li>Prior WAR rate</li>
      <li>Park/context where relevant</li>
    </ul>
    <p>These baseline variables are themselves legitimate projection inputs. Candidate-feature testing asks whether additional information improves on what this baseline already knows.</p>
    <p>That distinction prevents a metric from receiving credit simply for rediscovering recent performance.</p>

    <h2>What we measure for each candidate metric</h2>
    <p>No single statistic determines whether a feature belongs in a projection.</p>
    <p>Several pieces of evidence are considered together.</p>

    <h3>Future relationship</h3>
    <p>Do players with higher or lower values of this metric today tend to perform differently next season?</p>
    <p>The project reports Pearson correlation as a measure of linear association and Spearman correlation as a ranking-based robustness check.</p>
    <p>This is useful descriptive evidence, but correlation alone does not earn a metric Projection status.</p>
    <p>A metric can correlate strongly with future performance simply because it duplicates information already available in the model.</p>

    <h3>Relationship after the baseline</h3>
    <p>The project also asks:</p>
    <p class="method-question">Does the relationship remain after accounting for what the baseline already knows?</p>
    <p>This is summarized with partial correlation.</p>
    <p>The candidate metric and future target are each adjusted for the baseline using coefficients learned only from the training data. Their remaining relationship is then measured on the unseen validation season.</p>
    <p>This helps distinguish:</p>
    <ul>
      <li>“This metric is associated with good players.”</li>
      <li>“This metric tells us something about the future that our existing projection does not already know.”</li>
    </ul>
    <p>That distinction is central to the study.</p>

    <h3>Incremental out-of-time value</h3>
    <p>The most important prediction question is:</p>
    <p class="method-question">Does adding the metric actually improve forecasts of unseen future seasons?</p>
    <p>The candidate is added to the baseline and the two models are compared on future data.</p>
    <p>The technical metric is the change in RMSE, or root mean squared prediction error.</p>
    <p>On the public pages, this is translated into plain language such as:</p>
    <ul>
      <li>Reduced forecast error</li>
      <li>No meaningful improvement</li>
      <li>Forecast became slightly worse</li>
    </ul>
    <p>The sign of a technical error statistic is never treated as baseball interpretation by itself.</p>

    <h3>Drop-one importance</h3>
    <p>For metrics that make the final admitted-feature model, the reverse test is also useful:</p>
    <p class="method-question">Does prediction get worse if we remove this metric from the completed model?</p>
    <p>This guards against a feature appearing useful by itself but becoming unnecessary once the rest of the selected variables are present.</p>

    <h3>Temporal stability</h3>
    <p>A useful projection input should not work only because of one unusual season.</p>
    <p>The study examines:</p>
    <ul>
      <li>How stable the metric itself is from year to year.</li>
      <li>Whether its relationship with the future target remains reasonably consistent across historical validation periods.</li>
      <li>Whether the fitted model repeatedly uses the feature in the same general direction.</li>
    </ul>
    <p>This matters because baseball changes.</p>
    <p>Equipment, pitch design, league run environment, tracking technology, rules, training methods, and strategy can all change the meaning or distribution of a statistic over time.</p>
    <p>A metric that worked historically but loses its relationship with performance later should not be treated as permanently reliable.</p>

    <h3>Unique information and redundancy</h3>
    <p>Baseball metrics frequently measure overlapping concepts.</p>
    <p>Examples include:</p>
    <ul>
      <li>Exit Velocity, Hard-Hit Rate, and Barrel Rate</li>
      <li>wOBA, OPS, OBP, and SLG</li>
      <li>velocity measurements from different fastball definitions</li>
      <li>K%, BB%, and K-BB%</li>
    </ul>
    <p>K-BB% is exactly:</p>
    <p><b>K% − BB%</b></p>
    <p>Therefore K%, BB%, and K-BB% cannot be treated as three independent pieces of information.</p>
    <p>Candidate families are evaluated together. A metric may be strongly predictive by itself but still be classified as Diagnostic or Exclude if a simpler or more complete feature already contains most of the same useful information.</p>
    <p>The goal is not to maximize the number of variables.</p>
    <p>The goal is to preserve independent information.</p>

    <h3>Coverage and missing data</h3>
    <p>A feature can be excellent when available and still be unsuitable for a universal projection system.</p>
    <p>For each metric, the study asks:</p>
    <p class="method-question">How broadly can we obtain this information across the players and seasons we want to evaluate?</p>
    <p>Coverage is measured on the actual eligible modeling population rather than an unrelated unfiltered table.</p>
    <p>Missingness matters because it is often not random.</p>
    <p>A tracking metric may be missing mostly for:</p>
    <ul>
      <li>earlier seasons,</li>
      <li>players with very little playing time,</li>
      <li>minor-league players,</li>
      <li>particular tracking eras,</li>
      <li>or players outside the population for which the technology was available.</li>
    </ul>
    <p>Training only on the players who happen to have the metric can therefore introduce selection bias.</p>
    <p>Incomplete coverage does not automatically eliminate a feature.</p>
    <p>A strong but incomplete feature may receive Augmented Projection status and be used when available.</p>
    <p>When the historical window is too thin to make a defensible conclusion, it receives Insufficient Evidence rather than being called useless.</p>

    <h3>Subgroup robustness</h3>
    <p>A metric should not earn universal Projection status because it works extremely well for one narrow group while failing badly elsewhere.</p>
    <p>The study therefore examines whether results remain reasonable across relevant player subgroups, when sample size permits.</p>
    <p>Depending on the component, these can include differences such as:</p>
    <ul>
      <li>younger vs older players,</li>
      <li>higher vs lower playing time,</li>
      <li>handedness,</li>
      <li>starter vs reliever,</li>
      <li>position group,</li>
      <li>or other baseball-relevant groups.</li>
    </ul>
    <p>This does not require every subgroup to have identical coefficients.</p>
    <p>The question is whether the feature’s overall conclusion is robust enough that applying it broadly would not hide a major failure for an important population.</p>

    <h3>Target robustness</h3>
    <p>The final gate asks a different question:</p>
    <p class="method-question">Does the metric’s role change depending on what we are trying to predict?</p>
    <p>This was added because “predictive metric” is not a universal label.</p>
    <p>A metric can be:</p>
    <ul>
      <li>Projection for baserunning,</li>
      <li>Diagnostic for hitting,</li>
      <li>Diagnostic for defense,</li>
      <li>and still add little to overall WAR.</li>
    </ul>
    <p>Likewise, Stuff+ can contain information about future FIP without needing to be treated as a universal measure of pitcher value.</p>
    <p>The project therefore stores verdicts by metric and target, not only by metric.</p>

    <h2>The six admission gates</h2>
    <p>A candidate feature is evaluated through six related gates:</p>
    <ol>
      <li><b>Future predictive value</b> — Does it improve predictions on unseen future seasons relative to a meaningful baseline?</li>
      <li><b>Temporal stability</b> — Is the metric, and its relationship with the target, sufficiently stable across time?</li>
      <li><b>Unique information</b> — Does it add something beyond variables the model already knows, rather than duplicate a stronger or simpler feature?</li>
      <li><b>Coverage and selection bias</b> — Is it available for enough of the relevant player population to be used responsibly?</li>
      <li><b>Subgroup robustness</b> — Does the conclusion remain reasonable across important types of players?</li>
      <li><b>Target robustness</b> — Does its role depend on whether we are projecting hitting, pitching, baserunning, defense, or overall value?</li>
    </ol>
    <p>No single gate is intended to replace baseball judgment. Together they provide a repeatable standard for deciding what a metric should be used for.</p>

    <h2>Admission verdicts</h2>
    <p>Every tested metric receives a target-specific role.</p>

    <h3>Projection</h3>
    <p>Use it to help determine the projected number.</p>
    <p>The metric provides repeatable future information beyond what the model already knows, with acceptable stability, independence, coverage, and robustness.</p>

    <h3>Augmented Projection</h3>
    <p>Predictive when available, but not suitable for every player.</p>
    <p>The metric passes the predictive tests but its historical coverage is too incomplete for a universal core model.</p>
    <p>It can still be valuable for the covered population.</p>

    <h3>Diagnostic</h3>
    <p>Use it primarily to understand why the projection looks the way it does.</p>
    <p>A Diagnostic metric can describe a real and important baseball skill—such as chase behavior, pitch quality, contact quality, movement, speed, or another mechanism—without adding enough independent future information to the broad projection.</p>
    <p>Diagnostic does not mean unimportant.</p>
    <p>It means: useful for understanding the player, but not necessary for changing this particular projection.</p>

    <h3>Context</h3>
    <p>Use it to interpret or adjust performance rather than call it player skill.</p>
    <p>Examples include park environment, league environment, playing time, role, handedness, or position.</p>
    <p>Context can be essential to a good projection even though it is not a skill metric.</p>

    <h3>Exclude</h3>
    <p>The feature did not provide enough unique predictive or diagnostic value for this target in this study.</p>
    <p>An Exclude verdict is a modeling decision, not a claim that the statistic has no use anywhere in baseball.</p>

    <h3>Insufficient Evidence</h3>
    <p>The available data does not support a confident decision yet.</p>
    <p>This can result from limited historical coverage, too few temporal validation periods, changing tracking availability, or other evidence limitations.</p>
    <p>Insufficient Evidence is not Exclude.</p>
    <p>Exclude means the evidence argues against using the feature for this purpose.</p>
    <p>Insufficient Evidence means the study does not yet know.</p>

    <h2>Technical statistics shown in the project</h2>
    <p>The public pages translate most technical values into baseball language, while the underlying statistics remain available for transparency.</p>

    <h3>Future correlation</h3>
    <p>Do players with higher values now tend to perform differently next season?</p>
    <p>The reported Pearson correlation is calculated within the out-of-time validation framework and combined across historical folds using Fisher’s z transformation.</p>
    <p>Spearman correlation provides a rank-based robustness check.</p>
    <p>Correlation is an association. It is not model importance, causation, or the percentage of performance explained. Correlation alone does not earn a metric Projection status, and correlations do not assign verdicts by themselves.</p>

    <h3>Partial correlation</h3>
    <p>Does that relationship remain after accounting for what the baseline already knows?</p>
    <p>Both the candidate metric and target are adjusted for the study’s baseline before their remaining relationship is measured.</p>
    <p>The adjustment is learned from training data only.</p>
    <p>This helps reveal whether a seemingly strong metric actually contains new information.</p>

    <h3>Drop-one out-of-sample importance</h3>
    <p>Does the completed projection get worse without this information?</p>
    <p>The model is evaluated with and without an admitted metric on the same out-of-time observations.</p>
    <p>This is used as supporting evidence for how much unique value an already-selected feature contributes.</p>

    <h3>Standardized coefficient</h3>
    <p>How strongly and in which direction does the fitted model use this variable?</p>
    <p>Standardization puts inputs onto comparable scales.</p>
    <p>Coefficient paths are examined across historical test years primarily as a stability diagnostic.</p>
    <p>A large coefficient is not automatically evidence that the feature should be admitted.</p>

    <h3>Coverage</h3>
    <p>How broadly can this information be obtained for the population being evaluated?</p>
    <p>The public coverage number is the share of eligible player-seasons with usable observations for the metric.</p>

    <h3>Verdict</h3>
    <p>After considering prediction, stability, uniqueness, coverage, subgroup behavior, and the target itself, what job should this metric have?</p>
    <p>That is the final output of the admission framework.</p>

    <h2>Complete-model comparisons</h2>
    <p>The project also asks whether disciplined feature selection actually helps compared with simply giving a model every available variable.</p>
    <p>The admitted-feature model uses the features selected through the research framework.</p>
    <p>The all-feature model provides a comparison in which many eligible variables are allowed into the modeling pipeline.</p>
    <p>Missing values in this comparison are handled without leaking future information: median values are learned from each training fold and then applied to its future validation season. Validation data never determines its own imputation values.</p>
    <p>The purpose is not to prove that smaller models always win.</p>
    <p>In some targets, a selective model may generalize better.</p>
    <p>In others, the larger feature set may perform similarly or better.</p>
    <p>That result is itself informative: the appropriate amount of feature selection can depend on the projection problem.</p>

    <h2>The 2020 season</h2>
    <p>The shortened 2020 MLB season creates an unusual playing-time environment.</p>
    <p>The project therefore uses reduced eligibility thresholds for that season and separately checks whether including 2020 changes major conclusions.</p>
    <p>The shortened-season treatment does not overturn the main hitter findings.</p>
    <p>The purpose of the robustness check is not to pretend that 2020 was normal; it is to verify that the study’s conclusions are not artifacts of one unusual season.</p>

    <h2>Feature Universe Audit</h2>
    <p>Feature selection can become misleading if a researcher quietly begins with only the statistics expected to work.</p>
    <p>Projection Signal Lab therefore maintains a Feature Universe Audit.</p>
    <p>Every field available in the project’s defined source tables is accounted for before the public feature-selection story is presented.</p>
    <p>A field may be:</p>
    <ul>
      <li>tested directly,</li>
      <li>transformed into a more meaningful metric and tested,</li>
      <li>used only as context,</li>
      <li>identified as metadata,</li>
      <li>excluded because it would leak future information,</li>
      <li>represented by another variable containing the same information,</li>
      <li>unavailable with sufficient historical reliability,</li>
      <li>or otherwise unsuitable as an independent player-skill feature.</li>
    </ul>
    <p>Fields are not removed from the research record merely because they produce weak results.</p>
    <p>The audit also distinguishes two very different decisions:</p>
    <ul>
      <li><b>Pre-test eligibility:</b> Can this field be studied validly at all?</li>
      <li><b>Post-test admission:</b> After a valid test, should the metric be Projection, Augmented Projection, Diagnostic, Context, Exclude, or Insufficient Evidence?</li>
    </ul>
    <p>The full registry and omission reasons are available on the <a href="feature-audit.html">Feature Audit</a> page.</p>

    <h2>Data sources</h2>
    <p>The public study uses data assembled from:</p>
    <ul>
      <li>Baseball Savant / Statcast</li>
      <li>MLB Stats API</li>
      <li>park and player-context tables used by the project</li>
      <li>Baseball Reference component and WAR information where used for the component targets</li>
      <li>pitch-level Stuff+ generated from the project’s pitch-quality model</li>
    </ul>
    <p>Stuff+ is produced using an expanding-window pitch-level model so that a season’s score is constructed without training on future seasons.</p>
    <p>The pitch-quality methodology originates from Arsenal Intelligence, the related pitch-modeling project.</p>
    <p>The study does not fabricate statistics that cannot be obtained reliably.</p>

    <h2>Scouting, injuries, and minor-league information</h2>
    <p>The public study does not contain the full proprietary information that a major-league organization would possess.</p>
    <p>That does not change the admission framework.</p>

    <h3>Scouting evaluations</h3>
    <p>A scouting grade would be treated as another source of information and tested against the relevant target.</p>
    <p>Its role should depend on what it measures.</p>
    <p>For example:</p>
    <ul>
      <li>a speed grade may be relevant to baserunning or defense,</li>
      <li>a command grade may contain information about pitching,</li>
      <li>a raw power grade may help explain contact-quality potential.</li>
    </ul>
    <p>A scouting grade should not automatically enter every projection simply because an evaluator considers it meaningful. It should be tested for incremental future value, stability, redundancy with tracking data, coverage, and subgroup behavior.</p>
    <p>Even when it does not improve the statistical projection, it may remain valuable diagnostic information.</p>

    <h3>Injury history</h3>
    <p>Injury history often answers a somewhat different question:</p>
    <p class="method-question">How much will the player be available to perform?</p>
    <p>That makes it especially relevant to playing-time and availability projection.</p>
    <p>The rate-skill models in this project primarily ask how well a player is likely to perform when playing.</p>
    <p>If reliable injury history were available, the study would test whether it independently improves those rate projections as well, rather than assuming it does.</p>
    <p>A complete player-value system could then combine:</p>
    <p><b>performance rate × expected opportunity/availability</b></p>
    <p>rather than forcing injury information into every skill model.</p>

    <h3>Minor-league information</h3>
    <p>Raw minor-league statistics should not be treated as directly equivalent to MLB statistics.</p>
    <p>Before entering an MLB projection, minor-league performance would need to account for factors such as:</p>
    <ul>
      <li>level of competition,</li>
      <li>league run environment,</li>
      <li>park environment,</li>
      <li>age relative to level,</li>
      <li>playing time,</li>
      <li>and differences in tracking-data availability.</li>
    </ul>
    <p>After translation and contextual adjustment, minor-league metrics would enter the same admission framework as major-league metrics.</p>
    <p>A feature would still need to demonstrate that it improves future predictions rather than being admitted simply because it is available.</p>

    <h2>What this methodology is designed to prevent</h2>
    <p>The framework is intended to avoid several common projection mistakes:</p>
    <ul>
      <li>adding a statistic because it has an intuitive baseball story,</li>
      <li>rewarding a feature for fitting the same data on which it was developed,</li>
      <li>treating correlated versions of the same skill as independent evidence,</li>
      <li>training only on players with unusually complete tracking data,</li>
      <li>assuming a relationship from one era will remain unchanged,</li>
      <li>confusing environmental context with player ability,</li>
      <li>calling insufficient data evidence of no effect,</li>
      <li>and assuming that a metric useful for one part of player evaluation must be useful for every projection.</li>
    </ul>
    <p>The final goal is not the model with the most columns.</p>
    <p>It is a projection whose inputs have earned a reason to be there—and an accompanying diagnostic layer that preserves useful information about why a player may succeed, struggle, improve, or decline.</p>
    </article>
    """
