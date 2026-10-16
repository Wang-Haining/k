# Aggregate sensitivity analyses using the historical model and institution bootstrap.
data_dir <- Sys.getenv("DATA_DIR")
results_dir <- Sys.getenv("RESULTS_DIR")
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(dir.exists(data_dir), dir.exists(results_dir), !is.na(seed))
set.seed(seed)
n_boot <- 1000
out <- file.path(results_dir, "sensitivity")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
rd <- function(f) read.csv(file.path(data_dir, f), stringsAsFactors = FALSE)
save_rows <- function(rows, filename) {
  x <- do.call(rbind, rows)
  stopifnot(nrow(x) > 0)
  write.csv(x, file.path(out, filename), row.names = FALSE)
  cat(sprintf("%s: %d aggregate rows\n", filename, nrow(x)))
}
join <- function(a, b) {
  stopifnot(!anyDuplicated(a$blind_id), !anyDuplicated(b$blind_id), all(a$blind_id %in% b$blind_id))
  x <- merge(a, b, by = "blind_id")
  stopifnot(nrow(x) == nrow(a))
  x
}
h <- join(rd("historical/person_analysis.csv"), rd("derived/historical_extended.csv"))
h <- join(h, rd("derived/historical_reporting.csv"))
h <- join(h, source("analysis/start_flags.R")$value)
h <- join(h, rd("derived/revision_person.csv"))
h <- h[h$besh_only_classifier == 0, ]
h$ic <- factor(h$ic)
h$yearf <- factor(h$year)
h$year_c <- h$year - 2017
h$drift <- h$intent * pmax(h$year_c, 0)
h$k_minus_new <- h$ktrial_direct - h$primary
h$no_text_diff <- h$k_no_text - h$new_no_text
h$covid_diff <- h$k_excl_covid - h$new_excl_covid
h$R01nih_R34_trialgrant_5y <- as.integer(h$R01nih_or_trialgrant_5y == 1 | h$R34 == 1)
stopifnot(nrow(h[h$mechanism == "K23", ]) == 1847)
rhs <- ~ intent * post + yearf + ic
fit <- function(x, columns, formula = rhs, term = "intent:post") {
  x <- droplevels(x)
  drop <- Filter(function(v) is.factor(x[[v]]) && nlevels(x[[v]]) < 2, all.vars(formula))
  if (length(drop)) formula <- update(formula, as.formula(paste("~ . -", paste(drop, collapse = " - "))))
  y <- as.matrix(x[, columns, drop = FALSE])
  stopifnot(nrow(x) > 0, all(is.finite(y)), !anyNA(x[, all.vars(formula), drop = FALSE]))
  unname(as.matrix(lm.fit(model.matrix(formula, x), y)$coefficients)[term, ])
}
bootstrap <- function(x, fun) {
  est <- fun(x)
  stopifnot(all(is.finite(est)), !anyNA(x$org_id), all(nzchar(as.character(x$org_id))))
  cl <- split(seq_len(nrow(x)), x$org_id)
  reps <- t(matrix(replicate(n_boot, fun(x[unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE), ])),
      nrow = length(est)))
  stopifnot(ncol(reps) == length(est), all(colSums(is.finite(reps)) >= 0.95 * n_boot))
  list(est = est, reps = reps)
}
estimate_rows <- function(x, columns, spec, formula = rhs, term = "intent:post") {
  if (Sys.getenv("PUBLIC") == "1") {
    return(list(data.frame(
      mechanism = unique(x$mechanism), outcome = columns, spec = spec,
      estimate = round(100 * fit(x, columns, formula, term), 2), n = nrow(x),
      n_pre = if ("post" %in% names(x)) sum(x$post == 0) else NA_integer_,
      n_post = if ("post" %in% names(x)) sum(x$post == 1) else NA_integer_
    )))
  }
  b <- bootstrap(x, function(z) fit(z, columns, formula, term))
  lapply(seq_along(columns), function(j) {
    data.frame(
      mechanism = unique(x$mechanism), outcome = columns[j], spec = spec,
      estimate = round(100 * b$est[j], 2), lo = round(100 * quantile(b$reps[, j], .025, na.rm = TRUE), 2),
      hi = round(100 * quantile(b$reps[, j], .975, na.rm = TRUE), 2), n = nrow(x),
      n_pre = if ("post" %in% names(x)) sum(x$post == 0) else NA_integer_,
      n_post = if ("post" %in% names(x)) sum(x$post == 1) else NA_integer_, n_institutions = length(unique(x$org_id)),
      na_reps = sum(is.na(b$reps[, j])), row.names = NULL
    )
  })
}

k23 <- h[h$mechanism == "K23", ]
grant <- estimate_rows(k23, c("k_id_field", "k_text", "k_none"), "grant-link component; year FE + IC")
grant <- c(grant, estimate_rows(
  k23, c("k_no_text", "new_no_text", "no_text_diff"),
  "free-text links ignored; K/new judgment otherwise; year FE + IC"
))
stopifnot(all(k23$k_no_text == k23$ktrial_direct), all(k23$new_no_text == k23$primary))
save_rows(grant, "grant_link_estimates.csv")

legacy <- covid <- registration <- funding <- list()
for (m in c("K23", "K08")) {
  x <- h[h$mechanism == m, ]
  outcomes <- c("ktrial_direct", "primary", "secondary", "k_minus_new")
  legacy <- c(legacy, estimate_rows(
    x[x$post == 1 | x$stratum == "pre_legacy", ], outcomes,
    "FY2018-2019 legacy pre; all post; five-year outcomes"
  ))
  legacy <- c(legacy, estimate_rows(
    x[x$year %in% 2018:2019, ], outcomes,
    "FY2018-2019 legacy and post; five-year outcomes"
  ))
  old_legacy <- x[x$post == 1 | x$start_ge_2018 == 1, ]
  reproduction <- estimate_rows(old_legacy, "ktrial_direct", "existing calendar-start legacy restriction")
  existing <- read.csv(file.path(results_dir, "historical/leadership_estimates.csv"))
  old <- existing[existing$mechanism == m & existing$outcome == "ktrial_direct" &
      grepl("pre-policy limited to 2018-19", existing$spec), ]
  stopifnot(
    nrow(old) == 1, abs(reproduction[[1]]$estimate - old$estimate) <= 0.051,
    reproduction[[1]]$n == old$n
  )
  legacy <- c(legacy, reproduction)
  covid <- c(covid, estimate_rows(
    x, c("k_excl_covid", "new_excl_covid", "covid_diff"),
    "five-year outcomes excluding trial starts in 2020-2021; all awardees retained"
  ))
  s <- rd("derived/historical_seven_year.csv")
  s <- join(s[s$blind_id %in% x$blind_id, ], x)
  registration <- c(registration, estimate_rows(
    s, c("primary", "new_trial_7y"),
    "same complete seven-year sample; original registration rule"
  ))
  registration <- c(registration, estimate_rows(
    s, c("new_5y_registered", "new_7y_registered"),
    "same complete seven-year sample; first submitted by K start + horizon"
  ))
  funding <- c(funding, estimate_rows(x, "R01nih_R34_trialgrant_5y", "historical DID; year FE + IC"))
}
save_rows(legacy, "legacy_estimates.csv")
save_rows(covid, "covid_estimates.csv")
save_rows(registration, "registration_horizon_estimates.csv")

if (Sys.getenv("PUBLIC") != "1") {
  # Reuse the frozen hazard results; add the previously implicit awardee denominators.
  hz <- read.csv(file.path(results_dir, "supplementary/hazard_estimates.csv"), stringsAsFactors = FALSE)
  hz <- hz[hz$analysis == "historical hazard DID (per person-year)" & hz$spec %in%
      c("+ calendar x intent FE", "excluding 2020-2021 person-years"), ]
  py <- rd("derived/historical_person_years.csv")
  hazard <- lapply(seq_len(nrow(hz)), function(i) {
    r <- hz[i, ]
    z <- py[py$blind_id %in% h$blind_id[h$mechanism == r$mechanism], ]
    if (r$spec == "excluding 2020-2021 person-years") z <- z[!z$cal_year %in% c(2020, 2021), ]
    stopifnot(nrow(z) == r$n)
    cbind(r, n_awardees = length(unique(z$blind_id)))
  })
  save_rows(hazard, "covid_hazard_estimates.csv")
}

# Estimate the differential linear cohort slope only on early pre-policy cohorts.
# Common cohort effects are absorbed by year FE; extrapolate the intent-specific slope.
trend_columns <- c("ktrial_direct", "primary", "k_minus_new")
trend_fit <- function(x) {
  slopes <- fit(
    x[x$post == 0 & x$year <= 2017, ], trend_columns,
    ~ intent + yearf + ic + intent:year_c, "intent:year_c"
  )
  original <- fit(x, trend_columns)
  for (j in seq_along(trend_columns)) {
    x[[trend_columns[j]]] <- x[[trend_columns[j]]] - slopes[j] * x$intent * x$year_c
  }
  c(fit(x, trend_columns), slopes, fit(x, "drift"), original)
}
b <- if (Sys.getenv("PUBLIC") == "1") list(est = trend_fit(k23)) else bootstrap(k23, trend_fit)
trend <- bounds <- list()
for (j in seq_along(trend_columns)) {
  for (kind in c("pretrend_extrapolated", "pretrend_slope", "original")) {
    index <- switch(kind,
      pretrend_extrapolated = j,
      pretrend_slope = j + 3,
      original = j + 7
    )
    trend[[length(trend) + 1]] <- data.frame(
      outcome = trend_columns[j], spec = kind,
      estimate = round(100 * b$est[index], 3),
      lo = if (Sys.getenv("PUBLIC") != "1") round(100 * quantile(b$reps[, index], .025, na.rm = TRUE), 3) else NA,
      hi = if (Sys.getenv("PUBLIC") != "1") round(100 * quantile(b$reps[, index], .975, na.rm = TRUE), 3) else NA,
      n = nrow(k23), n_pretrend = sum(k23$post == 0 & k23$year <= 2017),
      na_reps = sum(is.na(b$reps[, index])), row.names = NULL
    )
  }
  if (Sys.getenv("PUBLIC") == "1") next
  for (kind in c("original", "pretrend_extrapolated")) {
    index <- if (kind == "original") j + 7 else j
    # M bounds an additional constant intent-specific drift after FY2017, in pp/year.
    # Envelope the two shifted percentile intervals, refitting slope and exposure in every draw.
    envelope <- function(m) {
      a <- 100 * b$reps[, index] - m * b$reps[, 7]
      z <- 100 * b$reps[, index] + m * b$reps[, 7]
      c(
        lo = unname(quantile(pmin(a, z), .025, na.rm = TRUE)),
        hi = unname(quantile(pmax(a, z), .975, na.rm = TRUE))
      )
    }
    includes_zero <- function(m) {
      q <- envelope(m)
      q[1] <= 0 && q[2] >= 0
    }
    breakdown <- 0
    if (!includes_zero(0)) {
      upper <- 1
      while (!includes_zero(upper)) upper <- 2 * upper
      lower <- 0
      for (iteration in seq_len(50)) {
        mid <- (lower + upper) / 2
        if (includes_zero(mid)) upper <- mid else lower <- mid
      }
      breakdown <- upper
    }
    for (m in c(0, .5, 1, 2)) {
      q <- envelope(m)
      bounds[[length(bounds) + 1]] <- data.frame(
        outcome = trend_columns[j], spec = kind, M_pp_per_year = m,
        estimate = round(100 * b$est[index], 3), lo = round(q[1], 3), hi = round(q[2], 3),
        drift_exposure_years = round(b$est[7], 4), breakdown_pp_per_year = round(breakdown, 4),
        n = nrow(k23), reps = n_boot, row.names = NULL
      )
    }
  }
}
save_rows(trend, "cohort_trend_estimates.csv")
if (Sys.getenv("PUBLIC") != "1") save_rows(bounds, "cohort_trend_bounds.csv")

if (Sys.getenv("PUBLIC") != "1") {
  report <- rd("derived/revision_reporting.csv")
  report$mechanism <- "K23"
  reporting <- list()
  for (s in c("pre_early", "pre_legacy", "post")) {
    x <- report[report$stratum == s, ]
    reporting <- c(reporting, estimate_rows(
      x, c("within12", "ever_submitted"), paste("trial share", s),
      ~1, "(Intercept)"
    ))
  }
  for (s in c("pre_early", "pre_legacy")) {
    x <- report[report$stratum %in% c(s, "post"), ]
    x$P <- as.integer(x$stratum == "post")
    reporting <- c(reporting, estimate_rows(x, c("within12", "ever_submitted"), paste("post minus", s), ~P, "P"))
  }
  save_rows(reporting, "reporting_trial_estimates.csv")
}

d <- rd("contemporaneous/person_analysis.csv")[, c(
  "blind_id", "mechanism", "group", "year", "ic", "eligible_main", "R34"
)]
d <- join(d, rd("derived/contemporaneous_extended.csv"))
d <- join(d, rd("instrument/analysis/person_variants.csv")[, c(
  "blind_id", if (Sys.getenv("PUBLIC") != "1") "org_id", "unresolved"
)])
d <- d[d$eligible_main == 1 & d$unresolved == 0, ]
d$A <- as.integer(d$group == "Required")
d$ic <- factor(d$ic)
d$yearf <- factor(d$year)
d$R01nih_R34_trialgrant_5y <- as.integer(d$R01nih_or_trialgrant_5y == 1 | d$R34 == 1)
for (m in c("K23", "K08")) {
  x <- d[d$mechanism == m, ]
  funding <- c(funding, estimate_rows(x, "R01nih_R34_trialgrant_5y", "contemporaneous RD; unadjusted", ~A, "A"))
  funding <- c(funding, estimate_rows(
    x, "R01nih_R34_trialgrant_5y", "contemporaneous RD; year FE + IC",
    ~ A + yearf + ic, "A"
  ))
}
save_rows(funding, "funding_broadened_estimates.csv")
old_funding <- read.csv(file.path(results_dir, "funding/estimates.csv"), stringsAsFactors = FALSE)
old_funding <- old_funding[old_funding$outcome %in% c("R01nih_5y", "R01nih_or_trialgrant_5y"), ]
save_rows(list(old_funding), "funding_existing_estimates.csv")
cat(sprintf("Revision models complete: K23 n=%d; institution bootstrap=%d; seed=%d\n",
    nrow(k23), if (Sys.getenv("PUBLIC") == "1") 0 else n_boot, seed
  ))
