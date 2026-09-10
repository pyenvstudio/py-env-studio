## 🛠️ Py-Tonic — Interactive Guidance (Beta)

Py-Tonic is an opt-in interactive guidance system that helps users follow Python environment best practices through contextual advice, scheduled notifications, and small hands-on challenges.rs follow Python environment best practices through contextual advice, scheduled notifications, and small hands-on challenges.

Key capabilities:
- Notification modes: daily, weekly, manual (configurable)
- Learning modes: strict and learning- Learning modes: strict and learning
- Topic-driven hints and challenges (core_python, python_django)opic-driven hints and challenges (core_python, python_django)
- Persistent per-user profile at ~/.py_env_studio/py_tonic_profile.json- Persistent per-user profile at ~/.py_env_studio/py_tonic_profile.json
- Smart scheduling (first-time notify, daily/weekly cadence)me notify, daily/weekly cadence)
- Challenge bank with hints and automated answer evaluation- Challenge bank with hints and automated answer evaluation
- Action-specific advice for operations (create_env, install_package, rename_env, delete_env, activate_env, import/export requirements, etc.)ice for operations (create_env, install_package, rename_env, delete_env, activate_env, import/export requirements, etc.)
- Programmatic API: get_py_tonic_advice(action), get_random_challenge(profile), evaluate_challenge_answer(...)advice(action), get_random_challenge(profile), evaluate_challenge_answer(...)
- Mark notifications as sent via mark_notified(profile) and profile sanitization/save routinesrk_notified(profile) and profile sanitization/save routines
