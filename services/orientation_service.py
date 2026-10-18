"""Service d'orientation — questionnaire, recommandations, compatibilité.

## Logique de recommandation (déterministe, documentée, testable)

1. Le questionnaire produit des réponses symboliques (clés stables, jamais de
   texte traduit stocké), par exemple ``["subj_accounting", "subj_math"]``.
2. Chaque **parcours** déclare des *signaux* : (question, réponse, pondération,
   expliquable). Voir ``PATHWAYS``.
3. Pour un parcours : la contribution d'une question est la somme des signaux
   actifs **plafonnée** au poids maximal du parcours sur cette question ; la
   valeur finale est ``100 × contribution obtenue / contribution maximale``.
   Cet **indice d'intérêt** (0–100) n'est ni une probabilité d'admission ni un
   classement.
4. Aucune randomisation, aucun modèle appris : mêmes réponses ⇒ mêmes
   résultats. Aucune intelligence artificielle n'est utilisée.

## Compatibilité avec les critères d'admission

Un critère n'est évalué que s'il est publiable (statut ``official_verified``
ou ``demo``) **et** si le profil contient l'information nécessaire. Sinon le
résultat est ``unknown`` (« Vérification nécessaire »), jamais une supposition.
Un critère obligatoire non satisfait donne ``ko`` et signale l'incompatibilité.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy.orm import Session

from database import repositories as repo
from database.models import (
    VERIFICATION_DEMO,
    VERIFICATION_OFFICIAL,
    CandidateProfile,
    OrientationResult,
    Program,
)

# --------------------------------------------------------------------------- #
# Définition du questionnaire
# --------------------------------------------------------------------------- #

# Types : "multiselect" (une ou plusieurs réponses) / "radio" / "select" / "number"
QUESTIONNAIRE: list[dict[str, Any]] = [
    {
        "id": "subjects",
        "label_key": "q_subjects",
        "type": "multiselect",
        "help_key": "ori_select_all",
        "required": True,
        "options": [
            "subj_math", "subj_physics", "subj_svt", "subj_economics", "subj_accounting",
            "subj_languages", "subj_literature", "subj_it", "subj_law", "subj_history",
        ],
    },
    {
        "id": "skills",
        "label_key": "q_skills",
        "type": "multiselect",
        "help_key": "ori_select_all",
        "required": True,
        "options": [
            "skill_analysis", "skill_calc", "skill_speak", "skill_write", "skill_team",
            "skill_orga", "skill_creativity", "skill_persuade", "skill_rigor", "skill_digital",
        ],
    },
    {
        "id": "interests",
        "label_key": "q_interests",
        "type": "multiselect",
        "help_key": "ori_select_all",
        "required": True,
        "options": [
            "int_manager", "int_finance", "int_marketing", "int_audit", "int_startup",
            "int_trade", "int_data", "int_teach", "int_law", "int_events",
        ],
    },
    {
        "id": "domains",
        "label_key": "q_domains",
        "type": "multiselect",
        "help_key": "ori_select_all",
        "required": True,
        "options": [
            "pw_commerce", "pw_finance", "pw_marketing", "pw_audit", "pw_economie",
            "pw_entrepreneuriat", "pw_commerce_intl", "pw_data",
        ],
    },
    {
        "id": "formation_pref",
        "label_key": "q_formation_pref",
        "type": "radio",
        "help_key": "ori_select_one",
        "required": True,
        "options": ["fpref_uni", "fpref_grande_ecole", "fpref_engineer", "fpref_short", "fpref_open"],
    },
    {
        "id": "geo_pref",
        "label_key": "q_geo_pref",
        "type": "radio",
        "help_key": "ori_select_one",
        "required": True,
        "options": ["geo_home", "geo_big_city", "geo_region", "geo_anywhere", "geo_abroad"],
    },
    {
        "id": "bac_series",
        "label_key": "q_series",
        "type": "select",
        "help_key": "common_optional",
        "required": False,
        "options": None,  # list fournie par la couche UI (database.models.BAC_SERIES)
    },
    {
        "id": "average",
        "label_key": "q_average",
        "type": "number",
        "help_key": "common_optional",
        "required": False,
        "min": 0.0,
        "max": 20.0,
        "step": 0.25,
    },
]

# Regroupement en étapes (2 à 3 questions par écran, barre de progression).
STEPS: list[list[str]] = [
    ["subjects"],
    ["skills"],
    ["interests"],
    ["domains"],
    ["formation_pref", "geo_pref"],
    ["bac_series", "average"],
]

QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONNAIRE}


# --------------------------------------------------------------------------- #
# Parcours et signaux
# --------------------------------------------------------------------------- #


def _signal(question: str, option: str, weight: int) -> dict[str, Any]:
    return {"question": question, "option": option, "weight": weight}


PATHWAYS: list[dict[str, Any]] = [
    {
        "key": "pw_commerce",
        "label_key": "pw_commerce",
        "signals": [
            _signal("subjects", "subj_economics", 4),
            _signal("subjects", "subj_languages", 1),
            _signal("skills", "skill_orga", 3),
            _signal("skills", "skill_team", 3),
            _signal("skills", "skill_speak", 2),
            _signal("skills", "skill_persuade", 2),
            _signal("interests", "int_manager", 5),
            _signal("interests", "int_events", 1),
            _signal("domains", "pw_commerce", 6),
        ],
    },
    {
        "key": "pw_finance",
        "label_key": "pw_finance",
        "signals": [
            _signal("subjects", "subj_accounting", 5),
            _signal("subjects", "subj_math", 3),
            _signal("subjects", "subj_economics", 2),
            _signal("skills", "skill_calc", 4),
            _signal("skills", "skill_rigor", 4),
            _signal("skills", "skill_analysis", 3),
            _signal("interests", "int_finance", 5),
            _signal("interests", "int_audit", 2),
            _signal("domains", "pw_finance", 6),
        ],
    },
    {
        "key": "pw_marketing",
        "label_key": "pw_marketing",
        "signals": [
            _signal("subjects", "subj_economics", 3),
            _signal("subjects", "subj_literature", 2),
            _signal("subjects", "subj_languages", 2),
            _signal("skills", "skill_creativity", 4),
            _signal("skills", "skill_speak", 3),
            _signal("skills", "skill_persuade", 4),
            _signal("interests", "int_marketing", 5),
            _signal("interests", "int_events", 3),
            _signal("domains", "pw_marketing", 6),
        ],
    },
    {
        "key": "pw_audit",
        "label_key": "pw_audit",
        "signals": [
            _signal("subjects", "subj_accounting", 4),
            _signal("subjects", "subj_economics", 3),
            _signal("subjects", "subj_math", 2),
            _signal("skills", "skill_rigor", 5),
            _signal("skills", "skill_analysis", 4),
            _signal("skills", "skill_calc", 2),
            _signal("interests", "int_audit", 6),
            _signal("interests", "int_finance", 1),
            _signal("domains", "pw_audit", 6),
        ],
    },
    {
        "key": "pw_economie",
        "label_key": "pw_economie",
        "signals": [
            _signal("subjects", "subj_economics", 5),
            _signal("subjects", "subj_math", 3),
            _signal("subjects", "subj_physics", 1),
            _signal("skills", "skill_analysis", 5),
            _signal("skills", "skill_calc", 3),
            _signal("skills", "skill_write", 2),
            _signal("interests", "int_finance", 2),
            _signal("interests", "int_data", 2),
            _signal("interests", "int_law", 1),
            _signal("domains", "pw_economie", 6),
        ],
    },
    {
        "key": "pw_entrepreneuriat",
        "label_key": "pw_entrepreneuriat",
        "signals": [
            _signal("subjects", "subj_economics", 3),
            _signal("skills", "skill_persuade", 4),
            _signal("skills", "skill_creativity", 4),
            _signal("skills", "skill_orga", 3),
            _signal("skills", "skill_team", 2),
            _signal("interests", "int_startup", 6),
            _signal("interests", "int_manager", 3),
            _signal("domains", "pw_entrepreneuriat", 6),
        ],
    },
    {
        "key": "pw_commerce_intl",
        "label_key": "pw_commerce_intl",
        "signals": [
            _signal("subjects", "subj_languages", 5),
            _signal("subjects", "subj_economics", 3),
            _signal("skills", "skill_speak", 3),
            _signal("skills", "skill_write", 2),
            _signal("skills", "skill_team", 2),
            _signal("interests", "int_trade", 6),
            _signal("interests", "int_marketing", 2),
            _signal("domains", "pw_commerce_intl", 6),
        ],
    },
    {
        "key": "pw_data",
        "label_key": "pw_data",
        "signals": [
            _signal("subjects", "subj_it", 5),
            _signal("subjects", "subj_math", 4),
            _signal("skills", "skill_digital", 5),
            _signal("skills", "skill_analysis", 4),
            _signal("skills", "skill_rigor", 1),
            _signal("interests", "int_data", 6),
            _signal("domains", "pw_data", 6),
        ],
    },
]

# Réponses qui déclenchent explicitement un parcours : utilisées pour signaler
# qu'aucun parcours du modèle ne correspond (le questionnaire n'est pas exhaustif).
OPEN_CHOICE_KEY = "pw_other"


# --------------------------------------------------------------------------- #
# Calcul des parcours
# --------------------------------------------------------------------------- #


def _selected(answers: dict[str, Any], question_id: str) -> set[str]:
    value = answers.get(question_id)
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(v) for v in value}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return set()  # question numérique : sans objet pour les signaux
    return {str(value)}


def compute_pathways(answers: dict[str, Any]) -> list[dict[str, Any]]:
    """Calcule l'indice d'intérêt de chaque parcours (déterministe).

    Retourne une liste triée par indice décroissant, chaque entrée contenant
    ``key``, ``label_key``, ``index`` (0–100), ``reasons`` (signaux actifs) et
    ``max_possible``.
    """
    results: list[dict[str, Any]] = []
    for pathway in PATHWAYS:
        max_by_question: dict[str, int] = {}
        earned_by_question: dict[str, int] = {}
        reasons: list[dict[str, Any]] = []
        for signal in pathway["signals"]:
            question = signal["question"]
            max_by_question[question] = max(max_by_question.get(question, 0), signal["weight"])
            if signal["option"] in _selected(answers, question):
                earned_by_question[question] = earned_by_question.get(question, 0) + signal["weight"]
                reasons.append(
                    {
                        "question": question,
                        "option": signal["option"],
                        "weight": signal["weight"],
                    }
                )
        earned = sum(min(earned_by_question.get(q, 0), cap) for q, cap in max_by_question.items())
        maximum = sum(max_by_question.values())
        index = round(100.0 * earned / maximum) if maximum else 0
        results.append(
            {
                "key": pathway["key"],
                "label_key": pathway["label_key"],
                "index": index,
                "earned": earned,
                "max_possible": maximum,
                "reasons": reasons,
            }
        )
    results.sort(key=lambda item: (-item["index"], item["key"]))
    return results


# --------------------------------------------------------------------------- #
# Compatibilité avec les critères d'admission
# --------------------------------------------------------------------------- #

EVALUABLE_STATUSES = (VERIFICATION_OFFICIAL, VERIFICATION_DEMO)

STATUS_OK = "ok"
STATUS_KO = "ko"
STATUS_UNKNOWN = "unknown"
STATUS_NO_RULE = "no_rule"


def _evaluable(status: Optional[str]) -> bool:
    return status in EVALUABLE_STATUSES


def evaluate_criterion(criterion, profile_values: dict[str, Any]) -> dict[str, Any]:
    """Évalue un critère unique. Retourne ``{status, key, params}``.

    ``status`` ∈ ``ok`` / ``ko`` / ``unknown`` — ``unknown`` signale qu'une
    vérification est nécessaire (information absente ou non vérifiée).
    """
    ctype = criterion.criterion_type
    series = profile_values.get("bac_series")
    average = profile_values.get("average")
    required = bool(criterion.is_required)

    if not _evaluable(criterion.verification_status):
        return {"status": STATUS_UNKNOWN, "key": "eval_series_unverified" if ctype == "bac_series" else "eval_unverified", "params": {}, "required": required}

    if ctype == "bac_series":
        accepted = criterion.value if isinstance(criterion.value, list) else []
        if not series:
            return {"status": STATUS_UNKNOWN, "key": "eval_series_missing", "params": {}, "required": required}
        if series in accepted:
            return {
                "status": STATUS_OK,
                "key": "eval_series_ok",
                "params": {"series": series},
                "required": required,
            }
        return {
            "status": STATUS_KO if required else STATUS_UNKNOWN,
            "key": "eval_series_ko",
            "params": {"series": series, "accepted": ", ".join(accepted)},
            "required": required,
        }

    if ctype == "min_average":
        try:
            minimum = float(criterion.value)
        except (TypeError, ValueError):
            return {"status": STATUS_UNKNOWN, "key": "eval_unverified", "params": {}, "required": required}
        if average is None:
            return {"status": STATUS_UNKNOWN, "key": "eval_avg_missing", "params": {"min_average": minimum}, "required": required}
        if float(average) >= minimum:
            return {
                "status": STATUS_OK,
                "key": "eval_avg_ok",
                "params": {"average": float(average), "min_average": minimum},
                "required": required,
            }
        return {
            "status": STATUS_KO if required else STATUS_UNKNOWN,
            "key": "eval_avg_ko",
            "params": {"average": float(average), "min_average": minimum},
            "required": required,
        }

    # exam_type / other : jamais évalués automatiquement.
    return {"status": STATUS_UNKNOWN, "key": "eval_manual", "params": {}, "required": required}


def evaluate_program(program: Program, profile_values: dict[str, Any]) -> dict[str, Any]:
    """Statut de compatibilité d'une formation avec un profil.

    Statuts :
    * ``ok``      — tous les critères évaluables et obligatoires sont satisfaits ;
    * ``ko``      — au moins un critère **obligatoire** n'est pas satisfait ;
    * ``unknown`` — information manquante ou non vérifiée : vérification requise ;
    * ``no_rule`` — aucun critère publié pour cette formation.

    Ce résultat porte uniquement sur les critères publiés : ce n'est **pas**
    une probabilité d'admission.
    """
    rules = list(getattr(program, "admission_rules", []) or [])
    checks: list[dict[str, Any]] = []
    for rule in rules:
        for criterion in getattr(rule, "criteria", []) or []:
            check = evaluate_criterion(criterion, profile_values)
            check["rule_label"] = rule.label
            check["criterion_type"] = criterion.criterion_type
            check["description"] = criterion.description
            checks.append(check)

    if not checks:
        status = STATUS_NO_RULE
    elif any(c["status"] == STATUS_KO for c in checks):
        status = STATUS_KO
    elif all(c["status"] == STATUS_OK for c in checks):
        status = STATUS_OK
    else:
        status = STATUS_UNKNOWN

    school = getattr(program, "school", None)
    return {
        "program_id": program.id,
        "program_name": program.name,
        "school_name": school.name if school else "",
        "school_id": school.id if school else None,
        "degree_level": program.degree_level,
        "domain": program.domain,
        "status": status,
        "checks": checks,
    }


def _profile_values(profile: Optional[CandidateProfile], answers: dict[str, Any]) -> dict[str, Any]:
    series = (profile.bac_series if profile else None) or answers.get("bac_series") or None
    average = profile.average if profile else None
    if average is None:
        raw_average = answers.get("average")
        if isinstance(raw_average, (int, float)) and not isinstance(raw_average, bool):
            average = float(raw_average)
    return {"bac_series": series, "average": average}


def compute_program_matches(
    programs: Sequence[Program],
    profile: Optional[CandidateProfile],
    answers: dict[str, Any],
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Évalue les formations connues (celles dotées de critères d'abord)."""
    values = _profile_values(profile, answers)
    matches = [evaluate_program(program, values) for program in programs]
    order = {STATUS_KO: 0, STATUS_UNKNOWN: 1, STATUS_OK: 2, STATUS_NO_RULE: 3}
    matches.sort(key=lambda m: (order.get(m["status"], 9), m["program_name"]))
    return [m for m in matches if m["status"] != STATUS_NO_RULE][:limit]


def compute_recommendations(
    answers: dict[str, Any],
    profile: Optional[CandidateProfile],
    programs: Sequence[Program],
    top_pathways: int = 4,
) -> dict[str, Any]:
    """Résultat complet : parcours + compatibilités + notes de préférence."""
    pathways = compute_pathways(answers)
    retained = [p for p in pathways if p["index"] > 0][:top_pathways]
    notes: list[dict[str, Any]] = []
    if not retained:
        notes.append({"key": "ori_note_no_pathway", "params": {}})

    geo_pref = answers.get("geo_pref")
    if geo_pref:
        notes.append({"key": "ori_note_geo", "params": {"preference": geo_pref}})
    formation_pref = answers.get("formation_pref")
    if formation_pref:
        notes.append({"key": "ori_note_formation", "params": {"preference": formation_pref}})

    return {
        "pathways": retained,
        "all_pathways": pathways,
        "program_matches": compute_program_matches(programs, profile, answers),
        "notes": notes,
        "disclaimer_key": "ori_score_disclaimer",
    }


# --------------------------------------------------------------------------- #
# Persistance
# --------------------------------------------------------------------------- #


def save_result(
    session: Session,
    user_id: Optional[int],
    answers: dict[str, Any],
    result: dict[str, Any],
) -> OrientationResult:
    row = OrientationResult(user_id=user_id, questionnaire=answers, result=result)
    session.add(row)
    session.flush()
    if user_id:
        repo.add_audit_log(
            session,
            actor_id=user_id,
            action="orientation.completed",
            entity_type="orientation_result",
            entity_id=row.id,
            detail={"pathways": [p["key"] for p in result.get("pathways", [])]},
        )
    return row


def last_result(session: Session, user_id: int) -> Optional[OrientationResult]:
    return repo.latest_orientation_result(session, user_id)


def answers_from_profile(profile: Optional[CandidateProfile]) -> dict[str, Any]:
    """Pré-remplit les questions à partir du profil (aucune donnée inventée)."""
    answers: dict[str, Any] = {}
    if profile is None:
        return answers
    if profile.bac_series:
        answers["bac_series"] = profile.bac_series
    if profile.average is not None:
        answers["average"] = profile.average
    if profile.favorite_subjects:
        answers["subjects"] = list(profile.favorite_subjects)
    return answers


def questions_for_step(step_index: int) -> list[dict[str, Any]]:
    ids = STEPS[step_index] if 0 <= step_index < len(STEPS) else []
    return [QUESTIONS_BY_ID[qid] for qid in ids]


def validate_step_answers(step_index: int, values: dict[str, Any]) -> list[str]:
    """Contrôle d'étape : retourne les clés de traduction des erreurs."""
    errors: list[str] = []
    for question in questions_for_step(step_index):
        value = values.get(question["id"])
        if question.get("required") and (value is None or value == [] or value == ""):
            errors.append(question["label_key"])
    return errors


__all__ = [
    "EVALUABLE_STATUSES",
    "OPEN_CHOICE_KEY",
    "PATHWAYS",
    "QUESTIONNAIRE",
    "QUESTIONS_BY_ID",
    "STATUS_KO",
    "STATUS_NO_RULE",
    "STATUS_OK",
    "STATUS_UNKNOWN",
    "STEPS",
    "answers_from_profile",
    "compute_pathways",
    "compute_program_matches",
    "compute_recommendations",
    "evaluate_criterion",
    "evaluate_program",
    "last_result",
    "questions_for_step",
    "save_result",
    "validate_step_answers",
]
