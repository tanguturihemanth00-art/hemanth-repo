"""
pages/__init__.py
"""
from pages.base_page import BasePage
from pages.login_page import LoginPage
from pages.navigation_page import NavigationPage
from pages.workflow_page import WorkflowPage

__all__ = ["BasePage", "LoginPage", "NavigationPage", "WorkflowPage"]
