data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- results_dir
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
s7 <- merge(h, read.csv(file.path(data_dir, "derived/historical_seven_year.csv")), by = "blind_id")
cells <- list()
for (m in c("K23", "K08")) {
  x <- s7[s7$mechanism == m, ]
  add("7-year sample DID", m, "primary (5 years)", "complete 7-year follow-up", boot(primary ~ intent *
        post + yearf + ic, x, "intent:post"))
  add("7-year sample DID", m, "new_trial_7y", "complete 7-year follow-up", boot(new_trial_7y ~ intent *
        post + yearf + ic, x, "intent:post"))
  add(
    "7-year sample DID", m, "new_trial_7y_timely",
    "complete 7-year follow-up; trials registered within 12 months of start",
    boot(new_trial_7y_timely ~ intent * post + yearf + ic, x, "intent:post")
  )
  for (p in 0:1) {
    for (i in 0:1) {
      z <- x[x$post == p & x$intent == i, ]
      cells[[length(cells) + 1]] <- data.frame(
        mechanism = m, post = p, intent = i, n = nrow(z),
        new_trial_5y = round(100 * mean(z$primary), 1), new_trial_7y = round(
          100 * mean(z$new_trial_7y),
          1
        )
      )
    }
  }
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "follow_up/estimates.csv"), row.names = FALSE)
write.csv(do.call(rbind, cells), file.path(out, "follow_up/cells.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
