# Human-corrected adjusted DIDs for K23 awardees in the historical comparison.
# Within each institution-bootstrap draw, awardees with a human reference state keep it; every other awardee's joint
# K-trial/new-trial state is drawn from the human distribution in its sampling cell refined by the instrument's joint
# state (Dirichlet posterior; the parent cell is used when a refined cell holds no rated awardee). Intent correction
# keeps human intent for rated abstracts and draws intent for the others either within instrument call x instrument
# any-trial state (pooled across strata, because the intent sample holds few no-intent trial leaders in any one
# stratum) or within stratum x instrument call. The same fiscal-year and institute adjusted models
# are refitted on each draw.
data_dir <- Sys.getenv("DATA_DIR")
seed <- as.integer(Sys.getenv("DID_CORRECTION_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
n_boot <- 2000
out <- file.path(Sys.getenv("RESULTS_DIR"), "validation")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
rd <- function(f) read.csv(file.path(data_dir, f), stringsAsFactors = FALSE, colClasses = "character")
h <- Reduce(function(a, b) merge(a, b, by = "blind_id"), list(
  read.csv(file.path(data_dir, "historical/person_analysis.csv"), stringsAsFactors = FALSE),
  read.csv(file.path(data_dir, "derived/historical_extended.csv"), stringsAsFactors = FALSE),
  read.csv(file.path(data_dir, "derived/historical_reporting.csv"), stringsAsFactors = FALSE)
))
h <- h[h$mechanism == "K23" & h$besh_only_classifier == 0, ]
h$ic <- factor(h$ic)
h$yearf <- factor(h$year)
h$state3 <- ifelse(h$primary == 1, "new_trial", ifelse(h$ktrial_direct == 1, "ktrial_only", "none"))
h$own <- paste0("k", h$ktrial_direct, "p", h$primary)
h$parent <- paste(h$stratum, h$intent, h$state3)
h$cell <- paste(h$parent, h$own)
h$icell <- paste(h$intent, as.integer(h$ktrial_direct == 1 | h$primary == 1))

states <- c("k0p0", "k0p1", "k1p0", "k1p1")
ref <- rd("validation/reference_dossier_private.csv")
ref$parent <- paste(ref$stratum, ref$intent, ref$instrument_cell)
ref$cell <- paste(ref$parent, ref$instrument_state)
stopifnot(all(ref$blind_id %in% h$blind_id))
iref <- rd("validation/reference_intent_private.csv")
iref <- iref[iref$human_intent != "", ]
iref <- merge(iref, h[, c("blind_id", "ktrial_direct", "primary")], by = "blind_id")
iref$icell <- paste(iref$call, as.integer(iref$ktrial_direct == 1 | iref$primary == 1))

tally <- function(lab, groups) {
  lapply(split(lab, groups), function(z) setNames(sapply(states, function(s) sum(z == s)), states))
}
rdir <- function(a) {
  g <- rgamma(length(a), a)
  g / sum(g)
}
prior <- function(own, kind) if (kind == "centered") ifelse(states == own, 0.5, 0.01) else rep(0.5, 4)

# Draw joint states. `known` holds the human reference (blank when unclear or unrated).
impute <- function(x, known, cell_counts, parent_counts, kind) {
  st <- known[x$blind_id]
  st[is.na(st)] <- ""
  todo <- st == ""
  key <- paste(x$cell[todo])
  draws <- character(sum(todo))
  for (u in unique(key)) {
    i <- which(key == u)
    xi <- which(todo)[i[1]]
    counts <- cell_counts[[x$cell[xi]]]
    if (is.null(counts) || sum(counts) == 0) counts <- parent_counts[[x$parent[xi]]]
    draws[i] <- sample(states, length(i), replace = TRUE, prob = rdir(counts + prior(x$own[xi], kind)))
  }
  st[todo] <- draws
  x$k <- as.integer(substr(st, 2, 2))
  x$p <- as.integer(substr(st, 4, 4))
  x
}
iknown <- setNames(as.integer(iref$human_intent), iref$blind_id)
iref$scell <- paste(iref$stratum, iref$call)
h$scell <- paste(h$stratum, h$intent)
count_intent <- function(groups) {
  lapply(split(as.integer(iref$human_intent), groups), function(v) c(n1 = sum(v), n0 = sum(1 - v)))
}
icounts <- list(outcome = count_intent(iref$icell), stratum = count_intent(iref$scell))
impute_intent <- function(x, mode) {
  out <- iknown[x$blind_id]
  todo <- is.na(out)
  groups <- if (mode == "outcome") x$icell else x$scell
  for (u in unique(groups[todo])) {
    i <- which(todo & groups == u)
    call <- as.integer(x$intent[i[1]])
    n <- icounts[[mode]][[u]]
    a <- n["n1"] + ifelse(call == 1, 0.5, 0.01)
    b <- n["n0"] + ifelse(call == 1, 0.01, 0.5)
    out[i] <- rbinom(length(i), 1, rbeta(1, a, b))
  }
  unname(out)
}

joint <- function(x, intent) {
  x$I <- intent
  x <- droplevels(x)
  f <- function(y) unname(coef(lm(y ~ I * post + yearf + ic, data = cbind(x, y = y)))["I:post"])
  k <- f(x$k)
  p <- f(x$p)
  c(
    k = k, new = p, diff = k - p, any = f(as.integer(x$k | x$p)),
    neither = f(as.integer(!x$k & !x$p)), k_only = f(as.integer(x$k & !x$p)),
    new_only = f(as.integer(!x$k & x$p)), both = f(as.integer(x$k & x$p))
  )
}
labels <- c(
  k = "K-trial DID", new = "new-trial DID", diff = "K-trial minus new-trial DID", any = "any-trial DID",
  neither = "neither-state DID", k_only = "K-only-state DID", new_only = "new-only-state DID",
  both = "both-state DID"
)

reference_variant <- function(column, kind, intent_mode = NULL) {
  lab <- ref[[column]]
  known <- setNames(lab, ref$blind_id)
  resolved <- lab != ""
  cell_counts <- tally(lab[resolved], ref$cell[resolved])
  parent_counts <- tally(lab[resolved], ref$parent[resolved])
  function(x) {
    y <- impute(x, known, cell_counts, parent_counts, kind)
    joint(y, if (is.null(intent_mode)) x$intent else impute_intent(x, intent_mode))
  }
}
h$k <- h$ktrial_direct
h$p <- h$primary
variants <- list(
  observed = function(x) joint(x, x$intent),
  human_centered = reference_variant("ref_primary", "centered"),
  human_jeffreys = reference_variant("ref_primary", "jeffreys"),
  human_swap = reference_variant("ref_swap", "centered"),
  human_rater_a = reference_variant("ref_rater_a", "centered"),
  human_rater_b = reference_variant("ref_rater_b", "centered"),
  human_plus_intent_by_outcome = reference_variant("ref_primary", "centered", intent_mode = "outcome"),
  human_plus_intent_by_stratum = reference_variant("ref_primary", "centered", intent_mode = "stratum")
)
cl <- split(seq_len(nrow(h)), h$org_id)
res <- list()
for (v in names(variants)) {
  reps <- t(replicate(n_boot, {
    ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
    variants[[v]](h[ix, ])
  }))
  est <- if (v == "observed") joint(h, h$intent) else colMeans(reps)
  for (q in names(labels)) {
    res[[length(res) + 1]] <- data.frame(
      variant = v, quantity = labels[[q]], estimate = round(100 * est[[q]], 1),
      lo = round(100 * quantile(reps[, q], 0.025), 1), hi = round(100 * quantile(reps[, q], 0.975), 1),
      n = nrow(h), reps = n_boot, row.names = NULL
    )
  }
}
r <- do.call(rbind, res)
write.csv(r, file.path(out, "corrected_did.csv"), row.names = FALSE)
cat(sprintf("corrected DID: %d rows; n=%d; replicates=%d\n", nrow(r), nrow(h), n_boot))
