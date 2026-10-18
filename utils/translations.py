"""Internationalisation — NextStep Maroc.

* Langues : ``fr`` (défaut), ``ar``, ``en``.
* Traductions centralisées ici : **une clé unique par texte d'interface**.
* Les contenus de données (conditions d'admission, dates, frais) ne sont pas
  traduits automatiquement : leur langue d'origine est indiquée dans l'UI.

Usage :
    from utils.translations import tr
    tr("btn_save", lang="ar")
"""

from __future__ import annotations

from typing import Optional

LANGUAGES: dict[str, str] = {"fr": "Français", "ar": "العربية", "en": "English"}
DEFAULT_LANGUAGE = "fr"
VALID_LANGUAGES = tuple(LANGUAGES)


def tr(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Retourne la traduction de ``key`` dans ``lang``.

    Repli : français, puis la clé elle-même (permet de repérer un texte
    manquant sans faire planter l'interface).
    """
    entry = T.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def series_label_key(value: str | None) -> str:
    """Clé de traduction pour une série du baccalauréat (libellé brut sinon)."""
    return SERIES_KEYS.get((value or "").strip(), "")


# Série brute -> clé de traduction (les séries inconnues restent affichées telles quelles).
SERIES_KEYS: dict[str, str] = {
    "SVT": "series_svt",
    "PC": "series_pc",
    "Mathématiques": "series_math",
    "Économie et Gestion": "series_eco_gest",
    "Sciences Économiques": "series_sci_eco",
    "Lettres et Sciences Humaines": "series_letters",
    "Langues Étrangères": "series_langs",
    "Techniques Mathématiques": "series_tm",
    "Techniques Physiques": "series_tp",
}

T: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- Marque
    "app_name": {"fr": "NextStep Maroc", "ar": "NextStep Maroc", "en": "NextStep Maroc"},
    "app_tagline": {
        "fr": "Oriente-toi après le bac, prépare les concours",
        "ar": "وجّه مسارك بعد البكالوريا و استعد للمباريات",
        "en": "Choose your path after the bac, prepare for entrance exams",
    },
    "nav_home": {"fr": "Accueil", "ar": "الرئيسية", "en": "Home"},
    "nav_dashboard": {"fr": "Tableau de bord", "ar": "لوحة التحكم", "en": "Dashboard"},
    "nav_orientation": {"fr": "Test d'orientation", "ar": "اختبار التوجيه", "en": "Orientation test"},
    "nav_schools": {"fr": "Écoles & formations", "ar": "المدارس والتكوينات", "en": "Schools & programs"},
    "nav_prep": {"fr": "Préparation aux concours", "ar": "تحضير للمباريات", "en": "Exam preparation"},
    "nav_favorites": {"fr": "Mes favoris", "ar": "المفضلة لدي", "en": "My favorites"},
    "nav_profile": {"fr": "Mon profil", "ar": "ملفي الشخصي", "en": "My profile"},
    "nav_admin": {"fr": "Administration", "ar": "الإدارة", "en": "Administration"},
    "lang_label": {"fr": "Langue", "ar": "اللغة", "en": "Language"},

    # ------------------------------------------------------------- Boutons
    "btn_start": {"fr": "Commencer mon orientation", "ar": "ابدأ توجيهي", "en": "Start my orientation"},
    "btn_catalog": {"fr": "Voir le catalogue des écoles", "ar": "تصفح كتالوج المدارس", "en": "Browse the school catalog"},
    "btn_login": {"fr": "Se connecter", "ar": "تسجيل الدخول", "en": "Log in"},
    "btn_logout": {"fr": "Se déconnecter", "ar": "تسجيل الخروج", "en": "Log out"},
    "btn_register": {"fr": "Créer un compte", "ar": "إنشاء حساب", "en": "Create an account"},
    "btn_save": {"fr": "Enregistrer", "ar": "حفظ", "en": "Save"},
    "btn_cancel": {"fr": "Annuler", "ar": "إلغاء", "en": "Cancel"},
    "btn_back": {"fr": "Retour", "ar": "رجوع", "en": "Back"},
    "btn_next": {"fr": "Suivant", "ar": "التالي", "en": "Next"},
    "btn_submit": {"fr": "Valider", "ar": "تأكيد", "en": "Submit"},
    "btn_search": {"fr": "Rechercher", "ar": "بحث", "en": "Search"},
    "btn_reset": {"fr": "Réinitialiser les filtres", "ar": "إعادة ضبط المرشحات", "en": "Reset filters"},
    "btn_retry": {"fr": "Réessayer", "ar": "إعادة المحاولة", "en": "Retry"},
    "btn_details": {"fr": "Voir la fiche", "ar": "عرض الملف", "en": "View details"},
    "btn_add_fav": {"fr": "Ajouter aux favoris", "ar": "إضافة إلى المفضلة", "en": "Add to favorites"},
    "btn_remove_fav": {"fr": "Retirer des favoris", "ar": "إزالة من المفضلة", "en": "Remove from favorites"},
    "btn_delete_my_data": {"fr": "Supprimer mes données personnelles", "ar": "حذف بياناتي الشخصية", "en": "Delete my personal data"},
    "btn_report": {"fr": "Signaler ce contenu", "ar": "الإبلاغ عن هذا المحتوى", "en": "Report this content"},
    "btn_view_results": {"fr": "Voir mes résultats", "ar": "عرض نتائجي", "en": "See my results"},

    # -------------------------------------------------------------- Commun
    "common_unknown": {"fr": "Information à vérifier", "ar": "معلومات بانتظار التحقق", "en": "Information to be verified"},
    "common_optional": {"fr": "facultatif", "ar": "اختياري", "en": "optional"},
    "common_none": {"fr": "Aucun", "ar": "لا يوجد", "en": "None"},
    "common_yes": {"fr": "Oui", "ar": "نعم", "en": "Yes"},
    "common_no": {"fr": "Non", "ar": "لا", "en": "No"},
    "common_demo_notice": {
        "fr": "Contenu de démonstration — ne constitue pas un catalogue officiel.",
        "ar": "محتوى تجريبي — ليس كتالوجاً رسمياً.",
        "en": "Demo content — not an official catalog.",
    },
    "common_loading": {"fr": "Chargement…", "ar": "جارٍ التحميل…", "en": "Loading…"},
    "common_source": {"fr": "Source", "ar": "المصدر", "en": "Source"},
    "common_language": {"fr": "Langue du contenu", "ar": "لغة المحتوى", "en": "Content language"},
    "common_status": {"fr": "Statut de vérification", "ar": "حالة التحقق", "en": "Verification status"},
    "common_last_verified": {"fr": "Dernière vérification", "ar": "آخر تحقق", "en": "Last verified"},
    "common_official_url": {"fr": "Site officiel", "ar": "الموقع الرسمي", "en": "Official website"},

    "status_official": {"fr": "Officiel vérifié", "ar": "رسمي مُتحقق منه", "en": "Officially verified"},
    "status_pending": {"fr": "En attente de vérification", "ar": "في انتظار التحقق", "en": "Pending verification"},
    "status_unknown": {"fr": "Inconnu / indisponible", "ar": "غير معروف / غير متوفر", "en": "Unknown / unavailable"},
    "status_community": {"fr": "Contenu communautaire", "ar": "محتوى مجتمعي", "en": "Community content"},
    "status_demo": {"fr": "Démonstration", "ar": "تجريبي", "en": "Demo data"},

    "role_candidat": {"fr": "Candidat", "ar": "مرشح", "en": "Candidate"},
    "role_moderateur": {"fr": "Modérateur", "ar": "مشرف", "en": "Moderator"},
    "role_administrateur": {"fr": "Administrateur", "ar": "مدير", "en": "Administrator"},

    "msg_saved": {"fr": "Modifications enregistrées.", "ar": "تم حفظ التعديلات.", "en": "Changes saved."},
    "msg_deleted": {"fr": "Élément supprimé.", "ar": "تم الحذف.", "en": "Item deleted."},
    "msg_fav_added": {"fr": "Ajouté aux favoris.", "ar": "تمت الإضافة إلى المفضلة.", "en": "Added to favorites."},
    "msg_fav_removed": {"fr": "Retiré des favoris.", "ar": "تمت الإزالة من المفضلة.", "en": "Removed from favorites."},
    "msg_login_ok": {"fr": "Connexion réussie.", "ar": "تم تسجيل الدخول بنجاح.", "en": "Logged in successfully."},
    "msg_register_ok": {"fr": "Compte créé. Vous êtes connecté.", "ar": "تم إنشاء الحساب وأنت الآن متصل.", "en": "Account created. You are signed in."},
    "msg_logout_ok": {"fr": "Vous êtes déconnecté.", "ar": "تم تسجيل الخروج.", "en": "You are logged out."},

    "error_generic": {"fr": "Une erreur est survenue. Réessayez.", "ar": "حدث خطأ. حاول مرة أخرى.", "en": "Something went wrong. Please retry."},
    "error_permission": {"fr": "Vous n'avez pas les droits nécessaires.", "ar": "لديك الصلاحيات الكافية.", "en": "You do not have the required permissions."},
    "error_not_found": {"fr": "Ressource introuvable.", "ar": "الموارد غير موجودة.", "en": "Resource not found."},
    "error_validation": {"fr": "Formulaire invalide : vérifiez les champs signalés.", "ar": "استمارة غير صالحة: راجع الحقول.", "en": "Invalid form: check the highlighted fields."},
    "error_credentials": {"fr": "E-mail ou mot de passe incorrect.", "ar": "البريد الإلكتروني أو كلمة السر غير صحيحة.", "en": "Incorrect email or password."},
    "error_account_disabled": {"fr": "Ce compte est désactivé.", "ar": "هذا الحساب معطل.", "en": "This account is disabled."},
    "error_rate_limited": {"fr": "Trop de tentatives. Réessayez dans {seconds} s.", "ar": "محاولات كثيرة. أعد المحاولة بعد {seconds} ثانية.", "en": "Too many attempts. Retry in {seconds}s."},
    "error_email_exists": {"fr": "Un compte existe déjà avec cet e-mail.", "ar": "يوجد حساب بهذا البريد الإلكتروني.", "en": "An account already exists with this email."},
    "error_required": {"fr": "Ce champ est obligatoire.", "ar": "هذا الحقل مطلوب.", "en": "This field is required."},

    # ------------------------------------------------------------- Accueil
    "home_kicker": {"fr": "Plateforme gratuite d'orientation", "ar": "منصة مجانية للتوجيه", "en": "Free orientation platform"},
    "home_hero_title": {"fr": "Choisis ta voie après le baccalauréat", "ar": "اختر مسارك بعد البكالوريا", "en": "Choose your path after the baccalaureate"},
    "home_hero_text": {
        "fr": "NextStep Maroc t'aide à découvrir les écoles et formations accessibles après le bac, à comprendre les critères d'admission et à préparer les concours — avec des informations sourcées, datées et vérifiées.",
        "ar": "يساعدك NextStep Maroc على اكتشاف المدارس والتكوينات المتاحة بعد البكالوريا، وفهم معايير القبول والاستعداد للمباريات — بمعلومات موثقة ومؤرخة ومُتحقق منها.",
        "en": "NextStep Maroc helps you discover schools and programs after the bac, understand admission criteria and prepare for entrance exams — with sourced, dated and verified information.",
    },
    "home_features_title": {"fr": "Ce que tu trouves sur NextStep Maroc", "ar": "ما ستجده في NextStep Maroc", "en": "What you get on NextStep Maroc"},
    "home_features_text": {
        "fr": "Six outils gratuits pour décider avec des informations claires plutôt que des rumeurs.",
        "ar": "ستة أدوات مجانية لاتخاذ قرار بناءً على معلومات واضحة بدلاً من الشائعات.",
        "en": "Six free tools to decide on clear information instead of rumors.",
    },
    "feat1_t": {"fr": "Catalogue des écoles", "ar": "كتالوج المدارس", "en": "School catalog"},
    "feat1_d": {"fr": "Recherche par nom, ville, domaine et niveau de diplôme, avec statut de vérification visible.", "ar": "بحث بالاسم والمدينة والمجال ومستوى الشهادة مع إظهار حالة التحقق.", "en": "Search by name, city, field and degree level, with a visible verification status."},
    "feat2_t": {"fr": "Test d'orientation", "ar": "اختبار التوجيه", "en": "Orientation test"},
    "feat2_d": {"fr": "Un questionnaire dont la logique de recommandation est explicite, déterministe et documentée.", "ar": "استمارة توصيات صريحة وحتمية وموثقة.", "en": "A questionnaire with an explicit, deterministic and documented recommendation logic."},
    "feat3_t": {"fr": "Critères d'admission", "ar": "شروط القبول", "en": "Admission criteria"},
    "feat3_d": {"fr": "Chaque critère indique sa source et sa date de vérification — ou « Information à vérifier ».", "ar": "كل معيار يوضح مصدره وتاريخ التحقق — أو «معلومات بانتظار التحقق».", "en": "Each criterion shows its source and verification date — or “Information to be verified”."},
    "feat4_t": {"fr": "Préparation aux concours", "ar": "تحضير للمباريات", "en": "Exam preparation"},
    "feat4_d": {"fr": "Fiches de révision et QCM interactifs avec correction expliquée et suivi de progression.", "ar": "بطاقات مراجعة وأسئلة تفاعلية بتصحيح موضح وتتبع للتقدم.", "en": "Revision sheets and interactive quizzes with explained corrections and progress tracking."},
    "feat5_t": {"fr": "Favoris et échéances", "ar": "المفضلة والمواعيد", "en": "Favorites and deadlines"},
    "feat5_d": {"fr": "Suis tes écoles préférées et les dates confirmées, chacune avec sa source.", "ar": "تابع مدارسك المفضلة والمؤكد منها بحسب مصدرها.", "en": "Track your favorite schools and confirmed dates, each with its source."},
    "feat6_t": {"fr": "Transparence des données", "ar": "شفافية البيانات", "en": "Data transparency"},
    "feat6_d": {"fr": "Aucune date, frais ou condition inventés : ce qui est inconnu reste affiché comme tel.", "ar": "لا تواريخ ولا رسوم ولا شروط مخترعة: ما هو غير معروف يظهر كذا.", "en": "No invented dates, fees or conditions: what is unknown stays displayed as unknown."},
    "home_how_title": {"fr": "Comment fonctionne le parcours", "ar": "كيف يسير المسار", "en": "How the journey works"},
    "home_how_text": {"fr": "Quatre étapes, à ton rythme, gratuitement.", "ar": "أربع خطوات، على وتيرتك، مجاناً.", "en": "Four steps, at your pace, free."},
    "how1_t": {"fr": "Crée ton profil", "ar": "أنشئ ملفك", "en": "Create your profile"},
    "how1_d": {"fr": "Série du bac, ville, moyenne et centres d'intérêt — uniquement les données utiles.", "ar": "شعبة البكالوريا، المدينة، المعدل واهتماماتك — البيانات المفيدة فقط.", "en": "Bac track, city, average and interests — only the useful data."},
    "how2_t": {"fr": "Réponds au test d'orientation", "ar": "أجب عن اختبار التوجيه", "en": "Take the orientation test"},
    "how2_d": {"fr": "Matières préférées, compétences, intérêts et préférences de formation.", "ar": "المواد المفضلة، المهارات، الاهتمامات وتفضيلات التكوين.", "en": "Favorite subjects, skills, interests and training preferences."},
    "how3_t": {"fr": "Explore les parcours et écoles", "ar": "استكشف المسارات والمدارس", "en": "Explore paths and schools"},
    "how3_d": {"fr": "Compare les formations, leurs critères connus et leur niveau de vérification.", "ar": "قارن التكوينات ومعارفها ومعاييرها ومستوى التحقق.", "en": "Compare programs, their known criteria and their verification level."},
    "how4_t": {"fr": "Prépare les concours", "ar": "استعد للمباريات", "en": "Prepare for the exams"},
    "how4_d": {"fr": "Fiches et QCM avec score, correction expliquée et historique.", "ar": "بطاقات وأسئلة مع نقاط وتصحيح وتاريخ المحاولات.", "en": "Sheets and quizzes with scores, explained corrections and history."},
    "home_stats_title": {"fr": "La plateforme en chiffres", "ar": "المنصة بالأرقام", "en": "The platform in numbers"},
    "home_stats_note": {"fr": "Statistiques calculées en direct depuis la base de données locale.", "ar": "إحصائيات محسوبة مباشرة من قاعدة البيانات المحلية.", "en": "Statistics computed live from the local database."},
    "stat_schools": {"fr": "Écoles référencées", "ar": "مدارس مسجلة", "en": "Schools listed"},
    "stat_programs": {"fr": "Formations", "ar": "تكوينات", "en": "Programs"},
    "stat_quizzes": {"fr": "QCM disponibles", "ar": "اختبارات متاحة", "en": "Available quizzes"},
    "stat_questions": {"fr": "Questions", "ar": "أسئلة", "en": "Questions"},
    "stat_users": {"fr": "Comptes créés", "ar": "حسابات منشأة", "en": "Accounts created"},
    "home_footer_title": {"fr": "Prêt à passer à l'étape suivante ?", "ar": "مستعد للخطوة التالية؟", "en": "Ready for the next step?"},

    # -------------------------------------------------------- Auth / profil
    "auth_login_title": {"fr": "Connexion", "ar": "تسجيل الدخول", "en": "Log in"},
    "auth_register_title": {"fr": "Inscription", "ar": "التسجيل", "en": "Sign up"},
    "auth_have_account": {"fr": "Tu as déjà un compte ?", "ar": "لديك حساب بالفعل؟", "en": "Already have an account?"},
    "auth_no_account": {"fr": "Pas encore de compte ?", "ar": "ليس لديك حساب؟", "en": "No account yet?"},
    "label_email": {"fr": "Adresse e-mail", "ar": "البريد الإلكتروني", "en": "Email address"},
    "label_password": {"fr": "Mot de passe", "ar": "كلمة السر", "en": "Password"},
    "label_password_hint": {"fr": "8 caractères minimum.", "ar": "8 أحرف على الأقل.", "en": "At least 8 characters."},
    "label_language": {"fr": "Langue de l'interface", "ar": "لغة الواجهة", "en": "Interface language"},
    "label_role": {"fr": "Rôle", "ar": "الدور", "en": "Role"},
    "auth_privacy_note": {
        "fr": "Nous collectons uniquement les données nécessaires à l'orientation. Aucun mot de passe n'est stocké en clair.",
        "ar": "نجمع فقط البيانات الضرورية للتوجيه. لا تُخزن أي كلمة سر كنص صريح.",
        "en": "We only collect data needed for orientation. No password is stored in plain text.",
    },

    "profile_title": {"fr": "Mon profil candidat", "ar": "ملفي كمرشح", "en": "My candidate profile"},
    "profile_intro": {
        "fr": "Ces informations servent à personnaliser les recommandations. Tout est facultatif sauf l'e-mail.",
        "ar": "تُستعمل هذه المعلومات لتخصيص التوصيات. كلها اختيارية ما عدا البريد الإلكتروني.",
        "en": "This information personalizes recommendations. Everything is optional except email.",
    },
    "profile_not_created": {"fr": "Ton profil n'est pas encore complété.", "ar": "لم يُكمل ملفك بعد.", "en": "Your profile is not complete yet."},
    "label_display_name": {"fr": "Prénom ou nom affiché", "ar": "الاسم المعروض", "en": "Display name"},
    "label_bac_series": {"fr": "Série du baccalauréat", "ar": "شعبة البكالوريا", "en": "Baccalaureate track"},
    "label_bac_year": {"fr": "Année du baccalauréat", "ar": "سنة البكالوريا", "en": "Baccalaureate year"},
    "label_city": {"fr": "Ville", "ar": "المدينة", "en": "City"},
    "label_average": {"fr": "Moyenne générale (/20)", "ar": "المعدل العام (/20)", "en": "Overall average (/20)"},
    "label_favorite_subjects": {"fr": "Matières préférées", "ar": "المواد المفضلة", "en": "Favorite subjects"},
    "label_interests": {"fr": "Centres d'intérêt", "ar": "اهتمامات", "en": "Interests"},
    "label_desired_fields": {"fr": "Domaines professionnels souhaités", "ar": "المجالات المهنية المرغوبة", "en": "Desired professional fields"},
    "label_geo_pref": {"fr": "Préférence géographique", "ar": "التفضيل الجغرافي", "en": "Geographic preference"},
    "label_budget_pref": {"fr": "Préférence budgétaire", "ar": "التفضيل المالي", "en": "Budget preference"},
    "profile_delete_confirm": {
        "fr": "Confirmer la suppression ? Cette action est irréversible : profil, favoris, tentatives et résultats d'orientation seront supprimés.",
        "ar": "تأكيد الحذف؟ لا رجعة فيها: الملف والمفضلة والمحاولات ونتائج التوجيه ستُحذف.",
        "en": "Confirm deletion? This is irreversible: profile, favorites, attempts and orientation results will be deleted.",
    },
    "profile_delete_done": {"fr": "Vos données personnelles ont été supprimées.", "ar": "تم حذف بياناتك الشخصية.", "en": "Your personal data has been deleted."},
    "profile_privacy_note": {
        "fr": "Données traitées localement dans le cadre du MVP. Une politique de confidentialité (loi 09-08 / CNDP) sera publiée avant tout lancement public.",
        "ar": "تُعالج البيانات محلياً في إطار النموذج الأولي. سيُنشر إشعار بالخصوصية (قانون 09-08 / الهيئة الوطنية لحماية المعاملات الشخصية) قبل الإطلاق العام.",
        "en": "Data processed locally for the MVP. A privacy notice (law 09-08 / CNDP) will be published before any public launch.",
    },

    # ---------------------------------------------------------- Séries bac
    "series_svt": {"fr": "SVT", "ar": "علوم الحياة والأرض", "en": "SVT"},
    "series_pc": {"fr": "Physique-Chimie", "ar": "فيزياء وكيمياء", "en": "Physics-Chemistry"},
    "series_math": {"fr": "Mathématiques", "ar": "رياضيات", "en": "Mathematics"},
    "series_eco_gest": {"fr": "Économie et Gestion", "ar": "اقتصاد وتدبير", "en": "Economics and Management"},
    "series_sci_eco": {"fr": "Sciences Économiques", "ar": "علوم اقتصادية", "en": "Economic Sciences"},
    "series_letters": {"fr": "Lettres et Sciences Humaines", "ar": "آداب وعلوم إنسانية", "en": "Literature and Humanities"},
    "series_langs": {"fr": "Langues Étrangères", "ar": "لغات أجنبية", "en": "Foreign Languages"},
    "series_tm": {"fr": "Techniques Mathématiques", "ar": "تقنيات رياضية", "en": "Technical Mathematics"},
    "series_tp": {"fr": "Techniques Physiques", "ar": "تقنيات فيزيائية", "en": "Technical Physics"},

    # ---------------------------------------------------------- Orientation
    "ori_title": {"fr": "Test d'orientation", "ar": "اختبار التوجيه", "en": "Orientation test"},
    "ori_intro": {
        "fr": "{count} questions pour faire ressortir les parcours qui te correspondent. Aucune réponse n'est bonne ou mauvaise : le résultat est une piste de réflexion, jamais une promesse d'admission.",
        "ar": "{count} أسئلة لإبراز المسارات المناسبة لك. لا توجد إجابة صحيحة أو خاطئة: النتيجة محاولة تفكير وليست وعداً بالقبول.",
        "en": "{count} questions to surface the paths that fit you. There is no right or wrong answer: results are a lead for reflection, never an admission promise.",
    },
    "ori_progress": {
        "fr": "Étape {current} / {total}",
        "ar": "الخطوة {current} / {total}",
        "en": "Step {current} / {total}",
    },
    "ori_select_all": {"fr": "Sélectionne toutes les réponses qui s'appliquent.", "ar": "اختر كل الإجابات المناسبة.", "en": "Select all answers that apply."},
    "ori_select_one": {"fr": "Choisis une réponse.", "ar": "اختر إجابة واحدة.", "en": "Choose one answer."},
    "ori_results_title": {"fr": "Tes pistes de parcours", "ar": "مساراتك المقترحة", "en": "Your suggested paths"},
    "ori_score_label": {"fr": "Indice d'intérêt", "ar": "مؤشر الاهتمام", "en": "Interest index"},
    "ori_score_disclaimer": {
        "fr": "L'indice d'intérêt mesure la correspondance entre tes réponses et la définition du parcours (0 à 100). Ce n'est ni une probabilité d'admission ni un classement.",
        "ar": "مؤشر الاهتمام يقيس مدى تطابق إجاباتك مع تعريف المسار (من 0 إلى 100). ليس احتمال قبول ولا ترتيباً.",
        "en": "The interest index measures how your answers match the path definition (0 to 100). It is neither an admission probability nor a ranking.",
    },
    "ori_reasons": {"fr": "Pourquoi ce parcours", "ar": "لماذا هذا المسار", "en": "Why this path"},
    "ori_matches": {"fr": "Formations dont les critères connus correspondent à ton profil", "ar": "تكوينات تطابق معاييرها المعروفة ملفك", "en": "Programs whose known criteria match your profile"},
    "ori_match_ok": {"fr": "Critères connus satisfaits", "ar": "المعايير المعروفة مُستوفاة", "en": "Known criteria met"},
    "ori_match_ko": {"fr": "Critère obligatoire non satisfait", "ar": "معيار إلزامي غير مُستوفى", "en": "Required criterion not met"},
    "ori_match_unknown": {"fr": "Vérification nécessaire", "ar": "التحقق ضروري", "en": "Verification required"},
    "ori_match_no_rule": {"fr": "Aucun critère publié pour cette formation", "ar": "لا معيار منشور لهذه التكوينة", "en": "No published criteria for this program"},
    "ori_not_probability": {
        "fr": "Ces indications portent uniquement sur les critères publiés et vérifiés. Elles ne préjugent pas de l'issue d'une candidature.",
        "ar": "تشير هذه الإرشادات إلى المعايير المنشورة والموثقة فقط، ولا تحدد نتيجة أي ترشح.",
        "en": "These indications only concern published and verified criteria. They do not prejudge any application outcome.",
    },
    "ori_save_ok": {"fr": "Résultats enregistrés dans ton profil.", "ar": "تم حفظ النتائج في ملفك.", "en": "Results saved to your profile."},
    "ori_login_required": {
        "fr": "Connecte-toi pour enregistrer tes résultats. Tu peux aussi faire le test sans compte (résultats non conservés).",
        "ar": "سجّل الدخول لحفظ نتائجك. يمكنك أيضاً التجربة دون حساب (لن تُحفظ النتائج).",
        "en": "Log in to save your results. You can also take the test without an account (results are not kept).",
    },
    "ori_take_test": {"fr": "Démarrer le test", "ar": "ابدأ الاختبار", "en": "Start the test"},
    "ori_retake": {"fr": "Refaire le test", "ar": "إعادة الاختبار", "en": "Retake the test"},
    "ori_method_title": {"fr": "Comment les pistes sont calculées", "ar": "كيفية احتساب المسارات", "en": "How paths are computed"},
    "ori_method_text": {
        "fr": "Chaque réponse active des signaux pondérés propres à un parcours. L'indice final est la somme des signaux actifs rapportée au maximum possible du parcours. L'algorithme est déterministe : mêmes réponses, mêmes résultats. Aucun modèle d'intelligence artificielle n'est utilisé.",
        "ar": "كل إجابة تفعّل إشارات مرجّحة خاصة بكل مسار. المؤشر النهائي هو مجموع الإشارات مقارنة بالحد الأقصى الممكن. الخوارزمية حتمية: نفس الإجابات تعطي نفس النتائج. لا يستعمل أي ذكاء اصطناعي.",
        "en": "Each answer activates weighted signals specific to a path. The final index is the sum of active signals over the path's maximum. The algorithm is deterministic: same answers, same results. No AI model is used.",
    },

    "ori_reason_line": {"fr": "{question} : {option} (+{weight})", "ar": "{question} : {option} (+{weight})", "en": "{question}: {option} (+{weight})"},
    "ori_top_signals": {"fr": "Signaux les plus forts", "ar": "أقوى الإشارات", "en": "Strongest signals"},
    "ori_note_no_pathway": {
        "fr": "Aucun parcours du modèle ne ressort nettement de ces réponses. Explore le catalogue et refais le test en précisant tes matières et intérêts.",
        "ar": "لا يبرز أي مسار بوضوح من هذه الإجابات. تصفّح الكتالوج وأعد الاختبار بتحديد موادك واهتماماتك.",
        "en": "No path clearly stands out from these answers. Browse the catalog and retake the test with your subjects and interests.",
    },
    "ori_note_geo": {"fr": "Préférence géographique prise en compte : {preference}.", "ar": "تم أخذ التفضيل الجغرافي بعين الاعتبار: {preference}.", "en": "Geographic preference taken into account: {preference}."},
    "ori_note_formation": {"fr": "Type de formation souhaité : {preference}.", "ar": "نوع التكوين المرغوب: {preference}.", "en": "Desired training type: {preference}."},

    "eval_series_ok": {"fr": "Série « {series} » conforme au critère publié.", "ar": "الشعبة « {series} » مطابقة للمعيار المنشور.", "en": "Track “{series}” meets the published criterion."},
    "eval_series_ko": {"fr": "Série « {series} » non listée parmi les séries acceptées ({accepted}).", "ar": "الشعبة « {series} » غير مدرجة ضمن الشعب المقبولة ({accepted}).", "en": "Track “{series}” is not among the accepted tracks ({accepted})."},
    "eval_series_missing": {"fr": "Série du bac non renseignée dans le profil : vérification nécessaire.", "ar": "شعبة البكالوريا غير مذكورة في الملف: التحقق ضروري.", "en": "Bac track missing from the profile: verification required."},
    "eval_series_unverified": {"fr": "Séries admissibles non vérifiées : Information à vérifier.", "ar": "الشعب المقبولة غير موثقة: معلومات بانتظار التحقق.", "en": "Admitted tracks unverified: information to be verified."},
    "eval_avg_ok": {"fr": "Moyenne {average}/20 ≥ moyenne minimale {min_average}/20.", "ar": "المعدل {average}/20 ≥ الحد الأدنى {min_average}/20.", "en": "Average {average}/20 ≥ minimum {min_average}/20."},
    "eval_avg_ko": {"fr": "Moyenne {average}/20 < moyenne minimale {min_average}/20 : critère obligatoire non satisfait.", "ar": "المعدل {average}/20 < الحد الأدنى {min_average}/20: معيار إلزامي غير مستوفى.", "en": "Average {average}/20 < minimum {min_average}/20: required criterion not met."},
    "eval_avg_missing": {"fr": "Moyenne non renseignée : vérification nécessaire (minimum attendu {min_average}/20).", "ar": "المعدل غير مذكور: التحقق ضروري (الحد الأدنى {min_average}/20).", "en": "Average missing: verification required (expected minimum {min_average}/20)."},
    "eval_unverified": {"fr": "Ce critère n'est pas vérifié : Information à vérifier.", "ar": "هذا المعيار غير موثق: معلومات بانتظار التحقق.", "en": "This criterion is not verified: information to be verified."},
    "eval_manual": {"fr": "Critère non vérifiable automatiquement (type de concours, dossier…) : Information à vérifier.", "ar": "معيار غير قابل للتحقق الآلي (نوع المباراة، الملف…) : معلومات بانتظار التحقق.", "en": "Criterion not automatically verifiable (exam type, file…): information to be verified."},

    "q_subjects": {"fr": "Quelles matières aimes-tu le plus ?", "ar": "ما هي المواد التي تحبها أكثر؟", "en": "Which subjects do you like most?"},
    "q_skills": {"fr": "Quelles compétences te décrivent le mieux ?", "ar": "ما المهارات التي تصفك؟", "en": "Which skills describe you best?"},
    "q_interests": {"fr": "Quels domaines professionnels t'attirent ?", "ar": "ما المجالات المهنية تجذبك؟", "en": "Which professional fields attract you?"},
    "q_domains": {"fr": "Quels parcours veux-tu explorer ?", "ar": "ما المسارات تريد استكشافها؟", "en": "Which paths do you want to explore?"},
    "q_formation_pref": {"fr": "Quel type de formation préfères-tu ?", "ar": "ما نوع التكوين تفضله؟", "en": "What type of training do you prefer?"},
    "q_geo_pref": {"fr": "Où veux-tu étudier ?", "ar": "أين تريد الدراسة؟", "en": "Where do you want to study?"},
    "q_series": {"fr": "Quelle est ta série du baccalauréat ?", "ar": "ما شعبتك في البكالوريا؟", "en": "What is your bac track?"},
    "q_average": {"fr": "Quelle est ta moyenne générale approximative ? (facultatif)", "ar": "ما معدلك العام التقريبي؟ (اختياري)", "en": "What is your approximate overall average? (optional)"},

    "subj_math": {"fr": "Mathématiques", "ar": "رياضيات", "en": "Mathematics"},
    "subj_physics": {"fr": "Physique", "ar": "فيزياء", "en": "Physics"},
    "subj_svt": {"fr": "Sciences de la vie et de la terre", "ar": "علوم الحياة والأرض", "en": "Life and earth sciences"},
    "subj_economics": {"fr": "Économie et gestion", "ar": "اقتصاد وتدبير", "en": "Economics and management"},
    "subj_accounting": {"fr": "Comptabilité et finance", "ar": "محاسبة ومالية", "en": "Accounting and finance"},
    "subj_languages": {"fr": "Langues étrangères", "ar": "لغات أجنبية", "en": "Foreign languages"},
    "subj_literature": {"fr": "Lettres et philosophie", "ar": "آداب وفلسفة", "en": "Literature and philosophy"},
    "subj_it": {"fr": "Informatique", "ar": "إعلام آلي", "en": "Computer science"},
    "subj_law": {"fr": "Droit", "ar": "قانون", "en": "Law"},
    "subj_history": {"fr": "Histoire et géographie", "ar": "تاريخ وجغرافيا", "en": "History and geography"},

    "skill_analysis": {"fr": "Analyser des données", "ar": "تحليل البيانات", "en": "Analyzing data"},
    "skill_calc": {"fr": "Calculer vite et avec rigueur", "ar": "الحساب بسرعة ودقة", "en": "Calculating fast and accurately"},
    "skill_speak": {"fr": "Prendre la parole en public", "ar": "التحدث أمام الجمهور", "en": "Public speaking"},
    "skill_write": {"fr": "Rédiger des textes clairs", "ar": "كتابة نصوص واضحة", "en": "Writing clear texts"},
    "skill_team": {"fr": "Travailler en équipe", "ar": "العمل الجماعي", "en": "Working in a team"},
    "skill_orga": {"fr": "Organiser et planifier", "ar": "التنظيم والتخطيط", "en": "Organizing and planning"},
    "skill_creativity": {"fr": "Imaginer des idées nouvelles", "ar": "ابتكار أفكار جديدة", "en": "Coming up with new ideas"},
    "skill_persuade": {"fr": "Convaincre et vendre", "ar": "الإقناع والبيع", "en": "Persuading and selling"},
    "skill_rigor": {"fr": "Veiller au détail et à la conformité", "ar": "الاهتمام بالتفاصيل والامتثال", "en": "Attention to detail and compliance"},
    "skill_digital": {"fr": "Utiliser les outils numériques", "ar": "استعمال الأدوات الرقمية", "en": "Using digital tools"},

    "int_manager": {"fr": "Diriger une équipe ou une entreprise", "ar": "قيادة فريق أو مؤسسة", "en": "Leading a team or a company"},
    "int_finance": {"fr": "Gérer l'argent et les investissements", "ar": "تدبير المال والاستثمارات", "en": "Managing money and investments"},
    "int_marketing": {"fr": "Promouvoir des produits et marques", "ar": "الترويج للمنتجات والعلامات", "en": "Promoting products and brands"},
    "int_audit": {"fr": "Contrôler et vérifier les comptes", "ar": "مراقبة وتدقيق الحسابات", "en": "Auditing and checking accounts"},
    "int_startup": {"fr": "Créer ma propre entreprise", "ar": "إنشاء مشروعي الخاص", "en": "Starting my own business"},
    "int_trade": {"fr": "Échanger à l'international", "ar": "التبادل الدولي", "en": "Trading internationally"},
    "int_data": {"fr": "Travailler avec les données et la technologie", "ar": "العمل مع البيانات والتكنولوجيا", "en": "Working with data and technology"},
    "int_teach": {"fr": "Transmettre et former", "ar": "التعليم والتكوين", "en": "Teaching and training"},
    "int_law": {"fr": "Rédiger et conseiller juridiquement", "ar": "التحرير والاستشارة القانونية", "en": "Drafting and legal advising"},
    "int_events": {"fr": "Organiser des événements et communiquer", "ar": "تنظيم الفعاليات والتواصل", "en": "Organizing events and communicating"},

    "pw_commerce": {"fr": "Commerce et gestion", "ar": "التجارة والتدبير", "en": "Business and management"},
    "pw_finance": {"fr": "Finance et comptabilité", "ar": "المالية والمحاسبة", "en": "Finance and accounting"},
    "pw_marketing": {"fr": "Marketing", "ar": "التسويق", "en": "Marketing"},
    "pw_audit": {"fr": "Audit et contrôle de gestion", "ar": "التدقيق ومراقبة التدبير", "en": "Audit and management control"},
    "pw_economie": {"fr": "Économie", "ar": "الاقتصاد", "en": "Economics"},
    "pw_entrepreneuriat": {"fr": "Entrepreneuriat", "ar": "ريادة الأعمال", "en": "Entrepreneurship"},
    "pw_commerce_intl": {"fr": "Commerce international", "ar": "التجارة الدولية", "en": "International trade"},
    "pw_data": {"fr": "Données et systèmes d'information", "ar": "البيانات ونظم المعلومات", "en": "Data and information systems"},
    "pw_other": {"fr": "Parcours à explorer", "ar": "مسار للاستكشاف", "en": "Path to explore"},

    "fpref_uni": {"fr": "Université (licence)", "ar": "الجامعة (إجازة)", "en": "University (bachelor)"},
    "fpref_grande_ecole": {"fr": "Grande école / école de gestion", "ar": "مدرسة كبرى / مدرسة التدبير", "en": "Grand école / business school"},
    "fpref_engineer": {"fr": "École d'ingénieurs", "ar": "مدرسة الهندسة", "en": "Engineering school"},
    "fpref_short": {"fr": "Formation courte et professionnalisante", "ar": "تكوين قصير مهني", "en": "Short professional training"},
    "fpref_open": {"fr": "Je reste ouvert(e)", "ar": "أنا منفتح(ة)", "en": "I'm open to anything"},

    "geo_home": {"fr": "Rester dans ma ville", "ar": "البقاء في مدينتي", "en": "Stay in my city"},
    "geo_big_city": {"fr": "Grandes villes (Casablanca, Rabat…)", "ar": "المدن الكبرى (الدار البيضاء، الرباط…)", "en": "Big cities (Casablanca, Rabat…)"},
    "geo_region": {"fr": "Rester dans ma région", "ar": "البقاء في مناطقي", "en": "Stay in my region"},
    "geo_anywhere": {"fr": "Partout au Maroc", "ar": "أي مكان في المغرب", "en": "Anywhere in Morocco"},
    "geo_abroad": {"fr": "Étudier à l'étranger ensuite", "ar": "الدراسة بالخارج لاحقاً", "en": "Studying abroad later"},

    # ---------------------------------------------------------------- Écoles
    "sch_title": {"fr": "Catalogue des écoles et formations", "ar": "كتالوج المدارس والتكوينات", "en": "Schools and programs catalog"},
    "sch_intro": {
        "fr": "Recherche et filtre les formations référencées. Chaque fiche indique son statut de vérification : aucune donnée non confirmée n'est présentée comme officielle.",
        "ar": "ابحث وصفِّ التكوينات المسجلة. كل ملف يوضح حالة التحقق: أي بيانات غير مؤكدة لا تُقدَّمة كرسمية.",
        "en": "Search and filter listed programs. Each sheet shows its verification status: no unconfirmed data is presented as official.",
    },
    "sch_search": {"fr": "Nom de l'école ou de la formation", "ar": "اسم المدرسة أو التكوين", "en": "School or program name"},
    "sch_filter_city": {"fr": "Ville", "ar": "المدينة", "en": "City"},
    "sch_filter_domain": {"fr": "Domaine", "ar": "المجال", "en": "Field"},
    "sch_filter_degree": {"fr": "Type de diplôme", "ar": "نوع الشهادة", "en": "Degree type"},
    "sch_filter_series": {"fr": "Série du bac admissible (si vérifiée)", "ar": "شعبة البكالوريا المقبولة (إن تحقق)", "en": "Admitted bac track (if verified)"},
    "sch_filter_type": {"fr": "Type d'établissement", "ar": "نوع المؤسسة", "en": "Institution type"},
    "sch_results": {"fr": "{count} résultat(s)", "ar": "{count} نتيجة", "en": "{count} result(s)"},
    "sch_no_result": {"fr": "Aucun résultat avec ces filtres. Élargis la recherche.", "ar": "لا نتائج بهذه المرشحات. وسّع البحث.", "en": "No results with these filters. Broaden your search."},
    "sch_all": {"fr": "Toutes", "ar": "الكل", "en": "All"},
    "sch_back_list": {"fr": "← Retour au catalogue", "ar": "← رجوع إلى الكتالوج", "en": "← Back to catalog"},
    "sch_programs": {"fr": "Formations proposées", "ar": "التكوينات المقدمة", "en": "Programs offered"},
    "sch_program_fees": {"fr": "Frais de formation", "ar": "رسوم التكوين", "en": "Tuition fees"},
    "sch_program_duration": {"fr": "Durée", "ar": "المدة", "en": "Duration"},
    "sch_program_language": {"fr": "Langue d'enseignement", "ar": "لغة التدريس", "en": "Teaching language"},
    "sch_admission": {"fr": "Conditions d'accès et concours", "ar": "شروط الدخول والمباريات", "en": "Entry conditions and exams"},
    "sch_no_admission": {"fr": "Aucun critère publié. Contacte l'établissement ou vérifie sur son site officiel.", "ar": "لا معيار منشور. اتصل بالمؤسسة أو تحقق من موقعها الرسمي.", "en": "No published criteria. Contact the institution or check its official website."},
    "sch_deadlines": {"fr": "Échéances", "ar": "المواعيد", "en": "Deadlines"},
    "sch_no_deadline": {"fr": "Aucune échéance confirmée pour le moment.", "ar": "لا موعد مؤكد حالياً.", "en": "No confirmed deadline at the moment."},
    "sch_years": {"fr": "{years} an(s)", "ar": "{years} سنة", "en": "{years} year(s)"},
    "sch_fees_value": {"fr": "{amount} MAD", "ar": "{amount} درهم", "en": "{amount} MAD"},
    "sch_demo_banner": {
        "fr": "Données de démonstration : les critères, dates et frais ne sont pas renseignés volontairement, faute de source vérifiée.",
        "ar": "بيانات تجريبية: لم تُملأ المعايير والتواريخ والرسوم عمداً لعدم وجود مصدر موثق.",
        "en": "Demo data: criteria, dates and fees are intentionally left blank for lack of a verified source.",
    },
    "sch_criteria_series": {"fr": "Séries acceptées", "ar": "الشعب المقبولة", "en": "Accepted tracks"},
    "sch_criteria_average": {"fr": "Moyenne minimale", "ar": "الحد الأدنى للمعدل", "en": "Minimum average"},
    "sch_criteria_exam": {"fr": "Type de concours", "ar": "نوع المباراة", "en": "Exam type"},
    "sch_criteria_other": {"fr": "Autre critère", "ar": "معيار آخر", "en": "Other criterion"},
    "sch_criteria_required": {"fr": "Obligatoire", "ar": "إلزامي", "en": "Required"},
    "sch_criteria_optional": {"fr": "Facultatif", "ar": "اختياري", "en": "Optional"},
    "sch_series_list": {"fr": "Séries du bac admissibles", "ar": "شعب البكالوريا المقبولة", "en": "Admitted bac tracks"},
    "sch_series_filter_note": {
        "fr": "Ce filtre ne porte que sur les formations dont les séries admissibles sont vérifiées.",
        "ar": "هذا المرشح يشمل فقط التكوينات التي تحقق شعبها المقبولة.",
        "en": "This filter only covers programs whose admitted tracks are verified.",
    },

    # ------------------------------------------------------------ Préparation
    "prep_title": {"fr": "Préparation aux concours", "ar": "تحضير للمباريات", "en": "Entrance exam preparation"},
    "prep_intro": {
        "fr": "Fiches de révision et QCM interactifs : choix d'une réponse, validation, correction expliquée, score et historique.",
        "ar": "بطاقات مراجعة وأسئلة تفاعلية: اختيار، تأكيد، تصحيح موضح، نقاط وتاريخ.",
        "en": "Revision sheets and interactive quizzes: pick an answer, validate, read the explained correction, get a score and history.",
    },
    "prep_sheets": {"fr": "Fiches de révision", "ar": "بطاقات المراجعة", "en": "Revision sheets"},
    "prep_quizzes": {"fr": "QCM par matière", "ar": "اختبارات حسب المادة", "en": "Quizzes by subject"},
    "prep_no_quiz": {"fr": "Aucun QCM disponible pour l'instant.", "ar": "لا اختبار متاح حالياً.", "en": "No quiz available yet."},
    "prep_start": {"fr": "Commencer ce QCM", "ar": "ابدأ هذا الاختبار", "en": "Start this quiz"},
    "prep_question_of": {"fr": "Question {current} / {total}", "ar": "السؤال {current} / {total}", "en": "Question {current} / {total}"},
    "prep_validate": {"fr": "Valider la réponse", "ar": "تأكيد الإجابة", "en": "Validate answer"},
    "prep_correct": {"fr": "Bonne réponse", "ar": "إجابة صحيحة", "en": "Correct answer"},
    "prep_incorrect": {"fr": "Mauvaise réponse", "ar": "إجابة خاطئة", "en": "Incorrect answer"},
    "prep_explanation": {"fr": "Explication", "ar": "الشرح", "en": "Explanation"},
    "prep_next": {"fr": "Question suivante", "ar": "السؤال التالي", "en": "Next question"},
    "prep_finish": {"fr": "Voir mon score", "ar": "عرض نتيجتي", "en": "See my score"},
    "prep_score": {"fr": "Score : {score} / {total} ({pct} %)", "ar": "النتيجة: {score} / {total} ({pct} %)", "en": "Score: {score} / {total} ({pct} %)"},
    "prep_history": {"fr": "Historique des tentatives", "ar": "سجل المحاولات", "en": "Attempt history"},
    "prep_no_history": {"fr": "Aucune tentative enregistrée pour l'instant.", "ar": "لا محاولة مسجلة بعد.", "en": "No attempt recorded yet."},
    "prep_progress": {"fr": "Progression par matière", "ar": "التقدم حسب المادة", "en": "Progress by subject"},
    "prep_best": {"fr": "Meilleur score", "ar": "أفضل نتيجة", "en": "Best score"},
    "prep_attempts_count": {"fr": "Tentatives", "ar": "محاولات", "en": "Attempts"},
    "prep_demo_notice": {
        "fr": "Questions originales de démonstration : elles ne constituent pas des sujets officiels de concours.",
        "ar": "أسئلة أصلية تجريبية: ليست مواضيع مباريات رسمية.",
        "en": "Original demo questions: these are not official entrance exam papers.",
    },
    "prep_provenance": {"fr": "Provenance", "ar": "المصدر", "en": "Provenance"},
    "prep_col_score": {"fr": "Score", "ar": "النتيجة", "en": "Score"},
    "prep_difficulty": {"fr": "Difficulté", "ar": "الصعوبة", "en": "Difficulty"},
    "prep_leave_warning": {"fr": "La tentative en cours n'est pas enregistrée tant qu'elle n'est pas terminée.", "ar": "المحاولة الجارية غير مسجَّلة ما لم تكتمل.", "en": "The current attempt is not saved until it is finished."},
    "prep_login_required": {"fr": "Connecte-toi pour enregistrer tes scores et ton historique.", "ar": "سجّل الدخول لحفظ نتائجك وسجلك.", "en": "Log in to save your scores and history."},

    # ------------------------------------------------------ Favoris / dates
    "fav_title": {"fr": "Mes favoris et échéances", "ar": "المفضلة والمواعيد لدي", "en": "My favorites and deadlines"},
    "fav_intro": {
        "fr": "Garde un œil sur les écoles et formations qui t'intéressent, et sur les dates confirmées.",
        "ar": "تابع المدارس والتكوينات التي تهمك والتواريخ المؤكدة.",
        "en": "Keep an eye on the schools and programs you care about, and on confirmed dates.",
    },
    "fav_schools": {"fr": "Écoles favorites", "ar": "المدارس المفضلة", "en": "Favorite schools"},
    "fav_programs": {"fr": "Formations favorites", "ar": "التكوينات المفضلة", "en": "Favorite programs"},
    "fav_empty": {"fr": "Aucun favori pour l'instant. Ajoute une école depuis le catalogue.", "ar": "لا مفضلة بعد. أضف مدرسة من الكتالوج.", "en": "No favorites yet. Add a school from the catalog."},
    "dl_title": {"fr": "Échéances", "ar": "المواعيد", "en": "Deadlines"},
    "dl_confirmed": {"fr": "Dates confirmées (source vérifiée)", "ar": "تواريخ مؤكدة (مصدر موثق)", "en": "Confirmed dates (verified source)"},
    "dl_unconfirmed": {"fr": "Dates non vérifiées", "ar": "تواريخ غير موثقة", "en": "Unverified dates"},
    "dl_none_confirmed": {"fr": "Aucune échéance confirmée. Nous n'affichons jamais de date sans source.", "ar": "لا موعد مؤكد. لا نعرض تاريخاً بلا مصدر.", "en": "No confirmed deadline. We never show a date without a source."},
    "dl_date_unknown": {"fr": "Date non communiquée", "ar": "التاريخ غير معلن", "en": "Date not published"},
    "dl_type_candidature": {"fr": "Candidature", "ar": "ترشيح", "en": "Application"},
    "dl_type_concours": {"fr": "Concours", "ar": "مباراة", "en": "Exam"},
    "dl_type_resultat": {"fr": "Résultats", "ar": "النتائج", "en": "Results"},
    "dl_type_autre": {"fr": "Autre", "ar": "أخرى", "en": "Other"},
    "dl_reminder_note": {
        "fr": "MVP : rappels visuels uniquement — aucun e-mail ni notification mobile n'est envoyé.",
        "ar": "نموذج أولي: تنبيهات بصرية فقط — لا رسائل بريد ولا إشعارات هاتف.",
        "en": "MVP: visual reminders only — no email or mobile notifications are sent.",
    },

    # -------------------------------------------------------- Tableau de bord
    "dash_title": {"fr": "Tableau de bord", "ar": "لوحة التحكم", "en": "Dashboard"},
    "dash_welcome": {"fr": "Bonjour {name}, bienvenue sur NextStep Maroc.", "ar": "مرحباً {name}، أهلاً بك في NextStep Maroc.", "en": "Hello {name}, welcome to NextStep Maroc."},
    "dash_login_required": {"fr": "Connecte-toi pour voir ton tableau de bord personnel.", "ar": "سجّل الدخول لعرض لوحة تحكمك.", "en": "Log in to see your personal dashboard."},
    "dash_guest_title": {"fr": "Bienvenue sur NextStep Maroc", "ar": "أهلاً بك في NextStep Maroc", "en": "Welcome to NextStep Maroc"},
    "dash_guest_text": {
        "fr": "Crée un compte gratuit pour retrouver ton profil, tes favoris, tes scores et tes résultats d'orientation.",
        "ar": "أنشئ حساباً مجانياً للاحتفاظ بملفك ومفضلتك ونتائجك ونتائج التوجيه.",
        "en": "Create a free account to keep your profile, favorites, scores and orientation results.",
    },
    "dash_profile": {"fr": "Profil scolaire", "ar": "الملف الدراسي", "en": "School profile"},
    "dash_profile_empty": {"fr": "Profil à compléter — aucune information renseignée.", "ar": "ملف غير مكتمل — لا معلومات.", "en": "Profile to complete — no information filled in."},
    "dash_favorites": {"fr": "Écoles favorites", "ar": "المدارس المفضلة", "en": "Favorite schools"},
    "dash_activity": {"fr": "Dernières activités", "ar": "آخر الأنشطة", "en": "Recent activity"},
    "dash_no_activity": {"fr": "Aucune activité enregistrée.", "ar": "لا نشاط مسجل.", "en": "No activity recorded."},
    "dash_quiz_progress": {"fr": "Progression dans les QCM", "ar": "التقدم في الاختبارات", "en": "Quiz progress"},
    "dash_orientation_results": {"fr": "Résultats du test d'orientation", "ar": "نتائج اختبار التوجيه", "en": "Orientation test results"},
    "dash_no_orientation": {"fr": "Tu n'as pas encore fait le test d'orientation.", "ar": "لم تجتز اختبار التوجيه بعد.", "en": "You have not taken the orientation test yet."},
    "dash_deadlines": {"fr": "Prochaines échéances confirmées", "ar": "المواعيد المؤكدة القادمة", "en": "Next confirmed deadlines"},
    "dash_recommendations": {"fr": "Recommandations de formations", "ar": "توصيات التكوينات", "en": "Program recommendations"},
    "dash_shortcuts": {"fr": "Raccourcis", "ar": "اختصارات", "en": "Shortcuts"},
    "dash_take_quiz": {"fr": "Faire le test d'orientation", "ar": "اجتز اختبار التوجيه", "en": "Take the orientation test"},
    "dash_browse_schools": {"fr": "Explorer les écoles", "ar": "استكشف المدارس", "en": "Browse schools"},
    "dash_prepare": {"fr": "Réviser les QCM", "ar": "راجع الاختبارات", "en": "Review quizzes"},
    "dash_edit_profile": {"fr": "Compléter mon profil", "ar": "أكمل ملفي", "en": "Complete my profile"},

    # ------------------------------------------------------------ Ressources
    "res_title": {"fr": "Ressources communautaires", "ar": "موارد المجتمع", "en": "Community resources"},
    "res_submit": {"fr": "Proposer une ressource", "ar": "اقترح مورداً", "en": "Submit a resource"},
    "res_intro": {
        "fr": "Toute ressource soumise est examinée par un modérateur : rien n'est publié automatiquement.",
        "ar": "كل مورد مقترح يخضع لمراجعة المشرف: لا شيء يُنشر تلقائياً.",
        "en": "Every submitted resource is reviewed by a moderator: nothing is published automatically.",
    },
    "res_pending_notice": {
        "fr": "Merci ! Ta ressource a été envoyée et sera examinée par un modérateur.",
        "ar": "شكراً! أُرسل موردك وسيُراجَع من طرف المشرف.",
        "en": "Thanks! Your resource has been sent and will be reviewed by a moderator.",
    },
    "res_report_notice": {"fr": "Signalement enregistré. Merci.", "ar": "تم تسجيل الإبلاغ. شكراً.", "en": "Report recorded. Thank you."},
    "res_status_draft": {"fr": "Brouillon", "ar": "مسودة", "en": "Draft"},
    "res_status_pending": {"fr": "En attente", "ar": "في الانتظار", "en": "Pending"},
    "res_status_published": {"fr": "Publié", "ar": "منشور", "en": "Published"},
    "res_status_rejected": {"fr": "Rejeté", "ar": "مرفوض", "en": "Rejected"},
    "res_status_to_revise": {"fr": "À réviser", "ar": "يحتاج مراجعة", "en": "To revise"},
    "res_status_archived": {"fr": "Archivé", "ar": "مؤرشف", "en": "Archived"},
    "res_label_title": {"fr": "Titre", "ar": "العنوان", "en": "Title"},
    "res_label_description": {"fr": "Description", "ar": "الوصف", "en": "Description"},
    "res_label_category": {"fr": "Catégorie", "ar": "الفئة", "en": "Category"},
    "res_label_author": {"fr": "Auteur", "ar": "المؤلف", "en": "Author"},
    "res_label_source": {"fr": "Source / provenance", "ar": "المصدر", "en": "Source / provenance"},
    "res_label_submitted_at": {"fr": "Soumis le", "ar": "تاريخ الإرسال", "en": "Submitted on"},
    "res_empty": {"fr": "Aucune ressource publiée pour l'instant.", "ar": "لا مورد منشور حالياً.", "en": "No published resource yet."},
    "res_report_title": {"fr": "Motif du signalement", "ar": "سبب الإبلاغ", "en": "Reason for reporting"},

    # ---------------------------------------------------------- Administration
    "adm_title": {"fr": "Administration", "ar": "الإدارة", "en": "Administration"},
    "adm_access_denied": {"fr": "Accès réservé aux modérateurs et administrateurs.", "ar": "الوصول مخصص للمشرفين والمديرين.", "en": "Access restricted to moderators and administrators."},
    "adm_stats": {"fr": "Statistiques réelles", "ar": "إحصائيات حقيقية", "en": "Real statistics"},
    "adm_users": {"fr": "Utilisateurs", "ar": "المستخدمون", "en": "Users"},
    "adm_schools": {"fr": "Écoles", "ar": "المدارس", "en": "Schools"},
    "adm_programs": {"fr": "Formations", "ar": "التكوينات", "en": "Programs"},
    "adm_rules": {"fr": "Critères d'admission", "ar": "شروط القبول", "en": "Admission criteria"},
    "adm_deadlines": {"fr": "Échéances", "ar": "المواعيد", "en": "Deadlines"},
    "adm_quizzes": {"fr": "QCM", "ar": "الاختبارات", "en": "Quizzes"},
    "adm_questions": {"fr": "Questions", "ar": "الأسئلة", "en": "Questions"},
    "adm_resources": {"fr": "Ressources", "ar": "الموارد", "en": "Resources"},
    "adm_reports": {"fr": "Signalements", "ar": "الإبلاغات", "en": "Reports"},
    "adm_audit": {"fr": "Journal d'audit", "ar": "سجل التدقيق", "en": "Audit log"},
    "adm_only_admin": {"fr": "Action réservée aux administrateurs.", "ar": "إجراء مخصص للإدارات.", "en": "Action restricted to administrators."},
    "adm_user_role_updated": {"fr": "Rôle mis à jour.", "ar": "تم تحديث الدور.", "en": "Role updated."},
    "adm_user_state_updated": {"fr": "État du compte mis à jour.", "ar": "تم تحديث حالة الحساب.", "en": "Account state updated."},
    "adm_created": {"fr": "Élément créé.", "ar": "تم إنشاء العنصر.", "en": "Item created."},
    "adm_updated": {"fr": "Élément mis à jour.", "ar": "تم تحديث العنصر.", "en": "Item updated."},
    "adm_deactivated": {"fr": "Élément désactivé.", "ar": "تم تعطيل العنصر.", "en": "Item deactivated."},
    "adm_status_updated": {"fr": "Statut de la ressource mis à jour.", "ar": "تم تحديث حالة المورد.", "en": "Resource status updated."},
    "adm_report_updated": {"fr": "Signalement traité.", "ar": "تمت معالجة الإبلاغ.", "en": "Report processed."},
    "adm_col_user": {"fr": "Utilisateur", "ar": "المستخدم", "en": "User"},
    "adm_col_email": {"fr": "E-mail", "ar": "البريد", "en": "Email"},
    "adm_col_state": {"fr": "État", "ar": "الحالة", "en": "State"},
    "adm_col_active": {"fr": "Actif", "ar": "نشط", "en": "Active"},
    "adm_col_inactive": {"fr": "Désactivé", "ar": "معطل", "en": "Disabled"},
    "adm_col_date": {"fr": "Date", "ar": "التاريخ", "en": "Date"},
    "adm_col_action": {"fr": "Action", "ar": "الإجراء", "en": "Action"},
    "adm_col_actor": {"fr": "Auteur", "ar": "المنفذ", "en": "Actor"},
    "adm_col_detail": {"fr": "Détail", "ar": "التفاصيل", "en": "Detail"},
    "adm_audit_empty": {"fr": "Aucun journal pour le moment.", "ar": "لا سجل حالياً.", "en": "No log entries yet."},
    "adm_report_reason": {"fr": "Motif", "ar": "السبب", "en": "Reason"},
    "adm_report_open": {"fr": "Ouvert", "ar": "مفتوح", "en": "Open"},
    "adm_report_resolved": {"fr": "Traité", "ar": "معالَج", "en": "Resolved"},
    "adm_report_dismissed": {"fr": "Écarté", "ar": "مرفوض", "en": "Dismissed"},
    "adm_resolve": {"fr": "Marquer traité", "ar": "وضع كمعالَج", "en": "Mark resolved"},
    "adm_dismiss": {"fr": "Écarter", "ar": "تجاهل", "en": "Dismiss"},
    "adm_form_school_name": {"fr": "Nom de l'établissement", "ar": "اسم المؤسسة", "en": "Institution name"},
    "adm_form_program_school": {"fr": "Établissement", "ar": "المؤسسة", "en": "Institution"},
    "adm_form_program_name": {"fr": "Nom de la formation", "ar": "اسم التكوين", "en": "Program name"},
    "adm_form_rule_program": {"fr": "Formation concernée", "ar": "التكوين المعني", "en": "Concerned program"},
    "adm_form_deadline_title": {"fr": "Intitulé de l'échéance", "ar": "عنوان الموعد", "en": "Deadline title"},
    "adm_form_deadline_date": {"fr": "Date (AAAA-MM-JJ, laisser vide si inconnue)", "ar": "التاريخ (سنة-شهر-يوم، اتركه فارغاً إن غير معروف)", "en": "Date (YYYY-MM-DD, leave empty if unknown)"},
    "adm_form_quiz_title": {"fr": "Titre du QCM", "ar": "عنوان الاختبار", "en": "Quiz title"},
    "adm_form_quiz_subject": {"fr": "Matière", "ar": "المادة", "en": "Subject"},
    "adm_form_question": {"fr": "Énoncé de la question", "ar": "نص السؤال", "en": "Question statement"},
    "adm_form_options": {"fr": "Propositions (une par ligne)", "ar": "الاقتراحات (سطر لكل اقتراح)", "en": "Options (one per line)"},
    "adm_form_correct": {"fr": "Numéro de la bonne réponse (1 = première)", "ar": "رقم الإجابة الصحيحة (1 = الأولى)", "en": "Correct answer number (1 = first)"},
    "adm_form_explanation": {"fr": "Explication affichée après validation", "ar": "الشرح المعروض بعد التأكيد", "en": "Explanation shown after validation"},
    "adm_form_verification": {"fr": "Statut de vérification", "ar": "حالة التحقق", "en": "Verification status"},
    "adm_only_official_allowed": {
        "fr": "Seul un administrateur peut déclarer une information « Officiel vérifié ».",
        "ar": "فقط المدير يمكنه تعيين معلومة كـ «رسمي مُتحقق منه».",
        "en": "Only an administrator may mark information as “Officially verified”.",
    },
    "adm_save_failed": {"fr": "Enregistrement impossible : vérifiez les champs.", "ar": "تعذر الحذف: راجع الحقول.", "en": "Could not save: check the fields."},
    "adm_select_placeholder": {"fr": "— Sélectionner —", "ar": "— اختر —", "en": "— Select —"},
    "adm_deactivate": {"fr": "Désactiver", "ar": "تعطيل", "en": "Deactivate"},
    "adm_activate": {"fr": "Réactiver", "ar": "إعادة التفعيل", "en": "Reactivate"},

    # ------------------------------------------------------ Mentions / footer
    "footer_about_t": {"fr": "À propos", "ar": "حول المنصة", "en": "About"},
    "footer_about_d": {
        "fr": "NextStep Maroc est une plateforme gratuite d'orientation et de préparation aux concours, destinée aux bacheliers marocains.",
        "ar": "NextStep Maroc منصة مجانية للتوجيه والتحضير للمباريات موجهة للبكالوريين المغاربة.",
        "en": "NextStep Maroc is a free orientation and exam-preparation platform for Moroccan bac graduates.",
    },
    "footer_sources_t": {"fr": "Sources et vérification", "ar": "المصادر والتحقق", "en": "Sources and verification"},
    "footer_sources_d": {
        "fr": "Chaque information affiche sa source, sa date de vérification et son statut. Ce qui n'est pas confirmé est marqué « Information à vérifier ».",
        "ar": "كل معلومة تعرض مصدرها وتاريخ التحقق وحالتها. ما لا يُؤكد يُعلَّم «معلومات بانتظار التحقق».",
        "en": "Each piece of information shows its source, verification date and status. Anything unconfirmed is marked “Information to be verified”.",
    },
    "footer_privacy_t": {"fr": "Confidentialité", "ar": "الخصوصية", "en": "Privacy"},
    "footer_privacy_d": {
        "fr": "Données collectées minimales, mots de passe hachés avec bcrypt, aucun revente de données. Politique conforme à la loi 09-08 (CNDP) à publier avant le lancement public.",
        "ar": "بيانات الحد الأدنى، كلمات السر مشفّرة بـ bcrypt، لا بيع للبيانات. سيُنشر إشعار متوافق مع القانون 09-08 قبل الإطلاق.",
        "en": "Minimal data collection, bcrypt-hashed passwords, no data resale. A policy compliant with law 09-08 (CNDP) to be published before public launch.",
    },
    "footer_terms_t": {"fr": "Conditions d'utilisation", "ar": "شروط الاستعمال", "en": "Terms of use"},
    "footer_terms_d": {
        "fr": "Service gratuit fourni à titre d'aide à la décision : il ne remplace ni les conseils d'orientation officiels ni les publications des établissements.",
        "ar": "خدمة مجانية لمساعدة القرار: لا تغني عن التوجيه الرسمي ولا عن بيانات المؤسسات.",
        "en": "A free decision-support service: it replaces neither official guidance nor institutions' publications.",
    },
    "footer_no_partnership": {
        "fr": "Les établissements cités sont référencés à titre informatif : aucune collaboration ni partenariat officiel n'est revendiqué.",
        "ar": "المؤسسات المذكورة للإعلام فقط: لا شراكة رسمية مُستساغة.",
        "en": "Institutions listed for information only: no official collaboration or partnership is claimed.",
    },
    "footer_copyright": {
        "fr": "© {year} NextStep Maroc — Projet MVP, contenu de démonstration.",
        "ar": "© {year} NextStep Maroc — نموذج أولي بمحتوى تجريبي.",
        "en": "© {year} NextStep Maroc — MVP project, demo content.",
    },
}


def action_label(action: Optional[str], lang: str = DEFAULT_LANGUAGE) -> str:
    """Libellé traduit d'une action d'audit (retourne l'action brute sinon)."""
    entry = ACTION_LABELS.get(action or "")
    if not entry:
        return action or "—"
    return entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or (action or "—")


# Libellés des actions journalisées (audit + activités du tableau de bord).
ACTION_LABELS: dict[str, dict[str, str]] = {
    "user.register": {"fr": "Création de compte", "ar": "إنشاء حساب", "en": "Account created"},
    "user.login": {"fr": "Connexion", "ar": "تسجيل الدخول", "en": "Logged in"},
    "user.password_changed": {"fr": "Mot de passe modifié", "ar": "تغيير كلمة السر", "en": "Password changed"},
    "user.role_change": {"fr": "Rôle modifié", "ar": "تغيير الدور", "en": "Role changed"},
    "user.activate": {"fr": "Compte réactivé", "ar": "إعادة تفعيل الحساب", "en": "Account reactivated"},
    "user.deactivate": {"fr": "Compte désactivé", "ar": "تعطيل الحساب", "en": "Account disabled"},
    "user.data_deleted": {"fr": "Données personnelles supprimées", "ar": "حذف البيانات الشخصية", "en": "Personal data deleted"},
    "profile.update": {"fr": "Profil mis à jour", "ar": "تحديث الملف", "en": "Profile updated"},
    "favorite.add": {"fr": "Favori ajouté", "ar": "إضافة مفضلة", "en": "Favorite added"},
    "favorite.remove": {"fr": "Favori retiré", "ar": "إزالة مفضلة", "en": "Favorite removed"},
    "quiz.attempt": {"fr": "Tentative de QCM enregistrée", "ar": "تسجيل محاولة اختبار", "en": "Quiz attempt saved"},
    "quiz.create": {"fr": "QCM créé", "ar": "إنشاء اختبار", "en": "Quiz created"},
    "quiz.question_create": {"fr": "Question ajoutée", "ar": "إضافة سؤال", "en": "Question added"},
    "orientation.completed": {"fr": "Test d'orientation terminé", "ar": "إتمام اختبار التوجيه", "en": "Orientation test completed"},
    "resource.submitted": {"fr": "Ressource soumise", "ar": "اقتراح مورد", "en": "Resource submitted"},
    "resource.moderated": {"fr": "Ressource modérée", "ar": "إشراف على مورد", "en": "Resource moderated"},
    "resource.reported": {"fr": "Contenu signalé", "ar": "الإبلاغ عن محتوى", "en": "Content reported"},
    "report.resolved": {"fr": "Signalement traité", "ar": "معالجة إبلاغ", "en": "Report processed"},
    "school.create": {"fr": "École créée", "ar": "إنشاء مدرسة", "en": "School created"},
    "school.update": {"fr": "École mise à jour", "ar": "تحديث مدرسة", "en": "School updated"},
    "school.activate": {"fr": "École réactivée", "ar": "إعادة تفعيل مدرسة", "en": "School reactivated"},
    "school.deactivate": {"fr": "École désactivée", "ar": "تعطيل مدرسة", "en": "School deactivated"},
    "program.create": {"fr": "Formation créée", "ar": "إنشاء تكوين", "en": "Program created"},
    "program.activate": {"fr": "Formation réactivée", "ar": "إعادة تفعيل تكوين", "en": "Program reactivated"},
    "program.deactivate": {"fr": "Formation désactivée", "ar": "تعطيل تكوين", "en": "Program deactivated"},
    "rule.create": {"fr": "Critères d'admission ajoutés", "ar": "إضافة شروط القبول", "en": "Admission criteria added"},
    "deadline.create": {"fr": "Échéance ajoutée", "ar": "إضافة موعد", "en": "Deadline added"},
}


def all_keys() -> list[str]:
    """Toutes les clés définies (utilisé par les tests)."""
    return sorted(T)


__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "SERIES_KEYS",
    "T",
    "action_label",
    "all_keys",
    "series_label_key",
    "tr",
]
