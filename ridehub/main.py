import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.uber import auto_setup_database, setup_database


def launch_app(user):
    """Called after successful login. Builds and runs the main application."""
    from ui.main_ui import App
    from modules.module1 import DashboardFrame
    from modules.module2 import RideManagementFrame
    from modules.module3 import UserProfileFrame
    from modules.module4 import RiskAnalysisFrame
    from modules.module5 import AIChatbotFrame
    from modules.settings import SettingsFrame

    frames_config = {
        "Dashboard": DashboardFrame,
        "Rides":     RideManagementFrame,
        "Users":     UserProfileFrame,
        "Risk":      RiskAnalysisFrame,
        "AI":        AIChatbotFrame,
        "Settings":  SettingsFrame,
    }

    app = App(frames_config=frames_config, user=user)
    app.mainloop()


def main():
    # 1. Setup rides table + import CSV if needed
    auto_setup_database()

    # 2. Create admin_users / flagged / suspended tables
    setup_database()

    # 3. Show login window → on success, launch the main app
    from modules.login import LoginWindow

    login = LoginWindow(on_login_success=launch_app)
    login.mainloop()


if __name__ == "__main__":
    main()
