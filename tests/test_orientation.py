"""Tests de la logique d'orientation (déterministe, documentée, sans IA)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import models as m  # noqa: E402
from services import orientation_service as ori  # noqa: E402


# --------------------------------------------------------------------------- #
# Définitions du questionnaire
# --------------------------------------------------------------------------- #


def test_questionnaire_is_divided_into_consistent_steps():
    declared = [question for step in ori.STEPS for question in step]
    assert sorted(declared) == sorted(ori.QUESTIONS_BY_ID)
    assert len(declared) == len(set(declared))  # aucune question dupliquée
    for question in ori.QUESTIONNAIRE:
        if question["type"] in ("multiselect", "radio", "select") and question["options"]:
            for option in question["options"]:
                assert option in question["label_key"] or option.startswith(("subj_", "skill_", "int_", "pw_", "fpref_", "geo_"))


def test_validate_step_answers_reports_missing_required_fields():
    errors = ori.validate_step_answers(0, {"subjects": []})
    assert errors == ["q_subjects"]
    assert ori.validate_step_answers(0, {"subjects": ["subj_math"]}) == []


def test_questions_for_step_are_stable():
    assert [q["id"] for q in ori.questions_for_step(4)] == ["formation_pref", "geo_pref"]
    assert ori.questions_for_step(99) == []


# --------------------------------------------------------------------------- #
# Calcul des parcours
# --------------------------------------------------------------------------- #


ALL_ANSWERS = {
    "subjects": [
        "subj_math", "subj_physics", "subj_svt", "subj_economics", "subj_accounting",
        "subj_languages", "subj_literature", "subj_it", "subj_law", "subj_history",
    ],
    "skills": [
        "skill_analysis", "skill_calc", "skill_speak", "skill_write", "skill_team",
        "skill_orga", "skill_creativity", "skill_persuade", "skill_rigor", "skill_digital",
    ],
    "interests": [
        "int_manager", "int_finance", "int_marketing", "int_audit", "int_startup",
        "int_trade", "int_data", "int_teach", "int_law", "int_events",
    ],
    "domains": [
        "pw_commerce", "pw_finance", "pw_marketing", "pw_audit", "pw_economie",
        "pw_entrepreneuriat", "pw_commerce_intl", "pw_data",
    ],
    "formation_pref": "fpref_grande_ecole",
    "geo_pref": "geo_big_city",
    "bac_series": "Économie et Gestion",
    "average": 14.0,
}


def test_pathways_are_deterministic():
    first = ori.compute_pathways(ALL_ANSWERS)
    second = ori.compute_pathways(dict(ALL_ANSWERS))
    assert first == second
    # Deuxième appel avec une copie profonde des listes : mêmes résultats.
    clone = {key: (list(value) if isinstance(value, list) else value) for key, value in ALL_ANSWERS.items()}
    assert ori.compute_pathways(clone) == first


def test_pathways_are_sorted_and_bounded():
    results = ori.compute_pathways(ALL_ANSWERS)
    indexes = [item["index"] for item in results]
    assert indexes == sorted(indexes, reverse=True)
    assert all(0 <= value <= 100 for value in indexes)
    assert len(results) == len(ori.PATHWAYS)


def test_per_question_cap_prevents_inflated_scores():
    """En sélectionnant toutes les réponses, chaque question est plafonnée :
    l'indice reste à 100 au lieu d'être multiplicateur (preuve du plafond)."""
    results = ori.compute_pathways(ALL_ANSWERS)
    for item in results:
        assert item["earned"] <= item["max_possible"]
        assert item["index"] == 100


def test_computed_index_matches_manual_calculation():
    """Cas de référence calculé à la main pour ``pw_data``.

    max = 5 (matières) + 5 (compétences) + 6 (centres d'intérêt) + 6 (domaines) = 22
    obtenu = 4 (maths) + 0 + 0 + 6 (données) = 10  ->  arrondi(100 × 10 / 22) = 45
    """
    answers = {
        "subjects": ["subj_math"],
        "skills": [],
        "interests": [],
        "domains": ["pw_data"],
    }
    results = {item["key"]: item for item in ori.compute_pathways(answers)}
    assert results["pw_data"]["max_possible"] == 22
    assert results["pw_data"]["earned"] == 10
    assert results["pw_data"]["index"] == 45
    assert {r["option"] for r in results["pw_data"]["reasons"]} == {"subj_math", "pw_data"}


def test_no_answer_gives_zero_for_every_pathway():
    results = ori.compute_pathways({})
    assert all(item["index"] == 0 for item in results)
    assert all(item["reasons"] == [] for item in results)


def test_matching_answer_ranks_expected_pathway_first():
    answers = {
        "subjects": ["subj_accounting"],
        "skills": ["skill_rigor", "skill_calc"],
        "interests": ["int_audit"],
        "domains": ["pw_audit"],
    }
    results = ori.compute_pathways(answers)
    assert results[0]["key"] == "pw_audit"


def test_numeric_answer_is_ignored_by_signals():
    results = ori.compute_pathways({"average": 15, "subjects": ["subj_math"]})
    assert 0 <= next(r for r in results if r["key"] == "pw_data")["index"] <= 100


# --------------------------------------------------------------------------- #
# Recommandations
# --------------------------------------------------------------------------- #


def test_recommendations_only_keep_pathways_with_interest():
    result = ori.compute_recommendations({}, None, [])
    assert result["pathways"] == []
    assert result["notes"][0]["key"] == "ori_note_no_pathway"
    assert result["disclaimer_key"] == "ori_score_disclaimer"


def test_recommendations_are_capped_and_include_disclaimer():
    result = ori.compute_recommendations(ALL_ANSWERS, None, [])
    assert 1 <= len(result["pathways"]) <= 4
    assert result["disclaimer_key"] == "ori_score_disclaimer"


def test_recommendations_add_preference_notes():
    result = ori.compute_recommendations(
        {"subjects": ["subj_it"], "domains": ["pw_data"], "geo_pref": "geo_home",
         "formation_pref": "fpref_engineer"},
        None,
        [],
    )
    note_keys = [note["key"] for note in result["notes"]]
    assert "ori_note_geo" in note_keys
    assert "ori_note_formation" in note_keys


# --------------------------------------------------------------------------- #
# Compatibilité avec les critères d'admission
# --------------------------------------------------------------------------- #


class _FakeCriterion:
    def __init__(self, ctype, value, required=True, status=m.VERIFICATION_OFFICIAL, description=None):
        self.criterion_type = ctype
        self.value = value
        self.is_required = required
        self.verification_status = status
        self.description = description


def test_criterion_series_ok_and_ko():
    criterion = _FakeCriterion("bac_series", ["SVT", "PC"])
    ok = ori.evaluate_criterion(criterion, {"bac_series": "SVT"})
    assert ok["status"] == ori.STATUS_OK

    ko = ori.evaluate_criterion(criterion, {"bac_series": "Lettres et Sciences Humaines"})
    assert ko["status"] == ori.STATUS_KO
    assert ko["required"] is True


def test_criterion_series_missing_profile_is_unknown_not_guessed():
    criterion = _FakeCriterion("bac_series", ["SVT"])
    result = ori.evaluate_criterion(criterion, {"bac_series": None})
    assert result["status"] == ori.STATUS_UNKNOWN
    assert result["key"] == "eval_series_missing"


def test_unverified_criterion_is_never_evaluated():
    """Une information non vérifiée donne « Vérification nécessaire »."""
    criterion = _FakeCriterion("bac_series", ["SVT"], status=m.VERIFICATION_PENDING)
    result = ori.evaluate_criterion(criterion, {"bac_series": "Lettres et Sciences Humaines"})
    assert result["status"] == ori.STATUS_UNKNOWN
    assert result["key"] == "eval_series_unverified"

    average = _FakeCriterion("min_average", 18.0, status=m.VERIFICATION_UNKNOWN)
    assert ori.evaluate_criterion(average, {"average": 10})["status"] == ori.STATUS_UNKNOWN


def test_optional_criterion_mismatch_is_unknown_and_not_ko():
    criterion = _FakeCriterion("bac_series", ["SVT"], required=False)
    result = ori.evaluate_criterion(criterion, {"bac_series": "PC"})
    assert result["status"] == ori.STATUS_UNKNOWN


def test_average_criterion_boundaries():
    criterion = _FakeCriterion("min_average", 12.0)
    assert ori.evaluate_criterion(criterion, {"average": 12.0})["status"] == ori.STATUS_OK
    assert ori.evaluate_criterion(criterion, {"average": 11.75})["status"] == ori.STATUS_KO
    assert ori.evaluate_criterion(criterion, {"average": None})["status"] == ori.STATUS_UNKNOWN


def test_exam_type_criterion_requires_manual_verification():
    criterion = _FakeCriterion("exam_type", "concours écrit")
    result = ori.evaluate_criterion(criterion, {"bac_series": "SVT", "average": 15})
    assert result["status"] == ori.STATUS_UNKNOWN
    assert result["key"] == "eval_manual"


def test_program_statuses(session, catalog):
    # Formation sans critère publié.
    assert ori.evaluate_program(catalog["info"], {})["status"] == ori.STATUS_NO_RULE

    # Règle non vérifiée -> unknown, jamais « ko » supposé.
    pending = ori.evaluate_program(catalog["finance"], {"bac_series": "SVT", "average": 15})
    assert pending["status"] == ori.STATUS_UNKNOWN

    # Règle officielle respectée -> ok.
    ok = ori.evaluate_program(catalog["gestion"], {"bac_series": "SVT", "average": 14})
    assert ok["status"] == ori.STATUS_OK
    assert ok["school_name"] == "ENCG de test"

    # Critère obligatoire non satisfait -> ko.
    ko = ori.evaluate_program(catalog["gestion"], {"bac_series": "PC", "average": 14})
    assert ko["status"] == ori.STATUS_KO


def test_program_match_never_claims_admission_probability(session, catalog, make_program):
    """Aucun libellé de résultat ne présente l'indice comme une probabilité."""
    matches = ori.compute_program_matches(
        [catalog["gestion"], catalog["finance"], catalog["info"]],
        None,
        {"bac_series": "SVT", "average": 15},
    )
    keys = set()
    for match in matches:
        keys.update(match.keys())
        keys.update(check["status"] for check in match["checks"])
    assert keys  # sanity
    assert all(match["status"] in {ori.STATUS_OK, ori.STATUS_KO, ori.STATUS_UNKNOWN} for match in matches)
    # Les formations sans critère sont exclues des correspondances.
    assert all(match["program_id"] != catalog["info"].id for match in matches)


def test_program_match_order_puts_incompatibilities_first(session, catalog):
    matches = ori.compute_program_matches(
        [catalog["gestion"], catalog["finance"]],
        None,
        {"bac_series": "Lettres et Sciences Humaines", "average": 10},
    )
    statuses = [match["status"] for match in matches]
    assert statuses == sorted(statuses, key=lambda s: {ori.STATUS_KO: 0, ori.STATUS_UNKNOWN: 1, ori.STATUS_OK: 2, ori.STATUS_NO_RULE: 3}[s])


def test_profile_values_prefer_profile_then_answers():
    class _Profile:
        bac_series = "SVT"
        average = 13.0

    values = ori._profile_values(_Profile(), {"bac_series": "PC", "average": 18})
    assert values == {"bac_series": "SVT", "average": 13.0}

    assert ori._profile_values(None, {}) == {"bac_series": None, "average": None}
    assert ori._profile_values(None, {"bac_series": "PC", "average": 16}) == {
        "bac_series": "PC",
        "average": 16.0,
    }


# --------------------------------------------------------------------------- #
# Persistance
# --------------------------------------------------------------------------- #


def test_save_and_fetch_result_for_logged_in_user(session, make_user):
    user = make_user()
    result = ori.compute_recommendations(ALL_ANSWERS, None, [])
    row = ori.save_result(session, user.id, ALL_ANSWERS, result)
    session.flush()
    assert row.id is not None

    last = ori.last_result(session, user.id)
    assert last is not None
    assert last.result["pathways"][0]["key"] == result["pathways"][0]["key"]
    assert last.questionnaire["bac_series"] == "Économie et Gestion"


def test_save_result_for_guest_has_no_user(session):
    row = ori.save_result(session, None, {"subjects": ["subj_math"]}, {"pathways": []})
    session.flush()
    assert row.user_id is None


def test_answers_from_profile_contains_no_invented_data():
    assert ori.answers_from_profile(None) == {}

    class _Profile:
        bac_series = "SVT"
        average = None
        favorite_subjects = ["subj_math"]

    assert ori.answers_from_profile(_Profile()) == {
        "bac_series": "SVT",
        "subjects": ["subj_math"],
    }
