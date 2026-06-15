"""Configuracion de pytest para los tests de NiceGUI (framework de testing)."""

# Usamos solo el plugin de usuario simulado (el plugin completo requiere selenium).
pytest_plugins = ["nicegui.testing.user_plugin"]
