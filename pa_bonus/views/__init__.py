"""
View package for pa_bonus.

Views are organised by audience in the submodules below. This module re-exports
them so that both access styles work:

    from pa_bonus.views import views_managers as vm   # used by bonus/urls.py
    from pa_bonus.views import upload_file            # flat access

The flat names were the original public API back when views lived in a single
pa_bonus/views.py module. Keeping them exported means callers written against
that layout - the test suite among them - keep working after the split.
"""

from pa_bonus.views.views_managers import (
    BatchSaveRewardRequestsView,
    ClientCreateView,
    ClientDetailView,
    ClientListView,
    EnhancedRewardRequestListView,
    ExportTelemarketingFileView,
    GoalEvaluationView,
    GoalsOverviewView,
    ManagerDashboardView,
    ManagerRewardRequestDetailView,
    ManagerRewardRequestListView,
    RewardRequestQuickEditView,
    SMSExportView,
    SubmitToAbraView,
    TransactionApprovalView,
    UnpaidInvoicesCheckView,
    UploadHistoryView,
    UserActivityDashboardView,
    upload_file,
    upload_stock,
)
from pa_bonus.views.views_public import PublicCatalogueView
from pa_bonus.views.views_reports import (
    ReportDownloadView,
    ReportsHubView,
)
from pa_bonus.views.views_salesreps import (
    SalesRepClientDetailView,
    SalesRepClientListView,
    SalesRepCreateRewardRequestView,
    SalesRepDashboardView,
    SalesRepPointExpirationView,
    SalesRepRewardRequestsView,
    get_rep_clients,
    get_rep_regions,
)
from pa_bonus.views.views_users import (
    DashboardView,
    ExtraGoalsDetailView,
    HistoryDetailView,
    HistoryView,
    PointExpirationView,
    RequestsDetailView,
    RewardsRequestConfirmationView,
    RewardsRequestsView,
    RewardsView,
)

__all__ = [
    # views_managers
    'BatchSaveRewardRequestsView',
    'ClientCreateView',
    'ClientDetailView',
    'ClientListView',
    'EnhancedRewardRequestListView',
    'ExportTelemarketingFileView',
    'GoalEvaluationView',
    'GoalsOverviewView',
    'ManagerDashboardView',
    'ManagerRewardRequestDetailView',
    'ManagerRewardRequestListView',
    'RewardRequestQuickEditView',
    'SMSExportView',
    'SubmitToAbraView',
    'TransactionApprovalView',
    'UnpaidInvoicesCheckView',
    'UploadHistoryView',
    'UserActivityDashboardView',
    'upload_file',
    'upload_stock',
    # views_public
    'PublicCatalogueView',
    # views_reports
    'ReportDownloadView',
    'ReportsHubView',
    # views_salesreps
    'SalesRepClientDetailView',
    'SalesRepClientListView',
    'SalesRepCreateRewardRequestView',
    'SalesRepDashboardView',
    'SalesRepPointExpirationView',
    'SalesRepRewardRequestsView',
    'get_rep_clients',
    'get_rep_regions',
    # views_users
    'DashboardView',
    'ExtraGoalsDetailView',
    'HistoryDetailView',
    'HistoryView',
    'PointExpirationView',
    'RequestsDetailView',
    'RewardsRequestConfirmationView',
    'RewardsRequestsView',
    'RewardsView',
]
