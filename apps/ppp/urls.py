from django.urls import path
from django.views.generic import RedirectView

from ppp.views import AddPPPRegistrationProtocolView, SavedPPPRegistrationProtocolListView, \
    EditPPPRegistrationProtocolView, PendingPPPRegistrationProtocolListView, PPPRegistrationProtocolListView, \
    PdfVersionView, DownloadListInExcelView

urlpatterns = [
    path('registration-protocol/add/', AddPPPRegistrationProtocolView.as_view(), name='add_ppp_registration_protocol'),
    path('registration-protocol/<int:pk>/edit/', EditPPPRegistrationProtocolView.as_view(), name='edit_ppp_registration_protocol'),
    path('registration-protocols/saved-list/', SavedPPPRegistrationProtocolListView.as_view(), name='saved_ppp_registration_protocols_list'),
    path('registration-protocols/pending-list/', PendingPPPRegistrationProtocolListView.as_view(), name='pending_ppp_registration_protocols_list'),
    path('registration-protocols/list/', PPPRegistrationProtocolListView.as_view(), name='ppp_registration_protocols_list'),
    path('registration-protocols/<slug:number>/pdf/', PdfVersionView.as_view(), name='pdf_of_ppp_registration_protocol'),
    path('registration-protocols/download-in-excel/', DownloadListInExcelView.as_view(), name='ppp_registration_protocol_download_in_excel'),
]
