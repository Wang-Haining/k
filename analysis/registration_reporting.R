data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- results_dir
dir.create(file.path(out, "supplementary"), recursive = TRUE, showWarnings = FALSE)
n_boot <- 1000
fit <- function(formula, x, term) {
  x <- droplevels(x)
  drop <- Filter(function(v) is.factor(x[[v]]) && nlevels(x[[v]]) < 2, all.vars(formula))
  if (length(drop)) {
    formula <- update(formula, as.formula(paste(". ~ . -", paste(drop, collapse = " - "))))
  }
  b <- tryCatch(coef(lm(formula, data = x))[term], error = function(e) stop("model fitting failed"))
  if (is.na(b)) {
    NA_real_
  } else {
    unname(b)
  }
}
boot <- function(formula, x, term) {
  est <- fit(formula, x, term)
  if (Sys.getenv("PUBLIC") == "1") return(c(est = est, n = nrow(x)))
  cl <- split(seq_len(nrow(x)), x$org_id)
  reps <- replicate(n_boot, {
    ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
    fit(formula, x[ix, ], term)
  })
  c(est = est, lo = unname(quantile(reps, 0.025, na.rm = TRUE)), hi = unname(quantile(reps, 0.975,
        na.rm = TRUE
      )), se = sd(reps, na.rm = TRUE), n = nrow(x), na = sum(is.na(reps)))
}
res <- list()
add <- function(analysis, m, outcome, spec, s, scale = 100) {
  res[[length(res) + 1]] <<- data.frame(
    analysis = analysis, mechanism = m, outcome = outcome, spec = spec,
    estimate = round(scale * s["est"], 1), lo = round(scale * s["lo"], 1), hi = round(
      scale * s["hi"],
      1
    ), se = round(scale * s["se"], 2), mde80 = round(2.8 * scale * s["se"], 1), n = s["n"],
    na_reps = s["na"], row.names = NULL
  )
}
h <- Reduce(function(a, b) merge(a, b, by = "blind_id"), list(read.csv(file.path(data_dir,
        "historical/person_analysis.csv"),
      stringsAsFactors = FALSE
    ), read.csv(file.path(data_dir, "derived/historical_extended.csv"), stringsAsFactors = FALSE)))
starts <- source("analysis/start_flags.R")$value
h <- merge(h, starts, by = "blind_id")
h$ic <- factor(h$ic)
h$yearf <- factor(h$year)
hall <- h
h <- h[h$besh_only_classifier == 0, ]
d <- read.csv(file.path(data_dir, "contemporaneous/person_analysis.csv"), stringsAsFactors = FALSE, na.strings = c(
  "",
  "NA"
))
d <- Reduce(function(a, b) merge(a, b, by = "blind_id"), list(d[, c(
  "blind_id", "mechanism", "group",
  "year", "ic", "eligible_main"
)], read.csv(file.path(data_dir, "derived/contemporaneous_extended.csv"),
  stringsAsFactors = FALSE
), read.csv(file.path(data_dir, "instrument/analysis/person_variants.csv"),
  stringsAsFactors = FALSE
)[, c("blind_id", if (Sys.getenv("PUBLIC") != "1") "org_id", "primary_main", "preK_PI", "unresolved")]))
d <- d[d$eligible_main == 1 & d$unresolved == 0, ]
d$A <- as.integer(d$group == "Required")
d$ic <- factor(d$ic)
d$yearf <- factor(d$year)
for (m in c("K23", "K08")) {
  x <- h[h$mechanism == m, ]
  y <- d[d$mechanism == m, ]
  for (o in c("ktrial_timely", "primary_timely", "nih_new_trial", "nih_new_trial_own_grant")) {
    add("historical DID", m, o, "year FE + IC", boot(
      as.formula(paste(o, "~ intent*post + yearf + ic")),
      x, "intent:post"
    ))
  }
  add(
    "historical DID", m, "new_trial_due_results12", "awardees with a new trial due for reporting",
    boot(new_trial_due_results12 ~ intent * post + yearf + ic, x[x$new_trial_due == 1, ], "intent:post")
  )
  for (o in c("ktrial_timely", "primary_timely", "nih_new_trial", "nih_new_trial_own_grant")) {
    add("main RD", m, o, "unadjusted", boot(as.formula(paste(o, "~ A")), y, "A"))
  }
  add("main RD", m, "new_trial_due_results12", "awardees with a new trial due for reporting",
    boot(new_trial_due_results12 ~
        A, y[y$new_trial_due == 1, ], "A"))
}
h <- merge(h, read.csv(file.path(data_dir, "derived/historical_prior_trials.csv")), by = "blind_id")
d <- merge(d, read.csv(file.path(data_dir, "derived/contemporaneous_prior_trials.csv")), by = "blind_id")
for (m in c("K23", "K08")) {
  x <- h[h$mechanism == m, ]
  y <- d[d$mechanism == m, ]
  add("main RD", m, "primary_main", "adjusted for prior non-K trial PI + FY + IC", boot(primary_main ~
        A + preK_PI_nonK + yearf + ic, y, "A"))
  add("main RD", m, "primary_main", "awardees with no prior non-K trial", boot(primary_main ~ A, y[y$preK_PI_nonK ==
          0, ], "A"))
  add("historical DID", m, "primary", "adjusted for prior non-K trial PI", boot(primary ~ intent *
        post + preK_PI_nonK + yearf + ic, x, "intent:post"))
  add("historical DID", m, "primary", "awardees with no prior non-K trial", boot(primary ~ intent *
        post + yearf + ic, x[x$preK_PI_nonK == 0, ], "intent:post"))
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "supplementary/registration_sensitivity_estimates.csv"), row.names = FALSE)
sh <- do.call(rbind, lapply(c("K23", "K08"), function(m) {
  do.call(rbind, lapply(c("Required", "Not Allowed"), function(g) {
    s <- d[d$mechanism == m & d$group == g, ]
    du <- s[s$new_trial_due == 1, ]
    data.frame(mechanism = m, group = g, n = nrow(s), ktrial_timely = round(
      100 * mean(s$ktrial_timely),
      1
    ), primary_timely = round(100 * mean(s$primary_timely), 1), nih_new_trial = round(100 *
        mean(s$nih_new_trial), 1), nih_new_trial_own_grant = round(
      100 * mean(s$nih_new_trial_own_grant),
      1
    ), n_due = nrow(du), results12_among_due = if (nrow(du)) {
      round(100 * mean(du$new_trial_due_results12), 1)
    } else {
      NA
    })
  }))
}))
write.csv(sh, file.path(out, "supplementary/contemporaneous_registration_shares.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
