data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- results_dir
dir.create(file.path(out, "historical"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(out, "reporting"), recursive = TRUE, showWarnings = FALSE)
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
h <- merge(h, read.csv(file.path(data_dir, "derived/historical_reporting.csv"), stringsAsFactors = FALSE),
  by = "blind_id"
)
joint <- function(x) {
  x <- droplevels(x)
  b1 <- tryCatch(coef(lm(ktrial_direct ~ intent * post + yearf + ic, data = x))["intent:post"],
    error = function(e) stop("model fitting failed"))
  b2 <- tryCatch(coef(lm(primary ~ intent * post + yearf + ic, data = x))["intent:post"],
    error = function(e) stop("model fitting failed"))
  c(k = unname(b1), new = unname(b2), diff = unname(b1 - b2))
}
dd <- list()
for (m in c("K23", "K08")) {
  x <- h[h$mechanism == m, ]
  est <- joint(x)
  if (Sys.getenv("PUBLIC") == "1") {
    dd[[length(dd) + 1]] <- data.frame(
      mechanism = m, quantity = c("K-trial DID", "new-trial DID", "K-trial minus new-trial DID"),
      estimate = round(100 * unname(est), 1), n = nrow(x)
    )
    next
  }
  cl <- split(seq_len(nrow(x)), x$org_id)
  reps <- t(replicate(n_boot, {
    ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
    joint(x[ix, ])
  }))
  for (k in c("k", "new", "diff")) {
    dd[[length(dd) + 1]] <- data.frame(mechanism = m, quantity = c(
      k = "K-trial DID", new = "new-trial DID",
      diff = "K-trial minus new-trial DID"
    )[k], estimate = round(100 * est[k], 1), lo = round(100 *
        quantile(reps[, k], 0.025, na.rm = TRUE), 1), hi = round(100 * quantile(reps[, k], 0.975,
        na.rm = TRUE
      ), 1), n = nrow(x), na_reps = sum(is.na(reps[, k])), row.names = NULL)
  }
}
write.csv(do.call(rbind, dd), file.path(out, "historical/joint_leadership_estimates.csv"), row.names = FALSE)
rr <- list()
x <- h[h$mechanism == "K23" & h$intent == 1, ]
for (s in c("pre_early", "pre_legacy", "post")) {
  y <- x[x$stratum == s, ]
  d <- y[y$ktrial_due == 1, ]
  rr[[length(rr) + 1]] <- data.frame(stratum = s, n_intent = nrow(y), n_due_k_trial = nrow(d),
    pct_due_of_intent = round(100 *
        mean(y$ktrial_due), 1), results_posted_pct = round(100 * mean(d$ktrial_due_results), 1),
    results_12mo_pct = round(100 *
        mean(d$ktrial_due_results12), 1), row.names = NULL)
}
for (o in c("ktrial_due_results", "ktrial_due_results12")) {
  for (ref in c("pre_early", "pre_legacy")) {
    z <- x[x$ktrial_due == 1 & x$stratum %in% c(ref, "post"), ]
    z$P <- as.integer(z$stratum == "post")
    s <- boot(as.formula(paste(o, "~ P")), z, "P")
    add("K-trial results reporting, post minus stratum", "K23", o, ref, s)
  }
}
write.csv(do.call(rbind, rr), file.path(out, "reporting/ktrial_by_stratum.csv"), row.names = FALSE)
est <- do.call(rbind, res)
write.csv(est, file.path(out, "reporting/estimates.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
