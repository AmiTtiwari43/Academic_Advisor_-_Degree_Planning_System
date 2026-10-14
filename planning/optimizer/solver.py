"""
CP-SAT constraint-based degree plan optimizer using Google OR-Tools.
Pure Python. Decoupled from Django ORM queries.
"""

from __future__ import annotations

import statistics
import time
from typing import Any

from ortools.sat.python import cp_model

from planning.optimizer.infeasibility import diagnose_infeasibility
from planning.optimizer.models import (
    CandidatePlan,
    OptimizationRequest,
    OptimizationResult,
    OptimizerCourse,
    ScheduledCourse,
    TradeOffSummary,
)

# Integer scaling factor for CP-SAT fractional credits (e.g. 3.5 cr -> 35 units)
CREDIT_SCALE = 10


def optimize_degree_plan(request: OptimizationRequest) -> OptimizationResult:
    """
    Executes lexicographic multi-objective constraint optimization to schedule
    degree requirements across available academic terms.

    Generates up to request.max_plans distinct candidate plans (Accelerated, Balanced, Light Pace)
    with trade-off summaries. If infeasible, diagnoses and reports exact blocking constraints.
    """
    start_time = time.perf_counter()

    available_terms = request.available_terms
    if not available_terms:
        return OptimizationResult(
            is_feasible=False,
            blocking_constraints=["No available terms provided for scheduling."],
            solver_status="NO_TERMS",
            solve_time_seconds=time.perf_counter() - start_time,
        )

    # Filter out courses already satisfied in student's academic history
    satisfied_codes = set(request.completed_courses) | set(request.in_progress_courses)
    schedulable_courses = [
        c for c in request.courses_to_schedule if c.code not in satisfied_codes
    ]

    # If student has already completed all courses, degree is already complete
    if not schedulable_courses:
        empty_plan = CandidatePlan(
            plan_index=1,
            plan_label="Complete",
            scheduled_courses=[],
            terms_used=[],
            term_loads={},
            trade_offs=TradeOffSummary(
                plan_label="Complete",
                total_terms_used=0,
                graduation_term_code="",
                total_credits=0.0,
                average_credits_per_term=0.0,
                workload_variance=0.0,
                max_term_credits=0.0,
                min_term_credits=0.0,
                trade_off_explanation="All required degree courses are already completed or in progress.",
            ),
            is_validated=True,
            validation_notes=["All degree requirements previously satisfied."],
        )
        return OptimizationResult(
            is_feasible=True,
            candidate_plans=[empty_plan],
            blocking_constraints=[],
            solver_status="OPTIMAL",
            solve_time_seconds=time.perf_counter() - start_time,
        )

    # Strategies to attempt in order
    strategies = [
        ("Accelerated", "ACCELERATED"),
        ("Balanced", "BALANCED"),
        ("Light Pace", "LIGHT"),
    ]

    candidate_plans: list[CandidatePlan] = []
    seen_signatures: set[tuple[tuple[str, str], ...]] = set()

    plan_index = 1
    last_solver_status = "UNKNOWN"

    for label, mode in strategies:
        if len(candidate_plans) >= request.max_plans:
            break

        plan, status = _solve_single_mode(
            request=request,
            schedulable_courses=schedulable_courses,
            satisfied_codes=satisfied_codes,
            mode=mode,
            plan_label=label,
            plan_index=plan_index,
        )
        last_solver_status = status

        if plan is not None:
            # Plan signature for deduplication: sorted ((course_code, term_code), ...)
            sig = tuple(
                sorted((sc.course_code, sc.term_code) for sc in plan.scheduled_courses)
            )
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                candidate_plans.append(plan)
                plan_index += 1

    total_time = time.perf_counter() - start_time

    if candidate_plans:
        return OptimizationResult(
            is_feasible=True,
            candidate_plans=candidate_plans,
            blocking_constraints=[],
            solver_status=last_solver_status,
            solve_time_seconds=total_time,
        )

    # Infeasible: run structural bottleneck diagnostic
    blocking_reasons = diagnose_infeasibility(request)
    return OptimizationResult(
        is_feasible=False,
        candidate_plans=[],
        blocking_constraints=blocking_reasons,
        solver_status=last_solver_status or "INFEASIBLE",
        solve_time_seconds=total_time,
    )


def _solve_single_mode(
    request: OptimizationRequest,
    schedulable_courses: list[OptimizerCourse],
    satisfied_codes: set[str],
    mode: str,
    plan_label: str,
    plan_index: int,
) -> tuple[CandidatePlan | None, str]:
    """Builds and executes a CP-SAT model for a specific pacing profile."""
    model: Any = cp_model.CpModel()
    num_terms = len(request.available_terms)

    course_map = {c.code: c for c in schedulable_courses}
    terms = request.available_terms

    # 1. Decision Variables
    # x[c_code, t_idx] in {0, 1}
    x: dict[tuple[str, int], cp_model.IntVar] = {}
    for c in schedulable_courses:
        for t in range(num_terms):
            x[(c.code, t)] = model.NewBoolVar(f"x_{c.code}_t{t}")

    # Term active indicators y[t_idx] in {0, 1}
    y: list[cp_model.IntVar] = [model.NewBoolVar(f"y_t{t}") for t in range(num_terms)]

    # Term credit loads L[t_idx]
    term_loads: list[cp_model.IntVar] = []
    for t_idx, term in enumerate(terms):
        max_cr = int(round(term.max_credits * CREDIT_SCALE))
        if mode == "LIGHT":
            # For light pace, cap per-term credits to 14.0 or term.max_credits
            max_cr = min(max_cr, int(round(14.0 * CREDIT_SCALE)))
        load_var = model.NewIntVar(0, max_cr, f"L_t{t_idx}")
        term_loads.append(load_var)

    # 2. Hard Constraints

    # A. Course exclusivity / mandatory completion
    for c in schedulable_courses:
        term_sum = sum(x[(c.code, t)] for t in range(num_terms))
        if c.is_mandatory:
            model.Add(term_sum == 1)
        else:
            model.Add(term_sum <= 1)

    # B. Term offerings season availability
    for c in schedulable_courses:
        offered_seasons = {s.upper() for s in c.offered_seasons}
        for t_idx, term in enumerate(terms):
            if term.season.upper() not in offered_seasons:
                model.Add(x[(c.code, t_idx)] == 0)

    # C. Prerequisites Precedence
    for c in schedulable_courses:
        for prereq in c.prerequisites:
            if prereq in satisfied_codes:
                # Met prior to term 0
                continue
            if prereq in course_map:
                # If taken in term t, prereq must be taken in term t_prev < t
                for t in range(num_terms):
                    prior_terms_sum = sum(x[(prereq, t_prev)] for t_prev in range(t))
                    model.Add(x[(c.code, t)] <= prior_terms_sum)
            else:
                # Prerequisite is not completed and not in curriculum -> course cannot be scheduled
                for t in range(num_terms):
                    model.Add(x[(c.code, t)] == 0)

    # D. Corequisites Precedence
    for c in schedulable_courses:
        for coreq in c.corequisites:
            if coreq in satisfied_codes:
                continue
            if coreq in course_map:
                # If taken in term t, coreq must be taken in term t_prev <= t
                for t in range(num_terms):
                    current_and_prior = sum(
                        x[(coreq, t_prev)] for t_prev in range(t + 1)
                    )
                    model.Add(x[(c.code, t)] <= current_and_prior)
            else:
                for t in range(num_terms):
                    model.Add(x[(c.code, t)] == 0)

    # E. Anti-requisites Exclusion
    for c in schedulable_courses:
        for anti in c.anti_requisites:
            if anti in satisfied_codes:
                # Anti-requisite already taken -> c cannot be scheduled
                for t in range(num_terms):
                    model.Add(x[(c.code, t)] == 0)
            elif anti in course_map:
                # Cannot take both c and anti in any terms
                c_sum = sum(x[(c.code, t)] for t in range(num_terms))
                anti_sum = sum(x[(anti, t)] for t in range(num_terms))
                model.Add(c_sum + anti_sum <= 1)

    # F. Term Loads and Credit Bounds
    for t_idx, term in enumerate(terms):
        c_weights = [
            int(round(c.credits * CREDIT_SCALE)) * x[(c.code, t_idx)]
            for c in schedulable_courses
        ]
        model.Add(term_loads[t_idx] == sum(c_weights))

        # Tie active indicator y[t_idx] to load
        max_cr = int(round(term.max_credits * CREDIT_SCALE))
        model.Add(term_loads[t_idx] <= max_cr * y[t_idx])
        model.Add(y[t_idx] <= term_loads[t_idx])

    # Minimum credit constraint for active non-final terms
    # Final active graduation term is exempt so student can graduate without forced extra credits
    total_sched_credits = sum(c.credits for c in schedulable_courses)
    for t_idx, term in enumerate(terms):
        min_cr = int(round(term.min_credits * CREDIT_SCALE))
        if request.enforce_min_credits and mode != "LIGHT" and min_cr > 0 and t_idx < num_terms - 1:
            # If total credits cannot support full-time load on prior terms, adjust threshold
            effective_min = min_cr
            if total_sched_credits < (num_terms - 1) * term.min_credits:
                effective_min = min(
                    min_cr,
                    int(round((total_sched_credits / max(1, num_terms)) * CREDIT_SCALE)),
                )

            if effective_min > 0:
                # Indicator whether any term after t_idx is active
                has_subsequent = model.NewBoolVar(f"has_subsequent_{t_idx}")
                future_active_sum = sum(y[t_next] for t_next in range(t_idx + 1, num_terms))
                model.Add(future_active_sum >= 1).OnlyEnforceIf(has_subsequent)
                model.Add(future_active_sum == 0).OnlyEnforceIf(has_subsequent.Not())

                # active_non_final = y[t_idx] AND has_subsequent
                active_non_final = model.NewBoolVar(f"active_non_final_{t_idx}")
                model.AddBoolAnd([y[t_idx], has_subsequent]).OnlyEnforceIf(active_non_final)
                model.AddBoolOr([y[t_idx].Not(), has_subsequent.Not()]).OnlyEnforceIf(
                    active_non_final.Not()
                )

                model.Add(term_loads[t_idx] >= effective_min).OnlyEnforceIf(active_non_final)

    # 3. Multi-Objective Function

    # G: Graduation term index (last active term)
    G = model.NewIntVar(0, num_terms - 1, "G")
    for c in schedulable_courses:
        for t in range(num_terms):
            model.Add(G >= t * x[(c.code, t)])

    # Target deviation per term: |L_t - target_load| when active
    target_load_int = int(round(request.target_credits_per_term * CREDIT_SCALE))
    deviations: list[cp_model.IntVar] = []
    for t_idx in range(num_terms):
        dev = model.NewIntVar(0, 30 * CREDIT_SCALE, f"dev_{t_idx}")
        # When y[t] == 1, dev >= |L_t - target|; when y[t] == 0, dev == 0
        diff = model.NewIntVar(-30 * CREDIT_SCALE, 30 * CREDIT_SCALE, f"diff_{t_idx}")
        model.Add(diff == term_loads[t_idx] - target_load_int)
        model.Add(dev >= diff).OnlyEnforceIf(y[t_idx])
        model.Add(dev >= -diff).OnlyEnforceIf(y[t_idx])
        model.Add(dev == 0).OnlyEnforceIf(y[t_idx].Not())
        deviations.append(dev)

    total_deviation = sum(deviations)

    # Soft preference bonus: preferred courses placed in earlier terms
    pref_terms: list[Any] = []
    for c in schedulable_courses:
        if c.preference_weight > 0:
            for t in range(num_terms):
                earlier_bonus = (num_terms - t) * c.preference_weight
                pref_terms.append(earlier_bonus * x[(c.code, t)])
    preference_objective = sum(pref_terms) if pref_terms else 0

    if mode == "ACCELERATED":
        # Strongly prioritize minimal graduation terms
        model.Minimize(
            100000 * G + 10 * total_deviation - preference_objective
        )
    elif mode == "BALANCED":
        # Prioritize smooth workload variance around target credits
        model.Minimize(
            10000 * G + 100 * total_deviation - preference_objective
        )
    else:  # LIGHT
        # Moderate graduation term, prioritize manageable per-term load
        model.Minimize(
            2000 * G + 50 * total_deviation - preference_objective
        )

    # 4. Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = request.timeout_seconds
    solver.parameters.num_workers = 1

    status_code = solver.Solve(model)
    status_name = solver.StatusName(status_code)

    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, status_name

    # 5. Extract Scheduled Courses
    scheduled_courses: list[ScheduledCourse] = []
    term_load_map: dict[str, float] = {t.code: 0.0 for t in terms}

    for t_idx, term in enumerate(terms):
        for c in schedulable_courses:
            if solver.Value(x[(c.code, t_idx)]) == 1:
                scheduled_courses.append(
                    ScheduledCourse(
                        course_code=c.code,
                        term_index=t_idx + 1,  # 1-indexed for academic plan convention
                        term_code=term.code,
                        credits=c.credits,
                    )
                )
                term_load_map[term.code] = round(term_load_map[term.code] + c.credits, 2)

    terms_used = [term.code for term in terms if term_load_map[term.code] > 0]
    total_credits = round(sum(sc.credits for sc in scheduled_courses), 2)
    active_loads = [term_load_map[code] for code in terms_used]

    num_terms_used = len(terms_used)
    grad_term_code = terms_used[-1] if terms_used else ""
    avg_credits = round(total_credits / num_terms_used, 2) if num_terms_used > 0 else 0.0
    variance = round(statistics.pvariance(active_loads), 2) if len(active_loads) > 1 else 0.0
    max_term_cr = max(active_loads) if active_loads else 0.0
    min_term_cr = min(active_loads) if active_loads else 0.0

    # Trade-off narrative
    if mode == "ACCELERATED":
        explanation = (
            f"Accelerated pace completes degree requirements in {num_terms_used} terms "
            f"({grad_term_code}) with a peak load of {max_term_cr:.1f} credits (avg: {avg_credits:.1f} cr/term). "
            f"Optimized for earliest possible graduation."
        )
    elif mode == "BALANCED":
        explanation = (
            f"Balanced pace completes degree requirements in {num_terms_used} terms "
            f"({grad_term_code}) with an even distribution averaging {avg_credits:.1f} credits/term "
            f"(workload variance: {variance:.2f}). Designed for academic sustainability."
        )
    else:
        explanation = (
            f"Light pace completes degree requirements across {num_terms_used} terms "
            f"({grad_term_code}) capping peak term load at {max_term_cr:.1f} credits (avg: {avg_credits:.1f} cr/term). "
            f"Recommended for students balancing external work or extracurricular responsibilities."
        )

    trade_offs = TradeOffSummary(
        plan_label=plan_label,
        total_terms_used=num_terms_used,
        graduation_term_code=grad_term_code,
        total_credits=total_credits,
        average_credits_per_term=avg_credits,
        workload_variance=variance,
        max_term_credits=max_term_cr,
        min_term_credits=min_term_cr,
        trade_off_explanation=explanation,
    )

    candidate_plan = CandidatePlan(
        plan_index=plan_index,
        plan_label=plan_label,
        scheduled_courses=scheduled_courses,
        terms_used=terms_used,
        term_loads=term_load_map,
        trade_offs=trade_offs,
        is_validated=False,
        validation_notes=[],
    )

    return candidate_plan, status_name
